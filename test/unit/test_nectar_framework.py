# -*- coding: utf-8 -*-

from nectar.request import DownloadRequest

import base


class DownloadRequestTests(base.NectarTests):
    def test__init__(self):
        url = 'http://www.fakeurl.com/articles/world-surrenders-to-pulp/'
        path = '/fake/path'
        request = DownloadRequest(url, path)
        self.assertEqual(request.url, url)
        self.assertEqual(request.destination, path)
