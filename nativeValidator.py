#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
from bs4 import UnicodeDammit #this is a python lib we should install called BeautifulSoup
from HTMLParser import HTMLParser
from urlparse import urlparse

#decode_html function is used for correct decode our html file
#if the input is already unicode string, we don't have to use beautiful soup to decode the html
#If we can easily decode the code to "utf-8", we don't need to use Beautiful Soup also.
def decode_html(html_string):
	new_doc = UnicodeDammit.detwingle(html_string)
	return new_doc.decode("utf-8")

class QCHTMLParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.__errMsg = {
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
		}
		#filter is used for some ET links
		self.__filter = ["%%view_email_url%%", "%%ftaf_url%%", "%%=GetSocialPublishURL("]
		#alias dict is used for counting alias, Key=AliasName Value=Times
		self.__aliasDict = {}
		#alias List is used for alias & rawlink pairs		
		self.__aliasList = []
		#each error will be append to this list
		self.__errors = []
		#dict used for counting, notice "plain_link" refers to the aTag which has href
		self.__aCount = {
			"plain_link": 0,
			"empty_link": 0,
			"alias": 0,
			"empty_alias": 0,
			"mail": 0,
			"tel": 0,
			"conversion": 0,
		}
		#signal used for catching title data, 
		#I'm still looking into this issue, because if title is null, handle data won't be called
		self.__signals = {
			"title": 0,
		}
		#below is the special characters used for mathing
		trade = unicode("™", encoding="utf-8")
		rball = unicode("®", encoding='utf-8')
		cball = unicode("©", encoding='utf-8')
		mdash = unicode("—", encoding="utf-8")
		#the characters will be put in to below list
		self.__specialCharList = [trade, rball, cball, mdash]

		#list for the escaped character, we can add what we want later
		self.__entityRef = ["amp", "reg", "trade", "copy", "nbsp", "gt", "lt", "mdash", "ndash", "quot", "rdquo", "ldquo"]

	#change the signal	
	def __changeSignal(self, target, number):
		self.__signals[target] = number;

	#input error to the list, param "name" used to indicate the specific wrong attr
	def __errInput(self, position, errMsg, name=None):
		self.__errors.append([position[0], position[1], errMsg, name])

	#if image don't have either width or height, or both are 0 then it will be reported
	#this may need further discussion, but now it is still working
	def __invalidImage(self, width, height):
		if width and height:
			if width == "0" and height == "0":
				self.__errInput(self.getpos(), "invalidImage")
		else: 
			self.__errInput(self.getpos(), "invalidImage")

	#if alias is not found in dict's key, then create one otherwise add 1
	def __isAliasDuplicated(self, alias):
		if self.__aliasDict.has_key(alias):
			self.__aliasDict[alias] += 1
			return True
		else: 
			self.__aliasDict[alias] = 1
			return False

	#the logic is a little confused but it use "urlparse", so check the document
	def __urlValidation(self, url):
		if any(url.startswith(x) for x in self.__filter):
			return
		if "replace" in url.lower():
			self.__errInput(self.getpos(), "replaceLink")	
		else:
			o = urlparse(url)
			if not any(x == o.scheme for x in ["mailto", "tel"]):
				if not o.scheme and " http" in o.path:
					self.__errInput(self.getpos(), "spaceLink")
				if not o.scheme and not o.netloc:
					self.__errInput(self.getpos(), "noHttp")
				if not ".com" in o.netloc and not o.netloc.startswith("http"):
					self.__errInput(self.getpos(), "noDotCom")
				if "http:" in o.netloc and "http" in o.scheme:
					self.__errInput(self.getpos(), "doubleHttp")
				if not o.query and "&" in o.path:
					self.__errInput(self.getpos(), "noQuestionMark")
				if any(x in o.fragment for x in ["?", "&"]):
					self.__errInput(self.getpos(), "wrongFragment")

	#using urlparse to get the scheme of a url
	def __getUrlScheme(self, url):
		o = urlparse(url)
		return o.scheme

	#check if alias contain return
	def __hasReturn(self, alias):
		if "\n" in alias:
			self.__errInput(self.getpos(), "returnInAlias")

	#check if has special char
	def __hasSpecialChar(self, content):
		if any(x in content for x in self.__specialCharList):
			self.__errInput(self.getpos(), "specialChar")

	#only equal true then it will pass the validation
	def __convValidation(self, value):
		if value.lower() == "true":
			return True
		return False

	#login the data to alias list
	def __aliasInput(self, alias, rawlink, conversion):
		isDuplicated = self.__isAliasDuplicated(alias)
		if conversion or conversion == "":
			hasConversion = self.__convValidation(conversion)
			if not hasConversion:
				hasConversion = "invalid"
				self.__errInput(self.getpos(), "wrongConv")
		else: hasConversion = False
		if not alias:
			alias = "None/Empty"
		if not rawlink:
			rawlink = "None/Empty"
		hasConversion = str(hasConversion)
		isDuplicated = str(isDuplicated)
		self.__aliasList.append([alias, rawlink, hasConversion, isDuplicated])

	#count the number of the link
	#if we can't get an attr, we will get None
	def __count(self, alias, link, conversion):
		scheme = self.__getUrlScheme(link)
		if link is None:
			self.__errInput(self.getpos(), "noAttr", "href")
		else:
			self.__aCount["plain_link"] += 1
			if link:
				if scheme == "tel":
					self.__aCount["tel"] += 1
				elif scheme == "mailto":
					self.__aCount["mail"] += 1
			else:
				self.__errInput(self.getpos(), "emptyValue", "href")
				self.__aCount["empty_link"] += 1
		if alias is None and scheme != "tel" and scheme != "mailto":
			self.__errInput(self.getpos(), "noAttr", "alias")
		elif alias and scheme != "tel" and scheme != "mailto":
			self.__aCount["alias"] += 1
		elif alias == "":
			self.__aCount["empty_alias"] += 1
			self.__errInput(self.getpos(), "emptyValue", "alias")
		if conversion or conversion == "":
			self.__aCount["conversion"] += 1
	
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
		self.__invalidImage(width, height)
		if alt:
			self.__hasSpecialChar(alt)

	#while a tag detected, pass it to this method
	def aTagCheck(self, attrs):
		link = None
		alias = None
		conversion = None
		for item in attrs:
			if item[0] == "href":
				link = item[1]
			if item[0] == "alias":
				alias = item[1]
			if item[0] == "conversion":
				conversion = item[1]
		self.__aliasInput(alias, link, conversion)
		self.__count(alias, link, conversion)
		#it's quite confusion here, the empty validation is done in __count method
		#maybe we can move that out here
		if link:
			self.__urlValidation(link)
		if alias:
			self.__hasReturn(alias)

	#handle_xxxxx overwrite the blank method in the HTMLParser
	def handle_starttag(self, tag, attrs):
		if tag == "img":
			self.imageCheck(attrs)
		elif tag == "a":
			self.aTagCheck(attrs)
		elif tag == "title":
			self.__changeSignal("title", 1)

	def handle_endtag(self, tag):
		if tag == "title":
			self.__changeSignal("title", 0)
	def handle_data(self,data):
		if self.__signals["title"] == 1:
			if not data:
				self.__errInput(self.getpos(), "emptyValue", "title")
		if data:
			self.__hasSpecialChar(data)

	#handle_entityref is used for handling escaped character like &amp &reg
	#for now, if we missing semi-colon after the &amp or &reg etc. , we won't catch the missing semi-colon
	#this could be fixed by modify the HTMLParser(Python built-in lib). Won't be difficult.
	def handle_entityref(self, name):
		if not any(x == name for x in self.__entityRef):
			self.__errInput(self.getpos(), "wrongEntity")

	##overwrite the original method which will convert the escaped character in the alt attr
	def unescape(self, s):
		return s
	#output all the errors
	def output(self, filename):
		outFile = open(filename, "w")
		#output the error pool
		outFile.write("\n"*2 + "*"*50 + "\n"*2)
		outFile.write("Outputing Errors......\n\n")
		outFile.write("*"*50 + "\n"*2)
		for error in self.__errors:
			if not error[-1]:
				error[-1] = ""
			outputStr = "Line: " + str(error[0]) + " Offset: " + str(error[1]) + " Error Message: " + self.__errMsg[error[2]] + error[3] + "\n"
			outFile.write(outputStr)
		# output the alias couting problems
		outputStr = "" 
		duplicatedones = []
		for key in self.__aliasDict:
			outputStr += str(key) + "\t" + str(self.__aliasDict[key]) + "\n"
			if self.__aliasDict[key] >1:
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
		for key in self.__aCount:
			outFile.write(str(key) + " : " + str(self.__aCount[key]) + "\n")
		# output the alias rawlink pairs
		outFile.write("\n"*2 + "*"*50 + "\n"*2)
		outFile.write("Outputing Alias , Rawlinks combination...\n\n")
		outFile.write("*"*50 + "\n"*2)
		outFile.write("Alias Name\tRaw Links\tConversion\tisDuplicated\n\n")
		for alias in self.__aliasList:
			outputStr = "\t".join(alias) + "\n"
			outFile.write(outputStr)
		outFile.close()


fileHTML = open("EMail/content.html").read()
parser = QCHTMLParser()
parser.feed(decode_html(fileHTML))
parser.output("result.txt")