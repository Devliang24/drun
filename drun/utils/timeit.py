from __future__ import annotations

import time
from contextlib import contextmanager


@contextmanager
def timeblock():
    start = time.perf_counter()
    try:
        yield lambda: (time.perf_counter() - start) * 1000.0
    finally:
        pass

