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

class ParseError(ValueError):
	pass

class logitem:
	"Class to hold one item"
	def __init__(self, head=None, subitems=[]):
		self.head = head
		self.subitems = subitems
	def rpmout(self):
		strg = '- ' + wrap(self.head, 2, 68) + '\n'
		for it in self.subitems:
			strg += '  * ' + wrap(it, 4, 68) + '\n'
		return strg
	def debout(self):
		strg = '  * ' + wrap(self.head, 4, 70) + '\n'
		for it in self.subitems:
			strg += '    - ' + wrap(it, 6, 70) + '\n'
		return strg
	def parse(self, txt, hdst, subst, subcnt = None):
		hdln  = len(hdst)
		subln = len(subst)
		if not subcnt:
			subcnt = ' '*subln
		subcln = len(subcnt)
		if not txt[0:hdln] == hdst:
			raise ParseError('should start with "- "')
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
					self.head += '\n' + ln
				elif ln[0:hdln] == hdst:
					self.head += ln[hdln:]
				else:
					raise ParseError('unexpected line start "%s"' % ln[0:subln]) 
			else:
				if ln[0:subcln] == subcnt:
					sub += '\n' + ln
				elif ln[0:subln] == subst:
					self.subitems.append(sub)
					sub = ln[subln:]
				else:
					raise ParseError('unexpected subitem line start "%s"' % ln[0:subln])
		if sub:
			self.subitems.append(sub)
			
	def rpmparse(self, txt):
		self.parse(txt, '- ', '  * ')
	def debparse(self, txt):
		self.parse(txt, '  * ', '    - ')
	def debparse_misssub(self, txt):
		self.parse(txt, '  * ', '    ', '     ')


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
		strg = '-------------------------------------------------------------------\n'
		strg += self.date.strftime("%a %b %d %H:%M:%S %Z %Y")
		if strg[78] == '0':
			strg[78] = ' '
		strg += " - %s\n\n" % self.email
		for ent in self.entries:
			strg += ent.rpmout() + '\n'
		return strg
	def debout(self):
		strg = '%s (%s) %s; urgency=%s\n\n' % (self.pkgnm, self.vers,
							self.dist, self.urg)
		for ent in self.entries:
			strg += ent.debout() + '\n'
		strg += ' -- %s <%s>  ' % (self.authnm, self.email)
		idx = len(strg)
		strg += self.date.strftime("%a, %d %b %Y %H:%M:%S %z")
		if strg[idx+6] == '0':
			strg[idx+6] = ' '
		strg += '\n\n'
		return strg

def main(argv):
	#TODO: set locale to en_US
	pass
