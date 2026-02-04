import sys
from pathlib import Path

# repo root = folder that contains "src/" and "tests/"
REPO_ROOT = Path(__file__).resolve().parents[1]

# Allow: import src.core...
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Allow: import tools.exergy_core... (because tools/ is inside src/)
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
