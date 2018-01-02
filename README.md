# About changelog-transform

[Open Build Service](https://build.opensuse.org/) 
is a very handy tool to create RPM and DEB pacakages
for various distributions and architectures.
I maintain a number of packages there and I got tired of manually tranforming
RPM .changes entries into debian.changelog formats all the time. Writing
good changelogs is enough work -- no need to add annoying 20% of mechanical
work on top of it if computers can do the job.

As of 2018-02-01, the changelog.py library is mostly complete and even somewhat
tested. What is needed still:
* Frontend CLI tool
* More tolerance against strangely formatted changelogs
