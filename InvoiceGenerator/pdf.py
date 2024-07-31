# -*- coding: utf-8 -*-
import errno
import locale
import os
import warnings

from InvoiceGenerator.api import Invoice
from InvoiceGenerator.conf import FONT_PATH, FONT_BOLD_PATH, FONT_ITALIC_PATH
from InvoiceGenerator.conf import LANGUAGE, get_gettext

from PIL import Image

from babel.dates import format_date
from babel.numbers import format_currency

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Frame, KeepInFrame, Paragraph

import io

__all__ = ['SimpleInvoice', 'ProformaInvoice', 'CorrectingInvoice']


def get_lang():
    return os.environ.get("INVOICE_LANG", LANGUAGE)

def separate_new_lines(str_in):
    """Separate new lines when new line strings are found

    Args:
        str_in (str): input string

    Returns:
        list: list of strings with each string being each line of the intended output string
    """
    #Count the number of new line strings in the input string
    count = str_in.count("\n")

    if count == 0:
        #If new line strings don't exist, just strip the string
        return [str_in.strip()]
    else:
        #If new line strings exist, split the string and put each of the string in the input list
        temp_string = str_in.split("\n")
        list_output = list()
        for each_string in temp_string:
            list_output.append(each_string.strip())
        return list_output

def split_long_address(str_in, line_length_limit):
    """Split long string into smaller strings by limiting the length of string in each line using the line_length_limit as maximum length

    Args:
        str_in (str): input string
        line_length_limit (int): string length limit for each line of string

    Returns:
        list: list of output string with each component being the string in each line
    """
    #Initialize the output string and the string for each line
    list_output_str = list()
    each_line_str = ''
    #Split the strings by looking at the blank spaces
    list_str = str_in.split()

    for each_ind, each_str in enumerate(list_str):
        #Go over each string in the list of strings
        if len(each_line_str) + len(each_str) <= line_length_limit:
            #Append the string into each-line string if the current string length is still under the limit
            each_line_str += each_str + ' '
        else:
            #If the length exceeds the limit, append the current line string to the list of output string
            #Then, create a new line string
            list_output_str.append(each_line_str)
            each_line_str = each_str + ' '

        if each_ind == len(list_str) - 1:
            #For the last string in the list, append the string to the list
            list_output_str.append(each_line_str)
    
    #Return the list of output string
    return list_output_str

def _(*args, **kwargs):
    lang = get_lang()
    try:
        gettext = get_gettext(lang)
    except ImportError:
        def gettext(x): x
    except OSError as e:
        if e.errno == errno.ENOENT:
            def gettext(x): x
        else:
            raise
    return gettext(*args, **kwargs)


class BaseInvoice(object):

    def __init__(self, invoice):
        assert isinstance(invoice, Invoice), "invoice is not instance of Invoice"

        self.invoice = invoice
        
    def gen(self, filename):
        """
        Generate the invoice into file

        :param filename: file in which the invoice will be written
        :type filename: string or File
        """
        pass


class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
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
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_page_number(self, page_count):
        """Draw page number for the current page

        Args:
            page_count (int): Total page count
        """
        self.setFont("DejaVu", 7)
        self.drawRightString(
            200*mm,
            20*mm,
            _("Page %(page_number)d of %(page_count)d") % {"page_number": self._pageNumber, "page_count": page_count},
        )


def prepare_invoice_draw(self):
    #Set the top location and the left location for the whole document
    self.TOP = 270
    self.LEFT = 18.5

    #Register the fonts
    pdfmetrics.registerFont(TTFont('DejaVu', FONT_PATH))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', FONT_BOLD_PATH))
    pdfmetrics.registerFont(TTFont('DejaVu-Italic', FONT_ITALIC_PATH))

    #Create a numbered canvas

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


class SimpleInvoice(BaseInvoice):
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
        self._drawMain() #Draw main layout of the document
        self._drawTitle() #Draw document title
        self._drawProvider(self.TOP - 10, self.LEFT + 3) #Draw document provider + EduSmith's information
        self._drawClient(self.TOP - 39.5, self.LEFT + 97) #Draw clients information
        self._drawPayment(self.TOP - 47, self.LEFT + 4) #Draw payment information
        self._drawDates(self.TOP - 10, self.LEFT + 97) #Draw dates for the document
        self._drawItems(self.TOP - 75, self.LEFT) #Draw the items in the document
        self._drawFooter(self.TOP - 230, self.LEFT + 13) #Draw the footer of the document

        #Show the PDF file and save it
        self.pdf.showPage()
        self.pdf.save()
        raw_pdf_content = buffer.getvalue()
        buffer.close()

        return raw_pdf_content
    
    def _addMetaInformation(self, pdf):
        pdf.setCreator(self.invoice.provider.summary)
        pdf.setTitle(self.invoice.title)
        pdf.setAuthor(self.invoice.creator.name)

    def _drawTitle(self):
        """
        Draw the document code number
        """
        #Draw the document title at the LEFT and the TOP location 
        self.pdf.setFont('DejaVu-Bold', 14)
        self.pdf.drawString(self.LEFT*mm, self.TOP*mm, self.invoice.title)
        
        #Draw the invoice number
        if self.invoice.number is not None:
            self.pdf.drawRightString(
                (self.LEFT + 175) * mm,
                (self.TOP + 3)*mm,
                self.invoice.number,
            )
            

    def _drawMain(self):
        """
        Draw the rectangular box in the document
        """
        #Draw the rectangular box for the upper part in the document
        self.pdf.rect(
            self.LEFT * mm,
            (self.TOP - 68) * mm,
            (self.LEFT + 156) * mm,
            65 * mm,
            stroke=True,
            fill=False,
        )

        #Draw the lines inside the rectangular box to separate the area inside into 4 sections
        path = self.pdf.beginPath()
        path.moveTo((self.LEFT + 100) * mm, (self.TOP - 3) * mm)
        path.lineTo((self.LEFT + 100) * mm, (self.TOP - 68) * mm)
        self.pdf.drawPath(path, True, True)

        path = self.pdf.beginPath()
        path.moveTo(self.LEFT * mm, (self.TOP - 27) * mm)
        path.lineTo((self.LEFT + 88) * mm, (self.TOP - 27) * mm)
        self.pdf.drawPath(path, True, True)

        path = self.pdf.beginPath()
        path.moveTo((self.LEFT + 88) * mm, (self.TOP - 27) * mm)
        path.lineTo((self.LEFT + 174.5) * mm, (self.TOP - 27) * mm)
        self.pdf.drawPath(path, True, True)


    def check_string_existing(self, str_in):
        """Check if the string exists and the string is not any kind of all of the None types

        Args:
            str_in (str): input string

        Returns:
            boolean: True if the string is not any kind of the None type. False if the string is None
        """
        if str_in in {'', 'NaN'} or str_in is None:
            return False
        else:
            return True

    def _create_paragraph_list(self, header_string, address, split_address_flag):
        """ Create a list of paragraphs for the and the company's client's contact info

        Args:
            header_string (str): String of the header for this section
            address (str): Address of the entity 
            split_address_flag (boolean): Boolean indicating whether we will split the address into multiple lines

        Returns:
            list: list of paragraphs to be splitted later drawn as different strings
        """
        header = ParagraphStyle('header', fontName='DejaVu-Bold', fontSize=10, leading=15)
        default = ParagraphStyle('default', fontName='DejaVu', fontSize=10, leading=8.5)
        default_bold = ParagraphStyle('default_bold', fontName='DejaVu-Bold', fontSize=8, leading=8.5)
        small = ParagraphStyle('small', parent=default, fontSize=6, leading=6)
        space = ParagraphStyle('space', fontName='DejaVu', fontSize=1, leading = 2)

        spacing = Paragraph(text = u'<br/><br/>', style = space)

        #Check if the header string exists
        if self.check_string_existing(header_string):
            list_output = [Paragraph(header_string, header)]
        else:
            list_output = []

        #Check if the summary string for the address exists in order to create the name paragraph
        if self.check_string_existing(address.summary):
            name_paragraph = Paragraph(text="<font name=DejaVu-Bold size=8.5>Name: </font><font name=DejaVu size=8.5>{}</font>".format(address.summary), style=default)
            list_output.append(name_paragraph)
            #Add the space after the name paragraph
            list_output.append(spacing)

        if self.check_string_existing(address.vat_id):
            vat_id_paragraph = Paragraph(text="<font name=DejaVu-Bold size=8.5>TAX ID: </font><font name=DejaVu size=8.5>{}</font>".format(''.join(address.vat_id)), style=default)
            list_output.append(vat_id_paragraph)
            list_output.append(spacing)
        
        if split_address_flag:
            #Check if we want to split the address into smaller parts
            #Split the long address into smaller parts in a list 
            address_list = split_long_address(''.join(address._get_address_lines()), 30)
            for each_ind, each_part in enumerate(address_list):
                if each_ind == 0:
                    address_paragraph = Paragraph(text="<font name=DejaVu-Bold size=8.5>Address: </font><font name=DejaVu size=8.5>{}</font>".format(each_part), style=default)   
                else:
                    address_paragraph = Paragraph(text="<font name=DejaVu size=8.5>{}</font>".format(each_part), style=default)
                #Append the results into the list
                list_output.append(address_paragraph)
                list_output.append(spacing)
        else:
            address_paragraph = Paragraph(text="<font name=DejaVu-Bold size=8.5>Address: </font><font name=DejaVu size=8.5>{}</font>".format(''.join(address._get_address_lines())), style=default)
            list_output.append(address_paragraph)
            list_output.append(spacing)

        if self.check_string_existing(address.email):
            #Check if the address' email exist, if so, add it into the new line of the output string
            email_paragraph = Paragraph(text="<font name=DejaVu-Bold size=8.5>Email: </font><font name=DejaVu size=8.5>{}</font>".format(address.email), style=default)
            list_output.append(email_paragraph)
            list_output.append(spacing)

        if self.check_string_existing(address.phone):
            #Similarly, add the phone number if it exists
            phone_paragraph = Paragraph(text="<font name=DejaVu-Bold size=8.5>Phone: </font><font name=DejaVu size=8.5>{}</font>".format(address.phone), style=default)
            list_output.append(phone_paragraph)

        return list_output
        

    def _drawAddress(self, top, left, width, height, header_string, address, split_address_flag):
        """Draw address for the specified entity

        Args:
            top (float): The top location for the address string
            left (float): The left location for the address
            width (float): The width limit for the paragraph
            height (float): The height limit for the paragraph
            header_string (str): string of the header for the section
            address (str): address string
            split_address_flag (boolean): boolean checking whether the program will split the input address into smaller addresses
        """
        #Start drawing the text
        self.pdf.setFont('DejaVu', 8.5)
        text = self.pdf.beginText((left + 40) * mm, (top - 4) * mm)
        self.pdf.drawText(text)

        #Create a frame in which the program will draw the address
        frame = Frame((left - 3) * mm, (top - 29) * mm, width*mm, height*mm)
        story = self._create_paragraph_list(header_string, address, split_address_flag)
        #Limit the string inside the given frame as specified before
        story_inframe = KeepInFrame(width*mm, height*mm, story)
        frame.addFromList([story_inframe], self.pdf)

        if address.logo_filename:
            #If the logo file name exists, we will open this file and draw it on the pdf file
            im = Image.open(address.logo_filename)
            height = 40.0
            width = float(im.size[0]) / (float(im.size[1])/height)
            self.pdf.drawImage(self.invoice.provider.logo_filename, (left + 32) * mm - width, (top + 12) * mm, width, height, mask="auto")
        

    def _drawClient(self, TOP, LEFT):
        """Draw the client's information on the specified location

        Args:
            TOP (float): Top location of the client part
            LEFT (float): Left location of the client part
        """
        if self.check_string_existing(self.invoice.client.vat_id):
            self._drawAddress(TOP, LEFT + 6, 75, 41, _(u'Client'), self.invoice.client, split_address_flag=True)
        else:
            self._drawAddress(TOP, LEFT + 6, 75, 41, _(u'Student'), self.invoice.client, split_address_flag=True)

    def _drawProvider(self, TOP, LEFT):
        """Draw the provider's information on the specified location

        Args:
            TOP (float): Top location of the provider part
            LEFT (float): Left location of the provider part
        """
        self._drawAddress(TOP, LEFT, 105, 36, _(u''), self.invoice.provider, split_address_flag=False)

    def _drawPayment(self, TOP, LEFT):
        """Draw payment information at the specified location

        Args:
            TOP (float): Top location of the payment part
            LEFT (float): Left location of the payment part
        """
        #Draw the header of the payment section
        self.pdf.setFont('DejaVu-Bold', 10)
        self.pdf.drawString((LEFT - 2) * mm, (TOP + 14) * mm, _(u'Payment Information'))
        #Draw the description of the payment section
        self.pdf.setFont('DejaVu', 8.5)
        self.pdf.drawString((LEFT - 2) * mm, (TOP + 9.5) * mm, 'Payment can be made via credit card or bank transfer')

        #Draw the names of all subsections
        self.pdf.setFont('DejaVu-Bold', 8.5)
        self.pdf.drawString((LEFT - 2) * mm, (TOP + 5) * mm, 'Bank:')
        self.pdf.drawString((LEFT - 2) * mm, (TOP + 0.5) * mm, 'Bank Account:')
        self.pdf.drawString((LEFT - 2) * mm, (TOP - 4) * mm, 'Account Name:')
        
        #Draw the information for all subsections
        self.pdf.setFont('DejaVu', 8.5)
        self.pdf.drawString((LEFT + 9) * mm, (TOP + 5) * mm, u'%s' % self.invoice.provider.bank_name)
        self.pdf.drawString((LEFT + 24) * mm, (TOP + 0.5) * mm, u'%s' % self.invoice.provider.bank_account)
        self.pdf.drawString((LEFT + 25) * mm, (TOP - 4) * mm, u'%s' % self.invoice.provider.bank_account_name)
        
        
    def _drawItemsHeader(self,  TOP, LEFT):
        """Draw the header of all items in the transaction

        Args:
            TOP (float): Top location of the item part
            LEFT (float): Left location of the item part
        Returns:
            float: the height in millimeter for this part
        """
        #Draw the border line for the header part
        path = self.pdf.beginPath()
        path.moveTo((LEFT + 10.5) * mm, (TOP - 3) * mm)
        path.lineTo((LEFT + 10.5) * mm, (TOP - 10.5) * mm)
        self.pdf.setLineWidth(1)
        self.pdf.drawPath(path, True, True)
        
        self.pdf.setFont('DejaVu-Bold', 8.5)

        #Draw the header strings for indicating the item order and the item descriptions
        self.pdf.drawString((LEFT + 3) * mm, (TOP - 9) * mm, _(u'No.'))
        self.pdf.drawString((LEFT + 12) * mm, (TOP - 9) * mm, _(u'Description'))
        
        i = 9
        #Draw Units, Unit Price, Total Price at the specified locations
        self.pdf.drawString(
            (LEFT + 118) * mm,
            (TOP - i) * mm,
            _(u'Units'),
        )
        self.pdf.drawString(
            (LEFT + 132) * mm,
            (TOP - i) * mm,
            _(u'Unit Price'),
        )

        self.pdf.drawString(
            (LEFT + 153) * mm,
            (TOP - i) * mm,
            _(u'Total Price'),
        )
        i += 5
        return i

    def _drawItems(self, TOP, LEFT):
        """Draw all of the items in the transaction at the specified location

        Args:
            TOP (float): Top location of the item part
            LEFT (float): Left location of the item part
        """
        #Draw the item header
        i = self._drawItemsHeader(TOP, LEFT)
        i_init = i
        self.pdf.setFont('DejaVu', 8.5)

        items_are_with_tax = self.invoice.use_tax

        will_wrap = False
        for ind, item in enumerate(self.invoice.items):
            #Go over all of the items in the invoice
            if TOP - i < 30 * mm:
                will_wrap = True

            style = ParagraphStyle('normal', fontName='DejaVu', fontSize=8.5)
            #Draw each item's description 
            p = Paragraph(item.description, style)
            pwidth, pheight = p.wrapOn(self.pdf, 103*mm, 30*mm)
            i_add = max(float(pheight)/mm, 4.23)

            if will_wrap and TOP - i - i_add < 8 * mm:
                #If will_wrap, the program will draw the rectangular box
                will_wrap = False
                self.pdf.rect(LEFT * mm, (TOP - i) * mm, (LEFT + 156) * mm, (i + 2) * mm, stroke=True, fill=False)  # Show the rectangular page 
                self.pdf.showPage()

                i = self._drawItemsHeader(self.TOP, LEFT)
                TOP = self.TOP
                self.pdf.setFont('DejaVu', 8.5)

            # Draw the separating line for each item
            path = self.pdf.beginPath()
            path.moveTo(LEFT * mm, (TOP - i + 3.5) * mm)
            path.lineTo((LEFT + 174.5) * mm, (TOP - i + 3.5) * mm)
            self.pdf.setLineWidth(0.1)
            self.pdf.drawPath(path, True, True)

            i += i_add
            p.drawOn(self.pdf, (LEFT + 12) * mm, (TOP - i + 3) * mm)
            i -= i_add
            self.pdf.drawString((LEFT + 4.5) * mm, (TOP - i) * mm, _(u'{}.'.format(ind + 1)))
            
            #Draw the item counts for each item depending on the number of counts specified
            if float(int(item.count)) == item.count:
                self.pdf.drawRightString((LEFT + 128) * mm, (TOP - i) * mm, u'%s %s' % (locale.format("%i", item.count, grouping=True), item.unit))
            else:
                self.pdf.drawRightString((LEFT + 128) * mm, (TOP - i) * mm, u'%s %s' % (locale.format("%.2f", item.count, grouping=True), item.unit))
            
            #Draw the item unit price and the item total price
            self.pdf.drawRightString((LEFT + 149) * mm, (TOP - i) * mm, currency(item.price, self.invoice.currency, self.invoice.currency_locale))
            self.pdf.drawRightString((LEFT + 171.5) * mm, (TOP - i) * mm, currency(item.total, self.invoice.currency, self.invoice.currency_locale))
            
            #If there exists any note for each item, draw it here and separate the lines in the paragraph
            if len(item.note) > 0:
                i += i_add - 4.23
                list_note = separate_new_lines(item.note)
                style = ParagraphStyle('normal', fontName='DejaVu-Italic', fontSize=8.5)
                for each_note in list_note:
                    p = Paragraph(each_note, style)
                    pwidth, pheight = p.wrapOn(self.pdf, 70*mm if items_are_with_tax else 90*mm, 30*mm)
                    i_add = max(float(pheight)/mm, 4.23)
                    p.drawOn(self.pdf, (LEFT + 12) * mm, (TOP - i - 1 - i_add) * mm)
                    i += i_add

            if ind < len(self.invoice.items) - 1:
                i += i_add + 3
            else:
                i += i_add - 1
        
        #Draw the vertical separating line for the item order
        path.moveTo((LEFT + 10.5) * mm, (TOP - i_init + 4) * mm)
        path.lineTo((LEFT + 10.5) * mm, (TOP - i) * mm)
        self.pdf.setLineWidth(1)
        self.pdf.drawPath(path, True, True)

        if self.invoice.document_type == 'receipt':
            #Draw the string for the payment method with the bold text
            self.pdf.setFont('DejaVu-Bold', 8.5)
            self.pdf.drawString((LEFT + 1) * mm, (TOP - i - 4) * mm, _(u'Payment Method:'))
            self.pdf.drawString((LEFT + 31.5) * mm, (TOP - i - 4) * mm, self.invoice.payment_method)
            count_note_line = 0
            payment_increment = 4
            
        else:
            #Otherwise, just neglect it
            count_note_line = 0
            payment_increment = 0

        self.pdf.setFont('DejaVu', 8.5)

        if len(self.invoice.notes) > 0:
            #This case holds if the invoice has notes for the bottom section of the document
            self.pdf.setFont('DejaVu-Bold', 8.5)
            self.pdf.drawString((LEFT + 1) * mm, (TOP - i - 4 - payment_increment) * mm, _(u'Note:'))
            self.pdf.setFont('DejaVu', 8.5)
            style = ParagraphStyle('normal', fontName='DejaVu', fontSize=8.5)
            
            for ind, note in enumerate(self.invoice.notes):
                #Iterate through each note in the list of notes and separate the lines
                list_note = separate_new_lines(note)
                for each_note in list_note:
                    #Create the note in a paragraph
                    p = Paragraph(each_note, style)
                    pwidth, pheight = p.wrapOn(self.pdf, 70*mm if items_are_with_tax else 90*mm, 30*mm)
                    i_add = max(float(pheight)/mm, 4.23)

                    #Draw the note paragraph
                    p.drawOn(self.pdf, (LEFT + 11) * mm, (TOP - i - 1 - i_add - payment_increment) * mm)
                    count_note_line += i_add
        

        if will_wrap:
            self.pdf.rect(LEFT * mm, (TOP - i) * mm, (LEFT + 156) * mm, (i + 2) * mm, stroke=True, fill=False)  # 140,142
            self.pdf.showPage()

            i = 0
            TOP = self.TOP
            self.pdf.setFont('DejaVu', 8)

        #Draw the bottom line the section
        path = self.pdf.beginPath()
        path.moveTo(LEFT * mm, (TOP - i) * mm)
        path.lineTo((LEFT + 174.5) * mm, (TOP - i) * mm)
        self.pdf.drawPath(path, True, True)
        
        #Draw the "this installment" part
        left_increment = 0
        if self.invoice.document_type in {'invoice', 'receipt'} and (self.invoice.this_installment > 0 or self.invoice.credit_spending > 0):
            #Draw the this installment part
            len_installment_str = len(str(currency(self.invoice.this_installment, self.invoice.currency, self.invoice.currency_locale)))
            #Set the length multiplier for the different cases when the string is larger and longer to make the "this installment" part align with the total part
            if len_installment_str <= 6:
                left_increment = 1.6 * len_installment_str
            elif len_installment_str == 7:
                left_increment = 1.7 * len_installment_str
            else:
                left_increment = 1.8 * len_installment_str

            len_credit_str = len(str(currency(self.invoice.credit_spending, self.invoice.currency, self.invoice.currency_locale)))
            #Set the length multiplier for the different cases when the string is larger and longer to make the "this installment" part align with the total part
            if len_installment_str <= 6:
                left_increment_credit = 1.3 * len_credit_str
            elif len_installment_str == 7:
                left_increment_credit = 1.4 * len_credit_str
            else:
                left_increment_credit = 1.5 * len_credit_str

            #Set the total payment in the currency form
            self.pdf.setFont('DejaVu-Bold', 10)
            if self.invoice.credit_spending > 0:
                self.pdf.drawRightString((LEFT + 171) * mm, (TOP - i - 5) * mm, '%s: %s' % (_(u'Subtotal'), currency(self.invoice.price, self.invoice.currency, self.invoice.currency_locale)))
            else:
                self.pdf.drawRightString((LEFT + 171) * mm, (TOP - i - 5) * mm, '%s: %s' % (_(u'Total Payment'), currency(self.invoice.price, self.invoice.currency, self.invoice.currency_locale)))
            
            #If the price exceeds the installment value, draw both the total value and the installment value. Otherwise, draw just the total price
            if self.invoice.price > self.invoice.this_installment:
                i += 5

                if self.invoice.credit_spending > 0:
                    credit_string = "Credit Payment"
                    style = ParagraphStyle('normal', fontName='DejaVu', fontSize=10)
                    p = Paragraph(u'{}: {}'.format(credit_string, currency(-1 * self.invoice.credit_spending, self.invoice.currency, self.invoice.currency_locale)), style)
                    pwidth, pheight = p.wrapOn(self.pdf, 90*mm, 30*mm)
                    #Draw the installment part at the specified location
                    p.drawOn(self.pdf, (LEFT + 135 - left_increment_credit) * mm, (TOP - i - 6) * mm)

                if self.invoice.this_installment > 0:
                    #Draw the line under the this installment part
                    if self.invoice.credit_spending > 0:
                        i_payment = i + 5
                    else:
                        i_payment = i
                    
                    if self.invoice.credit_spending > 0:
                        cash_string = "Total Payment"
                        str_pos = LEFT + 125 - left_increment
                    else:
                        cash_string = "This Installment"
                        str_pos = LEFT + 121.5 - left_increment
                    
                    style = ParagraphStyle('underline', fontName='DejaVu-Bold', fontSize=12)
                    p = Paragraph(u'<u>{}: {}</u>'.format(cash_string, currency(self.invoice.this_installment, self.invoice.currency, self.invoice.currency_locale)), style)
                    pwidth, pheight = p.wrapOn(self.pdf, 90*mm, 30*mm)
                    #Draw the installment part at the specified location
                    p.drawOn(self.pdf, str_pos * mm, (TOP - i_payment - 6) * mm)

        else:
            #Draw only the total payment part without the installment part
            self.pdf.setFont('DejaVu-Bold', 10)
            self.pdf.drawRightString((LEFT + 171.5) * mm, (TOP - i - 5) * mm, '%s: %s' % (_(u'Total Payment'), currency(self.invoice.price, self.invoice.currency, self.invoice.currency_locale)))

        i += count_note_line - 3

        if items_are_with_tax:
            #If the taxes are given, then put the information about the tax in the file too
            self.pdf.rect(LEFT * mm, (TOP - i - 17) * mm, (LEFT + 156) * mm, (i + 19) * mm, stroke=True, fill=False)  
        else:
            self.pdf.rect(LEFT * mm, (TOP - i - 16) * mm, (LEFT + 156) * mm, (i + 13) * mm, stroke=True, fill=False)  

        self._drawCreator(TOP - i - 20, self.LEFT + 98) #Currently not in use

    def _drawCreator(self, TOP, LEFT):
        height = 20*mm
        if self.invoice.creator.stamp_filename:
            im = Image.open(self.invoice.creator.stamp_filename)
            height = float(im.size[1]) / (float(im.size[0])/200.0)
            self.pdf.drawImage(self.invoice.creator.stamp_filename, (LEFT) * mm, (TOP - 2) * mm - height, 200, height, mask="auto")

        # path = self.pdf.beginPath()
        # path.moveTo((LEFT + 8) * mm, (TOP) * mm - height)
        # path.lineTo((LEFT + self.line_width) * mm, (TOP) * mm - height)
        # self.pdf.drawPath(path, True, True)

        # self.pdf.drawString((LEFT + 8) * mm, (TOP - 5) * mm - height, '%s: %s' % (_(u'Creator'), self.invoice.creator.name))

    def _drawFooter(self, TOP, LEFT):
        """Draw the footer information

        Args:
            TOP (float): Top location of the footer part
            LEFT (float): Left location of the footer part
        """
        self.pdf.setFont('DejaVu-Bold', 8)
        if self.invoice.document_type == 'receipt':
            self.pdf.drawString(LEFT * mm, TOP * mm, 'This document can be used as a proof of payment. For an official receipt, please contact us.')

    def _drawDates(self, TOP, LEFT):
        """Draw the issue date, the due date, and the payment date

        Args:
            TOP (float): Top location of the dates in millimeter
            LEFT (float): Left location of the dates in millimeter
        """
        self.pdf.setFont('DejaVu', 8.5)
        top = TOP + 2
        items = []
        lang = get_lang()
        if self.invoice.date:
            #If the date is given, then draw the date as the issue date 
            items.append(((LEFT + 5) * mm, '%s ' % (_(u'Issue Date:')), False, True))
            items.append(((LEFT + 25) * mm, '%s' % (format_date(self.invoice.date, format="long", locale=lang)), True, False))
        if self.invoice.payback:
            #This part holds when the payback date exists
            if self.invoice.document_type == 'receipt':
                #If the document is a receipt, draw it as payment date
                items.append(((LEFT + 5) * mm, '%s ' % (_(u'Payment Date:')), False, True))
                items.append(((LEFT + 30) * mm, '%s' % (format_date(self.invoice.payback, format="long", locale=lang)), True, False))
            else:
                #Otherwise, draw it as due date
                items.append(((LEFT + 5) * mm, '%s ' % (_(u'Due Date:')), False, True))
                items.append(((LEFT + 23) * mm, '%s' % (format_date(self.invoice.payback, format="long", locale=lang)), True, False))
        
        for item in items:
            spacing = item[2]
            bold = item[3]

            if bold:
                self.pdf.setFont('DejaVu-Bold', 8.5)
            else:
                self.pdf.setFont('DejaVu', 8.5)
            self.pdf.drawString(item[0], top * mm, item[1])
            if spacing:
                top += -4.5


