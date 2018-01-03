#!/usr/bin/env python3
#
# CLI frontend to changelog transformer
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2018
# License: CC-BY-SA 3.0

import sys
import os
import changelog
from six import print_

quiet    = False
verbose  = False
infmt    = None
outfmt   = None
tolerant = False
joinln   = False
initver  = '?-0'
authnm   = ''
dist     = 'stable'
pkgnm    = ''
maxent   = 0
emails   = {}
emaildb  = False

def helpout(rc=1):
	print_("Usage: changelog-transform.py [options] in out", file=sys.stderr)
	print_(" Options:", file=sys.stderr)
	print_(" -h, --help: Output this help", file=sys.stderr)
#	print_(" -v, --verbose: Increase verbosity (not implemented)", file=sys.stderr)
#	print_(" -q, --quiet: Be quiet (not implemented)", file=sys.stderr)
	print_(" -r, --rewrap: Rewrap changelog entries to fill width", file=sys.stderr)
	print_(" -t, --tolerant: Tolerate non-std formatting", file=sys.stderr)
	print_(" -i, --infmt rpm/deb: Override input file detection", file=sys.stderr)
	print_(" -o, --outfmt rpm/deb: Override output file detection", file=sys.stderr)
	print_(" -m, --maxent no: Set max number of entries to process (def=all)", file=sys.stderr)
	print_(" Options to fill in info for RPM->DEB conversions:", file=sys.stderr)
	print_(" -V, --version x.y-r: Set initial version (def: ?-0)", file=sys.stderr)
	print_(" -a, --author authorname: Set authors name (def: guess from addr)", file=sys.stderr)
	print_(" -e, --emails LIST: provide list of mails \"NAME <adr> [, NAME <adr> [..]]]\"", file=sys.stderr)
#	print_(" -E, --emaildb: use .emaildb and .guessemaildb for names", file=sys.stderr)
	print_(" -d, --distro distname: Override distro name (def=stable)", file=sys.stderr)
	print_(" -n, --pkgname pkgnm: Set package name (def=autodetect)", file=sys.stderr)
	sys.exit(rc)

def parse_args(argv):
	"Parse command line args"
	import getopt
	global quiet, verbose, infmt, outfmt, tolerant, joinln
	global initver, authnm, dist, pkgnm, maxent, emails, emaildb

	# options
	try:
		optlist, args = getopt.gnu_getopt(argv, 'vqhi:o:trV:a:d:n:m:e:E', ('help', 'quiet', 'verbose', 'tolerant', 'rewrap', 'infmt=', 'outfmt=', 'version=', 'author=', 'distro=', 'pkgname=', 'maxent=', 'emails=', 'emaildb'))
	except getopt.GetoptError as exc:
		print_(exc)
		helpout(1)
	for (opt, arg) in optlist:
		if opt == '-q' or opt == '--quiet':
			quiet = True
			continue
		if opt == '-v' or opt == '--verbose':
			verbose = True
			continue
		if opt == '-t' or opt == '--tolerant':
			tolerant = True
			continue
		if opt == '-r' or opt == '--rewrap':
			joinln = True
			continue
		if opt == '-i' or opt == '--infmt':
			infmt = arg
			continue
		if opt == '-o' or opt == '--outfmt':
			outfmt = arg
			continue
		if opt == '-m' or opt == '--maxent':
			maxent = int(arg)
			continue
		# for RPM -> DEB
		if opt == '-V' or opt == '--version':
			initver = arg
			continue
		if opt == '-a' or opt == '--author':
			authnm = arg
			continue
		if opt == '-e' or opt == '--emails':
			for addr in arg.split(','):
				idx = addr.find('<')
				idx2 = addr.find('>')
				if idx < 0 or idx2 < 0:
					raise ValueError("Invalid Mail Address \"%s\"" % addr)
				nm = addr[:idx].rstrip(' ')
				emails[addr[idx+1:idx2]] = nm
			continue
		if opt == '-E' or opt == '--emaildb':
			emaildb = True
			continue
		if opt == '-d' or opt == '--distro':
			dist = arg
			continue
		if opt == '-n' or opt == '--pkgname':
			pkgnm = arg
			continue
		if opt == '-h' or opt == '--help':
			helpout(0)
	if len(args) != 3:
		helpout(1)
	return args[1:]


def main(argv):
	global infmt, outfmt, pkgnm
	innm, outnm = parse_args(argv)
	if not infmt:
		if innm[-8:] == ".changes":
			infmt = "rpm"
		elif innm[-10:] == ".changelog":
			infmt = "deb"
		else:
			print_("ERROR: Can not determine input format", file=sys.stderr)
			sys.exit(2)
	if not outfmt:
		if outnm[-8:] == ".changes":
			outfmt = "rpm"
		elif outnm[-10:] == ".changelog":
			outfmt = "deb"
		else:
			print_("ERROR: Can not determine output format", file=sys.stderr)
			sys.exit(2)
	if not pkgnm:
		idx = innm.rfind('.')
		if idx > 0:
			pkgnm = os.path.basename(innm[0:idx])
		else:
			idx = outnm.rfind('.')
			if idx > 0:
				pkgnm = os.path.basename(outnm[0:idx])
			elif infmt == 'rpm':
				print_("WARN: Can not determine package name format", file=sys.stderr)

	if innm == '-':
		infd = sys.stdin
	else:
		infd = open(innm, 'r')

	chglog = changelog.changelog(pkgnm = pkgnm, authover = authnm, distover = dist, initver = initver, emaildb = emails)
	if infmt == 'rpm':
		chglog.rpmparse(infd, joinln, tolerant, maxent)
	elif infmt == 'deb':
		chglog.debparse(infd, joinln, tolerant, maxent)
	else:
		print_("ERROR: Input format %s unknown" % infmt)
		sys.exit(3)

	infd.close()

	if outnm == '-':
		outfd = sys.stdout
	else:
		outfd = open(outnm, 'w')

	if outfmt == 'rpm':
		print_(chglog.rpmout(), file=outfd, end='')
	elif outfmt == 'deb':
		print_(chglog.debout(), file=outfd, end='')
	else:
		print_("ERROR: Output format %s unknown" % outfmt)
		sys.exit(4)
	
	outfd.close()

	return 0

if __name__ == "__main__":
	sys.exit(main(sys.argv))

