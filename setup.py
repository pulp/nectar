#!/usr/bin/python

from setuptools import setup, find_packages

setup(name='nectar',
      version='0.0.90',
      url='https://github.com/pulp/nectar',
      description='Performance tuned network download client library',
      license='GPLv2',

      author='Pulp Team',
      author_email='pulp-list@redhat.com',

      packages=find_packages(),
      test_suite='nose.collector',

      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Information Technology',
                   'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
                   'Operating System :: POSIX',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Internet :: WWW/HTTP :: Client',
                   'Topic :: Software Developement :: Libraries :: Python Modules',],
     
      options={'build': {'build_base': '_build'},
               'sdist': {'dist_dir': '_dist'},},
      requires=['isodate >= 0.4.9',
                'pycurl >= 7.19.0',
                'eventlet >= 0.12.0',
                'requests >= 1.2.0',],)

