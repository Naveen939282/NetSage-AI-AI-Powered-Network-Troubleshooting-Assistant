"""Pytest bootstrap for NetSage-AI.

Makes the project root importable so `import checker`, `import ai`, etc.
work regardless of the directory pytest is launched from.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Default to the offline mock provider for tests (no API key required).
os.environ.setdefault("AI_PROVIDER", "mock")
