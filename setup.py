#!/usr/bin/env python

from distutils.core import setup
import sys

if sys.version_info < (2, 6) or sys.version_info >= (3,):
	print("rawdog requires Python 2.6 or later, and not Python 3.")
	sys.exit(1)

setup(name = "rawdog",
	version = "2.15",
	description = "RSS Aggregator Without Delusions Of Grandeur",
	author = "Adam Sampson",
	author_email = "ats@offog.org",
	url = "http://offog.org/code/rawdog.html",
	license = "GNU GPL v2 or later",
	scripts = ['rawdog'],
	data_files = [('share/man/man1', ['rawdog.1'])],
	packages = ['rawdoglib'])
