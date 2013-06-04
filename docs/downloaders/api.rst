.. _downloader_api:

Base Downloader API
===================

The Downloader base class defines the general downloader API. It has a number of
simple methods and behaviors that are common across any derived classes. This
provides the *pluggable* aspect of the Nectar library.

Instantiation
-------------

A downloader constructor takes two parameters, one required and one optional:

 * a :ref:`configuration object <config_object>`, required
 * an :ref:`event listener <event_listener>`, optional

Configuration
-------------

The :ref:`configuration object <config_object>` provides options that are common
across all download requests. Their documentation have be found :ref:`here <config_object>`.

Events
------

As the downloader downloads files, it fires off events by calling methods on the
provided :ref:`event listener <event_listener>`.

If no event listener is passed to a downloader's constructor, a no-op event
listener is automatically used.

Event listener's methods are described :ref:`here <event_listener>`.

Downloading Requests
--------------------

The downloaders do one thing: they download files. The ``download`` method on
a downloader takes a list of :ref:`request objects <request_object>` and
downloads them using information from it's :ref:`configuration <config_object>`.

The ``download`` signature::

 def download(self, request_list):

The ``request_list`` parameter doesn't necessarily need to be a list, but it
does need to be an **iterator** of request objects.

Canceling Downloads
-------------------

Downloaders support the canceling of the a call to ``download`` via the
``cancel`` method. Since downloading is synchronous and does not return until
all the download requests have been either successfully downloaded or have
failed in their attempt, the ``cancel`` method must be called by another thread.

