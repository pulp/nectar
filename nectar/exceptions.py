# -*- coding: utf-8 -*-

"""
Exception classes thrown by downloader implementations under error conditions.
"""


class DownloaderException(Exception):
    """
    General downloader exception base class.

    It's considered best practices not to raise or handle instances of this
    class, but of the derived classes below.

    :ivar report: nectar.report.DownloadReport instance
    """

    def __init__(self, report):
        self.report = report

# client-side problems ---------------------------------------------------------

class DownloadClientException(DownloaderException):
    """
    Base class for client-side downloader problems.
    """

# specific derived exceptions

class UnsupportedProtocol(DownloadClientException):
    """
    Raised when the request URL is for a protocol not supported by the downloader.
    """


class MalformedRequest(DownloadClientException):
    """
    Raised when the request cannot be parsed by the downloader.
    """


class ReadError(DownloadClientException):
    """
    Raised when the downloader cannot read the response sent by the remote server.
    """

# remote server problems -------------------------------------------------------

class RemoteServerException(DownloaderException):
    """
    Base class for remote server-side downloader problems.
    """

# specific derived exceptions

class FileNotFound(RemoteServerException):
    """
    Raised when the remote server cannot find the request file.
    """


class PartialFile(RemoteServerException):
    """
    Raised when the remote server only returns part of the requested file.
    """


class RemoteServerResolutionError(RemoteServerException):
    """
    Raised when the remote server's name cannot be resolved.
    (DNS lookup failure)
    """


class ServerTimedOut(RemoteServerException):
    """
    Raised when the connection to the remote server times out.
    """


class AuthorizationFailure(RemoteServerException):
    """
    Raised when the remote server denies access to the requested file due to
    invalid or missing credentials.
    """


class TooManyRedirects(RemoteServerException):
    """
    Raised when the remote server tries to redirect the request too many times.
    """


class UnknownResponse(RemoteServerException):
    """
    Raised when the remote server sends a response that cannot be parsed.
    """


class RemoteServerError(RemoteServerException):
    """
    Raised when there is an internal remote server error.
    """

# proxy server problems --------------------------------------------------------

class ProxyException(DownloaderException):
    """
    Base class for proxy server problems.
    """

# specific derived exceptions

class ProxyResolutionError(ProxyException):
    """
    Raised when the proxy server's name cannot be resolved.
    (DNS lookup failure)
    """


class ProxyConnectionTimedOut(ProxyException):
    """
    Raised when the connection to the proxy server times out.
    """


class ProxyAuthorizationFailure(ProxyException):
    """
    Raised when the connection to the proxy server cannot be established due to
    invalid or missing credentials.
    """

# ssl problems -----------------------------------------------------------------

class SSLException(DownloaderException):
    """
    Base class for SSL problems.
    """

# specific derived exceptions

class ServerSSLVerificationFailure(SSLException):
    """
    Raised with the server's ssl certificate fails verification.
    """


class ClientSSLAuthorizationFailure(SSLException):
    """
    Raised when the client's ssl certificate is rejected by the server.
    """

