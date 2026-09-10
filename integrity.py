"""Small shared I/O and numeric boundaries; no market-data dependencies."""
import json
import math
import os
import tempfile
from pathlib import Path


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def positive_number(value):
    value = finite_number(value)
    return value if value is not None and value > 0 else None


def atomic_text(path, text):
    """Replace only after a complete, flushed write in the target directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path, value):
    # Refuse NaN/Infinity instead of producing invalid JSON archives.
    atomic_text(path, json.dumps(value, indent=1, allow_nan=False) + '\n')
