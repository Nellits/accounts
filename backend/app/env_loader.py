"""Load backend/.env early regardless of CWD."""
from pathlib import Path

from dotenv import load_dotenv

_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV)
