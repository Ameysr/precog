import os
import warnings

warnings.filterwarnings("ignore", category=Warning, module="requests")

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
DEFAULT_COUNT = 15
MAX_PAGES = 10
REQUEST_TIMEOUT = 10

AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
AGENT_TYPE = os.getenv("AGENT_TYPE", "conversational")
AGENT_ADAPTER = os.getenv("AGENT_ADAPTER", "http")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o")
