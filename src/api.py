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

class AnalyzeResult(graphene.ObjectType):
    parsedTrace = List(TraceLine)
    error = Field(Error)

class Query(ObjectType):
    analyze = Field(AnalyzeResult, trace=String(required=True))

    def resolve_analyze(self, info, trace):
        result = analyze_trace(trace)
        return {
            "parsedTrace": result["parsedTrace"],
            "error": result["error"]
        }

schema = graphene.Schema(query=Query)