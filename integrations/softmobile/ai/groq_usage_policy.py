"""Operator-controlled development limits for Groq requests only."""
import os
import sys
from pathlib import Path

FLAG = Path("/etc/softmobile/groq-development-unlimited.enabled")

def unlimited_development():
    try:
        meta = FLAG.stat()
        return FLAG.is_file() and meta.st_uid == 0 and meta.st_mode & 0o022 == 0
    except OSError:
        return False

def request_cap(normal):
    if type(normal) is not int or normal < 1:
        raise ValueError("Invalid normal cap")
    return sys.maxsize if unlimited_development() else normal
