import re
from typing import List, Dict

def parse_trace(trace: str) -> List[Dict]:
    lines = trace.strip().split("\n")
    frames = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r'File "(.+?)", line (\d+), in (\S+)', line)

        if match:
            file, line_num, func = match.groups()
            code_line = lines[i+1].strip() if i+1 < len(lines) else ""
            frames.append({
                "file": file,
                "line": int(line_num),
                "function": func,
                "code": code_line
            })
            i += 2
        else:
            i += 1
        
    return frames



if __name__ == "__main__":
    sample_trace = """
    Traceback (most recent call last):
      File "main.py", line 10, in <module>
        result = divide(5, 0)
      File "main.py", line 6, in divide
        return a / b
    ZeroDivisionError: division by zero
    """

    parsed = parse_trace(sample_trace)
    for frame in parsed:
        print(frame)
