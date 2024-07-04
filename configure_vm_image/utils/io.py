import os
import shutil
import json


def makedirs(path):
    try:
        os.makedirs(os.path.expanduser(path))
        return True, "Created: {}".format(path)
    except Exception as err:
        return False, "Failed to create the directory path: {} - {}".format(path, err)
    return False, "Failed to create the directory path: {}".format(path)


def load(path, mode="r", readlines=False, handler=None, opener=None, **load_kwargs):
    if not opener:
        opener = open
    try:
        with opener(path, mode) as fh:
            if handler:
                return True, handler.load(fh, **load_kwargs)
            if readlines:
                return True, fh.readlines()
            return True, fh.read()
    except Exception as err:
        return False, "Failed to load file: {} - {}".format(path, err)
    return False, "Failed to load file: {}".format(path)


def load_json(path, opener=None):
    if not opener:
        opener = open
    try:
        with opener(path, "r") as fh:
            return True, json.load(fh)
    except IOError as err:
        return False, "Failed to load json: {} - {}".format(path, err)
    return False, "Failed to load json: {}".format(path)


def write(path, content, mode="w", mkdirs=False, handler=None, **handler_kwargs):
    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path) and mkdirs:
        if not makedirs(dir_path):
            return False
    try:
        with open(path, mode) as fh:
            if handler:
                handler.dump(content, fh, **handler_kwargs)
            else:
                if isinstance(content, (list, set)):
                    for line in content:
                        fh.write(line)
                else:
                    fh.write(content)
        return True, "Saved file: {}".format(path)
    except Exception as err:
        return False, "Failed to save file: {} - {}".format(path, err)
    return False, "Failed to save file: {}".format(path)


def remove(path):
    try:
        if exists(path):
            os.remove(os.path.expanduser(path))
            return True, "Removed file: {}".format(path)
    except Exception as err:
        return False, "Failed to remove file: {} - {}".format(path, err)
    return False, "Failed to remove file: {}".format(path)


def removedir(path):
    try:
        if exists(path):
            os.rmdir(os.path.expanduser(path))
            return True, "Removed directory: {}".format(path)
    except Exception as err:
        return False, "Failed to remove directory: {} - {}".format(path, err)
    return False, "Failed to remove directory: {}".format(path)


def exists(path):
    return os.path.exists(os.path.expanduser(path))


def which(command):
    return shutil.which(command)


def chmod(path, mode, **kwargs):
    try:
        os.chmod(os.path.expanduser(path), mode, **kwargs)
    except Exception as err:
        return (
            False,
            "Failed to set permissions: {} on: {} - {}".format(mode, path, err),
        )
    return True, "Set the path: {} with permissions: {}".format(path, mode)


def chown(path, uid, gid):
    try:
        os.chown(os.path.expanduser(path), uid, gid)
    except Exception as err:
        return False, "Failed to set owner: {} on: {} - {}".format(uid, path, err)
    return True, "Set the owner: {} on: {}".format(uid, path)


def copy(original, target):
    # Copy path to target
    try:
        shutil.copyfile(original, target)
    except Exception as err:
        return (
            False,
            "Failed to copy file: {} to: {} - {}".format(original, target, err),
        )
    return True, "Copied file: {} to: {}".format(original, target)


# Read chunks of a file, default to 64KB
def hashsum(path, algorithm="sha1", buffer_size=65536):
    try:
        import hashlib

        hash_algorithm = hashlib.new(algorithm)
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(buffer_size), b""):
                hash_algorithm.update(chunk)
        return hash_algorithm.hexdigest()
    except Exception as err:
        print("Failed to calculate hashsum: {} - {}".format(path, err))
    return False
