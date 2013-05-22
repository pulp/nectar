.. _config_object:

Downloader Configuration Objects
================================

Configuration objects represent common configuration across a set of
:ref:`download requests <request_object>`. They are *arbitrary* objects in that
any keyword value passed to the constructor will be a field in the configuration
object. However, only a very specific set of fields are honored by the
Downloader objects.

Construct Signature::

 def __init__(self **kwargs):


The currently honored fields (read: keyword arguments) are:

 * ``max_concurrent``
 * ``max_speed``
 * ``basic_auth_username``
 * ``basic_auth_password``
 * ``ssl_validation``
 * ``ssl_ca_cert``
 * ``ssl_ca_cert_path``
 * ``ssl_client_cert``
 * ``ssl_client_cert_path``
 * ``ssl_client_key``
 * ``ssl_client_key_path``
 * ``proxy_url``
 * ``proxy_port``
 * ``proxy_username``
 * ``proxy_password``

This list will continue to grow and evolve as more downloaders are added,
especially downloaders that support protocols other than HTTP and HTTPS.

Download Control
----------------

``max_concurrent`` is an integer that tells the downloader the maximum number of
files to download concurrently (read: in parallel). If this number is not
provided, each downloader has its own default value that will be used instead.

``max_speed`` is an integer that tells the downloader at what speed to throttle
the downloads. The units are: bytes/second.

HTTP Basic Auth Support
-----------------------

The fields ``basic_auth_username`` and ``basic_auth_password`` are used for
the HTTP basic authorization header. The username and password fields must be
provided in plain text. The downloaders will Base64 encode them.

SSL Support
-----------

``ssl_validation`` is a boolean that tells the downloader to verify the identity
of the remote server by checking its SSL certificate. If this parameter is not
provided, validation is assumed to be set to True.

``ssl_ca_cert`` and ``ssl_ca_cert_path`` parameters are used to provide an
alternative CA cert to the downloader. The ``ssl_ca_cert`` parameter should
point the CA pem data and the ``ssl_ca_cert_path`` is a file system path to the
CA cert file. Both are strings. However, these parameters are mutually exclusive,
and the behavior of the downloader is undefined if both are provided.

``ssl_client_cert``, ``ssl_client_cert_path``, ``ssl_client_key``, and
``ssl_client_key_path`` are used to provide two-way authentication via the SSL
protocol. Just like the ssl_ca_cert params, these point to either the data or
to a file path; and correlated parameters are mutually exclusive.

Proxy Support
-------------

``proxy_url`` is string in the form of scheme://host, where scheme is either
*http* or *https*.

``proxy_port`` is an integer port number.

``proxy_username`` and ``proxy_password`` are used for authentication and must
be provided in plain text.

