# Anemic replacement for feedfinder (which Debian can't distribute) so
# that ``rawdog -a'' at least does *something*. Only checks for the
# existence of <link rel='alternate' ... /> in an HTML (or XML) document;
# falls back to the given URI otherwise, e.g. if the URI is already a
# feed (and only contains text/html alternates, in the case of Atom), or
# is something we don't recognize. Unlike with the real feedfinder, you
# *can* add garbage to your config with this if you give it a garbage
# URI. Also, the first link that appears ends up at the head of the
# list, so hope it's not the RSS 0.9 one.

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

import urllib, urlparse
from HTMLParser import HTMLParser

def feeds(uri):
    parser = FeedFinder(uri)
    parser.feed(urllib.urlopen(uri).read())
    return parser.feeds + [uri]

class FeedFinder(HTMLParser):
    def __init__(self, base_uri):
        HTMLParser.__init__(self)
        self.feeds = []
        self.base_uri = base_uri
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'alternate' and \
                not attrs.get('type') == 'text/html':
            self.feeds.append(urlparse.urljoin(self.base_uri, attrs['href']))
