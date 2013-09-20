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

import os

import base

from nectar.config import DownloaderConfig


class InstantiationTests(base.NectarTests):

    @classmethod
    def setUpClass(cls):
        file_dir = os.path.dirname(__file__)
        cls.data_dir = os.path.join(file_dir, 'data')

    def test_empty_instantiation(self):
        try:
            DownloaderConfig()
        except Exception, e:
            self.fail(str(e))

    def test_default_configuration_value(self):
        config = DownloaderConfig(foo=True, bar=False)

        self.assertTrue(config.foo)
        self.assertFalse(config.bar)
        self.assertEqual(config.baz, None)

    def test_dict_semantic_default_value(self):
        config = DownloaderConfig(key_1='value_1')

        self.assertEqual(config.get('key_1'), 'value_1')
        self.assertEqual(config.get('key_2', 'value_2'), 'value_2')

    def test_valid_max_concurrent(self):
        config = DownloaderConfig(max_concurrent=3)

        self.assertEqual(config.max_concurrent, 3)

    def test_invalid_max_concurrent(self):
        self.assertRaises(ValueError, DownloaderConfig, max_concurrent=-1)

    def test_ssl_data_config_value(self):
        ca_cert_value = 'test cert'
        config = DownloaderConfig(ssl_ca_cert=ca_cert_value)

        # temporary file created
        self.assertTrue(os.path.exists(config.ssl_ca_cert_path))
        # same contents as data value
        self.assertEqual(ca_cert_value, open(config.ssl_ca_cert_path).read())

        config.finalize()

        # temporary file removed
        self.assertFalse(os.path.exists(config.ssl_ca_cert_path))

    def test_ssl_file_config_value(self):
        cert_file = os.path.join(self.data_dir, 'pki', 'bogus', 'cert.pem')
        key_file = os.path.join(self.data_dir, 'pki', 'bogus', 'key.pem')

        cert_contents = open(cert_file).read()
        key_contents = open(key_file).read()

        config = DownloaderConfig(ssl_client_cert_path=cert_file,
                                  ssl_client_key_path=key_file)

        self.assertEqual(cert_contents, config.ssl_client_cert)
        self.assertEqual(key_contents, config.ssl_client_key)

    def test_invalid_file_config_value(self):
        cert_file = '/path/to/nowhere'
        self.assertRaises(AttributeError, DownloaderConfig, ssl_client_cert_path=cert_file)

    def test_conflicting_ssl_config_values(self):
        key_file = os.path.join(self.data_dir, 'pki', 'bogus', 'key.pem')
        key_data = 'keyboard'
        self.assertRaises(AttributeError, DownloaderConfig,
                          ssl_client_key=key_data,
                          ssl_client_key_path=key_file)

