import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WIKI_DIR = DATA_DIR / "wiki"
OUTPUT_DIR = DATA_DIR / "output"

INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
IDEAS_FILE = OUTPUT_DIR / "ideas.md"

ISSUES_FILE = ROOT / "ISSUES.md"

INFRANODUS_DIR = DATA_DIR / "infranodus"
ONTOLOGY_FILE = INFRANODUS_DIR / "wiki-ontology.md"
TODOS_DIR = DATA_DIR / "todos"
GAPS_FILE = TODOS_DIR / "gaps.md"

# TrueFoundry LLM gateway
API_KEY: str = os.environ["TFY_API_KEY"]
BASE_URL: str = os.environ["TFY_BASE_URL"]
MODEL: str = os.getenv("DEFAULT_MODEL", "tfy-ai-anthropic/claude-sonnet-4-6")

MAX_SOURCE_CHARS = 20_000
