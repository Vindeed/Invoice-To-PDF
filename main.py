from bs4 import BeautifulSoup
from decimal import Decimal, getcontext, ROUND_HALF_UP
import pdfkit

from editInvoice import Ui_Dialog
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QDialog, QApplication, QFileDialog

# creating rounding function
round_context = getcontext()
round_context.rounding = ROUND_HALF_UP


def c_round(x, digits, precision=5):
    tmp = round(Decimal(x), precision)
    return float(tmp.__round__(digits))


# variables below are needed for globals
fileName = ''
fileNames = []  # used to store HTML files that will be amended
correctFile = 0  # used as a flag to see if the file is of correct type before amending
p = 0  # used to iterate over files to find if they are of type html
file = 0  # used to iterate over multiple files that require


class EditInvoice(qtw.QWidget):  # required for GUI https://www.youtube.com/watch?v=XXPNpdaK9WA <- for pyqt guide
    def __init__(self, *args, **kwargs):  # object stuff that I do not fully understand
        super().__init__(*args, **kwargs)

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.btnAmend.clicked.connect(self.checkBeforeAmendHTML)
        self.ui.btnFindFile.clicked.connect(self.findFile)

    def checkBeforeAmendHTML(self):
        if correctFile == 1:
            self.amendHTML()
        else:
            qtw.QMessageBox.critical(self, 'Error', 'No HTML file is currently selected. Click on Choose HTML File.')

    def amendHTML(self):
        global file
        file = 0
        while file < len(fileNames):
            # parsing through selected document
            source = BeautifulSoup(open(fileNames[file]), "html.parser")

            # finding column number of necessary headers
            uniqueCol = source.find_all("th", {"width": "70"})

            colGstFree = len(uniqueCol) + 3
            colPrice = colGstFree + 1
            colCredit = colPrice + 1
            colGst = colCredit + 1
            colTotal = colGst + 1

            totalGST = 0
            totalLine = 0

            # finding number of rows in the table to then loop through
            temp = source.find_all('td', class_='line-total')
            numOfRows = len(temp) - 1

            # editing inner table with correct GST values and Total values
            table = source.find_all('tr')
            i = 8
            while i < numOfRows + 8:
                temp = str(table[i]).splitlines()
                addedColumns = 0

                # 15/03/23 added for loop and variable 'addedColumns' to deal with </div></td> issues
                for x in range(len(temp) - 1):
                    if temp[x] == "</div></td>":
                        addedColumns += 1

                # string functions to get necessary text to replace
                incorrectGST = temp[colGst + addedColumns].replace('<td>$', '').replace('</td>', '')
                incorrectLineTotal = temp[colTotal + addedColumns].replace('<td class="line-total">$', '').replace('</td>', '')
                itemGST = (Decimal(temp[colPrice + addedColumns].replace('<td>$', '').replace('</td>', '').replace(',', '')) / 10)
                gstApplicable = Decimal(temp[colPrice + addedColumns].replace('<td>$', '').replace('</td>', '').replace(',', ''))
                totalGST = totalGST + gstApplicable
                lineTotal = (itemGST + gstApplicable +
                             Decimal(temp[colGstFree + addedColumns].replace('<td>$', '').replace('</td>', '').replace(',', '')) +
                             Decimal(temp[colCredit + addedColumns].replace('<td>$', '').replace('</td>', '').replace(',', '')))
                totalLine = totalLine + lineTotal

                itemGST = '{:,.2f}'.format(c_round(itemGST, 2))
                lineTotal = '{:,.2f}'.format(c_round(lineTotal, 2))

                # replacing gst value and line total value in HTML row to then replace in the 'source' object
                tempChangeTableRow = str(table[i]).replace(incorrectGST, str(itemGST)).replace(incorrectLineTotal,
                                                                                               str(lineTotal))
                soup = BeautifulSoup(tempChangeTableRow, "html.parser")

                for element in source.findAll('tr'):
                    if element == table[i]:
                        element.replaceWith(soup)

                i += 1

            # rounding totals
            totalGST = '{:,.2f}'.format(c_round(totalGST / 10, 2))
            totalLine = '{:,.2f}'.format(c_round(totalLine, 2))

            # a lot of replacing totals until line 129
            extraTotalsDivider = source.find('tr', class_="extra-totals divider")
            listExtraTotalsDivider = str(extraTotalsDivider).splitlines()

            incorrectGstTotal = listExtraTotalsDivider[6].replace('<td>$', '').replace('</td>', '')
            incorrectTotal = listExtraTotalsDivider[7].replace('<td class="line-total">$', '').replace('</td>', '')

            correctExtraTotalsDivider = str(extraTotalsDivider).replace(incorrectGstTotal, str(totalGST)).replace(
                incorrectTotal, str(totalLine))
            soup = BeautifulSoup(correctExtraTotalsDivider, "html.parser")

            for element in source.find('tr', class_="extra-totals divider"):
                element.replaceWith(soup)

            grandTotal = source.find('tr', class_="grand-total")
            correctGrandTotal = str(grandTotal).replace(incorrectTotal, str(totalLine))
            soup = BeautifulSoup(correctGrandTotal, "html.parser")

            for element in source.find('tr', class_="grand-total"):
                element.replaceWith(soup)

            gstGrandTotal = source.find_all('th', class_="line-total")
            correctGstGrandTotal = str(gstGrandTotal[1]).replace(incorrectGstTotal, str(totalGST))
            soup = BeautifulSoup(correctGstGrandTotal, "html.parser")

            for element in source.find_all('th', class_="line-total"):
                if element == gstGrandTotal[1]:
                    element.replaceWith(soup)

            # finding invoice name/id
            heading1s = source.find_all('h1')
            invoiceName = "EatFirst Invoice " + str(heading1s[1]).replace('<h1>Tax Invoice #', '').replace('</h1>', '')

            # creating new HTML file
            with open(invoiceName + '.html', 'w', encoding='utf-8') as f_out:
                f_out.write(source.prettify())

            # creating edited pdf
            # path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            # config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
            pdfkit.from_file(invoiceName + '.html', invoiceName + ".pdf")  # ", configuration=config" used to be there

            self.ui.lblResults.setText('Amended, Check File Explorer')

            file += 1

    def findFile(self):
        global fileName
        global fileNames
        fileName = QFileDialog.getOpenFileNames(self, 'Open HTML file')
        fileName = str(fileName).replace("'", "").replace("[", "").replace("'], 'All Files (*)')", "").replace(' ', '').replace('(', '').replace(')', '')
        fileName = fileName[:fileName.rfind('],AllFiles*')]
        fileNames = fileName.split(",")

        global correctFile
        global p  # dummy variable
        p = 0

        while p < len(fileNames):
            filePath = fileNames[p]
            print(filePath)
            if filePath.rfind('.html') == -1:
                self.ui.lblFileName.setText('No HTML file selected')
                self.ui.lblResults.setText('No HTML file selected')
                qtw.QMessageBox.critical(self, 'Error', 'A selected file is not a HTML file. Choose another file.')
                correctFile = 0
                p = len(fileNames)

            else:
                self.ui.lblFileName.setText('Files ready to amend')
                self.ui.lblResults.setText('Not amended')
                correctFile = 1
                p += 1

        print(fileNames)


if __name__ == '__main__':
    app = qtw.QApplication([])

    widget = EditInvoice()
    widget.show()

    app.exec_()

# check how to calculate gstTotal and lineTotal
# download files in /downloads/ directory
# wk-html needed for user
# change the header from being 'Dialog'
