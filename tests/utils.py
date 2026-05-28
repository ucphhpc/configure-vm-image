import os


def get_current_user_uid():
    return os.getuid()


def get_current_user_gid():
    return os.getgid()
