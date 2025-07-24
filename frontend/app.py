import streamlit as st
import requests
import json
from datetime import datetime
import time
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

st.set_page_config(
    page_title="Stack Trace Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200, response.json()
    except Exception:
        return False, None

def analyze_trace(trace_text):
    """Send trace to API for analysis"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/analyze",
            json={"trace": trace_text},
            timeout=30
        )
        return response.status_code == 200, response.json()
    except requests.exceptions.Timeout:
        return False, {"error": "Analysis timed out. Please try again."}
    except Exception as e:
        return False, {"error": f"Connection error: {str(e)}"}


st.title("🔍 Stack Trace Analyzer")
st.markdown("""
<div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
    <h3 style="color: white; margin: 0;">AI-Powered Python Error Analysis & Fix Suggestions</h3>
    <p style="color: #f0f0f0; margin: 0;">Paste your Python stack trace below for instant analysis and intelligent fix recommendations.</p>
</div>
""", unsafe_allow_html=True)


api_status, health_data = check_api_health()

if not api_status:
    st.error(f"⚠️ Backend API is not running. Please start the server at `{BACKEND_URL}`")
    st.stop()


with st.sidebar:
    st.header("🔧 System Status")
    if health_data:
        status = health_data.get("status", "unknown")
        if status == "healthy":
            st.success("✅ API: Healthy")
        elif status == "degraded":
            st.warning("⚠️ API: Degraded")
            st.caption("MongoDB unavailable - using file logging")
        else:
            st.error("❌ API: Unhealthy")
        
        deps = health_data.get("dependencies", {})
        st.caption(f"MongoDB: {'✅' if deps.get('mongodb') else '❌'}")
        st.caption(f"Filesystem: {'✅' if deps.get('filesystem') else '❌'}")


col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📝 Enter Your Stack Trace")
    
    sample_traces = {
        "Select a sample...": "",
        "ZeroDivisionError": """Traceback (most recent call last):
  File "calculator.py", line 15, in <module>
    result = divide(10, 0)
  File "calculator.py", line 5, in divide
    return a / b
ZeroDivisionError: division by zero""",
        "IndexError": """Traceback (most recent call last):
  File "list_example.py", line 8, in <module>
    item = my_list[100]
IndexError: list index out of range""",
        "KeyError": """Traceback (most recent call last):
  File "dict_example.py", line 12, in <module>
    value = data['missing_key']
KeyError: 'missing_key'"""
    }
    
    sample_choice = st.selectbox("Try a sample trace:", list(sample_traces.keys()))
    
    trace_input = st.text_area(
        "Stack Trace:",
        value=sample_traces[sample_choice],
        height=200,
        placeholder="""Traceback (most recent call last):
  File "your_script.py", line 10, in <module>
    result = some_function()
  File "your_script.py", line 5, in some_function
    return x / y
ZeroDivisionError: division by zero""",
        help="Paste your complete Python stack trace here. Include the full traceback from 'Traceback (most recent call last):' to the final error message."
    )

with col2:
    st.subheader("⚡ Quick Actions")
    analyze_btn = st.button("🔍 Analyze Trace", type="primary", use_container_width=True)
    clear_btn = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_btn:
        st.rerun()


if analyze_btn:
    if not trace_input.strip():
        st.error("❌ Please enter a stack trace to analyze.")
    else:
        with st.spinner("🤖 Analyzing your stack trace..."):
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            
            success, result = analyze_trace(trace_input)
            progress_bar.empty()
            
            if success:
                st.success("✅ Analysis Complete!")
                
                tab1, tab2, tab3, tab4 = st.tabs(["🐛 Error Analysis", "💡 Fix Suggestion", "📋 Parsed Trace", "🔗 Related Errors"])
                
                with tab1:
                    st.subheader("Error Details")
                    error_info = result.get("error", {})
                    if not isinstance(error_info, dict):
                        error_info = {}
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Error Type", error_info.get("errorType", "Unknown"))
                    with col2:
                        st.metric("Status", "Identified" if error_info.get("errorType") != "Unknown" else "Unknown")
                    
                    if error_info.get("message"):
                        st.info(f"**Message:** {error_info.get('message', 'No message')}")
                
                with tab2:
                    st.subheader("AI Fix Suggestion")
                    fix_info = result.get("fixSuggestion", {})
                    if not isinstance(fix_info, dict):
                        fix_info = {}
                    
                    if fix_info.get("summary"):
                        st.markdown(f"**Summary:** {fix_info.get('summary', 'No summary available')}")
                    
                    if fix_info.get("codeExample"):
                        st.markdown("**Code Example:**")
                        st.code(fix_info.get("codeExample", "No code example"), language="python")
                    
                    if fix_info.get("references"):
                        st.markdown("**References:**")
                        references = fix_info.get("references", [])
                        if isinstance(references, list):
                            for ref in references:
                                if isinstance(ref, dict) and ref.get("url"):
                                    st.markdown(f"- [{ref.get('snippet', 'Reference')}]({ref['url']})")
                                else:
                                    st.markdown(f"- {ref}")
                        else:
                            st.markdown("- No references available")
                
                with tab3:
                    st.subheader("Parsed Stack Trace")
                    parsed_trace = result.get("parsedTrace", [])
                    
                    if parsed_trace and isinstance(parsed_trace, list):
                        for i, frame in enumerate(parsed_trace):
                            if not isinstance(frame, dict):
                                continue
                            with st.expander(f"Frame {i+1}: {frame.get('file', 'Unknown')}:{frame.get('line', '?')}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.text(f"File: {frame.get('file', 'Unknown')}")
                                    st.text(f"Line: {frame.get('line', 'Unknown')}")
                                with col2:
                                    st.text(f"Function: {frame.get('function', 'Unknown')}")
                                
                                if frame.get("code"):
                                    st.code(frame.get("code", "No code available"), language="python")
                    else:
                        st.info("No parsed frames available.")
                
                with tab4:
                    st.subheader("Related Errors")
                    related_errors = result.get("relatedErrors", [])
                    
                    if related_errors and isinstance(related_errors, list):
                        for i, error in enumerate(related_errors[:3]): 
                            if not isinstance(error, dict):
                                continue
                            with st.expander(f"Similar Error {i+1}"):
                                st.code(error.get("snippet", "No snippet available"), language="python")
                                if error.get("sourceType"):
                                    st.caption(f"Source: {error.get('sourceType', 'Unknown')}")
                                if error.get("url"):
                                    st.markdown(f"[Learn more]({error.get('url', '#')})")
                    else:
                        st.info("No related errors found.")
                
                st.subheader("💾 Export Results")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📄 Download as JSON",
                        data=json.dumps(result, indent=2),
                        file_name=f"trace_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                with col2:
                    safe_error_info = error_info if isinstance(error_info, dict) else {}
                    safe_fix_info = fix_info if isinstance(fix_info, dict) else {}
                    
                    text_report = f"""Stack Trace Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ERROR ANALYSIS:
Type: {safe_error_info.get('errorType', 'Unknown')}
Message: {safe_error_info.get('message', 'No message')}

FIX SUGGESTION:
{safe_fix_info.get('summary', 'No fix suggestion available')}

CODE EXAMPLE:
{safe_fix_info.get('codeExample', 'No code example available')}
"""
                    st.download_button(
                        "📝 Download as Text",
                        data=text_report,
                        file_name=f"trace_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
            
            else:
                st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                if "detail" in result:
                    st.error(f"Details: {result['detail']}")


st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Powered by FastAPI + Streamlit | 
    <a href="{BACKEND_URL}/docs" target="_blank">API Docs</a> | 
    <a href="{BACKEND_URL}/health" target="_blank">API Health</a>
    </p>
</div>
""", unsafe_allow_html=True)
