"""Evaluation of the RAG pipeline: python -m eval.run

The evaluation imports the application code (`app.*`) to measure the real pipeline, not a copy.
When run from the repository root, `backend/` is added to the import path; inside the API
container the code is already importable.
"""

import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = EVAL_DIR.parent / "backend"
if _BACKEND_DIR.is_dir() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

PDF_DIR = EVAL_DIR / "pdfs"
DATASET_PATH = EVAL_DIR / "datasets" / "questions.jsonl"
REPORTS_DIR = EVAL_DIR / "reports"
