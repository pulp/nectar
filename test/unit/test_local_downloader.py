# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import tempfile
import sys
if sys.version_info.major == 3:
    from io import StringIO
    builtin_name = 'builtins.open'
    from unittest.mock import patch
else:
    from cStringIO import StringIO
    builtin_name = '__builtin__.open'
    from mock import patch
import unittest
import mock

from nectar.config import DownloaderConfig
from nectar.downloaders import local
from nectar.listener import AggregatingEventListener
from nectar.report import DownloadReport
from nectar.request import DownloadRequest

import base


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATA_FILES = ['100K_file', '500K_file', '1M_file']


class InstantiationTests(base.NectarTests):

    def test_instantiation(self):
        config = DownloaderConfig()

        try:
            local.LocalFileDownloader(config)

        except Exception as e:
            self.fail(str(e))

    def test_progress_interval(self):
        # check the default
        default_progress_interval = datetime.timedelta(seconds=local.DEFAULT_PROGRESS_INTERVAL)
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)

        self.assertFalse(hasattr(downloader, '_progress_interval'))
        self.assertEqual(downloader.progress_interval, default_progress_interval)
        self.assertTrue(hasattr(downloader, '_progress_interval'))

        # check configured value
        ten_second_interval = datetime.timedelta(seconds=10)
        config = DownloaderConfig(progress_interval=10)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.progress_interval, ten_second_interval)

    def test_download_method(self):
        # check the default
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.download_method, downloader._copy)

        # check configured hard links
        config = DownloaderConfig(use_hard_links=True)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.download_method, downloader._hard_link)

        # check configured symbolic links
        config = DownloaderConfig(use_sym_links=True)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.download_method, downloader._symbolic_link)


class DownloadTests(base.NectarTests):

    def setUp(self):
        super(DownloadTests, self).setUp()
        print("\t\nSETUP\t\n")
        self.dest_dir = tempfile.mkdtemp(prefix='nectar-local-testing-', dir='.')

    def tearDown(self):
        super(DownloadTests, self).tearDown()
        shutil.rmtree(self.dest_dir)

    def _make_requests(self, data_file_names=DATA_FILES):
        requests = []

        for d in data_file_names:
            src_url = 'file:/' + os.path.join(DATA_DIR, d)
            dest_path = os.path.join(self.dest_dir, d)
            requests.append(DownloadRequest(src_url, dest_path))

        return requests


class GoodDownloadTests(DownloadTests):

    def test_hard_link(self):
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)
        request_list = self._make_requests(DATA_FILES[:1])

        downloader._hard_link(request_list[0])

        cor_path = os.path.join(DATA_DIR, DATA_FILES[0])
        print("cor_path:")
        print(cor_path)
        src_stat = os.stat(cor_path)
        cor_dst = request_list[0].destination
        print("cor_dst:")
        print(cor_dst)
        dst_stat = os.stat(cor_dst)

        self.assertEqual(src_stat.st_ino, dst_stat.st_ino)
        self.assertEqual(src_stat.st_nlink, 2)

    def test_hard_link_download(self):
        config = DownloaderConfig(use_hard_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)
        request_list = self._make_requests(DATA_FILES[:1])
        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 1)
        self.assertEqual(len(listener.failed_reports), 0)

        src_stat = os.stat(os.path.join(DATA_DIR, DATA_FILES[0]))
        dst_stat = os.stat(request_list[0].destination)

        self.assertEqual(src_stat.st_ino, dst_stat.st_ino)
        self.assertEqual(src_stat.st_nlink, 2)

    def test_symbolic_link(self):
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)
        request_list = self._make_requests(DATA_FILES[:1])

        downloader._symbolic_link(request_list[0])

        self.assertTrue(os.path.islink(request_list[0].destination))

    def test_symbolic_link_download(self):
        config = DownloaderConfig(use_sym_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)
        request_list = self._make_requests(DATA_FILES[:1])
        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 1)
        self.assertEqual(len(listener.failed_reports), 0)

        self.assertTrue(os.path.islink(request_list[0].destination))

    @patch('nectar.report.DownloadReport.download_canceled')
    def test_common_link_canceled(self, mock_canceled):
        downloader = local.LocalFileDownloader(DownloaderConfig())
        downloader.cancel()
        request = DownloadRequest('file://' + __file__, '/bar')

        downloader._common_link(mock.MagicMock(), request)

        # make sure the cancel method was called on the report
        mock_canceled.assert_called_once_with()

    def test_copy(self):
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)
        request_list = self._make_requests(DATA_FILES[:1])

        downloader._copy(request_list[0])

        src_stat = os.stat(os.path.join(DATA_DIR, DATA_FILES[0]))
        dst_stat = os.stat(request_list[0].destination)

        self.assertEqual(src_stat.st_size, dst_stat.st_size)
        self.assertNotEqual(src_stat.st_ino, dst_stat.st_ino)

    @patch(builtin_name)
    @patch('nectar.report.DownloadReport.download_canceled')
    def test_copy_canceled(self, mock_canceled, mock_open):
        downloader = local.LocalFileDownloader(DownloaderConfig())
        downloader.cancel()
        request = DownloadRequest('file://' + __file__, '/bar')

        downloader._copy(request)

        # make sure the cancel method was called on the report
        mock_canceled.assert_called_once_with()
        # make sure the no writing was attempted
        self.assertEqual(mock_open.return_value.write.call_count, 0)

    @patch(builtin_name)
    @patch('nectar.report.DownloadReport.download_canceled')
    def test_copy_canceled_single_request(self, mock_canceled, mock_open):
        downloader = local.LocalFileDownloader(DownloaderConfig())
        request = DownloadRequest('file://' + __file__, '/bar')
        request.canceled = True

        downloader._copy(request)

        # make sure the cancel method was called on the report
        mock_canceled.assert_called_once_with()
        # make sure the no writing was attempted
        self.assertEqual(mock_open.return_value.write.call_count, 0)

    def test_copy_download(self):
        config = DownloaderConfig()
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)
        request_list = self._make_requests(DATA_FILES[:1])
        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 1)
        self.assertEqual(len(listener.failed_reports), 0)

        src_stat = os.stat(os.path.join(DATA_DIR, DATA_FILES[0]))
        dst_stat = os.stat(request_list[0].destination)

        self.assertEqual(src_stat.st_size, dst_stat.st_size)
        self.assertNotEqual(src_stat.st_ino, dst_stat.st_ino)


class PerformanceDownloadTests(DownloadTests):

    def test_copy(self):
        config = DownloaderConfig()
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)
        request_list = self._make_requests(DATA_FILES)
        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), len(request_list))
        self.assertEqual(len(listener.failed_reports), 0)


class BadDownloadTests(DownloadTests):

    def test_unsupported_url_scheme(self):
        config = DownloaderConfig(use_sym_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request = DownloadRequest('http://thiswontwork.com',
                                  os.path.join(self.dest_dir, 'doesnt.even.matter'))

        downloader.download([request])

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)

    def test_unlinkable_destination(self):
        config = DownloaderConfig(use_hard_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request_list = self._make_requests(DATA_DIR[:1])
        request_list[0].destination = StringIO()

        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)

    @patch('nectar.downloaders.local.logger')
    def test__copy_when_source_not_found(self, mock_logger):
        """
        Test that nectar properly handles an attempt to copy local files
        that do not exist.
        """
        config = DownloaderConfig(use_sym_links=False)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request = DownloadRequest('file://i/dont/exist',
                                  os.path.join(self.dest_dir, 'doesnt.even.matter'))
        downloader.download([request])

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)

        debug_messages = ''.join([mock_call[1][0][1] for mock_call in mock_logger.debug.mock_calls])
        self.assertTrue('No such file or directory' in debug_messages)
        self.assertEqual(mock_logger.exception.call_count, 0)

    def test__common_link_when_source_not_found(self):
        """
        Test that nectar properly handles an attempt to link local files
        that do not exist.
        """
        config = DownloaderConfig(use_sym_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request = DownloadRequest('file://i/dont/exist',
                                  os.path.join(self.dest_dir, 'doesnt.even.matter'))
        downloader.download([request])

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)

        self.assertTrue('No such file or directory' in listener.failed_reports[0].error_msg)

    def test_destination_not_found(self):

        config = DownloaderConfig(use_sym_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request_list = self._make_requests(DATA_DIR[:1])
        request_list[0].destination = '/i/dont/exist/' + DATA_FILES[0]

        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)

    def test_source_bad_permissions(self):
        config = DownloaderConfig(use_sym_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request = DownloadRequest('file://root/no',
                                  os.path.join(self.dest_dir, 'doesnt.even.matter'))

        downloader.download([request])

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)

    def test_destination_bad_permissions(self):
        config = DownloaderConfig(use_sym_links=True)
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)

        request_list = self._make_requests(DATA_DIR[:1])
        request_list[0].destination = '/' + DATA_FILES[0]

        downloader.download(request_list)

        self.assertEqual(len(listener.succeeded_reports), 0)
        self.assertEqual(len(listener.failed_reports), 1)


class TestDownloadOne(unittest.TestCase):
    def test_calls_download_method(self):
        config = DownloaderConfig()
        listener = AggregatingEventListener()
        downloader = local.LocalFileDownloader(config, listener)
        request = DownloadRequest('http://foo', StringIO())
        report = DownloadReport.from_download_request(request)

        # mock _copy, which is the default function to which requests are passed
        with mock.patch.object(downloader, '_copy') as mock_method:
            mock_method.return_value = report

            ret = downloader._download_one(request)

            self.assertEqual(ret, report)
            mock_method.assert_called_once_with(request)
