"""
FinStream AI - Root Test Configuration
Ensures the repository root is present in sys.path for test discovery across all platforms.
"""

import sys
from pathlib import Path

# Ensure project root is at the head of sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
