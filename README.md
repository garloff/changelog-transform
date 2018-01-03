# About changelog-transform

[Open Build Service](https://build.opensuse.org/) 
is a very handy tool to create RPM and DEB pacakages
for various distributions and architectures.
I maintain a number of packages there and I got tired of manually tranforming
RPM .changes file entries into debian.changelog formats all the time. Writing
good changelogs is enough work -- no need to add annoying 20% of mechanical
work on top of it if computers can do the job.

This tool has the ability to parse standard RPM .changes files (to be merged
into the RPM changelog in OBS) into debian.changelog files and vice versa.

Note that the translation RPM -> DEB does need to do some guessing, as debian
changelogs have more metadata (author's real name, package name, version number,
urgency, distro). The script attempts to do good guesses, but expect some postprocessing
to be required.
Note that wee have the ability to collect and remember email address -> name mappings
now, so that part at least gets better and better the more often you specify
mappings with -a.

As of 2018-01-03, the changelog.py library is mostly complete and even somewhat
tested. What is needed still:
* More tolerance against strangely formatted changelogs
