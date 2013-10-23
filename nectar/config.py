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
    as well as, it's configuration. Instances of this class are used by the
    download factory to determine which download backend to use.

    Currently supported configuration values are:

     * max_concurrent:       maximum number of downloads to run concurrently
     * basic_auth_username:  http basic auth username (basic_auth_password must also be
                             provided)
     * basic_auth_password:  http basic auth password (basic_auth_username must also be
                             provided)
     * ssl_ca_cert:          certificate authority cert for secure connections (https
                             protocol only)
     * ssl_ca_cert_path:     path to a ssl ca cert (incompatible with ssl_ca_cert)
     * ssl_client_cert:      client certificate for secure connections (https protocol
                             only)
     * ssl_client_cert_path: path to a ssl client cert (incompatible with ssl_client_cert)
     * ssl_client_key:       client private key for secure connections (https protocol
                             only)
     * ssl_client_key_path:  path to a ssl client key (incompatible with ssl_client_key)
     * ssl_validation:       A boolean value. If set to True, the downloader will verify that the remote
                             server's SSL certificate is signed by a trusted authority, and that the
                             certificate's CommonName field equals the hostname we are connecting to. If False,
                             no such verification is made.
     * proxy_url:            A string representing the URL of a proxy server that should
                             be used while retrieving content. It should be of the form
                             <scheme>://<hostname>/ where the scheme is http or https.
     * proxy_port:           The port on the proxy server to connect to. This should be
                             an integer value.
     * proxy_username:       The username to use when authenticating with the proxy server
     * proxy_password:       The password to use when authenticating with the proxy server
     * max_speed:            The maximum speed to be used during downloads. This should be an integer
                             value, and should be specified in units of bytes per second.
    """

    # -- instantiation ---------------------------------------------------------

    def __init__(self, **kwargs):
        """
        :param kwargs: keyword arguments representing the downloader's configuration.
                       See the DownloaderConfig's docblock for a list of supported
                       options.
        :type kwargs: dict
        """
        self._temp_files = []

        # concurrency options
        self._process_concurrency_kwargs(kwargs)

        # ssl file options
        self._process_ssl_file_kwargs(kwargs)

        # the open-ended nature of this will be solved with documentation
        self.__dict__.update(kwargs)

    def _process_concurrency_kwargs(self, kwargs):
        # assert that either the concurrency is unspecified or that it is a
        # positive integer

        max_concurrent = kwargs.pop('max_concurrent', None)

        if max_concurrent is None:
            return

        if max_concurrent <= 0:
            raise ValueError('max_concurrent must be greater than 0')

        kwargs['max_concurrent'] = max_concurrent

    def _process_ssl_file_kwargs(self, kwargs):
        # make sure both path and data configuration options were not specified,
        # but make both available

        # it is known that this is not the most performant solution, but I don't
        # think we really care

        ssl_kwargs = {}

        for data_arg_name, file_arg_name in (('ssl_ca_cert', 'ssl_ca_cert_path'),
                                             ('ssl_client_cert', 'ssl_client_cert_path'),
                                             ('ssl_client_key', 'ssl_client_key_path')):

            data_arg_value = kwargs.pop(data_arg_name, None)
            file_arg_value = kwargs.pop(file_arg_name, None)

            if data_arg_value is None and file_arg_value is None:
                continue

            if data_arg_value is None:
                ssl_kwargs[file_arg_name] = file_arg_value

                if not os.access(file_arg_value, os.F_OK | os.R_OK):
                    raise AttributeError('Cannot read file: %s' % file_arg_value)

                with open(file_arg_value, 'r') as file_arg_handle:
                    ssl_kwargs[data_arg_name] = file_arg_handle.read()

            elif file_arg_value is None:
                ssl_kwargs[data_arg_name] = data_arg_value

                prefix = 'nectar-%s-' % data_arg_name
                data_arg_os_handle, file_arg_value = tempfile.mkstemp(prefix=prefix)

                os.write(data_arg_os_handle, data_arg_value)
                os.close(data_arg_os_handle)

                self._temp_files.append(file_arg_value)
                ssl_kwargs[file_arg_name] = file_arg_value

            else:
                raise AttributeError('Incompatible configuration options provided: %s, %s' %
                                     (data_arg_name, file_arg_name))

        kwargs.update(ssl_kwargs)

    # -- finalization ----------------------------------------------------------

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

    # -- configuration query api -----------------------------------------------

    def __getattr__(self, item):
        """
        This allows us to retrieve configuration parameters from this object
        with getattr() or by accessing the attributes by name.
        """
        return self.__dict__.get(item, None)

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
        return self.__dict__.get(item, default)


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
