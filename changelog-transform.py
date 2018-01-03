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
dist     = 'stable'
pkgnm    = ''
maxent   = 0
emails   = {}
emaildb  = False
guessmail= False

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
	print_(" -a, --emails LIST: provide list of mails \"NAME <adr> [, NAME <adr> [..]]]\"", file=sys.stderr)
	print_(" -e, --emaildb: use .emaildb and for names", file=sys.stderr)
	print_(" -E, --emaildbguess: use .emaildb and .guessmaildb for names", file=sys.stderr)
	print_(" -d, --distro distname: Override distro name (def=stable)", file=sys.stderr)
	print_(" -n, --pkgname pkgnm: Set package name (def=autodetect)", file=sys.stderr)
	sys.exit(rc)

def parsemailaddr(addr):
	"Return tuple email, name from Name <addr> string"
	idx = addr.find('<')
	idx2 = addr.find('>')
	if idx < 0 or idx2 < 0:
		raise ValueError("Invalid Mail Address \"%s\"" % addr)
	nm = addr[:idx].lstrip(' ').rstrip(' ')
	return (addr[idx+1:idx2].lower(), nm)


def parse_args(argv):
	"Parse command line args"
	import getopt
	global quiet, verbose, infmt, outfmt, tolerant, joinln
	global initver, dist, pkgnm, maxent, emails, emaildb, guessmail

	# options
	try:
		optlist, args = getopt.gnu_getopt(argv, 'vqhi:o:trV:a:d:n:m:eE', ('help', 'quiet', 'verbose', 'tolerant', 'rewrap', 'infmt=', 'outfmt=', 'version=', 'distro=', 'pkgname=', 'maxent=', 'emails=', 'emaildb', 'emaildbguess'))
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
		if opt == '-a' or opt == '--emails':
			for addr in arg.split(','):
				email, name = parsemailaddr(addr)
				emails[email] = name
			continue
		if opt == '-e' or opt == '--emaildb':
			emaildb = True
			continue
		if opt == '-E' or opt == '--emaildbguess':
			emaildb = True
			guessmail = True
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

EMAILDB = 'emaildb'
GMAILDB = 'guessmaildb'

class emailsdb:
	def readdb(self, nm):
		fullnm = self.pref+nm
		emails = {}
		if not os.access(os.path.dirname(fullnm), os.X_OK):
			os.mkdir(os.path.dirname(fullnm), mode=0o750)
		if not os.access(fullnm, os.R_OK):
			open(fullnm, 'x').write('#EMail Address Database %s for changlog-transform.py\n' % nm)
			return emails
		fd = open(fullnm, 'r')
		for ln in fd:
			ln = ln.rstrip('\n')
			if not ln or ln[0] == '#':
				continue
			email, name = parsemailaddr(ln)
			emails[email] = name
		return emails
	def __init__(self, pref=os.environ['HOME']+'/.changelog-transform/', guess=True):
		self.pref = pref
		self.emaildb = self.readdb(EMAILDB)
		self.guess = guess
		if guess:
			self.guessmaildb = self.readdb(GMAILDB)
	def addrappend(self, nm, addrs):
		fullnm = self.pref+nm
		fd = open(fullnm, 'a')
		db = self.guessmaildb if nm == GMAILDB else self.emaildb
		for it in addrs.keys():
			val = db.get(it)
			if val:
				if val == addrs[it]:
					continue
				else:
					raise ValueError("Will not overwrite %s <%s> with %s" % (val, it, addrs[it]))
			print_("%s <%s>" % (addrs[it], it), file=fd)
			db[it] = addrs[it]
		return self
	def __getitem__(self, srch):
		srch = srch.lower()
		try:
			nm = self.emaildb[srch]
		except KeyError:
			nm = changelog.guessnm(srch)
			if self.guess:
				try:
					nm = self.guessmaildb[srch]
				except:
					#nm = changelog.guessnm(srch)
					print_("WARN: Add %s <%s> to guessmaildb" % (nm, srch), file=sys.stderr)
					self.addrappend(GMAILDB, {srch: nm})
			else:
				raise ValueError('No such email %s <%s>' % (nm, srch))
		return nm

def main(argv):
	global infmt, outfmt, pkgnm, emails
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

	if emaildb:
		if emails:
			emails = emailsdb(guess = guessmail).addrappend(EMAILDB, emails)
		else:
			emails = emailsdb(guess = guessmail)

	chglog = changelog.changelog(pkgnm = pkgnm, distover = dist, initver = initver, emaildb = emails)
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

