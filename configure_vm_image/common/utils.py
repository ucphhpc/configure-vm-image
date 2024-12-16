import datetime
import os
import sys


def error_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def to_str(o):
    if hasattr(o, "asdict"):
        return o.asdict()
    if isinstance(o, datetime.datetime):
        return o.__str__()
    if isinstance(o, bytes):
        return o.decode("utf-8")
    return o


def expand_path(path):
    return os.path.realpath(os.path.expanduser(path))
