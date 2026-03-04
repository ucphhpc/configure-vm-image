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


def transform_str_to_dict(
    string, string_split_on_char=",", key_value_split_on_char="="
):
    _dict = {
        key_value.split(key_value_split_on_char)[0]: key_value.split(
            key_value_split_on_char
        )[1]
        for key_value in string.split(string_split_on_char)
    }
    return _dict
