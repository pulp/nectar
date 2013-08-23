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

import datetime
import httplib
import Queue
import threading
import time
import urllib
import urlparse
from logging import getLogger

import requests

try:
    from requests.packages.urllib3.connectionpool import ClosedPoolError
except ImportError:
    from urllib3.connectionpool import ClosedPoolError

from nectar.downloaders.base import Downloader
from nectar.report import DownloadReport, DOWNLOAD_SUCCEEDED

# -- constants -----------------------------------------------------------------

_LOG = getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 5
DEFAULT_BUFFER_SIZE = 8192 # bytes
DEFAULT_PROGRESS_INTERVAL = 5 # seconds
DEFAULT_RETRIES = 3

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

class HTTPThreadedDownloader(Downloader):
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

    def progress_reporter(self, queue):
        """
        Useful in a thread to fire reports. See below for the sentinal value that
        signals the thread to end.

        :param queue:   queue that will contain tuples where the first member
                        is a DownloadReport, and the second member is a function
                        to call with that report. The function should handle
                        the firing of that report. If the first member is anything
                        besides a DownloadReport, this function will return.
        :type  queue:   Queue.Queue
        """
        while True:
            report, report_func = queue.get()
            if not isinstance(report, DownloadReport):
                # done!
                break
            report_func(report)
            queue.task_done()

    def worker(self, queue, queue_ready, session, report_queue):
        """
        :param queue:       queue of DownloadRequest instances
        :type  queue:       Queue.Queue
        :param queue_ready: threading event that signals when the queue has been
                            sufficiently populated that it is ready for workers
                            to start
        :type  queue_ready: threading.Event
        :param session:     Session instance
        :type  session:     requests.sessions.Session
        :param report_queue:queue where DownloadReport instances can be dropped
                            for reporting. Each item added should be a tuple
                            with the first member a DownloadReport instance, and
                            the second member a function to call with that report
        :type  report_queue:Queue.Queue

        """
        queue_ready.wait()
        while not self.is_canceled:
            try:
                request = queue.get_nowait()
            except Queue.Empty:
                break
            self._fetch(request, session, report_queue)
            queue.task_done()

    def feed_queue(self, queue, queue_ready, request_list):
        """
        takes DownloadRequests off of an iterator (which could be a generator),
        and adds them to a queue. This is only useful if the queue has a size
        limit. Sets queue_ready when the queue is full enough for workers to start.
        """
        for request in request_list:
            if self.is_canceled:
                break
            queue.put(request)
            if queue.full() and not queue_ready.is_set():
                queue_ready.set()
        # call again in case we never filled up the queue
        if not queue_ready.is_set():
            queue_ready.set()

    def download(self, request_list):
        session = build_session(self.config)
        queue = Queue.Queue(maxsize=self.max_concurrent*3)
        queue_ready = threading.Event()
        report_queue = Queue.Queue()
        _LOG.debug('starting feed queue thread')
        feeder = threading.Thread(target=self.feed_queue, args=[queue, queue_ready, request_list])
        threading.Thread(target=self.progress_reporter, args=[report_queue]).start()

        _LOG.debug('starting workers')
        for i in range(self.max_concurrent):
            threading.Thread(target=self.worker, args=[queue, queue_ready, session, report_queue]).start()

        feeder.start()
        feeder.join()

        queue.join()
        report_queue.join()
        report_queue.put((True, None))
        session.close()

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

    def _fetch(self, request, session, report_queue):
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
        report_queue.put((report, self.fire_download_started))

        retries = DEFAULT_RETRIES

        try:
            if self.is_canceled:
                raise DownloadCancelled(request.url)

            response = None

            while True:
                try:
                    response = session.get(request.url, headers=headers)
                except ClosedPoolError:
                    retries -= 1
                    if retries <= 0:
                        raise
                else:
                    break

            if response.status_code != httplib.OK:
                raise DownloadFailed(request.url, response.status_code, response.reason)

            progress_interval = self.progress_interval
            file_handle = request.initialize_file_handle()

            last_update_time = datetime.datetime.now()
            report_queue.put((report, self.fire_download_progress))

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
                    report_queue.put((report, self.fire_download_progress))

                with session.nectar_bytes_lock:
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

            # guarantee 1 report at the end
            report_queue.put((report, self.fire_download_progress))

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

        if report.state is DOWNLOAD_SUCCEEDED:
            report_queue.put((report, self.fire_download_succeeded))
        else: # DOWNLOAD_FAILED
            report_queue.put((report, self.fire_download_failed))

# -- requests utilities --------------------------------------------------------

def build_session(config):
    session = requests.Session()
    session.stream = True # required for reading the download in chunks
    _add_basic_auth(session, config)
    _add_ssl(session, config)
    _add_proxy(session, config)
    session.nectar_bytes_this_second = 0
    session.nectar_time_bytes_this_second_was_cleared = datetime.datetime.now()
    session.nectar_bytes_lock = threading.Lock()

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

    session.proxies[protocol] = url

