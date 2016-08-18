import sys
if sys.version_info.major == 3:
    from io import StringIO
    import http.client as httplib
    from urllib.parse import urlparse, quote
else:
    from cStringIO import StringIO
    import httplib
    from urllib import quote
import urllib
import datetime
import os
import random
import shutil
import string
import tempfile
import unittest

import mock
from requests import Response, ConnectionError, Timeout

import base
import http_static_test_server
from nectar import config, listener, request
from nectar.config import DownloaderConfig
from nectar.downloaders import threaded
from nectar.report import DownloadReport
from nectar.request import DownloadRequest


class InstantiationTests(base.NectarTests):
    def test_instantiation(self):
        cfg = config.DownloaderConfig()
        lst = listener.DownloadEventListener()

        try:
            downloader = threaded.HTTPThreadedDownloader(cfg, lst)
        except:
            self.fail('instantiation of requests eventlet downloader failed')

        self.assertEqual(cfg, downloader.config)
        self.assertEqual(lst, downloader.event_listener)

        self.assertEqual(downloader.buffer_size, threaded.DEFAULT_BUFFER_SIZE)
        self.assertEqual(downloader.max_concurrent, threaded.DEFAULT_MAX_CONCURRENT)
        self.assertEqual(downloader.progress_interval,
                         datetime.timedelta(seconds=threaded.DEFAULT_PROGRESS_INTERVAL))

    @mock.patch('nectar.config.DownloaderConfig._process_ssl_settings', mock.Mock())
    def test_requests_kwargs_from_config(self):
        """Assert that a Nectar config is translated to a requests config correctly."""
        nectar_config = DownloaderConfig(
            ssl_ca_cert_path='/tmp/CA.pem',
            ssl_client_cert_path='/tmp/cert.pem',
            ssl_client_key_path='/tmp/key.pem',
        )
        expected_kwargs = {'verify': '/tmp/CA.pem', 'cert': ('/tmp/cert.pem', '/tmp/key.pem')}

        actual = threaded.HTTPThreadedDownloader.requests_kwargs_from_nectar_config(nectar_config)
        self.assertEqual(expected_kwargs, actual)

    def test_requests_kwargs_defaults_secure(self):
        """
        Test that requests_kwargs_from_nectar_config creates a `proxies` kwarg
        and handles a missing password properly.
        """
        nectar_config = DownloaderConfig()
        expected_kwargs = {'verify': True}

        actual = threaded.HTTPThreadedDownloader.requests_kwargs_from_nectar_config(nectar_config)
        self.assertEqual(expected_kwargs, actual)

    def test_requests_kwargs_basic_auth(self):
        """
        Test that requests_kwargs_from_nectar_config creates an `auth` kwarg for basic auth.
        """
        nectar_config = DownloaderConfig(basic_auth_username='test', basic_auth_password='hunter2')
        expected_kwargs = {'verify': True, 'auth': ('test', 'hunter2')}

        actual = threaded.HTTPThreadedDownloader.requests_kwargs_from_nectar_config(nectar_config)
        self.assertEqual(expected_kwargs, actual)

    def test_requests_kwargs_proxy(self):
        """
        Test that requests_kwargs_from_nectar_config creates a `proxies` kwarg.
        """
        nectar_config = DownloaderConfig(proxy_url='http://proxy.example.com', proxy_port=3128)
        expected_kwargs = {
            'verify': True,
            'proxies': {
                'http': 'http://proxy.example.com:3128',
                'https': 'http://proxy.example.com:3128',
            }
        }

        actual = threaded.HTTPThreadedDownloader.requests_kwargs_from_nectar_config(nectar_config)
        self.assertEqual(expected_kwargs, actual)

    def test_requests_kwargs_basic_auth_proxy(self):
        """
        Test that requests_kwargs_from_nectar_config creates a `proxies` kwarg
        with basic auth credentials.
        """
        nectar_config = DownloaderConfig(basic_auth_username='test', basic_auth_password='hunter2',
                                         proxy_url='http://proxy.example.com', proxy_port=3128,
                                         proxy_username='proxy_user', proxy_password='test@123')
        expected_kwargs = {
            'verify': True,
            'auth': ('test', 'hunter2'),
            'proxies': {
                'http': 'http://proxy_user:test@123@proxy.example.com:3128',
                'https': 'http://proxy_user:test@123@proxy.example.com:3128',
            }
        }

        actual = threaded.HTTPThreadedDownloader.requests_kwargs_from_nectar_config(nectar_config)
        self.assertEqual(expected_kwargs, actual)

    def test_configure_session(self):
        kwargs = {'basic_auth_username': 'admin',
                  'basic_auth_password': 'admin',
                  'headers': {'pulp-header': 'awesome!'},
                  'ssl_validation': False,
                  'ssl_client_cert_path': os.path.join(_find_data_directory(),
                                                       'pki/bogus/cert.pem'),
                  'ssl_client_key_path': os.path.join(_find_data_directory(), 'pki/bogus/key.pem'),
                  'proxy_url': 'https://invalid-proxy.com',
                  'proxy_port': 1234,
                  'proxy_username': 'anon?ymous',
                  'proxy_password': 'anonymous$'}
        if sys.version_info.major == 3:
            parsed_url = urlparse(kwargs['proxy_url'])
            proxy_host = parsed_url.hostname
        else:
            proxy_host = urllib.splithost(urllib.splittype(kwargs['proxy_url'])[1])[0]

        cfg = config.DownloaderConfig(**kwargs)
        session = threaded.build_session(cfg)

        self.assertEqual(session.stream, True)
        # other headers get added by the requests library, so we'll just check
        # for the one we added
        self.assertEqual(session.headers.get('pulp-header'), 'awesome!')

        self.assertEqual(session.auth.username, kwargs['basic_auth_username'])
        self.assertEqual(session.auth.password, kwargs['basic_auth_password'])
        self.assertEqual(session.auth.proxy_username, kwargs['proxy_username'])
        self.assertEqual(session.auth.proxy_password, kwargs['proxy_password'])

        self.assertEqual(session.cert,
                         (kwargs['ssl_client_cert_path'], kwargs['ssl_client_key_path']))
        # test proxy username and passwod are url encoded before sending the request
        self.assertEqual(session.proxies,
                         {'http': 'https://%s:%s@%s:%d' % (quote(kwargs['proxy_username']),
                                                           quote(kwargs['proxy_password']),
                                                           proxy_host,
                                                           kwargs['proxy_port']),
                          'https': 'https://%s:%s@%s:%d' % (quote(kwargs['proxy_username']),
                                                            quote(kwargs['proxy_password']),
                                                            proxy_host,
                                                            kwargs['proxy_port'])})

    def test_empty_string_proxy_username(self):
        """
        Yoram Hekma submitted a patch[0] that ensured that an empty string in the proxy username
        would not count as the user supplying a username. This test ensures that behavior is tested.

        [0] https://github.com/pulp/nectar/pull/47
        """
        kwargs = {'proxy_url': 'https://invalid-proxy.com',
                  'proxy_port': 1234,
                  'proxy_username': '',
                  'proxy_password': ''}
        """
        urllib.splittype("https://invalid-proxy.com")
        ('https', '//invalid-proxy.com')
        urllib.splithost(urllib.splittype("https://invalid-proxy.com")[1])
        ('invalid-proxy.com', '')

        """
        if sys.version_info.major == 3:
            parsed_url = urlparse(kwargs['proxy_url'])
            proxy_host = parsed_url.hostname
        else:
            proxy_host = urllib.splithost(urllib.splittype(kwargs['proxy_url'])[1])[0]

        cfg = config.DownloaderConfig(**kwargs)
        session = threaded.build_session(cfg)

        self.assertEqual(session.stream, True)
        self.assertFalse(hasattr(session.auth, 'proxy_username'))
        self.assertFalse(hasattr(session.auth, 'proxy_password'))

        # Since the user provided the empty string for the proxy username, the username and password
        # should be missing in the session proxies.
        self.assertEqual(session.proxies,
                         {'http': 'https://%s:%d' % (proxy_host, kwargs['proxy_port']),
                          'https': 'https://%s:%d' % (proxy_host, kwargs['proxy_port'])})


# -- "live" tests --------------------------------------------------------------

class LiveDownloadingTests(base.NectarTests):
    data_directory = None
    data_file_names = ['100K_file', '500K_file', '1M_file']
    data_file_sizes = [102400, 512000, 1048576]

    server = None
    server_port = 8088

    @classmethod
    def setUpClass(cls):
        cls.data_directory = _find_data_directory()
        cls.server = http_static_test_server.HTTPStaticTestServer(port=cls.server_port)
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server = None
        cls.data_directory = None

    def setUp(self):
        super(LiveDownloadingTests, self).setUp()
        self.download_dir = tempfile.mkdtemp(prefix='nectar_threaded_unit_testing-')

    def tearDown(self):
        super(LiveDownloadingTests, self).tearDown()
        shutil.rmtree(self.download_dir)
        self.download_dir = None

    def test_single_download_success(self):
        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()
        downloader = threaded.HTTPThreadedDownloader(cfg, lst)

        file_path = os.path.join(self.data_directory, self.data_file_names[0])
        dest_path = os.path.join(self.download_dir, self.data_file_names[0])
        url = 'http://localhost:%d/%s' % (self.server_port, file_path)
        req = request.DownloadRequest(url, dest_path)

        downloader.download([req])

        self.assertTrue(os.path.exists(dest_path))
        self.assertEqual(os.path.getsize(dest_path), self.data_file_sizes[0])
        self.assertEqual(len(lst.succeeded_reports), 1)
        self.assertEqual(len(lst.failed_reports), 0)

    def test_single_download_failure(self):
        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()
        downloader = threaded.HTTPThreadedDownloader(cfg, lst)

        file_name = 'idontexistanddontcreateme'
        file_path = os.path.join(self.data_directory, file_name)
        dest_path = os.path.join(self.download_dir, file_name)
        url = 'http://localhost:%d/%s' % (self.server_port, file_path)
        req = request.DownloadRequest(url, dest_path)

        downloader.download([req])

        self.assertFalse(os.path.exists(dest_path))
        self.assertEqual(len(lst.succeeded_reports), 0)
        self.assertEqual(len(lst.failed_reports), 1)
        self.assertTrue(lst.failed_reports[0].error_msg is not None)

    def test_download_unhandled_exception(self):
        with mock.patch('nectar.downloaders.threaded._logger') as mock_logger:
            cfg = config.DownloaderConfig()
            lst = listener.AggregatingEventListener()
            downloader = threaded.HTTPThreadedDownloader(cfg, lst, session=mock.Mock())
            downloader._fetch = mock.Mock(side_effect=OSError)

            downloader.download([mock.Mock()])

            self.assertTrue(downloader.is_canceled)

            expected_log_message = 'Unhandled Exception in Worker Thread'
            log_calls = [mock_call[1][0] for mock_call in mock_logger.mock_calls]
            self.assertIn(expected_log_message, log_calls[1])

    def test_multiple_downloads(self):
        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()
        downloader = threaded.HTTPThreadedDownloader(cfg, lst)

        bogus_file_names = ['notme', 'notmeeither']
        all_file_names = self.data_file_names + bogus_file_names
        url_list = ['http://localhost:%d/%s%s' % (self.server_port, self.data_directory, n) for n in
                    all_file_names]
        dest_list = [os.path.join(self.download_dir, n) for n in all_file_names]
        request_list = [request.DownloadRequest(u, d) for u, d in zip(url_list, dest_list)]

        downloader.download(request_list)

        self.assertEqual(len(lst.succeeded_reports), len(self.data_file_names))
        self.assertEqual(len(lst.failed_reports), len(bogus_file_names))

        for i, dest in enumerate(dest_list[:len(self.data_file_names)]):
            self.assertTrue(os.path.exists(dest))
            self.assertEqual(os.path.getsize(dest), self.data_file_sizes[i])

        for dest in dest_list[len(self.data_file_names):]:
            self.assertFalse(os.path.exists(dest))

    def test_throttling(self):
        two_seconds = datetime.timedelta(seconds=2)
        three_seconds = datetime.timedelta(seconds=4)

        cfg = config.DownloaderConfig(max_speed=256000)  # 1/2 size of file
        lst = listener.AggregatingEventListener()
        downloader = threaded.HTTPThreadedDownloader(cfg, lst)

        # use the 500k file, should take >= 2 seconds to download, but < 4
        file_path = os.path.join(self.data_directory, self.data_file_names[1])
        dest_path = os.path.join(self.download_dir, self.data_file_names[1])

        url = 'http://localhost:%d/%s' % (self.server_port, file_path)
        req = request.DownloadRequest(url, dest_path)

        start = datetime.datetime.now()
        downloader.download([req])
        finish = datetime.datetime.now()

        self.assertTrue(finish - start >= two_seconds)
        self.assertTrue(finish - start < three_seconds)


class TestFetch(unittest.TestCase):
    def setUp(self):
        self.config = config.DownloaderConfig()
        self.listener = listener.AggregatingEventListener()
        self.session = mock.Mock()
        self.downloader = threaded.HTTPThreadedDownloader(self.config, self.listener,
                                                          session=self.session)

    def test_request_headers(self):
        URL = 'http://fakeurl/robots.txt'
        req = DownloadRequest(URL, StringIO(), headers={'pulp_header': 'awesome!'})
        response = Response()
        response.status_code = httplib.OK
        response.raw = StringIO('abc')
        self.session.get = mock.MagicMock(return_value=response, spec_set=self.session.get)

        self.downloader._fetch(req)

        self.session.get.assert_called_once_with(
            URL,
            headers={'pulp_header': 'awesome!'},
            timeout=(self.config.connect_timeout, self.config.read_timeout),
            verify=True,
        )

    @mock.patch('nectar.downloaders.threaded.DownloadReport.from_download_request')
    def test_request_cancel(self, mock_from_request):
        url = 'http://fakeurl/robots.txt'
        req = DownloadRequest(url, mock.Mock())
        req.canceled = True

        self.downloader._fetch(req)
        mock_from_request.return_value.download_canceled.assert_called_once_with()

    def test_response_headers(self):
        """
        Make sure that whatever headers come back on the response get added
        to the report.
        """
        URL = 'http://fakeurl/robots.txt'
        req = DownloadRequest(URL, StringIO(), headers={'pulp_header': 'awesome!'})
        response = Response()
        response.status_code = httplib.OK
        response.headers = {'content-length': '1024'}
        response.raw = StringIO('abc')
        self.session.get.return_value = response

        report = self.downloader._fetch(req)

        self.assertEqual(report.headers['content-length'], '1024')

    def test_wrong_content_encoding(self):
        URL = 'http://fakeurl/primary.xml.gz'
        req = DownloadRequest(URL, StringIO())
        response = Response()
        response.status_code = httplib.OK
        response.raw = StringIO('abc')
        self.session.get.return_value = response

        report = self.downloader._fetch(req)

        self.assertEqual(report.state, report.DOWNLOAD_SUCCEEDED)
        self.assertEqual(report.bytes_downloaded, 3)
        self.session.get.assert_called_once_with(URL, headers={'accept-encoding': ''},
                                                 timeout=(self.config.connect_timeout,
                                                          self.config.read_timeout),
                                                 verify=True)

    def test_normal_content_encoding(self):
        URL = 'http://fakeurl/primary.xml'
        req = DownloadRequest(URL, StringIO())
        response = Response()
        response.status_code = httplib.OK
        response.iter_content = mock.MagicMock(return_value=['abc'], spec_set=response.iter_content)
        self.session.get = mock.MagicMock(return_value=response, spec_set=self.session.get)

        report = self.downloader._fetch(req)

        self.assertEqual(report.state, report.DOWNLOAD_SUCCEEDED)
        self.assertEqual(report.bytes_downloaded, 3)
        # passing "None" for headers lets the requests library add whatever
        # headers it thinks are appropriate.
        self.session.get.assert_called_once_with(
            URL, headers={}, timeout=(self.config.connect_timeout, self.config.read_timeout), verify=True)

    def test_fetch_with_connection_error(self):
        """
        Test that the report state is failed and that the baseurl is not tried again.
        """

        # requests.ConnectionError
        def connection_error(*args, **kwargs):
            raise ConnectionError()

        with mock.patch('nectar.downloaders.threaded._logger') as mock_logger:
            URL = 'http://fakeurl/primary.xml'
            req = DownloadRequest(URL, StringIO())
            self.session.get = connection_error
            try:
                report = self.downloader._fetch(req)
            except ConnectionError:
                raise AssertionError("ConnectionError should be raised")

            self.assertEqual(report.state, report.DOWNLOAD_FAILED)
            self.assertIn('fakeurl', self.downloader.failed_netlocs)

            report2 = self.downloader._fetch(req)

            self.assertEqual(report2.state, report2.DOWNLOAD_FAILED)

            expected_log_message = "Skipping requests to fakeurl due to repeated " \
                                   "connection failures: "
            log_calls = [mock_call[1][0] for mock_call in mock_logger.mock_calls]

            self.assertIn(expected_log_message, log_calls)

    def test_fetch_with_timeout(self):
        """
        Test that the report state is failed and that the baseurl can be tried again.
        """

        with mock.patch('nectar.downloaders.threaded._logger') as mock_logger:
            URL = 'http://fakeurl/primary.xml'
            req = DownloadRequest(URL, StringIO())
            self.session.get.side_effect = Timeout
            report = self.downloader._fetch(req)

            self.assertEqual(report.state, report.DOWNLOAD_FAILED)
            self.assertNotIn('fakeurl', self.downloader.failed_netlocs)

            session2 = threaded.build_session(self.config)
            session2.get = mock.MagicMock()
            report2 = self.downloader._fetch(req)

            self.assertEqual(report2.state, report2.DOWNLOAD_FAILED)
            self.assertEqual(self.session.get.call_count, 2)

            expected_log_message = "Request Timeout - Connection with " \
                                   "http://fakeurl/primary.xml timed out."
            log_calls = [mock_call[1][0] for mock_call in mock_logger.mock_calls]

            self.assertIn(expected_log_message, log_calls)


class TestDownloadOne(unittest.TestCase):
    @mock.patch.object(threaded.HTTPThreadedDownloader, '_fetch', spec_set=True)
    def test_calls_fetch(self, mock_fetch):
        config = DownloaderConfig()
        request = DownloadRequest('http://foo', StringIO())
        report = DownloadReport.from_download_request(request)
        downloader = threaded.HTTPThreadedDownloader(config)
        mock_fetch.return_value = report

        ret = downloader._download_one(request)

        self.assertEqual(mock_fetch.call_count, 1)
        self.assertTrue(ret is report)
        self.assertTrue(mock_fetch.call_args[0][0] is request)


# -- utilities -----------------------------------------------------------------


def _find_data_directory():
    potential_directory = 'test/unit/data/'
    while potential_directory:
        if os.path.exists(potential_directory):
            return potential_directory
        potential_directory = potential_directory.split('/', 1)[1]
    raise RuntimeError('cannot find data directory')


def _generate_urls(num_urls, host_url='http://10.20.30.40/', path_prefix=''):
    file_names = [''.join(random.sample(string.letters, 7)) for i in range(num_urls)]
    return [urllib.basejoin(host_url, path_prefix + f) for f in file_names]
