#!/usr/bin/env python3
#
# Tool to transform debian.changelog into RPM .changes files
# and vice versa
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2018
# License: CC-BY-SA 3.0

import os
import sys
import datetime
import pytz

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
	#print(strg)
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


def findtz(tznm, date, email = ''):
	# Search TZ
	mylist = ['Europe/Amsterdam', 'Europe/Kiev', 'Europe/London', 'Europe/Moscow', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'America/Sao_Paulo', 'Asia/Seoul', 'Asia/Tokyo', 'Asia/Beijing', 'Australia/Sydney', 'Africa/Johannesburg']
	mylist.extend(list(pytz.common_timezones_set)) 
	# CST = China Std Time and Central Std Time
	if email.split('.')[-1] == 'cn':
		mylist.insert(0, 'Asia/Beijing')
	for tz in mylist:
		tzi = pytz.timezone(tz)
		if tzi.tzname(date) == tznm:
			return tzi
	print("WARNING: Could not parse TZ %s" % tznm, file=sys.stderr)
	return pytz.utc

class ParseError(ValueError):
	"Exceptions to throw when we fail to parse RPM/DEB changelog"
	pass

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
		hln = len(hdr)
		sln = len(sub)
		strg = hdr + wrap(self.head, hln, lnln)
		for it in self.subitems:
			strg += '\n' + sub + wrap(it, sln, lnln)
		return strg # + '\n'
	def rpmout(self):
		return self.genout(RPMHDR, RPMSUB, 68)
	def debout(self):
		return self.genout(DEBHDR, DEBSUB, 70)
	def genparse(self, txt, hdst, subst, joinln = False, subcnt = None):
		hdln  = len(hdst)
		subln = len(subst)
		if not subcnt:
			subcnt = ' '*subln
		subcln = len(subcnt)
		if not txt[0:hdln] == hdst:
			raise ParseError('should start with "%s", got "%s"' % (hdst, txt[0:hdln]))
		ishead = True
		self.head = ''
		self.subitems = []
		sub = ''
		for ln in txt.splitlines():
			#print(ln)
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
					raise ParseError('unexpected line start "%s"' % ln[0:subln]) 
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
					raise ParseError('unexpected subitem line start "%s"' % ln[0:subln])
		if sub:
			self.subitems.append(sub)
		return self
			
	def rpmparse(self, txt, joinln = False):
		return self.genparse(txt, '- ', '  * ', joinln)
	def debparse(self, txt, joinln = False):
		return self.genparse(txt, '  * ', '    - ', joinln)
	def debparse_misssub(self, txt, joinln = False):
		return self.genparse(txt, '  * ', '    ', joinln, '     ')


class logentry:
	"Class to hold one changelog entry data"
	def __init__(self, date=None, email=None, authnm=None, pkgnm=None, vers=None, dist='stable', urg='low', entries=[]):
		self.date = date
		self.email = email
		self.authnm = authnm
		self.pkgnm = pkgnm
		self.vers = vers
		self.dist = dist
		self.urg = urg
		self.entries = entries
	def rpmout(self):
		strg = RPMSEP + '\n'
		idx = len(strg)
		strg += self.date.strftime(RPMTMF)
		if strg[idx+8] == '0':
			strg = strg[0:idx+8]+' '+strg[idx+9:]
			#strg[idx+8] = ' '
		strg += " - %s\n\n" % self.email
		for ent in self.entries:
			strg += ent.rpmout() + '\n'
		return strg + '\n'
	def debout(self):
		strg = '%s (%s) %s; urgency=%s\n\n' % (self.pkgnm, self.vers,
							self.dist, self.urg)
		for ent in self.entries:
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
		import re
		rgx = re.compile(r'\-[0-9]*\.[^ :]*')
		for ent in self.entries:
			ln = ent.head
			m = rgx.search(ln)
			if m:
				self.vers = m.group(0)[1:]
				idx = ln.find(self.vers)
				pidx = ln[0:idx].rfind(' ')
				self.pkgnm = ln[pidx+1:idx-1]
				return
	def rpmparse(self, txt, joinln = False):
		self.email= ''
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
				(datestr, email) = ln.split(' - ')
				self.email = email
				tznm = datestr.split(' ')[-2]
				date = datetime.datetime.strptime(datestr, RPMTMF)
				self.date = findtz(tznm, date, email).localize(date)
				if not self.date:
					raise ParseError("No such timezone %s" % tznm)
				self.authnm = guessnm(email)
				continue
			# Handle empty line
			if not ln:
				if buf:
					#print("EMPTY: " + buf)
					le = logitem().rpmparse(buf, joinln)
					self.entries.append(le)
					buf = ''
					continue
				else:
					continue
			# Handle new log item
			if ln[0:2] == RPMHDR and buf:
				#print("NEW: " + buf)
				le = logitem().rpmparse(buf, joinln)
				self.entries.append(le)
				buf = ''
			buf += ln + '\n'
		if buf:
			print(buf)
			le = logitem().rpmparse(buf, joinln)
			self.entries.append(le)
		if not self.vers and not self.pkgnm:
			self.guess_ver_nm()
		return self
		#return procln


def main(argv):
	#TODO: set locale to en_US
	pass
