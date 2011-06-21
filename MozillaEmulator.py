#----------------------------------------------------------------------
#
# Author:      Laszlo Nagy
#
# Copyright:   (c) 2005 by Szoftver Messias Bt.
# Licence:     BSD style
#
#
#----------------------------------------------------------------------
import os
import md5
import urllib
import urllib2
import mimetypes
import cStringIO
from cPickle import loads,dumps
import cookielib


class MozillaEmulator(object):
    def __init__(self,cacher={},trycount=0):
        """Create a new MozillaEmulator object.

        @param cacher: A dictionary like object, that can cache search results on a storage device.
            You can use a simple dictionary here, but it is not recommended.
            You can also put None here to disable caching completely.
        @param trycount: The download() method will retry the operation if it fails. You can specify -1 for infinite retrying.
                A value of 0 means no retrying. A value of 1 means one retry. etc."""
        self.cacher = cacher
        self.cookies = cookielib.CookieJar()
        self.trycount = trycount
    def _hash(self,data):
        h = md5.new()
        h.update(data)
        return h.hexdigest()

    def build_opener(self,url,postdata=None,extraheaders={},forbid_redirect=False, proxy=None):
        txheaders = {
            'Accept':'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
            'Accept-Language':'en,hu;q=0.8,en-us;q=0.5,hu-hu;q=0.3',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
        }
        for key,value in extraheaders.iteritems():
            txheaders[key] = value
        req = urllib2.Request(url, postdata, txheaders)
        self.cookies.add_cookie_header(req)
        if forbid_redirect:
            redirector = HTTPNoRedirector()
        else:
            redirector = urllib2.HTTPRedirectHandler()

        http_handler = urllib2.HTTPHandler(debuglevel=False)
        https_handler = urllib2.HTTPSHandler(debuglevel=False)
        if proxy:
            proxy_support = urllib2.ProxyHandler(proxy)
            u = urllib2.build_opener(proxy_support, http_handler,https_handler,urllib2.HTTPCookieProcessor(self.cookies),redirector)
        else:
            u = urllib2.build_opener(http_handler,https_handler,urllib2.HTTPCookieProcessor(self.cookies),redirector)
        u.addheaders = [('User-Agent','Mozilla/5.0 (Windows; U; Windows NT 5.1; hu-HU; rv:1.7.8) Gecko/20050511 Firefox/1.0.4')]
        
        if not postdata is None:
            req.add_data(postdata)
        return (req,u)

    def download(self,url,postdata=None,extraheaders={},forbid_redirect=False,
            trycount=None,fd=None,onprogress=None,only_head=False, proxy=None):
        """Download an URL with GET or POST methods.

        @param postdata: It can be a string that will be POST-ed to the URL.
            When None is given, the method will be GET instead.
        @param extraheaders: You can add/modify HTTP headers with a dict here.
        @param forbid_redirect: Set this flag if you do not want to handle
            HTTP 301 and 302 redirects.
        @param trycount: Specify the maximum number of retries here.
            0 means no retry on error. Using -1 means infinite retring.
            None means the default value (that is self.trycount).
        @param fd: You can pass a file descriptor here. In this case,
            the data will be written into the file. Please note that
            when you save the raw data into a file then it won't be cached.
        @param onprogress: A function that has two parameters:
            the size of the resource and the downloaded size. This will be
            called for each 1KB chunk. (If the HTTP header does not contain
            the content-length field, then the size parameter will be zero!)
        @param only_head: Create the openerdirector and return it. In other
            words, this will not retrieve any content except HTTP headers.

        @return: The raw HTML page data, unless fd was specified. When fd
            was given, the return value is undefined.
        """
        if trycount is None:
            trycount = self.trycount
        cnt = 0
        #while True:
            #try:
        key = self._hash(url)
        if (self.cacher is None) or (not self.cacher.has_key(key)):
            req,u = self.build_opener(url,postdata,extraheaders,forbid_redirect, proxy=proxy)
            openerdirector = u.open(req)
            self.cookies.extract_cookies(openerdirector,req)
            if only_head:
                return openerdirector
            if openerdirector.headers.has_key('content-length'):
                length = long(openerdirector.headers['content-length'])
            else:
                length = 0
            dlength = 0
            if fd:
                while True:
                    data = openerdirector.read(1024)
                    dlength += len(data)
                    fd.write(data)
                    if onprogress:
                        onprogress(length,dlength)
                    if not data:
                        break
            else:
                data = ''
                while True:
                    newdata = openerdirector.read(1024)
                    dlength += len(newdata)
                    data += newdata
                    if onprogress:
                        onprogress(length,dlength)
                    if not newdata:
                        break
                if not (self.cacher is None):
                    self.cacher[key] = data
        else:
            data = self.cacher[key]
        return data
#            except urllib2.URLError:
#                cnt += 1
#                if (trycount > -1) and (trycount < cnt):
#                    raise