"""Unmodified AE quantity regression tests."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'frozen'))
sys.path.insert(0,str(Path(__file__).resolve().parent/'reference'))
from numeric_regression import *
