"""A request-rate limit per service shared by every process on this machine.

Each service has a file under .cache/throttle holding the earliest time its next request may start; a process
takes the file's lock, waits until then, and moves the time on by 1 / per_second, so concurrent workers
together stay under the service's limit.
"""
from __future__ import annotations

import fcntl
import os
import time

from pipeline import llm

DIR = os.path.join(llm.REPO, ".cache", "throttle")


def wait(service: str, per_second: float) -> None:
    """Block until this process may send one request to `service` without the machine exceeding per_second."""
    os.makedirs(DIR, exist_ok=True)
    with open(os.path.join(DIR, service), "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        text = f.read().strip()
        start = max(time.time(), float(text) if text else 0.0)
        f.seek(0)
        f.truncate()
        f.write(repr(start + 1 / per_second))
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)
    time.sleep(max(0.0, start - time.time()))
