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

import os
import tempfile

import requests


class DownloaderConfig(object):
    """
    Downloader configuration class that represents the type of download backend,
    as well as its configuration. Instances of this class are used by the
    download factory to determine which download backend to use.
    """
    def __init__(
            self, max_concurrent=None, basic_auth_username=None, basic_auth_password=None,
            ssl_ca_cert=None, ssl_ca_cert_path=None, ssl_client_cert=None,
            ssl_client_cert_path=None, ssl_client_key=None, ssl_client_key_path=None,
            ssl_validation=True, proxy_url=None, proxy_port=None, proxy_username=None,
            proxy_password=None, max_speed=None, headers=None, buffer_size=None,
            progress_interval=None, use_hard_links=False, use_sym_links=False):
        """
        Initialize the DownloaderConfig. All parameters are optional. Not all downloaders use each
        of the configuration items, so for each parameter documented below, the downloaders that
        use it are listed in parenthesis.

        :param max_concurrent:       maximum number of downloads to run concurrently (Threaded)
        :type  max_concurrent:       int
        :param basic_auth_username:  http basic auth username (basic_auth_password must also be
                                     provided) (Threaded)
        :type  basic_auth_username:  basestring
        :param basic_auth_password:  http basic auth password (basic_auth_username must also be
                                     provided) (Threaded)
        :type  basic_auth_password:  basestring
        :param ssl_ca_cert:          certificate authority cert for secure connections (https
                                     protocol only) (Threaded)
        :type  ssl_ca_cert:          basestring
        :param ssl_ca_cert_path:     path to a ssl ca cert (incompatible with ssl_ca_cert)
                                     (Threaded)
        :type  ssl_ca_cert_path:     basestring
        :param ssl_client_cert:      client certificate for secure connections (https protocol
                                     only) (Threaded)
        :type  ssl_client_cert:      basestring
        :param ssl_client_cert_path: path to a ssl client cert (incompatible with ssl_client_cert)
                                     (Threaded)
        :type  ssl_client_cert_path: basestring
        :param ssl_client_key:       client private key for secure connections (https protocol
                                     only) (Threaded)
        :type  ssl_client_key:       basestring
        :param ssl_client_key_path:  path to a ssl client key (incompatible with ssl_client_key)
                                     (Threaded)
        :type  ssl_client_key_path:  basestring
        :param ssl_validation:       If set to True, the downloader will verify that the remote
                                     server's SSL certificate is signed by a trusted authority, and
                                     that the certificate's CommonName field equals the hostname we
                                     are connecting to. If False, no such verification is made.
                                     ssl_validation defaults to True. (Threaded)
        :type  ssl_validation:       bool
        :param proxy_url:            The URL of a proxy server that should be used while retrieving
                                     content. It should be of the form
                                     <scheme>://<hostname>/ where the scheme is http or https.
                                     (Threaded)
        :type  proxy_url:            basestring
        :param proxy_port:           The port on the proxy server to connect to. (Threaded)
        :type  proxy_port:           int
        :param proxy_username:       The username to use when authenticating with the proxy server
                                     (Threaded)
        :type  proxy_username:       basestring
        :param proxy_password:       The password to use when authenticating with the proxy server
                                     (Threaded)
        :type  proxy_password:       basestring
        :param max_speed:            The maximum speed to be used during downloads. This should be
                                     specified in units of bytes per second. (Threaded)
        :type  max_speed:            int
        :param headers:              A dictionary specifying header names and values that will be
                                     used for each request. Headers specified for an individual
                                     request will be merged with headers specified here with an
                                     "update" call, potentially overriding the values given here.
                                     (Threaded)
        :param buffer_size:          The number of bytes to read/write in each chunk when copying
                                     files using the local file downloader. (Local)
        :type  buffer_size:          int
        :param progress_interval:    The interval on which progress should be reported, in seconds.
                                     (Local)
        :type  progress_interval:    int
        :param use_hard_links:       If True, use hard links instead of copying files. Defaults to
                                     False. (Local)
        :type  use_hard_links:       bool
        :param use_sym_links:        If True, use symlinks instead of copying files. Defaults to
                                     False. (Local)
        :type  use_sym_links:        bool
        :type  headers:              dict
        """
        self.max_concurrent = max_concurrent
        self.basic_auth_username = basic_auth_username
        self.basic_auth_password = basic_auth_password
        self.ssl_ca_cert = ssl_ca_cert
        self.ssl_ca_cert_path = ssl_ca_cert_path
        self.ssl_client_cert = ssl_client_cert
        self.ssl_client_cert_path = ssl_client_cert_path
        self.ssl_client_key = ssl_client_key
        self.ssl_client_key_path = ssl_client_key_path
        self.ssl_validation = ssl_validation
        self.proxy_url = proxy_url
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.max_speed = max_speed
        self.headers = headers
        self.buffer_size = buffer_size
        self.progress_interval = progress_interval
        self.use_hard_links = use_hard_links
        self.use_sym_links = use_sym_links
        self._temp_files = []

        # concurrency options
        self._process_concurrency()

        # ssl file options
        self._process_ssl_settings()

    def _process_concurrency(self):
        """
        Assert that either the concurrency is unspecified or that it is a positive integer.
        """
        if self.max_concurrent is None:
            return

        if self.max_concurrent <= 0:
            raise ValueError('max_concurrent must be greater than 0')

    def _process_ssl_settings(self):
        """
        Make sure both path and data configuration options were not specified, but make both
        available. It is known that this is not the most performant solution.
        """
        ssl_kwargs = {}

        for data_arg_name, file_arg_name in (('ssl_ca_cert', 'ssl_ca_cert_path'),
                                             ('ssl_client_cert', 'ssl_client_cert_path'),
                                             ('ssl_client_key', 'ssl_client_key_path')):

            data_arg_value = getattr(self, data_arg_name)
            file_arg_value = getattr(self, file_arg_name)

            if data_arg_value is None and file_arg_value is None:
                continue

            if data_arg_value is None:
                if not os.access(file_arg_value, os.F_OK | os.R_OK):
                    raise AttributeError('Cannot read file: %s' % file_arg_value)

                with open(file_arg_value, 'r') as file_arg_handle:
                    setattr(self, data_arg_name, file_arg_handle.read())

            elif file_arg_value is None:
                prefix = 'nectar-%s-' % data_arg_name
                data_arg_os_handle, file_arg_value = tempfile.mkstemp(prefix=prefix)

                os.write(data_arg_os_handle, data_arg_value)
                os.close(data_arg_os_handle)

                self._temp_files.append(file_arg_value)
                setattr(self, file_arg_name, file_arg_value)

            else:
                raise AttributeError('Incompatible configuration options provided: %s, %s' %
                                     (data_arg_name, file_arg_name))

    def __del__(self):
        self.finalize()

    def finalize(self):
        """
        Delete any persistent state.

        Note: this method should be called by the instantiator once they are
        finished with the configuration instance. It is *not* called by the
        downloaders themselves.
        """
        for file_name in self._temp_files:
            if not os.path.exists(file_name):
                continue
            os.unlink(file_name)

    def get(self, item, default=None):
        """
        Dictionary semantics for providing more convenient default values than
        None.

        :param item: configuration attribute to look for
        :type item: basestring
        :param default: default configuration attribute value
        :return: the value of the configuration attribute if found, otherwise
                 the default is returned
        """
        item = getattr(self, item)
        return item if item is not None else default


class HTTPBasicWithProxyAuth(requests.auth.AuthBase):
    """
    Attaches HTTP Basic Authentication and Proxy Authentication to the Request objects in a session.
    """
    def __init__(self, username, password, proxy_username, proxy_password):
        """
        :param username: username to be used to authenticate with the download server
        :type username: basestring
        :param password: password to be used to authenticate with the download server
        :type password: basestring
        :param proxy_username: username to be used to authenticate with the proxy server
        :type proxy_username: basestring
        :param proxy_password: password to be used to authenticate with the proxy server
        :type proxy_password: basestring
        """
        self.username = username
        self.password = password
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password

    def __call__(self, req):
        """
        Callable to be used by the requests library to populate the header of a download request.

        :param req: download request object used by the requests library
        :type  req: requests.models.Request
        """
        req.headers['Authorization'] = requests.auth._basic_auth_str(self.username, self.password)
        req.headers['Proxy-Authorization'] = requests.auth._basic_auth_str(self.proxy_username,
                                                                           self.proxy_password)
        return req
