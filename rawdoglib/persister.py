# rawdog: RSS aggregator without delusions of grandeur.
# Copyright 2003 Adam Sampson <azz@us-lot.org>
#
# rawdog is free software; you can redistribute and/or modify it
# under the terms of that license as published by the Free Software
# Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# rawdog is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with rawdog; see the file COPYING. If not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307 USA, or see http://www.gnu.org/.

import pickle, fcntl

class Persistable:
	"""Something which can be persisted. When a subclass of this wants to
	   indicate that it has been modified, it should call
	   self.modified()."""
	def __init__(self): self._modified = 0
	def modified(self, state = 1): self._modified = state
	def is_modified(self): return self._modified

class Persister:
	"""Persist another class to a file, safely. The class being persisted
	   must derive from Persistable (although this isn't enforced)."""

	def __init__(self, filename, klass):
		self.filename = filename
		self.klass = klass
		self.file = None
		self.object = None

	def load(self):
		"""Load the persisted object from the file, or create a new one
		   if this isn't possible. Returns the loaded object."""
		try:
			self.file = open(self.filename, "r+")
			fcntl.lockf(self.file.fileno(), fcntl.LOCK_EX)
			self.object = pickle.load(self.file)
			self.object.modified(0)
		except IOError:
			self.file = open(self.filename, "w+")
			fcntl.lockf(self.file.fileno(), fcntl.LOCK_EX)
			self.object = self.klass()
			self.object.modified()
		return self.object

	def save(self):
		"""Save the persisted object back to the file if necessary."""
		if self.object.is_modified():
			self.file.seek(0)
			self.file.truncate(0)
			pickle.dump(self.object, self.file)
		self.file.close()

