Threads+Requests-Based Downloader
=================================

The threaded downloader leverages both python threads and the requests library.
It is optimized for speed when use an already threaded applications. It provides
the :ref:`downloader API <downloader_api>`.

Its major use case is downloading lots of files quickly.


.. warning::
   The proxy support for this downloader is incomplete. Due to limitations in
   the urllib3 library, HTTPS requests via an HTTPS proxy is not supported.
   However, all other permutations are.
