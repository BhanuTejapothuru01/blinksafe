"""
SleepGuard — General Helpers
"""

import os


def ensure_dir(path: str):
    """Create directory (and parents) if it doesn't exist."""
    os.makedirs(path, exist_ok=True)
