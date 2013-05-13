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
import os
import random
import shutil
import string
import tempfile
import urllib

import mock

import base
import http_static_test_server

from nectar import config, listener, report, request
from nectar.downloaders import revent

# -- instantiation tests -------------------------------------------------------

class InstantiationTests(base.NectarTests):

    def test_instantiation(self):
        cfg = config.DownloaderConfig()
        lst = listener.DownloadEventListener()

        try:
            downloader = revent.HTTPEventletRequestsDownloader(cfg, lst)
        except:
            self.fail('instantiation of requests eventlet downloader failed')

        self.assertEqual(cfg, downloader.config)
        self.assertEqual(lst, downloader.event_listener)

        self.assertEqual(downloader.buffer_size, revent.DEFAULT_BUFFER_SIZE)
        self.assertEqual(downloader.max_concurrent, revent.DEFAULT_MAX_CONCURRENT)
        self.assertEqual(downloader.progress_interval, datetime.timedelta(seconds=revent.DEFAULT_PROGRESS_INTERVAL))

    def test_build_session(self):
        kwargs = {'basic_auth_username': 'admin',
                  'basic_auth_password': 'admin',
                  'ssl_validation': False,
                  'ssl_client_cert_path': '/etc/pki/bogus/cert.pem',
                  'ssl_client_key_path': '/etc/pki/bogus/key.pem',
                  'proxy_url': 'https://invalid-proxy.com',
                  'proxy_port': 1234,
                  'proxy_username': 'anonymous',
                  'proxy_password': 'anonymous'}
        proxy_host = urllib.splithost(urllib.splittype(kwargs['proxy_url'])[1])[0]

        cfg = config.DownloaderConfig(**kwargs)
        session = revent.build_session(cfg)

        self.assertEqual(session.stream, True)
        self.assertEqual(session.auth, (kwargs['basic_auth_username'], kwargs['basic_auth_password']))
        self.assertEqual(session.cert, (kwargs['ssl_client_cert_path'], kwargs['ssl_client_key_path']))
        self.assertEqual(session.proxies, {'https': '%s:%s@%s:%d' % (kwargs['proxy_username'],
                                                                     kwargs['proxy_password'],
                                                                     proxy_host,
                                                                     kwargs['proxy_port'])})

# -- mocked tests --------------------------------------------------------------

class MockDownloadingTests(base.NectarTests):

    def test_mock_fetch_succeeded(self):
        url_list = _generate_urls(1)
        request_list = [request.DownloadRequest(url, '/tmp/') for url in url_list]
        rep = report.DownloadReport.from_download_request(request_list[0])
        rep.state = report.DOWNLOAD_SUCCEEDED

        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()

        downloader = revent.HTTPEventletRequestsDownloader(cfg, lst)
        downloader._fetch = mock.MagicMock()
        downloader._fetch.return_value = rep

        downloader.download(request_list)

        self.assertEqual(downloader._fetch.call_count, 1)
        self.assertEqual(len(lst.failed_reports), 0)
        self.assertEqual(len(lst.succeeded_reports), 1)

    def test_mock_fetch_failed(self):
        url_list = _generate_urls(1)
        request_list = [request.DownloadRequest(url, '/tmp/') for url in url_list]
        rep = report.DownloadReport.from_download_request(request_list[0])
        rep.state = report.DOWNLOAD_FAILED

        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()

        downloader = revent.HTTPEventletRequestsDownloader(cfg, lst)
        downloader._fetch = mock.MagicMock()
        downloader._fetch.return_value = rep

        downloader.download(request_list)

        self.assertEqual(downloader._fetch.call_count, 1)
        self.assertEqual(len(lst.failed_reports), 1)
        self.assertEqual(len(lst.succeeded_reports), 0)

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
        self.download_dir = tempfile.mkdtemp(prefix='nectar_revent_unit_testing-')

    def tearDown(self):
        super(LiveDownloadingTests, self).tearDown()
        shutil.rmtree(self.download_dir)
        self.download_dir = None

    def test_single_download_success(self):
        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()
        downloader = revent.HTTPEventletRequestsDownloader(cfg, lst)

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
        downloader = revent.HTTPEventletRequestsDownloader(cfg, lst)

        file_name = 'idontexistanddontcreateme'
        file_path = os.path.join(self.data_directory, file_name)
        dest_path = os.path.join(self.download_dir, file_name)
        url = 'http://localhost:%d/%s' % (self.server_port, file_path)
        req = request.DownloadRequest(url, dest_path)

        downloader.download([req])

        self.assertFalse(os.path.exists(dest_path))
        self.assertEqual(len(lst.succeeded_reports), 0)
        self.assertEqual(len(lst.failed_reports), 1)

    def test_multiple_downloads(self):
        cfg = config.DownloaderConfig()
        lst = listener.AggregatingEventListener()
        downloader = revent.HTTPEventletRequestsDownloader(cfg, lst)

        bogus_file_names = ['notme', 'notmeeither']
        all_file_names = self.data_file_names + bogus_file_names
        url_list = ['http://localhost:%d/%s%s' % (self.server_port, self.data_directory, n) for n in all_file_names]
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

