#!/usr/bin/env python

import os
import logging

from nectar.config import DownloaderConfig
from nectar.request import DownloadRequest
from nectar.downloaders.revent import HTTPEventletRequestsDownloader

logging.basicConfig()

current_dir = os.path.dirname(__file__)

ca_file = 'cdn.redhat.com-chain.crt'
#cert_file = '8538048783306757070.pem'
#key_file = '8538048783306757070-key.pem'
cert_file = '1359391926_4512.crt'
key_file = '1359391926_4512.key'

#repo_url = 'https://cdn.redhat.com/content/dist/rhel/server/6/6Server/x86_64/os/'
repo_url = 'https://cdn.redhat.com/content/dist/rhel/rhui/server/6/6.2/x86_64/os/'
remote_file = 'repodata/repomd.xml'

dest_file = 'cdn-downloaded-repomd.xml'

requests = [DownloadRequest(repo_url + remote_file,
                            os.path.join(current_dir, dest_file))]

config = DownloaderConfig(
    ssl_validation=True,
    ssl_ca_cert_path=os.path.join(current_dir, ca_file),
    ssl_client_cert_path=os.path.join(current_dir, cert_file),
    ssl_client_key_path=os.path.join(current_dir, key_file),)

downloader = HTTPEventletRequestsDownloader(config)

downloader.download(requests)

