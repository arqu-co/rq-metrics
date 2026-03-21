"""Shared test fixtures for rq-metrics tests."""

import os
import sys

# Make docs/ and tests/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "docs"))
sys.path.insert(0, os.path.dirname(__file__))
