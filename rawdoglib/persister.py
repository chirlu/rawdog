# persister: persist Python objects safely to pickle files
# Copyright 2003, 2004, 2005, 2013 Adam Sampson <ats@offog.org>
#
# rawdog is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of the
# License, or (at your option) any later version.
#
# rawdog is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with rawdog; see the file COPYING.LGPL. If not,
# write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA, or see http://www.gnu.org/.

import cPickle as pickle
import errno
import fcntl
import os
import sys

class Persistable:
	"""An object which can be persisted."""

	def __init__(self):
		self._modified = False

	def modified(self, state=True):
		"""Mark the object as having been modified (or not)."""
		self._modified = state

	def is_modified(self):
		return self._modified

class Persisted:
	"""Context manager for a persistent object.  The object being persisted
	must implement the Persistable interface."""

	def __init__(self, klass, filename, persister):
		self.klass = klass
		self.filename = filename
		self.persister = persister
		self.file = None
		self.object = None
		self.refcount = 0

	def rename(self, new_filename):
		"""Rename the persisted file. This works whether the file is
		currently open or not."""

		self.persister._rename(self.filename, new_filename)
		os.rename(self.filename, new_filename)
		self.filename = new_filename

	def __enter__(self):
		"""As open()."""
		return self.open()

	def __exit__(self, type, value, tb):
		"""As close(), unless an exception occurred in which case do
		nothing."""
		if tb is None:
			self.close()

	def open(self, no_block=True):
		"""Return the persistent object, loading it from its file if it
		isn't already open. You must call close() once you're finished
		with the object.

		If no_block is True, then this will return None if loading the
		object would otherwise block (i.e. if it's locked by another
		process)."""

		if self.refcount > 0:
			# Already loaded.
			self.refcount += 1
			return self.object

		try:
			self._open(no_block)
		except KeyboardInterrupt:
			sys.exit(1)
		except:
			print "An error occurred while reading state from " + os.path.abspath(self.filename) + "."
			print "This usually means the file is corrupt, and removing it will fix the problem."
			sys.exit(1)

		self.refcount = 1
		return self.object

	def _get_lock(self, no_block):
		if not self.persister.use_locking:
			return True

		try:
			mode = fcntl.LOCK_EX
			if no_block:
				mode |= fcntl.LOCK_NB
			fcntl.lockf(self.file.fileno(), mode)
		except IOError, e:
			if no_block and e.errno in (errno.EACCES, errno.EAGAIN):
				return False
			raise e
		return True

	def _open(self, no_block):
		self.persister.log("Loading state file: ", self.filename)
		try:
			self.file = open(self.filename, "r+")
			if not self._get_lock(no_block):
				return None

			self.object = pickle.load(self.file)
			self.object.modified(False)
		except IOError:
			self.file = open(self.filename, "w+")
			if not self._get_lock(no_block):
				return None

			self.object = self.klass()
			self.object.modified()

	def close(self):
		"""Reduce the reference count of the persisted object, saving
		it back to its file if necessary."""

		self.refcount -= 1
		if self.refcount > 0:
			# Still in use.
			return

		if self.object.is_modified():
			self.persister.log("Saving state file: ", self.filename)
			newname = "%s.new-%d" % (self.filename, os.getpid())
			newfile = open(newname, "w")
			pickle.dump(self.object, newfile, pickle.HIGHEST_PROTOCOL)
			newfile.close()
			os.rename(newname, self.filename)

		self.file.close()
		self.persister._remove(self.filename)

class Persister:
	"""Manage the collection of persisted files."""

	def __init__(self, config):
		self.files = {}
		self.log = config.log
		self.use_locking = config.locking

	def get(self, klass, filename):
		"""Get a context manager for a persisted file.
		If the file is already open, this will return
		the existing context manager."""

		if filename in self.files:
			return self.files[filename]

		p = Persisted(klass, filename, self)
		self.files[filename] = p
		return p

	def _rename(self, old_filename, new_filename):
		self.files[new_filename] = self.files[old_filename]
		del self.files[old_filename]

	def _remove(self, filename):
		del self.files[filename]

