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

from nectar.request import DownloadRequest

import base


class DownloadRequestTests(base.NectarTests):
    def test__init__(self):
        url = 'http://www.theonion.com/articles/world-surrenders-to-north-korea,31265/'
        path = '/fake/path'
        request = DownloadRequest(url, path)
        self.assertEqual(request.url, url)
        self.assertEqual(request.destination, path)
