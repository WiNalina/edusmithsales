# -*- coding: utf-8 -*-
import locale
import os
import warnings

from InvoiceGenerator.api import Invoice
from InvoiceGenerator.conf import FONT_BOLD_PATH, FONT_PATH
from InvoiceGenerator.conf import LANGUAGE

from babel.dates import format_date
from babel.numbers import format_currency

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

import decimal
import io

#Set up all of the fontsizes for all of the parts in the document
company_name_size = 12
tax_id_size = 10
address_size = 10

doc_header_size = 15
date_number_size = 10

customer_size = 10

table_header_size = 10
item_size = 10
total_size = 10

#Set all of the decimals to have zero decimal place
zero_place = decimal.Decimal("0")

def get_lang():
    #Get the language for the app
    return os.environ.get("INVOICE_LANG", LANGUAGE)


class BaseInvoice(object):

    def __init__(self, invoice):
        assert isinstance(invoice, Invoice), "invoice is not instance of Invoice"

        self.invoice = invoice
        self.i = 0
        
    def gen(self, filename):
        """
        Generate the invoice into file

        :param filename: file in which the invoice will be written
        :type filename: string or File
        """
        pass

class NumberedCanvas(Canvas):
    """Set up a canvas for generating a PDF file

    Args:
        Canvas (Canvas object from the reportlab package): Canvas object
    """
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self.canvas = Canvas
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if num_pages > 1:
                self.draw_page_number(num_pages)
            self.canvas.showPage(self)
        self.canvas.save(self)

    def draw_page_number(self, page_count):
        """Generate a page number for each specific page

        Args:
            page_count (int): total document page count
        """
        self.setFont("DejaVu", 7)
        self.drawRightString(
            200*mm,
            20*mm,
            _("Page %(page_number)d of %(page_count)d") % {"page_number": self._pageNumber, "page_count": page_count},
        )


def prepare_invoice_draw(self):
    """
    Prepare all of the document's prerequisites before drawing
    """
    self.TOP = 250
    self.LEFT = 20

    #Register fonts
    pdfmetrics.registerFont(TTFont('DejaVu', FONT_PATH))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', FONT_BOLD_PATH))

    #Create a pdf object
    
    buffer = io.BytesIO()
    self.pdf = NumberedCanvas(buffer, pagesize=A4)
    
    self._addMetaInformation(self.pdf)

    self.pdf.setFont('DejaVu', 15)
    self.pdf.setStrokeColorRGB(0, 0, 0)

    if self.invoice.currency:
        warnings.warn("currency attribute is deprecated, use currency_locale instead", DeprecationWarning)

    return buffer

def currency(amount, unit, locale):
    """Specify the currency's format

    Args:
        amount (float): Currency amount
        unit (str): Currency unit
        locale (str): Locale string 

    Returns:
        str: Formatted currency string
    """
    currency_string = format_currency(amount, unit, locale=locale)
    if locale == 'cs_CZ.UTF-8':
        currency_string = currency_string.replace(u",00", u",-")
    return currency_string

class VatInvoice(BaseInvoice):
    """
    Generator of simple invoice in PDF format

    :param invoice: the invoice
    :type invoice: Invoice
    """
    line_width = 62

    def gen(self, filename=''):
        """
        Generate the invoice into file

        :param filename: file in which the PDF simple invoice will be written
        :type filename: string or File
        """
        self.filename = filename
        
        buffer = prepare_invoice_draw(self)

        # Texty
        self._drawTitle() #Draw document title
        self._drawInvoiceInfo() #Draw Document Date & Code
        self._drawClientInfo() #Draw client's information - name, address, and VAT ID
        self._drawItemsHeader(self.TOP - self.i, self.LEFT) #Draw the document's item header
        self._drawTableLines(self.TOP - self.i, self.LEFT) #Draw the document's table lines
        self._drawItems(self.TOP - self.i, self.LEFT) #Draw the document's items in the table
        self._drawtotal(self.TOP - self.i - 88, self.LEFT) #Draw transaction total information part
        
        self.pdf.showPage()
        self.pdf.save()
        raw_pdf_content = buffer.getvalue()
        buffer.close()

        return raw_pdf_content
        
    #############################################################
    # Draw methods
    #############################################################

    def _addMetaInformation(self, pdf):
        pdf.setCreator(self.invoice.provider.summary)
        pdf.setTitle(self.invoice.title)
        pdf.setAuthor(self.invoice.creator.name)
    
    def check_string_existing(self, str_in):
        if str_in not in {'', 'NaN'} and str_in is not None:
            return True
        else:
            return False
        

    def _drawTitle(self):
        # Draw the VAT invoice title
        self.pdf.setFont('DejaVu-Bold', doc_header_size) #Choose the bold font
        self.pdf.drawString((self.LEFT + 50)*mm, self.TOP*mm, self.invoice.title) #Draw the document title
        
        self.pdf.setFont('DejaVu', company_name_size)
        self.pdf.drawString((self.LEFT + 105) * mm, (self.TOP + 30)*mm, self.invoice.vat_company_name,) #Draw the company name
        
        #Draw the company's VAT ID and addresses
        self.pdf.setFont('DejaVu', tax_id_size)
        self.pdf.drawString((self.LEFT + 111) * mm, (self.TOP + 25)*mm, self.invoice.vat_tax_id,)
        self.pdf.drawString((self.LEFT + 86) * mm, (self.TOP + 20)*mm, self.invoice.company_address_1,)
        self.pdf.drawString((self.LEFT + 108.5) * mm, (self.TOP + 15)*mm, self.invoice.company_address_2,)

    def _drawInvoiceInfo(self):
        #Draw the invoice's date and document code
        #Draw the document's date with the format from the specified locale
        self.i += 8
        self.pdf.setFont('DejaVu-Bold', date_number_size)
        self.pdf.drawString((self.LEFT + 105) * mm, (self.TOP - self.i)*mm, u'วันที่')
        self.pdf.setFont('DejaVu', date_number_size)
        lang = get_lang()
        self.pdf.drawString((self.LEFT + 135) * mm, (self.TOP - self.i)*mm, format_date(self.invoice.date, locale=lang))

        #Draw the invoice number
        self.i += 5
        self.pdf.setFont('DejaVu-Bold', date_number_size)
        self.pdf.drawString((self.LEFT + 105) * mm, (self.TOP - self.i)*mm, u'เลขที่ใบเสร็จ')
        self.pdf.setFont('DejaVu', date_number_size)
        self.pdf.drawString((self.LEFT + 135) * mm, (self.TOP - self.i)*mm, self.invoice.number)

    def _drawClientInfo(self):
        #Draw the client's information
        self.i += 8
        self.pdf.setFont('DejaVu-Bold', customer_size)
        self.pdf.drawString((self.LEFT)*mm, (self.TOP - self.i)*mm, 'ข้อมูลลูกค้า')
        
        #Draw the client's name and VAT ID
        self.i += 5
        self.pdf.setFont('DejaVu-Bold', customer_size)
        self.pdf.drawString((self.LEFT)*mm, (self.TOP - self.i)*mm, 'ชื่อ')
        self.pdf.drawString((self.LEFT + 89) * mm, (self.TOP - self.i)*mm, u'เลขประจำตัวผู้เสียภาษี')
        self.pdf.setFont('DejaVu', customer_size)
        self.pdf.drawString((self.LEFT + 10)*mm, (self.TOP - self.i)*mm, self.invoice.client.summary)
        self.pdf.drawString((self.LEFT + 130)*mm, (self.TOP - self.i)*mm, self.invoice.client.vat_id)

        #Draw the client's address
        self.i += 5
        self.pdf.setFont('DejaVu-Bold', address_size)
        self.pdf.drawString((self.LEFT)*mm, (self.TOP - self.i)*mm, 'ที่อยู่')
        if self.check_string_existing(self.invoice.client.address):
            style = ParagraphStyle('normal', fontName='DejaVu', fontSize=10)
            p = Paragraph(self.invoice.client.address, style)
            pwidth, pheight = p.wrapOn(self.pdf, 150*mm, 30*mm)

            i_add = max(float(pheight)/mm, 4.23)
            self.i += i_add
            p.drawOn(self.pdf, (self.LEFT + 10)*mm, (self.TOP - self.i + 3.25)*mm)
        
    def _drawItemsHeader(self, TOP, LEFT):
        """Draw the VAT invoice's header

        Args:
            TOP (float): Top location millimeter
            LEFT (float): Left location millimeter
        """
        self.pdf.setFont('DejaVu-Bold', table_header_size)
        self.pdf.drawString((LEFT + 10) * mm, (TOP - 9) * mm, _(u'ลำดับ'))
        self.pdf.drawString((LEFT + 52.5) * mm, (TOP - 9) * mm, _(u'รายละเอียด'))
        self.pdf.drawString((LEFT + 99) * mm, (TOP - 9) * mm, _(u'จำนวน'))
        self.pdf.drawString((LEFT + 125.5) * mm, (TOP - 9) * mm, _(u'ราคา'))
        self.pdf.drawString((LEFT + 157) * mm, (TOP - 9) * mm, _(u'รวม'))

    def _drawTableLines(self, TOP, LEFT):
        """Draw the table lines

        Args:
            TOP (float): Top location millimeter
            LEFT (float): Left location millimeter
        """
        #Draw the table frame as the following
        path = self.pdf.beginPath()

        #Draw the top two lines of the table
        #Top line
        path.moveTo(LEFT * mm, (TOP-4) * mm)
        path.lineTo((LEFT + 176) * mm, (TOP-4) * mm)
        self.pdf.drawPath(path, True, True)

        #Second top line
        path.moveTo(LEFT * mm, (TOP - 11) * mm)
        path.lineTo((LEFT + 176) * mm, (TOP - 11) * mm)
        self.pdf.drawPath(path, True, True)

        #Left border line
        path.moveTo((LEFT) * mm, (TOP - 4) * mm)
        path.lineTo((LEFT) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        #Second border line between item order and description
        path.moveTo((LEFT + 30) * mm, (TOP - 4) * mm)
        path.lineTo((LEFT + 30) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        #Third border line between description and count 
        path.moveTo((LEFT + 95) * mm, (TOP - 4) * mm)
        path.lineTo((LEFT + 95) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        #Fourth border line between count and unit price
        path.moveTo((LEFT + 115) * mm, (TOP - 4) * mm)
        path.lineTo((LEFT + 115) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        #Fifth border line between unit price and total price
        path.moveTo((LEFT + 145) * mm, (TOP - 4) * mm)
        path.lineTo((LEFT + 145) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        #Last border line on the rightmost side of the table
        path.moveTo((LEFT + 176) * mm, (TOP - 4) * mm)
        path.lineTo((LEFT + 176) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        #Table line at the bottom of the table
        path.moveTo(LEFT * mm, (TOP - 100) * mm)
        path.lineTo((LEFT + 176) * mm, (TOP - 100) * mm)
        self.pdf.drawPath(path, True, True)

        self.i += 16

    def _drawItems(self, TOP, LEFT):
        """Draw items in the transaction on the document

        Args:
            TOP (float): Top location of the first item in mm
            LEFT (float): Left location of the first item in mm
        """
        temp_top = TOP
        self.pdf.setFont('DejaVu', item_size)

        #Create a paragraph style for writing each item's description
        style = ParagraphStyle('normal', fontName='DejaVu', fontSize=10)
        p = Paragraph('test', style)
        #Find the height a one-line description
        one_line_pwidth, one_line_pheight = p.wrapOn(self.pdf, 60*mm, 30*mm)
        
        item_order = 0
        for item in self.invoice.items:
            #Go over all of the items in the invoice
            #Iterate through the item orders
            item_order += 1

            #Create a paragraph of each item's description
            style = ParagraphStyle('normal', fontName='DejaVu', fontSize=10)
            p = Paragraph(item.description, style)
            pwidth, pheight = p.wrapOn(self.pdf, 60*mm, 30*mm)

            i_add = max(float(pheight)/mm, 4.23)
            temp_top -= i_add
            if item_order == 1:
                self.i += i_add
            diff_space = i_add - max(float(one_line_pheight)/mm, 4.23)
            #Draw the description paragraph on the PDF file
            p.drawOn(self.pdf, (LEFT + 33) * mm, (temp_top + 3) * mm)
            item_order_str = str(item_order)

            #Draw the order on the file
            self.pdf.drawRightString((LEFT + 16) * mm, (temp_top + diff_space + 3) * mm, item_order_str)

            #Draw thei item count on the file
            if float(int(item.count)) == item.count:
                #This case holds when the count is an integer
                self.pdf.drawRightString((LEFT + 108) * mm, (temp_top + diff_space + 3) * mm, u'%s %s' % (locale.format("%i", item.count, grouping=True), item.unit))
            else:
                #This case holds when the count is a float number with non-zero decimal values
                self.pdf.drawRightString((LEFT + 108) * mm, (temp_top + diff_space + 3) * mm, u'%s %s' % (locale.format("%.2f", item.count, grouping=True), item.unit))
            
            #Draw the unit price and the total price for each item
            self.pdf.drawRightString((LEFT + 140) * mm, (temp_top + diff_space + 3) * mm, currency(item.price, self.invoice.currency, self.invoice.currency_locale))
            self.pdf.drawRightString((LEFT + 170) * mm, (temp_top + diff_space + 3) * mm, currency(item.total, self.invoice.currency, self.invoice.currency_locale))

    def _drawtotal(self, TOP, LEFT):
        """Draw the total part or the summary part of the whole transaction

        Args:
            TOP (float): Top location of the total part
            LEFT ([type]): Left location of the total part
        """
        #Set price, total discount, and VAT value as decimals
        self.invoice.price = decimal.Decimal(self.invoice.price)
        self.invoice.total_discount = decimal.Decimal(self.invoice.total_discount)
        self.invoice.vat = decimal.Decimal(self.invoice.vat)

        #Total price for all items altogether 
        self.pdf.setFont('DejaVu-Bold', total_size)
        self.pdf.drawString((LEFT + 100) * mm, (TOP) * mm, 'รวมเงิน')
        self.pdf.setFont('DejaVu', total_size)
        self.pdf.drawRightString((LEFT + 170) * mm, (TOP) * mm, currency(self.invoice.price, self.invoice.currency, self.invoice.currency_locale))

        #Total discount for all items altogether
        self.pdf.setFont('DejaVu-Bold', total_size)
        self.pdf.drawString((LEFT + 100) * mm, (TOP - 5) * mm, 'ส่วนลด')
        self.pdf.setFont('DejaVu', total_size)
        self.pdf.drawRightString((LEFT + 170) * mm, (TOP - 5) * mm, currency(self.invoice.total_discount, self.invoice.currency, self.invoice.currency_locale))

        #Total prices after discounts
        self.pdf.setFont('DejaVu-Bold', total_size)
        self.pdf.drawString((LEFT + 100) * mm, (TOP - 10) * mm, 'มูลค่าสุทธิ')
        self.pdf.setFont('DejaVu', total_size)
        self.pdf.drawRightString((LEFT + 170) * mm, (TOP - 10) * mm, currency(self.invoice.price - self.invoice.total_discount, self.invoice.currency, self.invoice.currency_locale))
        
        #Total VAT value
        self.pdf.setFont('DejaVu-Bold', total_size)
        self.pdf.drawString((LEFT + 100) * mm, (TOP - 15) * mm, 'ภาษีมูลค่าเพิ่ม')
        self.pdf.setFont('DejaVu', total_size)
        self.pdf.drawRightString((LEFT + 170) * mm, (TOP - 15) * mm, currency(self.invoice.vat, self.invoice.currency, self.invoice.currency_locale))
        
        #Total value after discount and VAT
        self.pdf.setFont('DejaVu-Bold', total_size)
        self.pdf.drawString((LEFT + 100) * mm, (TOP - 20) * mm, 'จำนวนเงินทั้งสิ้น')
        self.pdf.setFont('DejaVu', total_size)
        self.pdf.drawRightString((LEFT + 170) * mm, (TOP - 20) * mm, currency(self.invoice.price - self.invoice.total_discount + self.invoice.vat, self.invoice.currency, self.invoice.currency_locale))
        
        #Draw the two lines below the total value after VAT and discount
        path = self.pdf.beginPath()
        path.moveTo((LEFT + 140) * mm, (TOP - 21) * mm)
        path.lineTo((LEFT + 170) * mm, (TOP - 21) * mm)
        self.pdf.drawPath(path, True, True)
        path.moveTo((LEFT + 140) * mm, (TOP - 22) * mm)
        path.lineTo((LEFT + 170) * mm, (TOP - 22) * mm)
        self.pdf.drawPath(path, True, True)

        self.pdf.setFont('DejaVu-Bold', total_size)
        self.pdf.drawString(LEFT * mm, (TOP - 90) * mm, 'ขอบคุณที่ท่านเลือกใช้บริการของเรา')