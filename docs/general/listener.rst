.. _event_listener:

Event Listeners
===============

A DownloadEventListener object is passed into a downloader's constructor. On
certain events, methods on the event listener are used as callbacks to inform on
headers availability, a download starting, a download's progress, and a download's
success or failure.

This gives the developer an opportunity to develop event-driven code by
overriding the this base class.

The event listener's interface is as follows::

 def download_started(self, report):
 def download_progress(self, report):
 def download_succeeded(self, report):
 def download_failed(self, report):
 def download_headers(self, report):


All methods are passed a :ref:`report object <report_object>` that corresponds
to the download request that has triggered the event.

Download Started
----------------

This event is handled by the ``download_started`` method. It is called once per
download request when the download starts.

Download Progress
-----------------

This event is handled by the ``download_progress`` method. It may be called
multiple times per download request. It is guaranteed to be called once.

Download Succeeded
------------------

This event is handled by the ``download_succeeded`` method. It is called if the
download completed successfullly.

Download Failed
---------------

This event is handled by the ``download_failed`` method. It is called if the
download encountered an error. Additional information about the error will be
in the report's ``error_report`` dictionary.

Download Headers
----------------

This event is handled by the ``download_headers`` method. It is called at the moment
when headers from the response are available.
