# -*- coding: utf-8 -*-

import os

import requests

import base
from nectar.config import DownloaderConfig, HTTPBasicWithProxyAuth


class InstantiationTests(base.NectarTests):

    @classmethod
    def setUpClass(cls):
        file_dir = os.path.dirname(__file__)
        cls.data_dir = os.path.join(file_dir, 'data')

    def test_empty_instantiation(self):
        try:
            DownloaderConfig()
        except Exception as e:
            self.fail(str(e))

    def test_default_configuration_values(self):
        config = DownloaderConfig()

        self.assertEqual(config.max_concurrent, None)
        self.assertEqual(config.basic_auth_username, None)
        self.assertEqual(config.basic_auth_password, None)
        self.assertEqual(config.ssl_ca_cert, None)
        self.assertEqual(config.ssl_ca_cert_path, None)
        self.assertEqual(config.ssl_client_cert, None)
        self.assertEqual(config.ssl_client_cert_path, None)
        self.assertEqual(config.ssl_client_key, None)
        self.assertEqual(config.ssl_client_key_path, None)
        self.assertEqual(config.ssl_validation, True)
        self.assertEqual(config.proxy_url, None)
        self.assertEqual(config.proxy_port, None)
        self.assertEqual(config.proxy_username, None)
        self.assertEqual(config.proxy_password, None)
        self.assertEqual(config.max_speed, None)
        self.assertEqual(config.headers, None)
        self.assertEqual(config.buffer_size, None)
        self.assertEqual(config.progress_interval, None)
        self.assertEqual(config.use_hard_links, False)
        self.assertEqual(config.use_sym_links, False)
        self.assertEqual(config.connect_timeout, 6.05)
        self.assertEqual(config.read_timeout, 27)

    def test_dict_semantic_default_value(self):
        config = DownloaderConfig(basic_auth_username='username')

        self.assertEqual(config.get('basic_auth_username'), 'username')
        # Make sure passing a default password works.
        self.assertEqual(config.get('basic_auth_password', 'default'), 'default')

    def test_valid_max_concurrent(self):
        config = DownloaderConfig(max_concurrent=3)

        self.assertEqual(config.max_concurrent, 3)

    def test_invalid_key(self):
        """
        Try to instantiate a DownloaderConfig with a non-existing key. This test asserts correct
        behavior for Bug #965764.

        https://bugzilla.redhat.com/show_bug.cgi?id=965764
        """
        self.assertRaises(TypeError, DownloaderConfig, invalid_setting='invalid')

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

    def test_http_basic_with_proxy_auth_config(self):
        username = 'username'
        password = 'password'
        proxy_username = 'proxy_username'
        proxy_password = 'proxy_password'
        basic_plus_proxy_config = HTTPBasicWithProxyAuth(username, password,
                                                         proxy_username, proxy_password)

        request = requests.models.Request()
        basic_plus_proxy_config(request)

        expected_authorization = requests.auth._basic_auth_str(username, password)
        expected_proxy_authorization = requests.auth._basic_auth_str(proxy_username, proxy_password)
        self.assertEquals(request.headers['Authorization'], expected_authorization)
        self.assertEquals(request.headers['Proxy-Authorization'], expected_proxy_authorization)
