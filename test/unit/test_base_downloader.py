from cStringIO import StringIO
import unittest

from nectar.config import DownloaderConfig
from nectar.downloaders.base import Downloader
from nectar.listener import AggregatingEventListener
from nectar.report import DownloadReport
from nectar.request import DownloadRequest


class TestDownloadOne(unittest.TestCase):
    def setUp(self):
        self.downloader = Downloader(DownloaderConfig())
        self.request = DownloadRequest('http://stuff/', StringIO())

    def test_raises_not_implemented(self):
        self.assertRaises(NotImplementedError, self.downloader.download_one, self.request)

    def test_does_not_fire_events(self):
        # collect the success event in this listener if one is fired
        listener = AggregatingEventListener()
        downloader = LyingDownloader(DownloaderConfig(), listener)

        downloader.download_one(self.request)

        self.assertEqual(len(listener.succeeded_reports), 0)

    def test_returns_report(self):
        downloader = LyingDownloader(DownloaderConfig())

        ret = downloader.download_one(self.request)

        self.assertTrue(isinstance(ret, DownloadReport))


class LyingDownloader(Downloader):
    def _download_one(self, request):
        # let's not, but say we did
        report = DownloadReport.from_download_request(request)
        self.fire_download_succeeded(report)
        return report


class TestDownloadReport(unittest.TestCase):

    def setUp(self):
        self.report = DownloadReport("fakeurl", "fakedestination")

    def test_download_connection_error(self):

        self.report.download_connection_error()
        self.assertEqual(self.report.state, self.report.DOWNLOAD_FAILED)
        self.assertEqual(self.report.error_msg, "A connection error occurred")