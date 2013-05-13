import contextlib
import os


@contextlib.contextmanager
def working_directory(path):
    """Context manager changing working directory."""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)
