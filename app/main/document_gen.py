from operator import add
from app.models import Service, Student, Office
from flask_login import current_user

import datetime
import os
import pickle

import numpy as np
from decimal import Decimal
import math

def my_round(n, ndigits):
    part = n * 10 ** ndigits
    delta = part - int(part)
    # always round "away from 0"
    if delta >= 0.5 or -0.5 < delta <= 0:
        part = math.ceil(part)
    else:
        part = math.floor(part)
    return part / (10 ** ndigits)

def create_pdf_document(transaction, document_number, service_dict, dict_all_payment, document_type, 
    calculated_count = None, vat_rate = 0.07, this_time_payment = 0.0, credit_spending = 0.0,
    student_country = 'Thailand', zero_discount_flag=True):
    """Create a pdf document as the output for each transaction

    Args:
        transaction (sqlalchemy query obj): transaction object with all transaction information
        document_number (str): document number generated with the following form [CYYMMNNN] - C being the document code, YY being the 2-digit year, MM being the 2-digit month, NNN being the three-digit document code 
        service_dict (dict): dictionary containing all services' information 
        dict_all_payment (dict):
        document_type (str): a string of document type used to determine the output document type
        calculated_count (list, optional): List of all item counts for the given amount of payment. Defaults to None.
        vat_rate (float, optional): VAT rate for the user's country. Defaults to 0.07.
        this_time_payment (float, optional): The payment value for this transaction. Defaults to 0.0.
        student_country (str, optional): Student's country name. Defaults to 'Thailand'.

    Returns:
        doc_directory (str): The document's PDF directory
        pickle_directory (str): The document's pickle directory
    """
    
    #Set invoice language to English
    os.environ["INVOICE_LANG"] = "en"
    
    from InvoiceGenerator.api import Invoice, Item, Client, Provider, Creator

    #Now, the only available document types are the following four. FIX THIS if any additional type exists
    assert document_type in {'quotation', 'invoice', 'receipt', 'vat_invoice'}
    #For the vat invoice case, we will assert that the item counts are all 1.
    if document_type == 'vat_invoice':
        assert calculated_count is not None

    #Query target student's information
    student = Student.query.filter_by(name = transaction.student_full_name, student_country=student_country).first_or_404()
    
    #Check if the student's address is available. If not, let it be blank
    if transaction.use_company_info_flag:
        if transaction.company_address is None or transaction.company_address == 'NaN':
            if transaction.company_tax_id is not None and transaction.company_tax_id != '' and transaction.company_tax_id != 'NaN':
                client = Client(transaction.company_name, address = ' ', vat_id = transaction.company_tax_id)
            else:
                client = Client(transaction.company_name, address = ' ')
        else:
            if transaction.company_tax_id is not None and transaction.company_tax_id != '' and transaction.company_tax_id != 'NaN':
                client = Client(transaction.company_name, address = transaction.company_address, vat_id = transaction.company_tax_id)
            else:
                client = Client(transaction.company_name, address = transaction.company_address)
    
    else:
        if student.address is None or student.address == 'NaN':
            if student.tax_id is not None and student.tax_id != '' and student.tax_id != 'NaN':
                if document_type == 'vat_invoice':
                    client = Client(student.name, address=' ', vat_id = student.tax_id)
                else:
                    client = Client(student.name, address=' ')
            else:
                client = Client(student.name, address=' ')
        else:
            if student.tax_id is not None and student.tax_id != '' and student.tax_id != 'NaN':
                if document_type == 'vat_invoice':
                    client = Client(student.name, address=student.address, vat_id = student.tax_id)
                else:
                    client = Client(student.name, address=student.address)
            else:
                client = Client(student.name, address=student.address)
    
    #Query office's contact/payment information and put it into output pdf file 
    non_vat_office_obj = Office.query.filter_by(country = student_country, info_for_vat = False).first()
    edusmith_address = non_vat_office_obj.address_1 # Mailing address
    edusmith_email = non_vat_office_obj.email #Email
    edusmith_phone = non_vat_office_obj.phone #Phone number
    edusmith_bank_account_name = non_vat_office_obj.bank_account_name #Bank account name
    edusmith_bank_name = non_vat_office_obj.bank_name #Bank name
    edusmith_bank_account_number = non_vat_office_obj.bank_account_number #Bank account number
    edusmith_logo_filename = non_vat_office_obj.logo_directory #Logo file directory

    #Instantiate the provider variable with all EduSmith information
    provider = Provider('', address = edusmith_address, email = edusmith_email, phone = edusmith_phone, bank_account_name = edusmith_bank_account_name, bank_name = edusmith_bank_name , bank_account=edusmith_bank_account_number, logo_filename=edusmith_logo_filename)
    
    #Can put the preparer's name here if wanted - not currently in use
    if current_user.first_name is None:
        creator = Creator('EduSmith Staff')
    else:
        creator = Creator(current_user.first_name)

    #Combine all information together in the invoice object
    invoice = Invoice(client, provider, creator)
    #Fill in all information for the invoice
    invoice.document_type = document_type
    #Fill in this installment's value using the decimal version of this time payment
    invoice.this_installment = Decimal(this_time_payment)
    #Fill in the credit value using the decimal version of credit spending
    invoice.credit_spending = Decimal(credit_spending)
    #Currency character - used if the user wants to add a currency sign to the output document e.g. '$'
    invoice.currency = ''
    #Payment method - a string determining the payment method described in the receipt
    invoice.payment_method = transaction.payment_method
    #Document number
    invoice.number = document_number
    #Current datetime
    invoice.date = datetime.datetime.now()
    
    if document_type == 'receipt':
        #If it is a receipt, the payment date and the issue date are identical
        invoice.payback = invoice.date
    else:
        #Otherwise, set it to be equal to the due date
        invoice.payback = transaction.due_date

    if document_type == 'vat_invoice':
        #if the document type is a VAT invoice, we will query the information used for the VAT invoice document
        vat_office_obj = Office.query.filter_by(country = student.student_country, info_for_vat = True).first()
        #Set the title as descrube in the vat office object
        invoice.title = vat_office_obj.title
        #Set the VAT invoice company name - can be different from the usual company name    
        invoice.vat_company_name = vat_office_obj.company_name
        
        #Set the format of VAT tax id for each different country
        if student_country == 'Thailand':
            if transaction.use_company_info_flag:
                invoice.vat_tax_id = 'เลขประจำตัวผู้เสียภาษี ' + transaction.company_tax_id
            else:
                invoice.vat_tax_id = 'เลขประจำตัวผู้เสียภาษี ' + vat_office_obj.vat_tax_id
        else:
            invoice.vat_tax_id = vat_office_obj.vat_tax_id
        #Set the two lines of company addresses
        invoice.company_address_1 = vat_office_obj.address_1
        invoice.company_address_2 = vat_office_obj.address_2

    #Set all of the service names in a list
    all_service_name = [transaction.service_1_name, transaction.service_2_name, transaction.service_3_name, transaction.service_4_name, transaction.service_5_name, transaction.service_6_name]
    
    all_original_service_count = np.array([transaction.service_1_count, transaction.service_2_count, transaction.service_3_count, transaction.service_4_count, transaction.service_5_count, transaction.service_6_count], dtype=float)

    #The counts for the vat_invoice will usually be just one
    #However, for other documents, the counts will be rounded to one decimal value
    if document_type == 'vat_invoice':
        all_service_count = calculated_count
    else:
        all_service_count = np.array([transaction.service_1_count, transaction.service_2_count, transaction.service_3_count, transaction.service_4_count, transaction.service_5_count, transaction.service_6_count], dtype=float)

    #Set prices, final prices, discounts, and notes in the array form
    all_service_price = np.array([transaction.service_1_price, transaction.service_2_price, transaction.service_3_price, transaction.service_4_price, transaction.service_5_price, transaction.service_6_price], dtype=float)
    all_service_final_price = np.array([transaction.service_1_final_price, transaction.service_2_final_price, transaction.service_3_final_price, transaction.service_4_final_price, transaction.service_5_final_price, transaction.service_6_final_price], dtype=float)
    all_service_discount = np.array([transaction.service_1_discount_value, transaction.service_2_discount_value, transaction.service_3_discount_value, transaction.service_4_discount_value, transaction.service_5_discount_value, transaction.service_6_discount_value], dtype=float)
    all_service_note = np.array([transaction.service_1_note, transaction.service_2_note, transaction.service_3_note, transaction.service_4_note, transaction.service_5_note, transaction.service_6_note])

    vat_discount_dict = dict()

    #Query vat proportions for all of the services in the transaction
    if document_type == 'vat_invoice':
        #Store all of the VAT proportions in a list
        all_service_vat_rate = []
        for each_service_name in all_service_name:
            if each_service_name in dict_all_payment and each_service_name is not None and each_service_name != '':
                all_service_vat_rate.append(dict_all_payment[each_service_name]['vat_proportion'])
            else:
                all_service_vat_rate.append(np.nan)
        #Set the output in a form of a list
        all_service_vat_rate = np.array(all_service_vat_rate)

    #Check if all iterables have the same length
    assert len(all_service_name) == len(all_service_count) == len(all_service_price) == len(all_service_final_price) == len(all_service_discount) == len(all_service_note)
    
    total_vat = 0 #Total VAT value
    #credit_amount_after_discount_and_tax = 0

    if document_type == 'vat_invoice':
        total_discount = 0
        for i in range(len(all_service_name)):
            if all_service_name[i] in dict_all_payment and all_service_name[i] is not None and all_service_name[i] != '':
                discount_per_unit = dict_all_payment[all_service_name[i]]['original_price_per_unit'] - dict_all_payment[all_service_name[i]]['final_price_per_unit']
                each_service_discount = dict_all_payment[all_service_name[i]]['service_count'] * discount_per_unit
                each_service_vat_discount = each_service_discount * dict_all_payment[all_service_name[i]]['vat_proportion']
                vat_discount_dict[all_service_name[i]] = each_service_vat_discount
                total_discount += each_service_vat_discount * 1/(1+vat_rate)
    else:
        total_discount = np.sum(all_service_price * all_service_count) - np.sum(all_service_final_price) #Total discount value

    #Add all items to the output using the service's display name
    for i in range(len(all_service_name)):
        if all_service_name[i] is not None and all_service_name[i] != '':
            each_service_dict = service_dict[all_service_name[i]]
            
            if document_type == 'vat_invoice':
                #Set item name for a VAT invoice document
                if 'vat_name' in each_service_dict and each_service_dict['vat_name'] is not None:
                    item_name = each_service_dict['vat_name']
                elif 'display_name' in each_service_dict and each_service_dict['display_name'] is not None:
                    item_name = each_service_dict['display_name']
                else:
                    item_name = all_service_name[i]
            else:
                #Otherwise, generally use the display name, or just the ordinary service name if the display name doesn't exist
                if 'display_name' in each_service_dict and each_service_dict['display_name'] is not None:
                    item_name = each_service_dict['display_name']
                else:
                    item_name = all_service_name[i]

            if document_type == 'vat_invoice':
                #This case happens for the case of VAT invoice - the count is always 1 without any discount included
                if all_service_count[i] > 0 and all_service_vat_rate[i] > 0:
                    if zero_discount_flag:
                        this_installment_amount = dict_all_payment[all_service_name[i]]['service_count'] * dict_all_payment[all_service_name[i]]['final_price_per_unit']
                        this_installment_vat_amount = this_installment_amount * dict_all_payment[all_service_name[i]]['vat_proportion']

                        price_after_discount_and_tax = this_installment_vat_amount * (1/(1+vat_rate))
                        total_vat += this_installment_vat_amount - price_after_discount_and_tax

                        invoice.add_item(Item(1, price_after_discount_and_tax, description=item_name))

                        # if dict_all_payment[all_service_name[i]]['service_credit_count'] > 0:
                        #     this_installment_credit_amount = dict_all_payment[all_service_name[i]]['service_credit_count'] * dict_all_payment[all_service_name[i]]['final_price_per_unit']
                        #     this_installment_credit_vat_amount = this_installment_credit_amount * dict_all_payment[all_service_name[i]]['vat_proportion']
                        #     credit_amount_after_discount_and_tax -= this_installment_credit_vat_amount * (1/(1+vat_rate))
                        #     total_vat -= this_installment_credit_vat_amount - credit_amount_after_discount_and_tax
                    
                    else:
                        this_installment_amount = dict_all_payment[all_service_name[i]]['service_count'] * dict_all_payment[all_service_name[i]]['original_price_per_unit']
                        this_installment_vat_amount = this_installment_amount * dict_all_payment[all_service_name[i]]['vat_proportion']

                        price_before_discount_and_tax = this_installment_vat_amount * (1/(1+vat_rate))
                        total_vat += (this_installment_vat_amount - vat_discount_dict[all_service_name[i]]) * (vat_rate/(1+vat_rate))

                        invoice.add_item(Item(1, price_before_discount_and_tax, description=item_name))

                        # if dict_all_payment[all_service_name[i]]['service_credit_count'] > 0:
                        #     this_installment_credit_amount = dict_all_payment[all_service_name[i]]['service_credit_count'] * dict_all_payment[all_service_name[i]]['original_price_per_unit']
                        #     this_installment_credit_vat_amount = this_installment_credit_amount * dict_all_payment[all_service_name[i]]['vat_proportion']
                        #     credit_amount_after_discount_and_tax -= this_installment_credit_vat_amount * (1/(1+vat_rate))
                        #     total_vat -= this_installment_credit_vat_amount - credit_amount_after_discount_and_tax
                    

            else:
                #Otherwise, add the item with or without the note
                if all_service_note[i] is not None and all_service_note[i] != '':
                    invoice.add_item(Item(all_service_count[i], all_service_price[i], description=item_name, note = all_service_note[i]))
                else:
                    invoice.add_item(Item(all_service_count[i], all_service_price[i], description=item_name))
    
    # if document_type == 'vat_invoice' and credit_amount_after_discount_and_tax > 0:
    #     credit_name = 'Credit Discount'
    #     invoice.add_item(Item(1, credit_amount_after_discount_and_tax, description=credit_name))

    if document_type == 'vat_invoice' and credit_spending > 0:
        credit_name = 'Credit'
        credit_discount_amount = (-1 * credit_spending)/(1+vat_rate)
        total_vat += credit_discount_amount * (vat_rate)
        invoice.add_item(Item(1, credit_discount_amount, description=credit_name))

    if total_discount > 0:
        #If discount exists, we include it only in the non-VAT-related documents
        if document_type == 'vat_invoice':
            if zero_discount_flag:
                invoice.total_discount = 0.00
            else:
                invoice.total_discount = float(total_discount)
        else:
            actual_discount_value = -1.0 * float(total_discount)
            invoice.add_item(Item(1, actual_discount_value, description='Discount')) 

    if total_vat > 0:
        total_vat = my_round(total_vat, 2)
        invoice.vat = Decimal(total_vat)

    if transaction.note is not None and transaction.note != '':
        #change the new line character in the note to <br> for the correct display in the PDF file
        transaction_note = transaction.note.replace("\n", "<br/>")
        if credit_spending > 0 and document_type == 'receipt':
            transaction_note += "<br/>- Spent the remaining credit for " + "฿{:,.2f}".format(int(credit_spending)) 
        invoice.add_note(transaction_note)
    elif credit_spending > 0 and document_type == 'receipt':
        transaction_note = "- Spent the remaining credit for " + "฿{:,.2f}".format(int(credit_spending))
        invoice.add_note(transaction_note)

    #Save the pickle file in the target directory if the file is for uploading
    pickle_binary = pickle.dumps(invoice)

    #Add the PDF extention to the filename
    if document_number[-4:] != '.pdf':
        document_number = document_number + '.pdf'

    #Generate the PDF files
    if document_type == 'vat_invoice':
        from InvoiceGenerator.pdf_vat import VatInvoice
        pdf = VatInvoice(invoice)
    else:
        from InvoiceGenerator.pdf import SimpleInvoice
        pdf = SimpleInvoice(invoice)
    pdf_binary = pdf.gen()

    return pdf_binary, pickle_binary