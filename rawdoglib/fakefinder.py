# Anemic replacement for feedfinder (which Debian can't distribute) so
# that ``rawdog -a'' at least does *something*. Only checks for the
# existence of <link rel='alternate' ... /> in an HTML (or XML) document;
# falls back to the given URI otherwise, e.g. if the URI is already a
# feed (and only contains text/html alternates, in the case of Atom), or
# is something we don't recognize. The first link that appears ends up at the
# head of the list, so hope it's not the RSS 0.9 one.

__license__ = """
Copyright (c) 2008 Decklin Foster <decklin@red-bean.com>
Copyright (c) 2013 Adam Sampson <ats@offog.org>

Permission to use, copy, modify, and/or distribute this software for
any purpose with or without fee is hereby granted, provided that
the above copyright notice and this permission notice appear in all
copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA
OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
"""

import feedparser
import urllib
import urlparse
import HTMLParser

def is_feed(url):
    """Return true if feedparser can understand the given URL as a feed."""

    p = feedparser.parse(url)
    version = p.get("version")
    if version is None:
        version = ""
    return (version != "")

def feeds(page_url):
    """Search the given URL for possible feeds, returning a list of them."""

    found = []

    parser = FeedFinder(page_url)
    try:
        parser.feed(urllib.urlopen(page_url).read())
    except HTMLParser.HTMLParseError:
        pass
    found += parser.feeds

    found.append(page_url)

    # Return only feeds that feedparser can understand.
    return [feed for feed in found if is_feed(feed)]

class FeedFinder(HTMLParser.HTMLParser):
    def __init__(self, base_uri):
        HTMLParser.HTMLParser.__init__(self)
        self.feeds = []
        self.base_uri = base_uri
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'alternate' and \
                not attrs.get('type') == 'text/html':
            self.feeds.append(urlparse.urljoin(self.base_uri, attrs['href']))
