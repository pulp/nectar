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
import itertools
import logging
import os
import urllib

from nectar.downloaders.base import Downloader
from nectar.report import DownloadReport, DOWNLOAD_SUCCEEDED


# -- constants -----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

DEFAULT_BUFFER_SIZE = 1048576 # 1 MB in bytes
DEFAULT_PROGRESS_INTERVAL = 5 # seconds

# -- exceptions ----------------------------------------------------------------

class UnlinkableDestination(Exception):
    """
    Exception thrown when the downloader is configured to use hard or soft
    links, but the destination is a file handle instead of a path.
    """

# -- local file downloader -----------------------------------------------------

class LocalFileDownloader(Downloader):
    """
    Downloader class that handles local file URLs. It has the ability to hard
    link files, symbolic link files, or copy files.
    """

    @property
    def buffer_size(self):
        buffer_size_str = self.config.buffer_size

        if buffer_size_str is None:
            return DEFAULT_BUFFER_SIZE

        try:
            return int(buffer_size_str)
        except ValueError:
            return DEFAULT_BUFFER_SIZE

    @property
    def progress_interval(self):
        if not hasattr(self, '_progress_interval'):
            seconds = self.config.get('progress_interval', DEFAULT_PROGRESS_INTERVAL)
            self._progress_interval = datetime.timedelta(seconds=seconds)
        return self._progress_interval

    @property
    def download_method(self):
        method = self._copy
        if self.config.use_hard_links:
            method = self._hard_link
        if self.config.use_sym_links:
            method = self._symbolic_link
        return method

    # -- public api ------------------------------------------------------------

    def download(self, request_list):

        for report in itertools.imap(self.download_method, request_list):

            if report.state == DOWNLOAD_SUCCEEDED:
                self.fire_download_succeeded(report)

            else: # DOWNLOAD_FAILED
                self.fire_download_failed(report)

    # -- types of downloads ----------------------------------------------------

    def _hard_link(self, request, report=None):
        """
        Hard link the source and destination together.

        :param request: request instance
        :type request: nectar.request.DownloadRequest
        :param report: report instance for the request
        :type report: nectar.report.DownloadReport
        :return: report instance
        :rtype: nectar.report.DownloadReport
        """
        return self._common_link(os.link, request, report)

    def _symbolic_link(self, request, report=None):
        """
        Symbolic link the source and destination together.

        :param request: request instance
        :type request: nectar.request.DownloadRequest
        :param report: report instance for the request
        :type report: nectar.report.DownloadReport
        :return: report instance
        :rtype: nectar.report.DownloadReport
        """
        return self._common_link(os.symlink, request, report)

    def _copy(self, request, report=None):
        """
        Copy the source file to the destination.

        This is the default behavior and most useful for files that live on
        different disk partitions or networked file systems.

        :param request: request instance
        :type request: nectar.request.DownloadRequest
        :param report: report instance for the request
        :type report: nectar.report.DownloadReport
        :return: report instance
        :rtype: nectar.report.DownloadReport
        """

        report = report or DownloadReport.from_download_request(request)
        report.download_started()
        src_handle = None

        try:
            src_path = self._file_path_from_url(request.url)
            src_handle = open(src_path, 'rb')
            dst_handle = request.initialize_file_handle()
            buffer_size = self.buffer_size

            self.fire_download_started(report)
            last_progress_update = datetime.datetime.now()

            while True:

                if self.is_canceled:
                    report.download_cancelled()
                    # NOTE the control flow here will pass through the finally
                    # block on the way out, but not the else block :D
                    return report

                chunk = src_handle.read(buffer_size)

                if not chunk:
                    break

                dst_handle.write(chunk)
                report.bytes_downloaded += len(chunk)

                now = datetime.datetime.now()

                if now - last_progress_update < self.progress_interval:
                    continue

                self.fire_download_progress(report)
                last_progress_update = now

        except Exception, e:
            _LOG.exception(e)
            report.error_msg = str(e)
            report.download_failed()

        else:
            report.download_succeeded()

        finally:
            if src_handle is not None:
                src_handle.close()
            request.finalize_file_handle()

        return report

    # -- common link function --------------------------------------------------

    def _common_link(self, link_method, request, report=None):
        """
        Link files using either a hard link or symbolic link method.

        :param link_method: hard link or symbolic link method
        :type link_method: callable
        :param request: request instance
        :type request: nectar.request.DownloadRequest
        :param report: report instance for the request
        :type report: nectar.report.DownloadReport
        :return: report instance
        :rtype: nectar.report.DownloadReport
        """

        report = report or DownloadReport.from_download_request(request)

        report.download_started()
        self.fire_download_started(report)

        if self.is_canceled:
            report.download_cancelled()
            return report

        try:
            if not isinstance(request.destination, basestring):
                raise UnlinkableDestination(request.destination)

            src_path = self._file_path_from_url(request.url)
            link_method(src_path, request.destination)

            report.bytes_downloaded = os.path.getsize(request.destination)

        except Exception, e:
            _LOG.exception(e)
            report.error_msg = str(e)
            report.download_failed()

        else:
            report.download_succeeded()

        return report

    # -- utility functions -----------------------------------------------------

    def _file_path_from_url(self, url):
        """
        Strip off the url scheme and return the absolute path to the local file.

        :param url: URL to parse
        :type url: basestring
        :return: absolute file path
        :rtype: str
        :raises ValueError: if the URL is not for a local file
        """
        scheme, file_path = urllib.splittype(url)

        if not scheme.startswith('file'):
            raise ValueError('Unsupported scheme: %s' % scheme)

        return file_path

