import os
import warnings

warnings.filterwarnings("ignore", category=Warning, module="requests")

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_COUNT = 60
MAX_PAGES = 10
REQUEST_TIMEOUT = 10
