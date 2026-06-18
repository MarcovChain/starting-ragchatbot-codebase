import sys
import os

# Make backend/ importable from backend/tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
