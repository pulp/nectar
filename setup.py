#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from setuptools import setup, find_packages

setup(name='nectar',
      version='1.1.6',
      url='https://github.com/pulp/nectar',
      description='Performance tuned network download client library',
      license='GPLv2',

      author='Pulp Team',
      author_email='pulp-list@redhat.com',

      packages=find_packages(),
      test_suite='nose.collector',

      classifiers=['Intended Audience :: Developers',
                   'Intended Audience :: Information Technology',
                   'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
                   'Operating System :: POSIX',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Software Development :: Libraries :: Python Modules',],

      options={'build': {'build_base': '_build'},
               'sdist': {'dist_dir': '_dist'},},

      install_requires=['isodate >= 0.4.9',
                        'requests >= 2.0.0',],)

