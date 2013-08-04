# testserver: servers for rawdog's test suite.
# Copyright 2013 Adam Sampson <ats@offog.org>
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
# along with rawdog; see the file COPYING. If not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA, or see http://www.gnu.org/.

import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import base64
import cStringIO
import gzip
import hashlib
import os
import re
import sys
import threading
import time

class TimeoutRequestHandler(SocketServer.BaseRequestHandler):
    """Request handler for a server that just does nothing for a few
    seconds, then disconnects. This is used for testing timeout handling."""

    def handle(self):
        time.sleep(5)

class TimeoutServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """Timeout server for rawdog's test suite."""
    pass

class HTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """HTTP request handler for rawdog's test suite."""

    # do_GET/do_HEAD are copied from SimpleHTTPServer because send_head isn't
    # part of the API.

    def do_GET(self):
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def do_HEAD(self):
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        # Look for lines of the form "/oldpath /newpath" in .rewrites.
        try:
            f = open(os.path.join(self.server.files_dir, ".rewrites"))
            for line in f.readlines():
                (old, new) = line.split(None, 1)
                if self.path == old:
                    self.path = new
            f.close()
        except IOError:
            pass

        m = re.match(r'^/auth-([^/-]+)-([^/]+)(/.*)$', self.path)
        if m:
            # Require basic authentication.
            auth = "Basic " + base64.b64encode(m.group(1) + ":" + m.group(2))
            if self.headers.get("Authorization") != auth:
                self.send_response(401)
                self.end_headers()
                return None
            self.path = m.group(3)

        m = re.match(r'^/digest-([^/-]+)-([^/]+)(/.*)$', self.path)
        if m:
            # Require digest authentication. (Not a good implementation!)
            realm = "rawdog test server"
            nonce = "0123456789abcdef"
            a1 = m.group(1) + ":" + realm + ":" + m.group(2)
            a2 = "GET:" + self.path
            def h(s):
                return hashlib.md5(s).hexdigest()
            response = h(h(a1) + ":" + nonce + ":" + h(a2))
            mr = re.search(r'response="([^"]*)"',
                         self.headers.get("Authorization", ""))
            if mr is None or mr.group(1) != response:
                self.send_response(401)
                self.send_header("WWW-Authenticate",
                                 'Digest realm="%s", nonce="%s"'
                                     % (realm, nonce))
                self.end_headers()
                return None
            self.path = m.group(3)

        m = re.match(r'^/(\d\d\d)(/.*)?$', self.path)
        if m:
            # Request for a particular response code.
            code = int(m.group(1))
            self.send_response(code)
            if m.group(2):
                self.send_header("Location", self.server.base_url + m.group(2))
            self.end_headers()
            return None

        encoding = None
        m = re.match(r'^/(gzip)(/.*)$', self.path)
        if m:
            # Request for a content encoding.
            encoding = m.group(1)
            self.path = m.group(2)

        m = re.match(r'^/([^/]+)$', self.path)
        if m:
            # Request for a file.
            filename = os.path.join(self.server.files_dir, m.group(1))
            try:
                f = open(filename, "rb")
            except IOError:
                self.send_response(404)
                self.end_headers()
                return None

            # Use the SHA1 hash as an ETag.
            etag = '"' + hashlib.sha1(f.read()).hexdigest() + '"'
            f.seek(0)

            # Oversimplistic, but matches what feedparser sends.
            if self.headers.get("If-None-Match", "") == etag:
                self.send_response(304)
                self.end_headers()
                return None

            size = os.fstat(f.fileno()).st_size

            mime_type = "text/plain"
            if filename.endswith(".rss") or filename.endswith(".rss2"):
                mime_type = "application/rss+xml"
            elif filename.endswith(".rdf"):
                mime_type = "application/rdf+xml"
            elif filename.endswith(".atom"):
                mime_type = "application/atom+xml"
            elif filename.endswith(".html"):
                mime_type = "text/html"

            self.send_response(200)

            if encoding:
                self.send_header("Content-Encoding", encoding)
                if encoding == "gzip":
                    data = f.read()
                    f.close()
                    f = cStringIO.StringIO()
                    g = gzip.GzipFile(fileobj=f, mode="wb")
                    g.write(data)
                    g.close()
                    size = f.tell()
                    f.seek(0)

            self.send_header("Content-Length", size)
            self.send_header("Content-Type", mime_type)
            self.send_header("ETag", etag)
            self.end_headers()
            return f

        # A request we can't handle.
        self.send_response(500)
        self.end_headers()
        return None

    def log_message(self, fmt, *args):
        f = open(self.server.files_dir + "/.log", "a")
        f.write(fmt % args + "\n")
        f.close()

class HTTPServer(BaseHTTPServer.HTTPServer):
    """HTTP server for rawdog's test suite."""

    def __init__(self, base_url, files_dir, *args, **kwargs):
        self.base_url = base_url
        self.files_dir = files_dir
        BaseHTTPServer.HTTPServer.__init__(self, *args, **kwargs)

def main(args):
    if len(args) < 3:
        print "Usage: testserver.py HOSTNAME TIMEOUT-PORT HTTP-PORT FILES-DIR"
        sys.exit(1)

    hostname = args[0]
    timeout_port = int(args[1])
    http_port = int(args[2])
    files_dir = args[3]

    timeoutd = TimeoutServer((hostname, timeout_port), TimeoutRequestHandler)
    t = threading.Thread(target=timeoutd.serve_forever)
    t.daemon = True
    t.start()

    base_url = "http://" + hostname + ":" + str(http_port)
    httpd = HTTPServer(base_url, files_dir, (hostname, http_port), HTTPRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main(sys.argv[1:])
