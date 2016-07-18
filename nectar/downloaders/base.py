# -*- coding: utf-8 -*-

import logging

from nectar.listener import DownloadEventListener


_LOG = logging.getLogger(__name__)


class Downloader(object):
    """
    Abstract backend base class for downloader implementations. This class
    provides the base APIs required of any concrete downloader class.

    Backend implementations are expected to override the ``download`` method.
    They can (optionally) download any other methods, but they are not required.

    :ivar config: downloader configuration
    :ivar event_listener: event listener providing life-cycle callbacks.
    :ivar is_cancelled: boolean showing if the cancel method has been called.
    """

    def __init__(self, config, event_listener=None):
        """
        :param config: configuration for this backend
        :type config: nectar.config.DownloaderConfig
        :param event_listener: event listener coupled to this backend
        :type event_listener: nectar.listener.DownloadEventListener
        """
        self.config = config
        self.event_listener = event_listener or DownloadEventListener()
        self.is_canceled = False
        # If False, no events will be fired to a listener. This is useful for
        # doing a synchronous download.
        self.fire_events = True

    # download api -------------------------------------------------------------

    def download(self, request_list):
        """
        Download the files represented by the download requests in the provided
        request list.

        :param request_list: list of download requests
        :type request_list: iterator of nectar.request.DownloadRequest
        :return: list of download reports corresponding the the download requests
        :rtype: list of nectar.report.DownloadReport
        """
        raise NotImplementedError()

    def download_one(self, request, events=False):
        """
        Downloads one url, blocks, and returns a DownloadReport.

        :param request: download request object with details about what to
                        download and where to put it
        :type  request: nectar.request.DownloadRequest
        :param events:  defaults to False and sets fire_events variable value
        :type  events:  bool

        :return:    download report
        :rtype:     nectar.report.DownloadReport
        """
        # by default don't fire events to a listener for this synchronous call
        self.fire_events = events
        try:
            return self._download_one(request)
        finally:
            self.fire_events = True

    def _download_one(self, request):
        """
        Downloads one url, blocks, and returns a DownloadReport.

        :param request: download request object with details about what to
                        download and where to put it
        :type  request: nectar.request.DownloadRequest

        :return:    download report
        :rtype:     nectar.report.DownloadReport
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Set the boolean is_cancelled flag to True.

        NOTE: it is up the ``download`` implementation to honor this flag.
        """
        self.is_canceled = True

    # events api ---------------------------------------------------------------

    def fire_download_headers(self, report):
        """
        Fire the ``download_headers`` event using the download report provided.

        :param report: download reports
        :type report: nectar.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_headers, report)

    def fire_download_started(self, report):
        """
        Fire the ``download_started`` event using the download report provided.

        :param report: download reports
        :type report: nectar.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_started, report)

    def fire_download_progress(self, report):
        """
        Fire the ``download_progress`` event using the download report provided.

        :param report: download reports
        :type report: nectar.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_progress, report)

    def fire_download_succeeded(self, report):
        """
        Fire the ``download_succeeded`` event using the download report provided.

        :param report: download reports
        :type report: nectar.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_succeeded, report)

    def fire_download_failed(self, report):
        """
        Fire the ``download_failed`` event using the download report provided.

        :param report: download reports
        :type report: nectar.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_failed, report)

    # events utility methods ---------------------------------------------------

    def _fire_event_to_listener(self, event_listener_callback, *args, **kwargs):
        try:
            if self.fire_events:
                event_listener_callback(*args, **kwargs)
        except Exception as e:
            _LOG.exception(e)
