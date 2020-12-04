%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from %distutils.sysconfig import get_python_lib; print get_python_lib()")}

%if 0%{?fedora} >= 33
%define __python /usr/bin/python2
%endif

# The release number
%global release_number 1

# Create tag for the Source0 and setup
%global git_tag %{name}-%{version}-%{release_number}

Name:           python-nectar
Version:        1.6.3
Release:        1%{?dist}
Summary:        A download library that separates workflow from implementation details

Group:          Development/Tools
License:        GPLv2
URL:            https://github.com/pulp/nectar
Source0:        https://codeload.github.com/pulp/nectar/tar.gz/%{git_tag}#/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires:  python-setuptools

Provides:       python2-nectar
Obsoletes:      python2-nectar < %{version}
Requires:       python-isodate >= 0.4.9
Requires:       python-requests >= 2.4.3

%description
Nectar is a download library that abstracts the workflow of making and tracking
download requests away from the mechanics of how those requests are carried
out. It allows multiple downloaders to exist with different implementations,
such as the default "threaded" downloader, which uses the "requests" library
with multiple threads. Other experimental downloaders have used tools like
pycurl and eventlets.

%prep
%setup -q -n nectar-%{git_tag}

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{python_sitelib}/nectar/
%{python_sitelib}/nectar*.egg-info
%doc COPYRIGHT LICENSE.txt README.rst

%changelog
* Wed Dec 02 2020 Evgeni Golov 1.6.3-1
- Fixed RST handling. (ipanova@redhat.com)

* Mon Sep 14 2020 Evgeni Golov 1.6.2-1
- Fix timeout test. (ipanova@redhat.com)
- Remove outdated comments. (ipanova@redhat.com)
- Better retries for nectar which can handle interrupted connections (#72)
  (jluza@redhat.com)
- Added 'extra_headers' attribute as replacement for session.headers (#70)
  (jluza@redhat.com)
- Fixed missing return value in _get session reversed arguments order for
  _fetch (jluza@redhat.com)
- Do not share requests session within multiple threads (jluza@redhat.com)

* Thu Sep 19 2019 Patrick Creech <pcreech@redhat.com> 1.6.1-1
- Always retry on 429 response, even without a retry-after header
  (twaugh@redhat.com)

* Mon Apr 08 2019 Patrick Creech <pcreech@redhat.com> - 1.6.0-1
- Problem: downloader can't be configured to NOT decode (dkliban@redhat.com)

* Wed Oct 18 2017 Ina Panova <ipanova@redhat.com> 1.5.6-1
- UnicodeEncodeError in comments provided with SSL cert/key/CA
  (ammaransari004@gmail.com)
- Revert "UnicodeEncodeError in comments provided with SSL cert/key/CA"
  (mhrivnak@hrivnak.org)
- UnicodeEncodeError in comments provided with SSL cert/key/CA
  (ammaransari004@gmail.com)

* Wed Aug 02 2017 Ina Panova <ipanova@redhat.com> 1.5.5-1
- Update spec files Source0 (zhunting@redhat.com)
- Update nectar to also read headers from config (bihan.zh@gmail.com)

* Fri Apr 21 2017 Ina Panova <ipanova@redhat.com> 1.5.4-1
- Re-enable request streaming (alex@linfratech.co.uk)
- Better logging at INFO level for downloads (daviddavis@redhat.com)
- update mention-bot userBlacklist (seanokeeffe797@gmail.com)

* Wed Sep 14 2016 Ina Panova <ipanova@redhat.com> 1.5.3-1
- Change how Nectar configures requests to be thread-safe (jeremy@jcline.org)
- Add mention-bot blacklist (jeremy@jcline.org)

* Wed May 25 2016 Ina Panova <ipanova@redhat.com> 1.5.2-1
- ConnectionError exceptions are logged at the error level (jeremy@jcline.org)
- Add a unit test for proxy username being ''. (rbarlow@redhat.com)
- if config.proxy_username is an empty string, testing if it is equal to None
  evaluates to false. (hekma.yoram@gmail.com)

* Mon Mar 14 2016 Ina Panova <ipanova@redhat.com> 1.5.1-1
- Revert changes for digest proxy (pcreech@redhat.com)

* Tue Mar 01 2016 Ina Panova <ipanova@redhat.com> 1.5.0-1
- Use urllib3's retry functionality for failed connections. (jeremy@jcline.org)

* Fri Feb 19 2016 Ina Panova <ipanova@redhat.com> 1.4.5-1
- 1626 - Fix yum repo sync cancellation. (ipanova@redhat.com)
- Log the specific ConnectionError. (jeremy@jcline.org)

* Wed Feb 03 2016 Ina Panova <ipanova@redhat.com> 1.4.4-1
- Enable content sync via digest proxy (pcreech@redhat.com)
- PEP-8 Nectar. (rbarlow@redhat.com)
- Make Nectar use a single requests Session. (jeremy@jcline.org)
- switch thread locks to reentrant locks (asmacdo@gmail.com)

* Mon Jan 11 2016 Ina Panova <ipanova@redhat.com> 1.4.3-1
- An individual request can now be canceled. (jeremy@jcline.org)
- Debug log now logs every url it attempts to connect to
  (seanokeeffe797@gmail.com)

* Tue Dec 15 2015 Ina Panova <ipanova@redhat.com> 1.4.2-1
- Now static server listens on ipv6 (ipanova@redhat.com)
- Tests do not have to depend on the internet. (ipanova@redhat.com)
- Convert shebang to python2 (ipanova@redhat.com)
- Add a shebang to the setup.py. (rbarlow@redhat.com)
- PEP-8 setup.py. (rbarlow@redhat.com)

* Wed Oct 21 2015 Ina Panova <ipanova@redhat.com> 1.4.1-1
- 1229-Json config file values must be url encoded. (ipanova@redhat.com)

* Wed Sep 16 2015 Ina Panova <ipanova@redhat.com> 1.4.0-1
- As a developer I can receive headers while using download_one()
  (ipanova@redhat.com)
- 1033 - Error during build_session does not propagate to importer.
  (ipanova@redhat.com)

* Mon Aug 31 2015 Ina Panova <ipanova@redhat.com> 1.3.3-1
- Issue#1210 ConnectionError - BadStatusLine during repo sync. (ipanova@redhat.com)

* Tue Jun 02 2015 Ina Panova <ipanova@redhat.com> 1.3.2-1
- 1174283 - bump python-requests requirement to match included dep
  (asmacdo@gmail.com)
- 1124625 - fail quickly if there is a connection error (asmacdo@gmail.com)
- Log OSErrors at debug level when attempting to link files that do not exist
  (asmacdo@gmail.com)
- Handle local IOErrors in debug level logs rather than error level.
  (asmacdo@gmail.com)

* Thu Aug 21 2014 Barnaby Court <bcourt@redhat.com> 1.3.1-1
- 1127298 - Canceling a download causes hang in ThreadedDownloader (bcourt@redhat.com)

* Thu Aug 07 2014 Jeff Ortel <jortel@redhat.com> 1.3.0-1
- Updated API to support synchronous downloading of a single file.

* Thu Aug 07 2014 Jeff Ortel <jortel@redhat.com> 1.2.2-1
- 1126083 - no longer logging a failed download at ERROR level
  (mhrivnak@redhat.com)
* Fri Mar 28 2014 Jeff Ortel <jortel@redhat.com> 1.2.1-1
- 1078945 - Canceling a repo sync task does not seem to halt the
  rpm sync (bcourt@redhat.com)
- 965764 - DownloaderConfig is explicit. (rbarlow@redhat.com)
- 1078945 - Avoid use of thread join and Event.wait() so that we don't end up
  in C code that will block python signal handlers. (bcourt@redhat.com)

* Fri Mar 21 2014 Michael Hrivnak <mhrivnak@redhat.com> 1.2.0-1
- custom headers can now be specified on sessions and requests
  (mhrivnak@redhat.com)
- correcting typo in the python-requests version dep (skarmark@redhat.com)
- updating python-requests depedency version to 2.1.1 (skarmark@redhat.com)
- removing downloaders that we aren't using or supporting. Both are also known
  to have serious bugs. (mhrivnak@redhat.com)

* Mon Oct 28 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.6-1
- Merge pull request #13 from pulp/skarmark-1021662 (skarmark@redhat.com)
- 1021662 - adding proxy auth to proxy urls along with the headers
  (skarmark@redhat.com)

* Wed Oct 23 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.5-1
- minor update to the unit test (skarmark@redhat.com)
- adding a unit test to verify request headers when using
  HTTPBasicWithProxyAuth (skarmark@redhat.com)
- Moving HTTPBasicWithProxyAuth class to nectar.config and adding doc blocks
  (skarmark@redhat.com)
- 1021662 - adding a class which inherits requests.auth.AuthBase and sets up
  proxy and user basic authentication headers correctly instead of overwriting
  each other (skarmark@redhat.com)
- 1021662 - using HTTPProxyAuth when using proxy with authentication to
  populate correct field in the header (skarmark@redhat.com)

* Wed Oct 09 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.4-1
- adding dependency to python-requests >= 2.0.0 to support proxy with https
  (skarmark@redhat.com)

* Wed Oct 09 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.3-1
- updating revent downloader with the latest change in threaded downloader
  since it is generally maintained in lock-step with the threaded downloader
  (skarmark@redhat.com)
- we need to set both the 'http' and 'https' protocols to '://'.join((protocol,
  url)) (skarmark@redhat.com)
- removed workaround for no https proxy support, since we now carry python-
  requests-2.0.0 which includes updated urlllib3 and provides the https proxy
  support (skarmark@redhat.com)
- bumped docs version to match latest tag (jason.connor@gmail.com)

* Thu Sep 26 2013 Jason L Connor <jason.connor@gmail.com> 1.1.2-1
- added warnings about incomplete proxy support for the revent and threaded
  downloader (jason.connor@gmail.com)
- 1009078 - correctly set the proxies to supported protocols
  (jason.connor@gmail.com)
- always use http:// for proxy url (lars.sjostrom@svenskaspel.se)

* Tue Sep 03 2013 Jason L Connor <jason.connor@gmail.com> 1.1.1-1
- removed progress reporter thread due to race condition in the .join() with this queue and substituted it with thread-safe event firing and join()s on the worker threads (jason.connor@gmail.com)
- removed race condition between feeder thread and worker threads daemonized all spawned threads (jason.connor@gmail.com)

* Fri Aug 23 2013 Jason L Connor <jason.connor@gmail.com> 1.1.0-1
- new threaded downloader and unit tests (jason.connor@gmail.com)
- bumped nectar version to 1.1 (jason.connor@gmail.com)

* Wed Jul 31 2013 Jeff Ortel <jortel@redhat.com> 1.0.0-1
- got rid of fancy eventlet concurrency, regular os operations are faster;
  fixed bug where the report state was never started (jason.connor@gmail.com)
- fixed bug that sets mex_concurrent to None when max_concurrent is not
  provided (jason.connor@gmail.com)
- initial attempt at implementing an eventlet-based local file downloader
  (jason.connor@gmail.com)
* Wed Jul 03 2013 Jeff Ortel <jortel@redhat.com> 0.99-2
- 979582 - nectar now compensates for servers that send an incorrect content-
  encoding header for files that are gzipped. (mhrivnak@redhat.com)

* Wed Jun 05 2013 Jay Dobies <jason.dobies@redhat.com> 0.99-1
- Tweaking the version numbering until we come out with 1.0 to make it play
  nicer with tito (jason.dobies@redhat.com)

* Wed Jun 05 2013 Jay Dobies <jason.dobies@redhat.com> 0.97.1-1
- 970741 - Added error_msg field to the download report
  (jason.dobies@redhat.com)

* Mon Jun 03 2013 Jason L Connor <jason.connor@gmail.com> 0.97.0-1
- initial pass at leaky bucket throttling algorithm (jason.connor@gmail.com)

* Thu May 30 2013 Jason L Connor <jason.connor@gmail.com> 0.95.0-1
- 967939 - added kwarg processing for ssl file and data configuration options
  that make both available via the configuration instance
  (jason.connor@gmail.com)
* Mon May 20 2013 Jason L Connor <jason.connor@gmail.com> 0.90.3-2
- changed requires so for epel and fedora; commented out (for now) %%check
  (jason.connor@gmail.com)
- revent test script (jason.connor@gmail.com)
- no longer patching the thread module as it causes problems with threaded
  programs (jason.connor@gmail.com)
* Tue May 14 2013 Jason L Connor <jason.connor@gmail.com>
- new package built with tito

* Mon May 13 2013 Jason L Connor (jconnor@redhat.com) 0.90.0-1
- brought in new revent downloader to replace old eventlet downloader
- bumped version in preparation of 1.0.0 release

* Wed May 08 2013 Jason L Connor (jconnor@redhat.com) 0.0.90-1
- cut project from pulp
- initial spec file and setup.py

