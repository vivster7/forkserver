# setup.py
from setuptools import setup

setup(
    name="forkserver",
    version="0.1",
    description="A pytest plugin for forkserver functionality.",
    packages=["forkserver"],
    entry_points={"pytest11": ["forkserver = forkserver.plugin"]},
    install_requires=["watchdog"],
)
