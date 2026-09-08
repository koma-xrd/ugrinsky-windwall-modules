"""Test-only output directories with normal inherited Windows permissions."""

from contextlib import contextmanager
from pathlib import Path
import shutil
from uuid import uuid4


@contextmanager
def temporary_build_directory():
    # tempfile's private Windows ACL can exclude the sandbox's restricted token.
    # An ordinary mkdir inherits the already-authorized workspace permissions.
    build = Path(__file__).resolve().parents[1] / "build"
    build.mkdir(exist_ok=True)
    destination = build / f"windwall-test-{uuid4().hex}"
    destination.mkdir()
    try:
        yield destination
    finally:
        shutil.rmtree(destination)
