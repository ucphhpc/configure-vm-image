#!/usr/bin/python
# coding: utf-8
import os
from setuptools import setup, find_packages

cur_dir = os.path.abspath(os.path.dirname(__file__))


def read(path):
    with open(path, "r") as _file:
        return _file.read()


def read_req(name):
    path = os.path.join(cur_dir, name)
    return [req.strip() for req in read(path).splitlines() if req.strip()]


version_ns = {}
version_path = os.path.join(cur_dir, "configure_vm_image", "_version.py")
version_content = read(version_path)
exec(version_content, {}, version_ns)


long_description = open("README.rst").read()
setup(
    name="configure-vm-image",
    version=version_ns["__version__"],
    description="This tool can be used for configuring virtual machine images.",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Rasmus Munk",
    author_email="munk1@live.dk",
    packages=find_packages(),
    url="https://github.com/rasmunk/configure-vm-image",
    license="MIT",
    keywords=["Virtual Machine", "VM", "Images"],
    install_requires=read_req("requirements.txt"),
    extras_require={
        "dev": read_req("requirements-dev.txt"),
    },
    entry_points={
        "console_scripts": [
            "configure-vm-image = configure_vm_image.cli.configure_image:run_configure_image",
        ]
    },
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
