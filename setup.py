#!/usr/bin/env python

from distutils.core import setup

setup(name = "rawdog",
	version = "2.11",
	description = "RSS Aggregator Without Delusions Of Grandeur",
	author = "Adam Sampson",
	author_email = "ats@offog.org",
	url = "http://offog.org/code/rawdog.html",
	license = "GNU GPL v2 or later",
	scripts = ['rawdog'],
	data_files = [('share/man/man1', ['rawdog.1'])],
	packages = ['rawdoglib'])


