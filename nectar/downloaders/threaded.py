import datetime
import httplib
import threading
import time
import urllib
import urlparse
from gettext import gettext as _
from logging import getLogger

import requests
from requests.packages.urllib3.util import retry

from nectar.config import HTTPBasicWithProxyAuth
from nectar.downloaders.base import Downloader
from nectar.report import DownloadReport, DOWNLOAD_SUCCEEDED

# -- constants -----------------------------------------------------------------

_logger = getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 5
DEFAULT_BUFFER_SIZE = 8192  # bytes
DEFAULT_PROGRESS_INTERVAL = 5  # seconds
DEFAULT_TRIES = 5

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


class SkipLocation(Exception):
    pass


# -- downloader class ----------------------------------------------------------


class HTTPThreadedDownloader(Downloader):
    """
    Downloader class that uses native Python threads with Requests to handle
    HTTP, HTTPS and proxied download requests by the server.
    """

    def __init__(self, config, event_listener=None, tries=DEFAULT_TRIES, session=None):
        """
        :param config: downloader configuration
        :type config: nectar.config.DownloaderConfig
        :param event_listener: event listener providing life-cycly callbacks
        :type event_listener: nectar.listener.DownloadEventListener
        :param tries: total number of requests made to the remote server,
                      including first unsuccessful one
        :type tries: int
        :param session: The requests Session to use when downloaded. If one
                        is not provided, one will be created and used for the
                        lifetime of this downloader.
        :type  session: requests.Session
        """

        super(HTTPThreadedDownloader, self).__init__(config, event_listener)

        # throttling support
        self._bytes_lock = threading.RLock()
        self._bytes_this_second = 0
        self._time_bytes_this_second_was_cleared = datetime.datetime.now()

        # thread-safety when firing events
        self._event_lock = threading.RLock()

        # default tries to fetch item
        self.tries = tries

        # set of locations that produced a connection error
        self.failed_netlocs = set([])

        self.session = session or build_session(config)

        # Configure an adapter to retry failed requests. See urllib3's documentation
        # for details on each argument.
        retry_conf = retry.Retry(total=tries, connect=tries, read=tries, backoff_factor=1)
        retry_conf.BACKOFF_MAX = 8
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_conf)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

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

    def worker(self, queue):
        """
        :param queue:       queue of DownloadRequest instances
        :type  queue:       WorkerQueue

        """
        try:
            while True:
                request = queue.get()
                if request is None or self.is_canceled:
                    break
                self._fetch(request)
        except:
            msg = _('Unhandled Exception in Worker Thread [%s]') % threading.currentThread().ident
            _logger.exception(msg)
            # cancelling the download in case of unhandled exception, otherwise we will get stuck
            # in the infinite loop in download() method
            self.cancel()

    def download(self, request_list):
        worker_threads = []
        queue = WorkerQueue(request_list)
        self.session = build_session(self.config, self.session)

        _logger.debug('starting workers')
        for i in range(self.max_concurrent):
            worker_thread = threading.Thread(target=self.worker, args=[queue])
            worker_thread.setDaemon(True)
            worker_thread.start()
            worker_threads.append(worker_thread)

        # We want to wait for the queue to be empty and for all worker threads to be completed.
        # Do this with a sleep loop instead of thread joins & thread Events so that signals are
        # able to be intercepted by projects using this library.
        while True:
            still_processing = False
            if not queue.finished and not self.is_canceled:
                still_processing = True
            for thread in worker_threads:
                if thread.is_alive():
                    still_processing = True
            if still_processing:
                time.sleep(1)
            else:
                break

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

    def _download_one(self, request):
        """
        Downloads one url, blocks, and returns a DownloadReport.

        :param request: download request object with details about what to
                        download and where to put it
        :type  request: nectar.request.DownloadRequest

        :return:    download report
        :rtype:     nectar.report.DownloadReport
        """
        self.session = build_session(self.config, self.session)
        return self._fetch(request)

    def _fetch(self, request):
        """
        :param request: download request object with details about what to
                        download and where to put it
        :type  request: nectar.request.DownloadRequest

        :return:    download report
        :rtype:     nectar.report.DownloadReport
        """
        headers = (request.headers or {}).copy()
        ignore_encoding, additional_headers = self._rfc2616_workaround(request)
        headers.update(additional_headers or {})
        max_speed = self._calculate_max_speed()  # None or integer in bytes/second
        report = DownloadReport.from_download_request(request)
        report.download_started()
        self.fire_download_started(report)
        netloc = urlparse.urlparse(request.url).netloc
        try:
            if self.is_canceled or request.canceled:
                raise DownloadCancelled(request.url)

            if netloc in self.failed_netlocs:
                raise SkipLocation()

            _logger.debug("Attempting to connect to {url}.".format(url=request.url))
            response = self.session.get(request.url, headers=headers,
                                        timeout=(self.config.connect_timeout,
                                                 self.config.read_timeout))
            report.headers = response.headers
            self.fire_download_headers(report)

            if response.status_code != httplib.OK:
                raise DownloadFailed(request.url, response.status_code, response.reason)

            progress_interval = self.progress_interval
            file_handle = request.initialize_file_handle()

            last_update_time = datetime.datetime.now()
            self.fire_download_progress(report)

            if ignore_encoding:
                chunks = self.chunk_generator(response.raw, self.buffer_size)
            else:
                chunks = response.iter_content(self.buffer_size)

            for chunk in chunks:
                if self.is_canceled or request.canceled:
                    raise DownloadCancelled(request.url)

                file_handle.write(chunk)

                bytes_read = len(chunk)
                report.bytes_downloaded += bytes_read

                now = datetime.datetime.now()

                if now - last_update_time >= progress_interval:
                    last_update_time = now
                    self.fire_download_progress(report)

                with self._bytes_lock:
                    if now - self._time_bytes_this_second_was_cleared >= ONE_SECOND:
                        self._bytes_this_second = 0
                        self._time_bytes_this_second_was_cleared = now
                    self._bytes_this_second += bytes_read

                if max_speed is not None and self._bytes_this_second >= max_speed:
                    # it's not worth doing fancier mathematics than this, very
                    # fine-grained sleep times [1] are not honored by the system
                    # [1] for example, sleeping the remaining fraction of time
                    # before this second is up
                    time.sleep(0.5)

            # guarantee 1 report at the end
            self.fire_download_progress(report)

        except SkipLocation:
            _logger.debug("Skipping {url} because {netloc} could not be reached.".format(
                url=request.url, netloc=netloc)
            )
            report.download_skipped()

        except requests.ConnectionError as e:
            _logger.warning(_('Skipping requests to {netloc} due to repeated connection'
                              ' failures: {e}').format(netloc=netloc, e=str(e)))
            self.failed_netlocs.add(netloc)
            report.download_connection_error()

        except requests.Timeout:
            """
            Handle a timeout differently than a connection error. Do not add
            to failed_netlocs so that a new connection can be attempted.
            """
            _logger.warning("Request Timeout - Connection with {url} timed out.".format(
                url=request.url)
            )
            report.download_connection_error()

        except DownloadCancelled as e:
            _logger.debug(str(e))
            report.download_canceled()

        except DownloadFailed as e:
            _logger.debug('download failed: %s' % str(e))
            report.error_msg = e.args[2]
            report.error_report['response_code'] = e.args[1]
            report.error_report['response_msg'] = e.args[2]
            report.download_failed()

        except Exception as e:
            _logger.exception(e)
            report.error_msg = str(e)
            report.download_failed()

        else:
            report.download_succeeded()

        request.finalize_file_handle()

        if report.state is DOWNLOAD_SUCCEEDED:
            self.fire_download_succeeded(report)
        else:  # DOWNLOAD_FAILED
            self.fire_download_failed(report)

        return report

    @staticmethod
    def _rfc2616_workaround(request):
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

        return ignore_encoding, headers

    def _calculate_max_speed(self):
        # this incorporates a bit of "fudge factor" into the max_speed due the
        # fact that the system doesn't honor very fine-grained control in while
        # in sleep()
        max_speed = self.config.max_speed

        if max_speed is not None:
            # because we test *after* reading and only sleep for 1/2 second
            max_speed -= (2 * self.buffer_size)
            max_speed = max(max_speed, (2 * self.buffer_size))  # because we cannot go slower

        return max_speed

    def _fire_event_to_listener(self, event_listener_callback, *args, **kwargs):
        # thread-safe event firing
        with self._event_lock:
            super(HTTPThreadedDownloader, self)._fire_event_to_listener(event_listener_callback,
                                                                        *args, **kwargs)

# -- requests utilities --------------------------------------------------------


def build_session(config, session=None):
    if session is None:
        session = requests.Session()
    session.stream = True  # required for reading the download in chunks
    _add_basic_auth(session, config)
    _add_ssl(session, config)
    _add_proxy(session, config)
    session.headers.update(config.get('headers', {}))

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

    # Set session.proxies according to given url and port
    protocol, remainder = urllib.splittype(config.proxy_url)
    host, remainder = urllib.splithost(remainder)
    url = ':'.join((host, str(config.proxy_port)))

    if config.proxy_username:
        password_part = config.get('proxy_password', '') and ':%s' % config.proxy_password
        auth = config.proxy_username + password_part
        auth = urllib.quote(auth, safe=':')
        url = '@'.join((auth, url))

    session.proxies['https'] = '://'.join((protocol, url))
    session.proxies['http'] = '://'.join((protocol, url))

    # Set session.auth if proxy username is specified
    if config.proxy_username is not None:
        proxy_password = config.get('proxy_password', '')
        if None in (config.basic_auth_username, config.basic_auth_password):
            # bz 1021662 - Proxy authentiation using username and password in session.proxies urls
            # does not setup correct headers in the http download request because of a bug in
            # urllib3. This is an alternate approach which sets up the headers correctly.
            session.auth = requests.auth.HTTPProxyAuth(config.proxy_username, proxy_password)
        else:
            # The approach mentioned above works well except when a basic user authentication is
            # used, along with the proxy authentication. Therefore, we define and use a custom class
            # which inherits AuthBase class provided by the requests library to add the headers
            # correctly.
            session.auth = HTTPBasicWithProxyAuth(config.basic_auth_username,
                                                  config.basic_auth_password,
                                                  config.proxy_username,
                                                  proxy_password)

# -- thread-safe generator queue -----------------------------------------------


class WorkerQueue(object):
    """
    Simple, thread-safe, wrapper around an iterable.
    """

    def __init__(self, iterable):
        self._iterable = iterable
        self._generator = _generator_wrapper(self._iterable)

        self._lock = threading.Lock()
        self.finished = False

    def get(self):
        """
        Get the next item from the queue in a thread-safe manner.
        Returns None if the queue is empty.
        :return: next item in the queue or None
        """
        with self._lock:
            try:
                return next(self._generator)
            except StopIteration:
                self.finished = True
            self.finished = True
            return None


def _generator_wrapper(iterable):
    # support next() for iterables, without screwing up iterators or generators
    for i in iterable:
        yield i
