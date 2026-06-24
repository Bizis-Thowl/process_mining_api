from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from dotenv import load_dotenv
import os

load_dotenv()
PHOENIX_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", None)

def init_phoenix(project_name: str = "tracing-agent"):
    
    PROJECT_NAME = project_name

    tracer_provider = register(
        project_name=PROJECT_NAME,
        endpoint= PHOENIX_ENDPOINT + "v1/traces",
    )
    
    OpenAIInstrumentor().instrument(tracer_provider = tracer_provider)

    tracer = tracer_provider.get_tracer(__name__)
    
    return tracer