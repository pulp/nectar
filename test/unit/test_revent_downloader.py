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

import mock

import base
import http_static_test_server

from nectar import config, listener, report, request
from nectar.downloaders import revent


class InstantiationTests(base.NectarTests):
    pass


class MockDownloadingTests(base.NectarTests):
    pass


class LiveDownloadingTests(base.NectarTests):

    server = None

    @classmethod
    def setUpClass(cls):
        cls.server = http_static_test_server.HTTPStaticTestServer()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server = None

