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

from cStringIO import StringIO
import datetime
import httplib
import os
import random
import shutil
import string
import tempfile
import unittest
import urllib

import mock
from requests import Response, Session

import base
import http_static_test_server

from nectar import config, listener, request
from nectar.config import DownloaderConfig
from nectar.downloaders import threaded
from nectar.report import DownloadReport
from nectar.request import DownloadRequest

# -- instantiation tests -------------------------------------------------------


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

    def test_build_session(self):
        kwargs = {'basic_auth_username': 'admin',
                  'basic_auth_password': 'admin',
                  'headers': {'pulp-header': 'awesome!'},
                  'ssl_validation': False,
                  'ssl_client_cert_path': os.path.join(_find_data_directory(),
                                                       'pki/bogus/cert.pem'),
                  'ssl_client_key_path': os.path.join(_find_data_directory(), 'pki/bogus/key.pem'),
                  'proxy_url': 'https://invalid-proxy.com',
                  'proxy_port': 1234,
                  'proxy_username': 'anonymous',
                  'proxy_password': 'anonymous'}
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
        self.assertEqual(session.proxies,
                         {'http': 'https://%s:%s@%s:%d' % (kwargs['proxy_username'],
                                                           kwargs['proxy_password'],
                                                           proxy_host,
                                                           kwargs['proxy_port']),
                          'https': 'https://%s:%s@%s:%d' % (kwargs['proxy_username'],
                                                            kwargs['proxy_password'],
                                                            proxy_host,
                                                            kwargs['proxy_port'])})


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
        self.downloader = threaded.HTTPThreadedDownloader(self.config, self.listener)

    def test_request_headers(self):
        URL = 'http://pulpproject.org/robots.txt'
        req = DownloadRequest(URL, StringIO(), headers={'pulp_header': 'awesome!'})
        response = Response()
        response.status_code = httplib.OK
        response.raw = StringIO('abc')
        session = threaded.build_session(self.config)
        session.get = mock.MagicMock(return_value=response, spec_set=session.get)

        self.downloader._fetch(req, session)

        session.get.assert_called_once_with(URL, headers={'pulp_header': 'awesome!'})

    def test_response_headers(self):
        """
        Make sure that whatever headers come back on the response get added
        to the report.
        """
        URL = 'http://pulpproject.org/robots.txt'
        req = DownloadRequest(URL, StringIO(), headers={'pulp_header': 'awesome!'})
        response = Response()
        response.status_code = httplib.OK
        response.headers = {'content-length': '1024'}
        response.raw = StringIO('abc')
        session = threaded.build_session(self.config)
        session.get = mock.MagicMock(return_value=response, spec_set=session.get)

        report = self.downloader._fetch(req, session)

        self.assertEqual(report.headers['content-length'], '1024')

    def test_wrong_content_encoding(self):
        URL = 'http://pulpproject.org/primary.xml.gz'
        req = DownloadRequest(URL, StringIO())
        response = Response()
        response.status_code = httplib.OK
        response.raw = StringIO('abc')
        session = threaded.build_session(self.config)
        session.get = mock.MagicMock(return_value=response, spec_set=session.get)

        report = self.downloader._fetch(req, session)

        self.assertEqual(report.state, report.DOWNLOAD_SUCCEEDED)
        self.assertEqual(report.bytes_downloaded, 3)
        session.get.assert_called_once_with(URL, headers={'accept-encoding': ''})

    def test_normal_content_encoding(self):
        URL = 'http://pulpproject.org/primary.xml'
        req = DownloadRequest(URL, StringIO())
        response = Response()
        response.status_code = httplib.OK
        response.iter_content = mock.MagicMock(return_value=['abc'], spec_set=response.iter_content)
        session = threaded.build_session(self.config)
        session.get = mock.MagicMock(return_value=response, spec_set=session.get)

        report = self.downloader._fetch(req, session)

        self.assertEqual(report.state, report.DOWNLOAD_SUCCEEDED)
        self.assertEqual(report.bytes_downloaded, 3)
        # passing "None" for headers lets the requests library add whatever
        # headers it thinks are appropriate.
        session.get.assert_called_once_with(URL, headers={})


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
        self.assertTrue(isinstance(mock_fetch.call_args[0][1], Session))


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
