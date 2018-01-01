#!/usr/bin/env python3
#
# Tool to transform debian.changelog into RPM .changes files
# and vice versa
#
# (c) Kurt Garloff <kurt@garloff.de>, 1/2018
# License: CC-BY-SA 3.0

import os
import sys

def wrap(txt, indent, maxln):
	"Amazingly complex code to wrap text"
	strg = ''
	idx = 0
	while len(txt[idx:]) > maxln-indent:
		# Handle preformatted text
		lf   = txt[idx:idx+maxln-indent+1].rfind('\n')
		if lf > 0 and txt[idx+lf+1:idx+lf+2] == ' ':
			strg += txt[idx:idx+lf+1]
			idx += lf+1
			strg += ' '*indent
			while txt[idx:idx+1] == ' ':
				idx+=1
			continue
		# Reformatting (wrapping) necessary
		sep  = txt[idx:idx+maxln-indent].rfind(' ')
		sep2 = txt[idx:idx+maxln-indent].rfind('-')
		if sep == -1 and sep2 == -1:
			strg += txt[idx:idx+maxln-indent] + '\n' + ' '*indent
			idx += maxln-indent
		elif sep2 > sep:
			strg += txt[idx:idx+sep2+1] + '\n' + ' '*indent
			idx += sep2+1
		else:
			strg += txt[idx:idx+sep] + '\n' + ' '*indent
			idx += sep+1
	strg += txt[idx:]
	#print(strg)
	return strg

class logitem:
	"Class to hold one item"
	def __init__(self, head, subitems=[]):
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


class logentry:
	"Class to hold one changelog entry data"
	pass
