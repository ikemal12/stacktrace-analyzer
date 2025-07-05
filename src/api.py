import graphene
from graphene import ObjectType, String, Int, List, Field
from pipeline import analyze_trace

class TraceLine(graphene.ObjectType):
    file = String()
    line = Int()
    function = String()
    code = String()

class Error(graphene.ObjectType):
    errorType = String()
    message = String()

class FixSuggestion(graphene.ObjectType):
    summary = String()
    codeExample = String()
    references = List(String)

class AnalyzeResult(graphene.ObjectType):
    parsedTrace = List(TraceLine)
    error = Field(Error)
    relatedErrors = List(String)
    fixSuggestion = Field(FixSuggestion)

class Query(ObjectType):
    analyze = Field(AnalyzeResult, trace=String(required=True))

    def resolve_analyze(self, info, trace):
        result = analyze_trace(trace)
        return {
            "parsedTrace": result["parsedTrace"],
            "error": result["error"],
            "relatedErrors": result["relatedErrors"],
            "fixSuggestion": result["fixSuggestion"]
        }

schema = graphene.Schema(query=Query)