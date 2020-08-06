import datetime
import httplib
import threading
import time
import urllib
import urlparse
import base64
from gettext import gettext as _
from logging import getLogger

import xmlrpclib
import requests
from requests.packages.urllib3.util import retry, url as urllib3_url
from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.config import HTTPBasicWithProxyAuth
from nectar.downloaders.base import Downloader
from nectar.report import DownloadReport, DOWNLOAD_SUCCEEDED

# -- constants -----------------------------------------------------------------

_logger = getLogger(__name__)

ULN_ORACLE_URL = "https://linux-update.oracle.com"

# -- exception classes ---------------------------------------------------------


class ULNCredentialsNotProvided(Exception):
    def __init__(self, url):
        super(DownloadCancelled, self).__init__(url)

    def __str__(self):
        return 'No ULN user or password provided' % self.args[0]

# -- downloader class ----------------------------------------------------------

# partly taken from spacewalk rhn-clone-errata.py
class ULNAuthProxyTransport(xmlrpclib.Transport):
    def set_proxy(self, proxy_host, proxy_port, proxy_user=None, proxy_pass=None):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_pass = proxy_pass

    def request(self, host, handler, request_body, verbose=0):
        puser_pass = None
        if self.proxy_user and self.proxy_pass:
            puser_pass = base64.encodestring('%s:%s' % (urllib.unquote(self.proxy_user),urllib.unquote(self.proxy_pass))).strip()

        proxy_url = self.proxy_host + ":" + str(self.proxy_port)
        urlopener = urllib.FancyURLopener({'http':proxy_url})
        if not puser_pass:
            urlopener.addheaders = [('User-agent', self.user_agent)]
        else:
            urlopener.addheaders = [('User-agent', self.user_agent),('Proxy-authorization', 'Basic ' + puser_pass)]

        host = urllib.unquote(host)
        f = urlopener.open("http://%s%s"%(host,handler), request_body)

        self.verbose = verbose
        return self.parse_response(f)


class ULNHTTPThreadedDownloader(HTTPThreadedDownloader):
    """
    Downloader class that uses native Python threads with Requests to handle
    HTTP, HTTPS and proxied download requests by the server.
    """
    def _fetch(self, request):
        """
        :param request: download request object with details about what to
                        download and where to put it
        :type  request: nectar.request.DownloadRequest

        :return:    download report
        :rtype:     nectar.report.DownloadReport
        """

        report = DownloadReport.from_download_request(request)
        report.download_started()

        try:
            parsed = urlparse.urlparse(request.url)
            scheme = parsed.scheme
            _logger.debug("Url scheme is "+ scheme)
            _logger.debug("user: " + self.config.basic_auth_username)
            if not self.config.basic_auth_username: 
                raise ULNCredentialsNotProvided(request.url)
            if not self.config.basic_auth_password: 
                raise ULNCredentialsNotProvided(request.url)
            if self.config.proxy_url and self.config.proxy_port:
                _logger.debug("proxy server: %s:%s"%(self.config.proxy_url,self.config.proxy_port)) 
                transport=ULNAuthProxyTransport()
                transport.set_proxy(self.config.proxy_url, self.config.proxy_port, self.config.proxy_username, self.config.proxy_password)
                client = xmlrpclib.Server(ULN_ORACLE_URL + "/rpc/api", verbose=0, transport=transport)
            else:
                client = xmlrpclib.Server(ULN_ORACLE_URL + "/rpc/api", verbose=0)
            key = client.auth.login(self.config.basic_auth_username, self.config.basic_auth_password)    
            self.config.headers.update({ "X-ULN-Api-User-Key" : key })
            request.url = ULN_ORACLE_URL + "/XMLRPC/GET-REQ/" + parsed.netloc + "/" + parsed.path
            _logger.debug("updated uln request url: " + request.url)


        except ULNCredentialsNotProvided as e:
            _logger.info(str(e))
            report.download_failed()

        except Exception as e:
            _logger.exception(e)
            report.error_msg = str(e)
            report.download_failed()

        else: 
            return super(ULNHTTPThreadedDownloader, self)._fetch(request)

        request.finalize_file_handle()
        self.fire_download_failed(report)
        return report
