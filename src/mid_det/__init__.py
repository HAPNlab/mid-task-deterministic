from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mid-task-deterministic")
except PackageNotFoundError:
    __version__ = "unknown"
