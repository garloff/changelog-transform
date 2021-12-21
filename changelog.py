#!/usr/bin/env python3
#
# Classes to hold RPM .changes and debian.changelog information and to do
# conversions with them.
#
# Ensure that you have a POSIX or en_US.UTF-8 locale when using this.
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2018
# License: CC-BY-SA 3.0

#import os
import sys
import datetime
import pytz
from six import print_

plineno = 0

def wrap(txt, indent, maxln):
	"Amazingly complex code to wrap text"
	strg = ''
	idx = 0
	while len(txt[idx:]) > maxln-indent:
		# Handle preformatted text
		lf   = txt[idx:idx+maxln-indent+1].rfind('\n')
		if lf > 0 and txt[idx+lf+1] == ' ':
			strg += txt[idx:idx+lf+1]
			idx += lf+1
			strg += ' '*indent
			while txt[idx] == ' ':
				idx+=1
			continue
		# Reformatting (wrapping) necessary
		sep  = txt[idx:idx+maxln-indent].rfind(' ')
		sep2 = txt[idx:idx+maxln-indent].rfind('-')
		if sep == -1 and sep2 == -1:
			strg += txt[idx:idx+maxln-indent] + '\n' + ' '*indent
			idx += maxln-indent
		elif sep2 > sep and not txt[sep2+1].isdigit():
			strg += txt[idx:idx+sep2+1] + '\n' + ' '*indent
			idx += sep2+1
		else:
			strg += txt[idx:idx+sep] + '\n' + ' '*indent
			idx += sep+1
	strg += txt[idx:]
	#print_(strg)
	return strg

def mycapwd(txt):
	"Custom version of capwords()"
	#import string
	ans = ''
	for ix in range(0, len(txt)):
		if ix == 0 or txt[ix-1] == '.' or txt[ix-1] == '-':
			ans += txt[ix].upper()
		else:
			ans += txt[ix]
	return ans

def guessnm(email):
	(acct, dom) = email.split('@')
	# Try firstname.lastname@domain
	acct = mycapwd(acct)
	nms = acct.split('.')
	if len(nms) > 1:
		return ' '.join(nms)
	# Try firstname@lastname.xxx
	dom  = mycapwd(dom)
	doms = dom.split('.')
	return acct + ' ' + doms[0]


def tzsearchlist(email):
	mylist = ['Europe/Amsterdam', 'Europe/Kiev', 'Europe/London', 'Europe/Moscow', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'America/Sao_Paulo', 'Asia/Seoul', 'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney', 'Africa/Johannesburg']
	mylist.extend(list(pytz.common_timezones_set)) 
	# CST = China Std Time and Central Std Time
	if email and email.split('.')[-1] == 'cn':
		mylist.insert(0, 'Asia/Shanghai')
	return mylist

def findtz(tznm, date, email = ''):
	"Find timezone by abbreviation, use heuristics"
	mylist = tzsearchlist(email)
	for tz in mylist:
		tzi = pytz.timezone(tz)
		if tzi.tzname(date) == tznm:
			return tzi
	print_("WARNING: Could not parse TZ %s" % tznm, file=sys.stderr)
	return pytz.utc

def findtzoff(offstr, date, email = ''):
	"Find timezone by UTC offset, use heuristics"
	mylist = tzsearchlist(email)
	sgn = -1 if offstr[0] == '-' else 1
	off = datetime.timedelta(0, sgn*60*(60*int(offstr[1:3])+int(offstr[3:5])))
	# Need naive datetime
	dt = datetime.datetime(date.year, date.month, date.day, date.hour, date.minute, date.second)
	for tz in mylist:
		tzi = pytz.timezone(tz)
		if tzi.utcoffset(dt) == off:
			return tzi
	print_("WARNING: Could not parse TZ %s" % tznm, file=sys.stderr)
	return pytz.utc

def increl(prevver):
	"Incr. -release string by one"
	pver = prevver.split('-')
	try:
		pver[-1] = str(int(pver[-1])+1)
	except:
		pass
	return '-'.join(pver)

class ParseError(ValueError):
	"Exceptions to throw when we fail to parse RPM/DEB changelog"
	def __init__(self, errstr, ln = plineno):
		ValueError.__init__(self, errstr + ' (line ~ %i)' % ln)

RPMSEP = '-------------------------------------------------------------------'
RPMHDR = '- '
RPMSUB = '  * '
RPMTMF = '%a %b %d %H:%M:%S %Z %Y'
DEBHDR = '  * '
DEBSUB = '    - '
DEBTMF = '%a, %d %b %Y %H:%M:%S %z'

class logitem:
	"Class to hold one item"
	def __init__(self, head=None, subitems=[]):
		self.head = head
		self.subitems = subitems
	def genout(self, hdr, sub, lnln):
		"return generic output string"
		hln = len(hdr)
		sln = len(sub)
		strg = hdr + wrap(self.head, hln, lnln)
		for it in self.subitems:
			strg += '\n' + sub + wrap(it, sln, lnln)
		return strg # + '\n'
	def rpmout(self):
		"RPM formatted output"
		return self.genout(RPMHDR, RPMSUB, 68)
	def debout(self):
		"DEB formatted output"
		return self.genout(DEBHDR, DEBSUB, 70)
	def genparse(self, txt, hdst, subst, joinln = False, tolerant = False, subcnt = None):
		"Parse one log item, consisting of head entry and (optionally) subitems"
		txtln = txt.count('\n')
		hdln  = len(hdst)
		subln = len(subst)
		if not subcnt:
			subcnt = ' '*subln
		subcln = len(subcnt)
		if not txt[0:hdln] == hdst:
			raise ParseError('should start with "%s", got "%s"' % (hdst, txt[0:hdln]), plineno-txtln-2)
		ishead = True
		self.head = ''
		self.subitems = []
		sub = ''
		lnno = 0
		for ln in txt.splitlines():
			#print_(ln)
			lnno += 1
			if ishead:
				if ln[0:subln] == subst:
					ishead = False
					sub = ln[subln:]
				elif ln[0:hdln] == ' '*hdln:
					if joinln:
						self.head += ln[hdln-1:]
					else:
						self.head += '\n' + ln
				elif ln[0:hdln] == hdst:
					self.head += ln[hdln:]
				else:
					raise ParseError('unexpected line start "%s"' % ln[0:subln], plineno-txtln-2+lnno)
			else:
				if ln[0:subcln] == subcnt:
					if joinln:
						sub += ln[subcln-1:]
					else:
						sub += '\n' + ln
				elif ln[0:subln] == subst:
					self.subitems.append(sub)
					sub = ln[subln:]
				else:
					raise ParseError('unexpected subitem line start "%s"' % ln[0:subln], plineno-txtln-2+lnno)
		if sub:
			self.subitems.append(sub)
		return self
			
	def rpmparse(self, txt, joinln = False, tolerant = False):
		return self.genparse(txt, '- ', '  * ', joinln, tolerant)
	def debparse(self, txt, joinln = False, tolerant = False):
		return self.genparse(txt, '  * ', '    - ', joinln, tolerant)
	def debparse_misssub(self, txt, joinln = False, tolerant = False):
		return self.genparse(txt, '  * ', '    ', joinln, tolerant, '     ')
	def contains(self, slist):
		for strg in slist:
			if strg in self.head:
				return True
			for sit in self.subitems:
				if strg in sit:
					return True
		return False


class logentry:
	"Class to hold one changelog entry data"
	import re
	verrgx = re.compile(r'\-([0-9]*\.[^ :]*):')
	ver1rgx = re.compile(r'\-([0-9]*\.[^ :]*)')
	ver2rgx = re.compile(r'[uU]pdate to [ a-zA-Z-]*([0-9]*\.[^ :]*)')
	ver3rgx = re.compile(r'[vV]ersion[: ]*([0-9]*\.[^ :]*)')
	ver4rgx = re.compile(r'[rR]elease[: ]*([0-9]*\.[^ :]*)')
	emerkwds = ('emergency',)
	highkwds = ('CVE', 'exploit')
	medkwds  = ('security', 'vulnerability', 'leak', 'major', ' critical')
	def __init__(self, date=None, email=None, authnm=None, pkgnm=None, vers=None, dist='stable', urg='', emaildb = None, items=[]):
		self.date = date
		self.email = email
		self.authnm = authnm
		self.pkgnm = pkgnm
		self.ver0rgx = logentry.re.compile(r'%s[- ]([0-9]*\.[^ :]*)' % pkgnm)
		self.vers = vers
		self.dist = dist
		self.urg = urg
		self.emaildb = emaildb
		self.items = items
	def rpmout(self):
		"Return string with RPM formatted changelog"
		strg = RPMSEP + '\n'
		idx = len(strg)
		strg += self.date.strftime(RPMTMF)
		if strg[idx+8] == '0':
			strg = strg[0:idx+8]+' '+strg[idx+9:]
			#strg[idx+8] = ' '
		strg += " - %s\n\n" % self.email
		for ent in self.items:
			strg += ent.rpmout() + '\n'
		return strg + '\n'
	def debout(self, prevver = ''):
		"Return string with DEB formatted changelog"
		vers = self.vers
		if not vers and prevver:
			vers = increl(prevver)
		strg = '%s (%s) %s; urgency=%s\n\n' % (self.pkgnm, vers,
							self.dist, self.urg)
		for ent in self.items:
			strg += ent.debout() + '\n'
		strg += '\n -- %s <%s>  ' % (self.authnm, self.email)
		idx = len(strg)
		strg += self.date.strftime(DEBTMF)
		if strg[idx+5] == '0':
			strg = strg[0:idx+5]+' '+strg[idx+6:]
			#strg[idx+6] = ' '
		strg += '\n\n'
		return strg
	def guess_ver_nm(self):
		"Try to determine pkg version and name from changelog text"
		for ent in self.items:
			ln = ent.head
			m = logentry.verrgx.search(ln)
			if not m:
				m = self.ver0rgx.search(ln)
			if not m:
				m = logentry.ver1rgx.search(ln)
			if not m:
				m = logentry.ver2rgx.search(ln)
			if not m:
				m = logentry.ver3rgx.search(ln)
			if m:
				#self.vers = m.group(0)[1:].rstrip('.')
				self.vers = m.group(1).rstrip('.')
				if not self.pkgnm:
					idx = ln.find(self.vers)
					pidx = ln[0:idx].rfind(' ')
					self.pkgnm = ln[pidx+1:idx-1]
					self.ver0rgx = logentry.re.compile(r'%s[- ]([0-9]*\.[^ :]*)' % self.pkgnm)
				if self.vers.find('-') == -1:
					self.vers += '-1'
				return


	def guess_urg(self):
		"Guess urgency"
		for ent in self.items:
			if ent.contains(logentry.emerkwds):
				self.urg = 'emergency'
				return
			if ent.contains(logentry.highkwds):
				self.urg = 'high'
				return
			if ent.contains(logentry.medkwds):
				self.urg = 'medium'
		if not self.urg:
			self.urg = 'low'
	def rpmparse(self, txt, joinln = False, tolerant = False):
		"Parse one RPM changelog entry section"
		txtln = txt.count('\n')
		self.email= ''
		self.items = []
		buf = ''
		procln = 0
		for ln in txt.splitlines():
			procln += 1
			# Handle separator lines
			if ln == RPMSEP:
				if self.email:
					break
				else:
					continue
			# Handle header
			if not self.email:
				try:
					(datestr, email) = ln.split(' - ')
				except ValueError as exc:
					raise ParseError('Could not split date - email in "%s"' % ln, plineno-txtln+procln)
				self.email = email
				tznm = datestr.split(' ')[-2]
				date = datetime.datetime.strptime(datestr, RPMTMF)
				self.date = findtz(tznm, date, email).localize(date)
				if not self.date:
					raise ParseError("No such timezone %s" % tznm, plneno-txtln+procln)
				if not self.authnm:
					if self.emaildb:
						try:
							# Need dict-like iface (__getitem__)
							self.authnm = self.emaildb[email]
						except KeyError:
							self.authnm = guessnm(email)
							print_("WARN: No name found for email %s, guess %s" % (email, self.authnm), file=sys.stderr)
					else:
						self.authnm = guessnm(email)
				continue
			# Handle empty line
			if not ln:
				if buf:
					#print_("EMPTY: " + buf)
					le = logitem().rpmparse(buf, joinln, tolerant)
					self.items.append(le)
					buf = ''
					continue
				else:
					continue
			# Handle new log item
			if ln[0:2] == RPMHDR and buf:
				#print_("NEW: " + buf)
				le = logitem().rpmparse(buf, joinln, tolerant)
				self.items.append(le)
				buf = ''
			buf += ln + '\n'
		if buf:
			#print_("END: "+ buf)
			le = logitem().rpmparse(buf, joinln, tolerant)
			self.items.append(le)
		if not self.vers:
			self.guess_ver_nm()
		if not self.urg:
			self.guess_urg()
		return self
		#return procln
	def debparse(self, txt, joinln = False, tolerant = False):
		"Parse one DEB changelog entry section"
		txtln = txt.count('\n')
		self.urg = ''
		self.items = []
		buf = ''
		procln = 0
		for ln in txt.splitlines():
			procln += 1
			# Handle separator lines
			if ln and ln[0] != ' ':
				if self.email:
					break
			# Handle header
			if not self.pkgnm:
				(self.pkgnm, vers, dist, urg) = ln.split(' ')
				self.vers = vers[1:-1]
				self.dist = dist[0:-1]
				self.urg = urg[8:]
				continue
			# Handle empty line
			if not ln:
				if buf:
					#print_("EMPTY: " + buf)
					le = logitem().debparse(buf, joinln, tolerant)
					self.items.append(le)
					buf = ''
					continue
				else:
					continue
			# Handle new log item
			if ln[0:4] == DEBHDR and buf:
				#print_("NEW: " + buf)
				le = logitem().debparse(buf, joinln, tolerant)
				self.items.append(le)
				buf = ''
			# Handle footer
			if ln[0:4] == " -- ":
				idx = ln.find('<')
				if idx < 0:
					raise ParseError("No email address in footer %s" % ln, plineno-txtln+procln)
				idx2 = ln.find('>')
				self.authnm = ln[4:idx-1]
				self.email = ln[idx+1:idx2]
				self.date = datetime.datetime.strptime(ln[idx2+3:], DEBTMF)
				tzi = findtzoff(ln[-5:], self.date, self.email)
				if tzi.zone != 'UTC':
					self.date = self.date.astimezone(tzi)
				break
			# Normal line, process ...
			buf += ln + '\n'
		if buf:
			#print_("END: "+ buf)
			le = logitem().debparse(buf, joinln, tolerant)
			self.items.append(le)
		return self
		#return procln

class changelog:
	"Container for full changelog"
	def __init__(self, pkgnm=None, authover=None, distover='stable', urgover='', initver = '?-0', emaildb = None, entries=[]):
		self.pkgnm = pkgnm
		self.authover = authover
		self.distover = distover
		self.urgover = urgover
		self.initver = initver
		self.emaildb = emaildb
		self.entries = entries
	def rpmout(self):
		"output RPM changelog as string"
		strg = ''
		for ent in self.entries:
			strg += ent.rpmout()
		return strg
	def fixupdebver(self):
		"fill in missing versions by guessing ..."
		lastver = self.initver
		lastpkg = None
		for idx in range(len(self.entries)-1, -1, -1):
			#print_(sys.stderr, lastver)
			if not self.entries[idx].vers:
				self.entries[idx].vers = increl(lastver)
			if lastpkg and not self.entries[idx].pkgnm:
				self.entries[idx].pkgnm = lastpkg
			elif not lastpkg:
				lastpkg = self.entries[idx].pkgnm
			lastver = self.entries[idx].vers
	def debout(self):
		"output DEB changelog as string"
		self.fixupdebver()
		strg = ''
		for ent in self.entries:
			strg += ent.debout()
		return strg

	def rpmparse(self, fd, joinln = False, tolerant = False, maxent = 0):
		"Parse full RPM changelog"
		global plineno
		buf = ''
		ent = 0
		for ln in fd:
			plineno += 1
			if ln == RPMSEP+'\n':
				if buf:
					#print_(buf)
					self.entries.append(logentry(authnm = self.authover, pkgnm = self.pkgnm, dist = self.distover, urg = self.urgover, emaildb = self.emaildb).rpmparse(buf, joinln, tolerant))
					buf = ''
				ent += 1
				if maxent and ent > maxent:
					break
			buf += ln
		if buf:
			#print_(buf)
			self.entries.append(logentry(authnm = self.authover, pkgnm = self.pkgnm, dist = self.distover, urg = self.urgover, emaildb = self.emaildb).rpmparse(buf, joinln, tolerant))
		return self

	def debparse(self, fd, joinln = False, tolerant = False, maxent = 0):
		"Parse full DEB changelog"
		global plineno
		buf = ''
		ent = 0
		for ln in fd:
			plineno += 1
			if ln != '\n' and ln[0] != ' ':
				if buf:
					#print_(buf)
					self.entries.append(logentry(authnm = self.authover, pkgnm = self.pkgnm, dist = self.distover, urg = self.urgover).debparse(buf, joinln, tolerant))
					buf = ''
				ent += 1
				if maxent and ent > maxent:
					break
			buf += ln
		if buf:
			#print_(buf)
			self.entries.append(logentry(authnm = self.authover, pkgnm = self.pkgnm, dist = self.distover, urg = self.urgover).debparse(buf, joinln, tolerant))
		return self


