#!/usr/bin/env python2

from setuptools import setup, find_packages


setup(name='nectar',
      version='1.4.4',
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
                   'Topic :: Software Development :: Libraries :: Python Modules'],

      options={'build': {'build_base': '_build'},
               'sdist': {'dist_dir': '_dist'}},

      install_requires=['isodate >= 0.4.9',
                        'requests >= 2.0.0',
                        'requests-toolbelt >= 0.6.0'],)
