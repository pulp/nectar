Nectar
======

Nectar is aimed at being a performance-tuned HTTP and HTTPS download client. It
implements a number of different downloader classes, each with their own
strengths and weaknesses, but all having the same API. This allows developers
to interchange different downloader implementations according to their needs.

Current Downloaders
-------------------

**Curl Downloader**

Curl is a full-featured and mature library for downloading content from a
variety of different protocols. This downloader implementation looks to leverage
curl to deliver as many features as possible to the developer.

The downloader is in the ``nectar.downloaders.curl`` module.

**Eventlet + Requests Downloader**

Eventlet is an event-driven I/O library and requests is a feature-rich library
for downloading content. This downloader implementation leverages the
single-threaded, event-driven nature of eventlet to deliver performance and
speed over features.

The downloader is in the ``nectar.downloaders.revent`` module.

Complete Documentation
----------------------

In the works...

