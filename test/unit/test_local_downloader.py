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

from nectar.config import DownloaderConfig
from nectar.downloaders import local

import base


class InstantiationTests(base.NectarTests):

    def test_instantiation(self):
        config = DownloaderConfig()

        try:
            local.LocalFileDownloader(config)

        except Exception, e:
            self.fail(str(e))

    def test_max_concurrent(self):
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.max_concurrent, local.DEFAULT_MAX_CONCURRENT)

        ten = 10
        config = DownloaderConfig(max_concurrent=ten)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.max_concurrent, ten)

    def test_progress_interval(self):
        default_progress_interval = datetime.timedelta(seconds=local.DEFAULT_PROGRESS_INTERVAL)
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)

        self.assertFalse(hasattr(downloader, '_progress_interval'))
        self.assertEqual(downloader.progress_interval, default_progress_interval)
        self.assertTrue(hasattr(downloader, '_progress_interval'))

        ten_second_interval = datetime.timedelta(seconds=10)
        config = DownloaderConfig(progress_interval=10)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.progress_interval, ten_second_interval)

    def test_download_method(self):
        config = DownloaderConfig()
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.download_method, downloader._copy)

        config = DownloaderConfig(use_hard_links=True)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.download_method, downloader._hard_link)

        config = DownloaderConfig(use_sym_links=True)
        downloader = local.LocalFileDownloader(config)

        self.assertEqual(downloader.download_method, downloader._symbolic_link)

