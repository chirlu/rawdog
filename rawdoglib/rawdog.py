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

VERSION = "1.1"
import feedparser
from persister import Persistable, Persister
import os, time, sha

def format_time(secs, config):
	"""Format a time and date nicely."""
	t = time.localtime(secs)
	return time.strftime(config["timeformat"], t) + ", " + time.strftime(config["dayformat"], t)

class Feed:
	"""An RSS feed."""

	def __init__(self, url, period):
		self.url = url
		self.period = period
		self.etag = None
		self.modified = None
		self.title = None
		self.link = None
		self.last_update = 0
	
	def update(self, articles, now, force = 0):
		"""Fetch articles from a feed and add them to the collection.
		Returns 1 if any articles were read, 0 otherwise."""

		if not force and (now - self.last_update) < (self.period * 60):
			return 0
		self.last_update = now

		try:
			p = feedparser.parse(self.url, self.etag,
				self.modified,	"rawdog/" + VERSION)
		except:
			print "Error fetching " + self.url
			return 0

		self.etag = p.get("etag")
		self.modified = p.get("modified")
		# In the event that the feed hasn't changed, then both channel
		# and feed will be empty. In this case we return 0 so that
		# we know not to expire articles that came from this feed.

		channel = p["channel"]
		if channel.has_key("title"):
			self.title = channel["title"]
		if channel.has_key("link"):
			self.link = channel["link"]

		feed = self.url
		seen_items = 0
		sequence = 0
		for item in p["items"]:
			title = item.get("title")
			link = item.get("link")
			if item.has_key("content_encoded"):
				description = item["content_encoded"]
			else:
				description = item.get("description")

			article = Article(feed, title, link, description,
				now, sequence)
			sequence += 1

			if articles.has_key(article.hash):
				articles[article.hash].last_seen = now
			else:
				articles[article.hash] = article
			seen_items = 1

		return seen_items

	def get_html_name(self):
		if self.title is not None:
			return self.title
		elif self.link is not None:
			return self.link
		else:
			return self.url

	def get_html_link(self):
		s = self.get_html_name()
		if self.link is not None:
			return '<a href="' + self.link + '">' + s + '</a>'
		else:
			return s

class Article:
	"""An article retrieved from an RSS feed."""

	def __init__(self, feed, title, link, description, now, sequence):
		self.feed = feed
		self.title = title
		self.link = link
		self.description = description
		self.sequence = sequence

		s = str(feed) + str(title) + str(link) + str(description)
		self.hash = sha.new(s).hexdigest()

		self.last_seen = now
		self.added = now

	def get_sequence(self):
		try:
			return self.sequence
		except AttributeError:
			# This Article came from an old state file.
			return 0

	def can_expire(self, now):
		return ((now - self.last_seen) > (24 * 60 * 60))

class DayWriter:
	"""Utility class for writing day sections into a series of articles."""

	def __init__(self, file, config):
		self.lasttime = [-1, -1, -1, -1, -1]
		self.file = file
		self.counter = 0
		self.config = config

	def start_day(self, tm):
		print >>self.file, '<div class="day">'
		day = time.strftime(self.config["dayformat"], tm)
		print >>self.file, '<h2>' + day + '</h2>'
		self.counter += 1

	def start_time(self, tm):
		print >>self.file, '<div class="time">'
		clock = time.strftime(self.config["timeformat"], tm)
		print >>self.file, '<h3>' + clock + '</h3>'
		self.counter += 1

	def time(self, s):
		tm = time.localtime(s)
		if tm[:3] != self.lasttime[:3]:
			self.close(0)
			self.start_day(tm)
		if tm[:6] != self.lasttime[:6]:
			self.close(1)
			self.start_time(tm)
		self.lasttime = tm

	def close(self, n = 0):
		while self.counter > n:
			print >>self.file, "</div>"
			self.counter -= 1

class ConfigError(Exception): pass

class Config:
	"""The aggregator's configuration."""

	def __init__(self):
		self.config = {
			"feedslist" : [],
			"outputfile" : "output.html",
			"maxarticles" : 200,
			"dayformat" : "%A, %d %B %Y",
			"timeformat" : "%I:%M %p",
			"userefresh" : 0,
			"showfeeds" : 1,
			}

	def __getitem__(self, key): return self.config[key]
	def __setitem__(self, key, value): self.config[key] = value

	def load(self, filename):
		"""Load configuration from a config file."""
		try:
			f = open(filename, "r")
			lines = f.readlines()
			f.close()
		except IOError:
			raise ConfigError("Can't read config file: " + filename)
		for line in lines:
			self.load_line(line.strip())

	def load_line(self, line):
		"""Process a configuration line."""

		if line == "" or line[0] == "#":
			return

		l = line.split(" ", 1)
		if len(l) != 2:
			raise ConfigError("Bad line in config: " + line)

		if l[0] == "feed":
			l = l[1].split(" ", 1)
			if len(l) != 2:
				raise ConfigError("Bad line in config: " + line)
			self["feedslist"].append((l[1], int(l[0])))
		elif l[0] == "outputfile":
			self["outputfile"] = l[1]
		elif l[0] == "maxarticles":
			self["maxarticles"] = int(l[1])
		elif l[0] == "dayformat":
			self["dayformat"] = l[1]
		elif l[0] == "timeformat":
			self["timeformat"] = l[1]
		elif l[0] == "userefresh":
			self["userefresh"] = int(l[1])
		elif l[0] == "showfeeds":
			self["showfeeds"] = int(l[1])
		else:
			raise ConfigError("Unknown config command: " + l[0])

class Rawdog(Persistable):
	"""The aggregator itself."""

	def __init__(self):
		self.feeds = {}
		self.articles = {}

	def list(self):
		for url in self.feeds.keys():
			feed = self.feeds[url]
			print url
			print "  Title:", feed.title
			print "  Link:", feed.link

	def update(self, config, feedurl = None):
		now = time.time()

		seenfeeds = {}
		for (url, period) in config["feedslist"]:
			seenfeeds[url] = 1
			if not self.feeds.has_key(url):
				self.feeds[url] = Feed(url, period)
			else:
				self.feeds[url].period = period
		for url in self.feeds.keys():
			if not seenfeeds.has_key(url):
				del self.feeds[url]

		if feedurl is None:
			update_feeds = self.feeds.keys()
			force = 0
		elif self.feeds.has_key(feedurl):
			update_feeds = [feedurl]
			force = 1
		else:
			print "No such feed: " + feedurl
			update_feeds = []
	
		seen_some_items = {}
		for url in update_feeds:
			if self.feeds[url].update(self.articles, now, force):
				seen_some_items[url] = 1

		for key in self.articles.keys():
			article = self.articles[key]
			if ((not self.feeds.has_key(article.feed))
			    or (seen_some_items.has_key(article.feed)
			        and article.can_expire(now))):
				del self.articles[key]

		self.modified()

	def write(self, config):
		outputfile = config["outputfile"]
		now = time.time()

		f = open(outputfile + ".new", "w")

		refresh = 24 * 60
		for feed in self.feeds.values():
			if feed.period < refresh: refresh = feed.period
		
		print >>f, """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">
<html lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">"""
		if config["userefresh"]:
    			print >>f, """<meta http-equiv="Refresh" """ + 'content="' + str(refresh * 60) + '"' + """>"""
		print >>f, """    <link rel="stylesheet" href="style.css" type="text/css">
    <title>rawdog</title>
</head>
<body id="rawdog">
<div id="header">
<h1>rawdog</h1>"""

		articles = self.articles.values()
		def compare(a, b):
			"""Compare two articles to decide how they
			   should be sorted. Sort by added date, then
			   by feed, then by sequence, then by hash."""
			i = cmp(b.added, a.added)
			if i != 0:
				return i
			i = cmp(a.feed, b.feed)
			if i != 0:
				return i
			i = cmp(a.get_sequence(), b.get_sequence())
			if i != 0:
				return i
			return cmp(a.hash, b.hash)
		articles.sort(compare)
		articles = articles[:config["maxarticles"]]

		print >>f, """</div>
<div id="items">"""

		dw = DayWriter(f, config)

		for article in articles:
			dw.time(article.added)

			feed = self.feeds[article.feed]
			f.write('<div class="item">\n')
			f.write('<p class="itemheader">\n')

			title = article.title
			link = article.link
			description = article.description
			if title is None:
				if link is None:
					title = "Article"
				else:
					title = "Link"

			f.write('<span class="itemtitle">')
			if link is not None: f.write('<a href="' + article.link + '">')
			f.write(title)
			if link is not None: f.write('</a>')
			f.write('</span>\n')

			f.write('<span class="itemfrom">[' + feed.get_html_link() + ']</span>')

			f.write('</p>\n')

			if description is not None:
				f.write('<div class="itemdescription"><p>' + description + '</p></div>\n')

			f.write('</div>\n')

		dw.close()
		print >>f, '</div>'

		if config["showfeeds"]:
			print >>f, """<h2 id="feedstatsheader">Feeds</h2>
<div id="feedstats">
<table id="feeds">
<tr id="feedsheader">
<th>Feed</th><th>RSS</th><th>Last update</th><th>Next update</th>
</tr>"""
			feeds = self.feeds.values()
			feeds.sort(lambda a, b: cmp(a.get_html_name().lower(), b.get_html_name().lower()))
			for feed in feeds:
				print >>f, '<tr class="feedsrow">'
				print >>f, '<td>' + feed.get_html_link() + '</td>'
				print >>f, '<td><a class="xmlbutton" href="' + feed.url + '">XML</a></td>'
				print >>f, '<td>' + format_time(feed.last_update, config) + '</td>'
				print >>f, '<td>' + format_time(feed.last_update + 60 * feed.period, config) + '</td>'
				print >>f, '</tr>'
			print >>f, """</table>
</div>"""

		print >>f, """<div id="footer">
<p id="aboutrawdog">Generated by rawdog version """ + VERSION + """
by <a href="mailto:azz@us-lot.org">Adam Sampson</a>.</p>
</div>
</body>
</html>"""

		f.close()
		os.rename(outputfile + ".new", outputfile)

def main(argv):
	"""The command-line interface to the aggregator."""

	if len(argv) < 1:
		print "Usage: rawdog action [action ...]"
		print "action can be list, update, write, <feed URL>"
		return 1

	statedir = os.environ["HOME"] + "/.rawdog"
	try:
		os.chdir(statedir)
	except OSError:
		print "No ~/.rawdog directory"
		return 1

	config = Config()
	try:
		config.load("config")
	except ConfigError, err:
		print err
		return 1

	persister = Persister("state", Rawdog)	
	rawdog = persister.load()

	for action in argv:
		if action == "list":
			rawdog.list()
		elif action == "update":
			rawdog.update(config)
		elif action == "write":
			rawdog.write(config)
		else:
			rawdog.update(config, action)

	persister.save()

	return 0

