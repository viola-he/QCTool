#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
from bs4 import UnicodeDammit #this is a python lib we should install called BeautifulSoup
from HTMLParser import HTMLParser
from urlparse import urlparse
from htmlentitydefs import entitydefs
import re, codecs

#Beautiful Soup could be found here http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser

class QCHTMLParser(HTMLParser):
	def __init__(self, data):
		HTMLParser.__init__(self)
		self.source = self.decode_html(data)
		self.errMsg = {
			#dictionary for errors. Output metthod will use the "key" to get the "value" to output the error.
			"invalidImage": "The dimension of the image is invalided.",
			"replaceLink": "Word \"replace\" found in link.",
			"spaceLink": "Space found before http.",
			"noDotCom": "Can't find .com in the url host.",
			"doubleHttp": "Found http twice in the url.",
			"noQuestionMark": "& symbol found in URL, but no ? symbol found, query parse failed.",
			"wrongFragment": "& or ? symbol found after # symbol, please make sure it's correct.",
			"emptyValue": "Empty value found in ",
			"noAttr": "Unable to find attribute ",
			"returnInAlias": "Found return symbol in alias.",
			"specialChar": "Found spcial character in the copy.",
			"noHttp": "No http found at the begining of the url.",
			"wrongConv": "Conversion detected but value invalided.",
			"wrongEntity": "Wrong escaped character found",
			"duplicatedAlias": "Found alias duplicated with former alias",
			"over500": "line over 500",
		}
		#filter is used for some ET links
		self.filter = ["%%view_email_url%%", "%%ftaf_url%%", "%%=GetSocialPublishURL("]
		#alias dict is used for counting alias, Key=AliasName Value=Times
		self.aliasDict = {}
		#alias List is used for alias & rawlink pairs		
		self.aliasList = []
		#each error will be append to this list
		self.errors = []
		#dict used for counting, notice "plain_link" refers to the aTag which has href
		self.aCount = {
			"view_email": 0,
			"plain_link": 0,
			"empty_link": 0,
			"alias": 0,
			"empty_alias": 0,
			"mail": 0,
			"tel": 0,
			"conversion": 0,
		}
		self.sline = ""
		#signal used for catching title data, 
		#I'm still looking into this issue, because if title is null, handle data won't be called
		self.signals = {
			"title": 0, # 0=Unreached, 1=Reached, 2=DataFound
			"style-end": 0, # 0=Unreached, 1=Reached
		}
		#below is the special characters used for mathing
		trade = unicode("™", encoding="utf-8")
		rball = unicode("®", encoding='utf-8')
		cball = unicode("©", encoding='utf-8')
		mdash = unicode("—", encoding="utf-8")
		#the characters will be put in to below list
		self.specialCharList = [trade, rball, cball, mdash]
	def run(self):
		self.check500Chars()
		self.feed(self.source)

	#decode_html function is used for correct decode our html file
	#if the input is already unicode string, we don't have to use beautiful soup to decode the html
	#If we can easily decode the code to "utf-8", we don't need to use Beautiful Soup also.
	def decode_html(self, html_string):
		new_doc = UnicodeDammit.detwingle(html_string)
		return new_doc.decode("utf-8")

	#change the signal	
	def changeSignal(self, target, number):
		self.signals[target] = number;

	#input error to the list, param "name" used to indicate the specific wrong attr
	def errInput(self, position, errMsg, name=None):
		self.errors.append([position[0], position[1], errMsg, name])

	#if image don't have either width or height, or both are 0 then it will be reported
	#this may need further discussion, but now it is still working
	def invalidImage(self, width, height):
		if width and height:
			if width == "0" and height == "0":
				self.errInput(self.getpos(), "invalidImage")
		else: 
			self.errInput(self.getpos(), "invalidImage")

	#if alias is not found in dict's key, then create one otherwise add 1
	def isAliasDuplicated(self, alias):
		bObj = False
		for item in alias:
			if self.aliasDict.has_key(item):
				self.aliasDict[item] += 1
				bObj = True
			else: 
				self.aliasDict[item] = 1
		return bObj

	#the logic is a little confused but it use "urlparse", so check the document
	def urlValidation(self, url):
		if any(url.startswith(x) for x in self.filter):
			return
		if "replace" in url.lower():
			self.errInput(self.getpos(), "replaceLink")	
		else:
			o = urlparse(url)
			if not any(x == o.scheme for x in ["mailto", "tel"]):
				if not o.scheme and " http" in o.path:
					self.errInput(self.getpos(), "spaceLink")
				if not o.scheme and not o.netloc:
					self.errInput(self.getpos(), "noHttp")
				if not ".com" in o.netloc and not o.netloc.startswith("http"):
					self.errInput(self.getpos(), "noDotCom")
				if "http:" in o.netloc and "http" in o.scheme:
					self.errInput(self.getpos(), "doubleHttp")
				if not o.query and "&" in o.path:
					self.errInput(self.getpos(), "noQuestionMark")
				if any(x in o.fragment for x in ["?", "&"]):
					self.errInput(self.getpos(), "wrongFragment")

	#using urlparse to get the scheme of a url
	def getUrlScheme(self, url):
		o = urlparse(url)
		return o.scheme

	#check if alias contain return
	def hasReturn(self, alias):
		for item in alias:
			if "\n" in item:
				self.errInput(self.getpos(), "returnInAlias")

	#check if has special char
	def hasSpecialChar(self, content):
		if any(x in content for x in self.specialCharList):
			self.errInput(self.getpos(), "specialChar")

	#only equal true then it will pass the validation
	def convValidation(self, value):
		if value.lower() == "true":
			return True
		return False

	#login the data to alias list
	def aliasInput(self, alias, rawlink, conversion):
		isDuplicated = self.isAliasDuplicated(alias)
		if conversion or conversion == "":
			hasConversion = self.convValidation(conversion)
			if not hasConversion:
				hasConversion = "invalid"
				self.errInput(self.getpos(), "wrongConv")
		else: hasConversion = False
		if not alias:
			aliasStr = "None/Empty"
		else:
			aliasStr = "|".join(alias)
		if not rawlink:
			rawlink = "None/Empty"
		hasConversion = str(hasConversion)
		isDuplicated = str(isDuplicated)
		self.aliasList.append([aliasStr, rawlink, hasConversion, isDuplicated])

	#count the number of the link
	#if we can't get an attr, we will get None
	def count(self, alias, link, conversion):
		scheme = self.getUrlScheme(link)
		if link is None:
			self.errInput(self.getpos(), "noAttr", "href")
		else:
			self.aCount["plain_link"] += 1
			if link:
				if scheme == "tel":
					self.aCount["tel"] += 1
				elif scheme == "mailto":
					self.aCount["mail"] += 1
				elif link == "%%view_email_url%%":
					self.aCount["view_email"] += 1
			else:
				self.errInput(self.getpos(), "emptyValue", "href")
				self.aCount["empty_link"] += 1
		if len(alias) == 0 and scheme != "tel" and scheme != "mailto":
			self.errInput(self.getpos(), "noAttr", "alias")
		elif alias[0] and scheme != "tel" and scheme != "mailto":
			self.aCount["alias"] += 1
		elif any(x == "" for x in alias):
			self.aCount["empty_alias"] += 1
			self.errInput(self.getpos(), "emptyValue", "alias")
		if conversion or conversion == "":
			self.aCount["conversion"] += 1

	def check500Chars(self):
		source = self.source.split('\n')
		for lineno, line in enumerate(source):
			if len(line)>500:
				self.errInput([lineno, 0], "over500")
	
	#while img tag detected, pass it to this method
	def imageCheck(self, attrs):
		width = None
		height = None
		alt = None
		for item in attrs:
			if item[0] == "width":
				width = item[1]
			if item[0] == "height":
				height = item[1]
			if item[0] == "alt":
				alt = item[1]
		self.invalidImage(width, height)
		if alt:
			self.hasSpecialChar(alt)

	#using re to grab the subjectline -- need further test
	def get_sline(self, text):
		regex = re.compile(r'set\s@subjectline\s?=\s?"([^"\\]*(?:\\.[^"\\]*)*)"', re.IGNORECASE)
		match = regex.search(text)
		if match:
			return match.group(1)
		else:
			return match

	#while a tag detected, pass it to this method
	def aTagCheck(self, attrs):
		link = None
		alias = []
		conversion = None
		for item in attrs:
			if item[0] == "href":
				link = item[1]
			if item[0] == "alias":
				alias.append(item[1])
			if item[0] == "conversion":
				conversion = item[1]
		self.aliasInput(alias, link, conversion)
		self.count(alias, link, conversion)
		#it's quite confusion here, the empty validation is done in count method
		#maybe we can move that out here
		if link:
			self.urlValidation(link)
		if len(alias) != 0:
			self.hasReturn(alias)

	#handle_xxxxx overwrite the blank method in the HTMLParser
	def handle_starttag(self, tag, attrs):
		if tag == "img":
			self.imageCheck(attrs)
		elif tag == "a":
			self.aTagCheck(attrs)
		elif tag == "title":
			self.changeSignal("title", 1)

	def handle_endtag(self, tag):
		if tag == "title":
			if self.signals["title"] == 1:
				#if not 2, means not data found. So report error
				self.errInput(self.getpos(), "emptyValue", "title")
			self.changeSignal("title", 0)
		if tag == "style":
			self.changeSignal("style-end", 1)
		if tag == "head":
			self.changeSignal("style-end", 0)
	def handle_data(self,data):
		if self.signals["title"] == 1:
			self.changeSignal('title', 2)
		if data:
			self.hasSpecialChar(data)
		if self.signals["style-end"] == 1:
			#we can get the AMP Script
			sline = self.get_sline(data)
			if sline: 
				self.sline = sline

	#handle_entityref is used for handling escaped character like &amp &reg
	#for now, if we missing semi-colon after the &amp or &reg etc. , we won't catch the missing semi-colon
	#this could be fixed by modify the HTMLParser(Python built-in lib). Won't be difficult.
	def handle_entityref(self, name):
		if not entitydefs.get(name):
			self.errInput(self.getpos(), "wrongEntity")

	##overwrite the original method which will convert the escaped character in the alt attr
	def unescape(self, s):
		return s
	#output all the errors
	def outputToFile(self, filename):
		outFile = codecs.open(filename, "w", "utf-8")
		#output the sline
		outFile.write("\n"*2 + "The subjectline in AMPScript is:\n")
		outFile.write("*"*50 + "\n"*2)
		outFile.write(self.sline + "\n"*2)
		outFile.write("*"*50 + "\n"*2)
		#output the error pool
		outFile.write("\n"*2 + "*"*50 + "\n"*2)
		outFile.write("Outputing Errors......\n\n")
		outFile.write("*"*50 + "\n"*2)
		for error in self.errors:
			if not error[-1]:
				error[-1] = ""
			outputStr = "Line: " + str(error[0]) + " Offset: " + str(error[1]) + " Error Message: " + self.errMsg[error[2]] + error[3] + "\n"
			outFile.write(outputStr)
		# output the alias couting problems
		outputStr = "" 
		duplicatedones = []
		for key in self.aliasDict:
			outputStr += str(key) + "\t" + str(self.aliasDict[key]) + "\n"
			if self.aliasDict[key] >1:
				duplicatedones.append(str(key))
		outFile.write("\n"*2 + "*"*50 + "\n"*2)
		outFile.write("Outputing Alias Duplicated times, if number equals 1, then means it's not duplicated.\n\n")
		outFile.write("*"*50 + "\n"*2)
		outFile.write("Following alias are duplicated. \n" + "\n".join(duplicatedones) + "\n"*2)
		outFile.write("Alias Name\tAppear times\n")
		outFile.write(outputStr + "\n")
		# output the count pool
		outFile.write("\n"*2 + "*"*50 + "\n"*2)
		outFile.write("Outputing the counts of the a tags\n\n")
		outFile.write("*"*50 + "\n"*2)
		for key in self.aCount:
			outFile.write(str(key) + " : " + str(self.aCount[key]) + "\n")
		# output the alias rawlink pairs
		outFile.write("\n"*2 + "*"*50 + "\n"*2)
		outFile.write("Outputing Alias , Rawlinks combination...\n\n")
		outFile.write("*"*50 + "\n"*2)
		outFile.write("Alias Name\tRaw Links\tConversion\tisDuplicated\n\n")
		for alias in self.aliasList:
			outputStr = "\t".join(alias) + "\n"
			outFile.write(outputStr)
		outFile.close()
