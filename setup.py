#!/usr/bin/env python

from setuptools import setup

setup(
    name="rawdog",
    version="2.24rc1",
    description="RSS Aggregator Without Delusions Of Grandeur",
    python_requires=">=3.11",
    author="Adam Sampson",
    author_email="ats@offog.org",
    url="http://offog.org/code/rawdog/",
    scripts=['rawdog'],
    data_files=[('share/man/man1', ['rawdog.1'])],
    packages=['rawdoglib'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Topic :: Internet :: WWW/HTTP",
    ])
