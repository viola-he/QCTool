from nativeValidator import QCHTMLParser

fileHTML = open("EMail/content.html").read()
QCParser = QCHTMLParser(fileHTML)
QCParser.run()
QCParser.outputToFile("result.txt")