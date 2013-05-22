.. _report_object:

Report Objects
==============

Report objects are created to correspond to a give :ref:`request object <request_object>`.
They are not usually instantiated by a developer, but are passed back as the
parameter to event methods in an :ref:`event listener <event_listener>`.

They contain following fields that directly correspond to its request object:

 * ``url``
 * ``destination``
 * ``data``

They also contain the following informational fields:

 * ``state``
 * ``total_bytes``
 * ``bytes_downloaded``
 * ``start_time``
 * ``finish_time``
 * ``error_report``

State
-----

The ``state`` field describes the current state of the download request. It is
always one of the following five states:

 * ``waiting`` - the download has not yet started
 * ``downloading`` - the download is in progress
 * ``succeeded`` - the download is done and was successful
 * ``failed`` - the download is done and was unsuccessful
 * ``canceled`` - the download is done and was canceled

Total Bytes
-----------

The total bytes to be downloaded as an integer. If this could not be determined,
this field will be None.

Bytes Downloaded
----------------

The bytes downloaded so far as an integer. Initially 0.

Start Time
----------

The date and time the download started as a ``datetime.datetime`` instance in
the UTC timezone.

Finish Time
-----------

The date and time the download finished as a ``datetime.datetime`` instance in
the UTC timezone.

Error Report
------------

This field is an arbitrary dictionary that is populated only with the ``state``
field is ``failed``. It's primary purpose is for debugging unsuccessful
downloads.

When the state is not failed, this dictionary will be empty.

