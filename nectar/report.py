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
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from datetime import datetime
from gettext import gettext as _

from isodate import UTC


class DownloadReport(object):
    """
    Report object for individual downloads.

    :ivar url:              url requested to be downloaded
    :ivar destination:      destination of the downloaded file, either a string representing the
                            filesystem path to the file, or a file-like object
    :ivar state:            current state of the download (waiting, downloading, succeeded, failed,
                            canceled)
    :ivar data:             arbitrary data provided at instantiation
    :ivar total_bytes:      total bytes of the file to be downloaded, None if this could not be
                            determined
    :ivar bytes_downloaded: bytes of the file downloaded so far
    :ivar start_time:       start time of the file download
    :ivar finish_time:      finish time of the file download
    :ivar error_msg:        string field where an error message should be stored. This will likely
                            be displayed to an end user.
    :ivar error_report:     arbitrary dictionary containing debugging info in the event of a
                            failure
    :ivar headers:          dictionary containing response headers if they are
                            available, such as from an http-related downloader.
    """
    DOWNLOAD_WAITING = 'waiting'
    DOWNLOAD_DOWNLOADING = 'downloading'
    DOWNLOAD_SUCCEEDED = 'succeeded'
    DOWNLOAD_FAILED = 'failed'
    DOWNLOAD_CANCELED = 'canceled'

    @classmethod
    def from_download_request(cls, request):
        """
        Factory method for building a report based on a request
        :param request: request to build a report for
        :type request: nectar.request.DownloadRequest
        :return: report for request
        :rtype: nectar.report.DownloadReport
        """
        return cls(request.url, request.destination, request.data)

    def __init__(self, url, destination, data=None):
        """
        :param url:         url requested to be downloaded
        :type  url:         str
        :param destination: destination of the downloaded file, either a string representing the
                            filesystem path to the file, or a file-like object
        :type  destination: str or file-like object
        :param data:        arbitrary data attached to the request instance
        """

        self.url = url
        self.destination = destination
        self.data = data

        self.state = self.DOWNLOAD_WAITING

        self.total_bytes = None
        self.bytes_downloaded = 0

        self.start_time = None
        self.finish_time = None

        self.error_msg = None
        self.error_report = {}

        self.headers = None

    # state management methods -------------------------------------------------

    def download_started(self):
        """
        Mark the report as having started.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls amount to
        no-ops.
        """
        if self.state != self.DOWNLOAD_WAITING:
            return
        self.state = self.DOWNLOAD_DOWNLOADING
        self.start_time = datetime.now(tz=UTC)

    def download_succeeded(self):
        """
        Mark the report as having succeeded.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls to this
        method or download_failed or download_canceled amount to no-ops.
        """
        self._download_finished(self.DOWNLOAD_SUCCEEDED)

    def download_failed(self):
        """
        Mark the report as having failed.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls to this
        method or download_succeeded or download_canceled amount to no-ops.
        """
        # default message in case a downloader doesn't set an error message
        if self.error_msg is None:
            self.error_msg = _('Download Failed')
        self._download_finished(self.DOWNLOAD_FAILED)

    def download_skipped(self):
        """
        Mark that this download has been skipped.
        """
        self.error_msg = _('Download skipped')
        self.state = self.DOWNLOAD_FAILED

    def download_connection_error(self):
        """
        Indicate that a connection error occurred
        """

        self.error_msg = _('A connection error occurred')
        self.state = self.DOWNLOAD_FAILED
        self.finish_time = datetime.now(tz=UTC)

    def download_canceled(self):
        """
        Mark the report as having been canceled.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls to this
        method or download_succeeded or download_failed amount to no-ops.
        """
        self._download_finished(self.DOWNLOAD_CANCELED)

    def _download_finished(self, state):
        if self.state != self.DOWNLOAD_DOWNLOADING:
            return
        self.state = state
        self.finish_time = datetime.now(tz=UTC)


# here for backward-compatibility. It is preferable to access these directly on
# the DownloadReport object.
DOWNLOAD_WAITING = DownloadReport.DOWNLOAD_WAITING
DOWNLOAD_DOWNLOADING = DownloadReport.DOWNLOAD_DOWNLOADING
DOWNLOAD_SUCCEEDED = DownloadReport.DOWNLOAD_SUCCEEDED
DOWNLOAD_FAILED = DownloadReport.DOWNLOAD_FAILED
DOWNLOAD_CANCELED = DownloadReport.DOWNLOAD_CANCELED
