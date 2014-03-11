.. _request_object:

Request Objects
===============

Request objects represent remote resource, in the form of a URL, and local
storage in form of either a path or an open file-like object.

The ``DownloadRequest`` class has these parameters:

 * url (required) the URL of the file to be downloaded as a string
 * destination (required) either a local filesystem path as a string or an open file-like object
 * data (optional) arbitrary data that will be passed back as part of a corresponding :ref:`report object <report_object>`
 * headers (optional) a dictionary of additional headers

Constructor Signature::

 def __init__(self, url, destination, data=None, headers=None):


URL
---

The URL parameter ``url`` must be of a scheme (read: protocol) supported by the
downloader instance that it will be passed to.

Destination
-----------

The ``destination`` parameter is either an absolute filesystem path as a string
or an open file-like object. If the destination is an open file-like object, the
downloader will **not** close it upon completion of the download; even if an
error occurs.

Example::

 destination = '/tmp/myfile'

 destination = open('/tmp/myfile', wb)

Data
----

The parameter is passed, unadulterated, to the :ref:`report object <report_object>`
that corresponds to the request object. This is convenience mechanism to allow
developers to pass arbitrary data to an :ref:`event listener <event_listener>`.

Headers
-------

The ``headers`` parameter is an option dictionary that can contain any custom
headers for a particular request.
