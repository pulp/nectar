# -*- coding: utf-8 -*-

class DownloadRequest(object):
    """
    Representation of a request for a file download.
    """

    def __init__(self, url, destination, data=None, headers=None):
        """
        :param url:         url of the file to be downloaded
        :type  url:         str
        :param destination: specifies where the downloader should store the contents of the URL
                            once they are retrieved. You can provide either a file-system path for
                            this parameter, or an open file-like object. If you provide a file-like
                            object, it is your responsibility to close the file after the download
                            is finished.
        :type  destination: str or file-like object
        :param data:        arbitrary data to be passed back as part of the
                            reports to the listener callbacks
        :param headers:     A dictionary specifying header names and values that will
                            be used for this request. Headers specified here
                            will override any headers of the same key that
                            are specified in the config.
        :type  headers:     dict
        """

        self.url = url
        self.destination = destination
        self.data = data
        self.headers = headers
        self.canceled = False

        self._file_handle = None

    def initialize_file_handle(self):
        """
        Returns a file handle for the request's destination.

        :return: file-like object for writing the download to
        """
        # if the destination is already a file-like object, return it
        if hasattr(self.destination, 'write'):
            return self.destination

        self._file_handle = open(self.destination, 'wb') # cache the handle
        return self._file_handle

    def finalize_file_handle(self):
        """
        Cleanup the request destination's file handle. This is a no-op if the
        file handle wasn't create with the initialize_file_handle method.
        """
        # don't close the file handle if it wasn't opened by get_file_handle
        if self._file_handle in (None, self.destination):
            return

        self._file_handle.close()
        self._file_handle = None

