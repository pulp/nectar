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


class DownloadReport(object):
    """
    Report object for individual downloads.
    """

    @classmethod
    def from_download_request(cls, request):

        return cls(request.url, request.file_path, request.file_size)

    def __init__(self, url, file_path, file_size=None):

        self.url = url
        self.file_path = file_path
        self.file_size = file_size

        self.bytes_downloaded = 0
        self.start_time = None
        self.finish_time = None
