# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

# first, so that all subsequently imported modules are the monkey patched versions
import eventlet
eventlet.monkey_patch(thread=False)

import datetime
import httplib
import time
import urllib
import urlparse
from logging import getLogger

import requests

from nectar.downloaders.base import Downloader
from nectar.report import DownloadReport, DOWNLOAD_SUCCEEDED

# -- constants -----------------------------------------------------------------

_LOG = getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 5
DEFAULT_BUFFER_SIZE = 8192 # bytes
DEFAULT_PROGRESS_INTERVAL = 5 # seconds

ONE_SECOND = datetime.timedelta(seconds=1)

# -- exception classes ---------------------------------------------------------

class DownloadCancelled(Exception):
    def __init__(self, url):
        super(DownloadCancelled, self).__init__(url)
    def __str__(self):
        return 'Download of %s was cancelled' % self.args[0]

class DownloadFailed(Exception):
    def __init__(self, url, code, msg=None):
        super(DownloadFailed, self).__init__(url, code, msg)
    def __str__(self):
        return 'Download of %s failed with code %d: %s' % tuple(a for a in self.args)

# -- downloader class ----------------------------------------------------------

class HTTPEventletRequestsDownloader(Downloader):
    """
    Downloader class that uses the third party Eventlets with Requests to handle
    HTTP, HTTPS and proxied download requests by the server.
    """

    @property
    def buffer_size(self):
        return self.config.buffer_size or DEFAULT_BUFFER_SIZE

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    @property
    def progress_interval(self):
        seconds = self.config.progress_interval or DEFAULT_PROGRESS_INTERVAL
        return datetime.timedelta(seconds=seconds)

    def download(self, request_list):

        pool = eventlet.GreenPool(size=self.max_concurrent)
        session = build_session(self.config)

        def _session_generator():
            while True: yield session

        for report in pool.imap(self._fetch, request_list, _session_generator()):

            if report.state is DOWNLOAD_SUCCEEDED:
                self.fire_download_succeeded(report)

            else: # DOWNLOAD_FAILED
                self.fire_download_failed(report)

    @staticmethod
    def chunk_generator(raw, chunk_size):
        """
        Return a generator of chunks from a file-like object

        :param raw:         the "raw" object from a Response object
        :type  raw:         file

        :param chunk_size:  size in bytes that should be read into one chunk
        :type  chunk_size:  int

        :return:    generator of chunks
        :rtype:     generator
        """
        while True:
            chunk = raw.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def _fetch(self, request, session):
        """
        :param request: download request object with details about what to
                        download and where to put it
        :type  request: nectar.request.DownloadRequest
        :param session: session object used by the requests library
        :type  session: requests.sessions.Session
        """
        # this is to deal with broken web servers that violate RFC 2616 by sending
        # a header 'content-encoding: x-gzip' when it's really just a gzipped
        # file. In that case, we must ignore the declared encoding and thus prevent
        # the requests library from automatically decompressing the file.
        parse_url = urlparse.urlparse(request.url)
        if parse_url.path.endswith('.gz'):
            ignore_encoding = True
            # declare that we don't accept any encodings, so that if we do still
            # get a content-encoding value in the response, we know for sure the
            # other end is broken/misbehaving.
            headers = {'accept-encoding': ''}
        else:
            ignore_encoding = False
            headers = None

        max_speed = self.config.max_speed # None or integer in bytes/second

        if max_speed is not None:
            max_speed -= (2 * self.buffer_size) # because we test *after* reading and only sleep for 1/2 second
            max_speed = max(max_speed, (2 * self.buffer_size)) # because we cannot go slower

        report = DownloadReport.from_download_request(request)
        report.download_started()
        self.fire_download_started(report)

        try:
            if self.is_canceled:
                raise DownloadCancelled(request.url)

            response = session.get(request.url, headers=headers)

            if response.status_code != httplib.OK:
                raise DownloadFailed(request.url, response.status_code, response.reason)

            progress_interval = self.progress_interval
            file_handle = request.initialize_file_handle()

            last_update_time = datetime.datetime.now()
            self.fire_download_progress(report) # guarantee 1 report at the beginning

            if ignore_encoding:
                chunks = self.chunk_generator(response.raw, self.buffer_size)
            else:
                chunks = response.iter_content(self.buffer_size)

            for chunk in chunks:
                if self.is_canceled:
                    raise DownloadCancelled(request.url)

                file_handle.write(chunk)

                bytes_read = len(chunk)
                report.bytes_downloaded += bytes_read

                now = datetime.datetime.now()

                if now - last_update_time >= progress_interval:
                    last_update_time = now
                    self.fire_download_progress(report)

                if now - session.nectar_time_bytes_this_second_was_cleared >= ONE_SECOND:
                    session.nectar_bytes_this_second = 0
                    session.nectar_time_bytes_this_second_was_cleared = now

                session.nectar_bytes_this_second += bytes_read

                if max_speed is not None and session.nectar_bytes_this_second >= max_speed:
                    # it's not worth doing fancier mathematics than this, very
                    # fine-grained sleep times [1] are not honored by the system
                    # [1] for example, sleeping the remaining fraction of time
                    # before this second is up
                    time.sleep(0.5)

            self.fire_download_progress(report) # guarantee 1 report at the end

        except DownloadCancelled, e:
            _LOG.debug(str(e))
            report.download_canceled()

        except DownloadFailed, e:
            _LOG.error(str(e))
            report.error_msg = e.args[2]
            report.error_report['response_code'] = e.args[1]
            report.error_report['response_msg'] = e.args[2]
            report.download_failed()

        except Exception, e:
            _LOG.exception(e)
            report.error_msg = str(e)
            report.download_failed()

        else:
            report.download_succeeded()

        finally:
            request.finalize_file_handle()

        return report

# -- requests utilities --------------------------------------------------------

def build_session(config):
    session = requests.Session()
    session.stream = True # required for reading the download in chunks
    _add_basic_auth(session, config)
    _add_ssl(session, config)
    _add_proxy(session, config)
    session.nectar_bytes_this_second = 0
    session.nectar_time_bytes_this_second_was_cleared = datetime.datetime.now()

    return session


def _add_basic_auth(session, config):
    if None in (config.basic_auth_username, config.basic_auth_password):
        return

    session.auth = (config.basic_auth_username, config.basic_auth_password)


def _add_ssl(session, config):
    session.verify = config.ssl_validation if config.ssl_validation is not None else True
    if session.verify and config.ssl_ca_cert_path is not None:
        session.verify = config.ssl_ca_cert_path

    client_cert_tuple = (config.ssl_client_cert_path, config.ssl_client_key_path)

    if None not in client_cert_tuple:
        session.cert = client_cert_tuple


def _add_proxy(session, config):
    if None in (config.proxy_url, config.proxy_port):
        return

    protocol, remainder = urllib.splittype(config.proxy_url)
    host, remainder = urllib.splithost(remainder)
    url = ':'.join((host, str(config.proxy_port)))

    if config.proxy_username is not None:
        password_part = config.get('proxy_password', '') and ':%s' % config.proxy_password
        auth = config.proxy_username + password_part
        url = '@'.join((auth, url))

    session.proxies['https'] = '://'.join((protocol, url))
    session.proxies['http'] = '://'.join((protocol, url))

