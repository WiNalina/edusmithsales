import datetime
import numpy as np
import pandas as pd

from app import db
from flask import current_app
from app.models import Accounting_record, Sale_record, Service, Student, Role, Transaction, User, Office, VAT_info

from flask_login import current_user
from app.util import datetimefilter

import pytz

import io
from app.main.document_gen import create_pdf_document
from sqlalchemy import desc

import zipfile
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


def retrieve_service_dict():
    """ Create a dict with keys being strings of service categories and values being lists of subcategories

    Returns:
        dict: dictionary of all services' categories and subcategories
    """
    service_dict = {
        'None': [],
        'Coaching': ['Strategy Meeting', 'Project Development', 'Skill Development', 'Others'],
        'Counseling': ['Boarding School', 'US College', 'UK College', 'Graduate', 'MBA', 'Thai Med', 'Thai App', 'Interview', 'Essay Review', 'Canada', 'Other'],                                                 
        'Group course': ['SSAT', 'SAT', 'ACT', 'TOEFL/IELTS', 'GMAT/GRE', 'Reading and Writing', 'Other'],
        'Private': ['SSAT', 'SAT', 'ACT', 'TOEFL', 'IETLS', 'GRE', 'GMAT', 'Subject Test', 'Math', 'AP', 'A-Level', 'Reading and Writing', 'IB', 'Other'],
        'APPA': ['Counseling', 'Essay Review', 'Interview Prep', 'Workshop', 'Camp', 'IELTS', 'Private Class']
    }
    return service_dict


def save_accounting_record(transaction, this_transaction_id, dict_all_payment, receipt_number, service_dict):
    """Save accounting record using the transaction's data

    Args:
        transaction (SQLAlchemy query object): Transaction query object
        this_transaction_id (int): this transaction's id number
        dict_all_payment (dict): dictionary of all payments
        receipt_number (str): string of the document's code 
        service_dict (dict): dict of all services' information
    """

    #Query the target student's information
    student_query = Student.query.filter_by(name = transaction.student_full_name).first()
    vat_rate = VAT_info.query.filter_by(country=current_user.user_country).first()
    

    if len(dict_all_payment) > 0:
        #This case holds when the non-VAT services exist in the dict_non_vat_payment
        
        total_discount = 0
        for each_service in dict_all_payment:
            #Iterate through all of the services in the dictionary

            #Set the non-VAT record's country, document number, transaction ID, student's name and the date created
            accounting_record = Accounting_record()
            accounting_record.country = current_user.user_country
            accounting_record.code_number = receipt_number
            accounting_record.transaction_id = this_transaction_id
            accounting_record.name = transaction.student_full_name
            accounting_record.date_created = datetimefilter(datetime.datetime.utcnow(), return_string=False)
            

            if student_query is not None:
                # Fill in student's information if it exists in the database
                if accounting_record.name_th is None or accounting_record.name_th == 'NaN':
                    accounting_record.name_th = ''
                else:
                    accounting_record.name_th = student_query.name_th
                
                if accounting_record.address is None or accounting_record.address == 'NaN':
                    accounting_record.address = ''
                else:
                    accounting_record.address = student_query.address

            #Set the record's service name - either using the non-VAT name or using the service's usual name
            if 'non_vat_name' in service_dict[each_service] and service_dict[each_service]['non_vat_name'] is not None:
                accounting_record.service = service_dict[each_service]['non_vat_name']
            else:
                accounting_record.service = each_service
            
            #Set the two different cases of service counts
            if service_dict[each_service]['category'] == 'Counseling':
                #If the service's type is counseling, we will set its count to 1 and the price to the total value
                accounting_record.service_count = 1
                accounting_record.price_per_unit = my_round(dict_all_payment[each_service]['total_vat_amount'] + dict_all_payment[each_service]['total_non_vat_amount'], 2)
                accounting_record.total_non_vat_amount = my_round(dict_all_payment[each_service]['total_non_vat_amount'], 2)
                accounting_record.tax_invoice_amount = my_round(accounting_record.total_non_vat_amount * (1-vat_rate), 2)
                accounting_record.vat_amount = my_round(accounting_record.total_non_vat_amount * vat_rate, 2)
                accounting_record.total_vat_amount = my_round(dict_all_payment[each_service]['total_vat_amount'], 2)
                accounting_record.total_amount = accounting_record.total_non_vat_amount + accounting_record.total_vat_amount
            else:
                #Otherwise, set the count to be the actual value but being rounded to at most 2 decimal values
                accounting_record.service_count = my_round(dict_all_payment[each_service]['service_count'], 2)
                accounting_record.price_per_unit = my_round(dict_all_payment[each_service]['original_price_per_unit'], 2)
                accounting_record.total_non_vat_amount = my_round(dict_all_payment[each_service]['total_non_vat_amount'], 2)
                accounting_record.tax_invoice_amount = my_round(accounting_record.total_non_vat_amount * (1-vat_rate), 2)
                accounting_record.vat_amount = my_round(accounting_record.total_non_vat_amount * vat_rate, 2)
                accounting_record.total_vat_amount = my_round(dict_all_payment[each_service]['total_vat_amount'], 2)
                accounting_record.total_amount = accounting_record.total_non_vat_amount + accounting_record.total_vat_amount

            #Add the non-VAT record to the database
            db.session.add(accounting_record)
            db.session.commit()

            #Calculate the discount to add the entry to the non-VAT record
            discount_per_unit = dict_all_payment[each_service]['original_price_per_unit'] - dict_all_payment[each_service]['final_price_per_unit']
            total_discount += dict_all_payment[each_service]['service_count'] * discount_per_unit
        
        if total_discount > 0:
            #If the total discount > 0, we will create another entry of discount, with the name being 'ส่วนลด nonVAT'
            #For this case, we will repeat all of the processes as before
            accounting_record_discount = Accounting_record()
            accounting_record_discount.country = current_user.user_country
            accounting_record_discount.code_number = receipt_number
            accounting_record_discount.transaction_id = this_transaction_id
            accounting_record_discount.name = transaction.student_full_name
            accounting_record_discount.date_created = datetimefilter(datetime.datetime.utcnow(), return_string=False)
            
            if student_query is not None:
                if accounting_record_discount.name_th is None or accounting_record_discount.name_th == 'NaN':
                    accounting_record_discount.name_th = ''
                else:
                    accounting_record_discount.name_th = student_query.name_th
                
                if accounting_record_discount.name_th is None or accounting_record_discount.name_th == 'NaN':
                    accounting_record_discount.address = ''
                else:
                    accounting_record_discount.address = student_query.address

            accounting_record_discount.service = 'ส่วนลด nonVAT'
            accounting_record_discount.service_count = 1
            accounting_record_discount.price_per_unit = my_round(total_discount, 2)
            accounting_record_discount.total_non_vat_amount = my_round(total_discount, 2)
            accounting_record_discount.tax_invoice_amount = 0
            accounting_record_discount.vat_amount = 0
            accounting_record_discount.total_vat_amount = 0
            accounting_record_discount.total_amount = accounting_record_discount.total_non_vat_amount + accounting_record_discount.total_vat_amount

            db.session.add(accounting_record_discount)
            db.session.commit()


def convert_local_to_utc_time(local_dt):
    """Convert the local datetime to the UTC datetime

    Args:
        local_dt (datetime object): datetime of the local timezone with respect to the client

    Returns:
        datetime object: normalize the datetime to the UTC timezone
    """
    #Check the user's country and find the timezone for it
    if current_user.user_country == 'Myanmar':
        local_tz = pytz.timezone('Asia/Yangon')
    else:
        local_tz = pytz.timezone('Asia/Bangkok')

    utc_dt = local_dt.replace(tzinfo=local_tz).astimezone(pytz.utc)
    return pytz.utc.normalize(utc_dt)

def append_service(filename_in, service_table_name):
    """Append all of the services in the input excel file to the database

    Args:
        filename_in (str): directory string of the input excel file
        service_table_name (str): name of the service table in the database 
    """
    #Read the excel file and save it to the SQL database
    df = pd.read_excel(filename_in)
    df.to_sql(service_table_name, con = db.engine, index=False, if_exists = 'append')
    db.session.commit()


def fill_payment_method():
    all_sales = Sale_record.query.all()
    for each_sale in all_sales:
        transaction_obj = Transaction.query.filter_by(id = each_sale.transaction_id).first()
        if transaction_obj is not None:
            each_sale.payment_method = transaction_obj.payment_method
    db.session.commit()

def fill_grad_year():
    all_sales = Sale_record.query.all()
    for each_sale in all_sales:
        student_obj = Student.query.filter_by(name = each_sale.student_name).first()
        if student_obj is not None:
            each_sale.graduate_year = student_obj.graduate_year
    db.session.commit()

def fill_accounting_service_part():
    all_accounting_obj = Accounting_record.query.all()
    for each_accounting in all_accounting_obj:
        service_obj = Service.query.filter_by(name = each_accounting.service).first()
        if service_obj is not None:
            each_accounting.service_category = service_obj.category
            each_accounting.service_subcategory = service_obj.subcategory
    db.session.commit()

def fill_student_credit_outstanding_part():
    all_student_obj = Student.query.all()
    for each_student in all_student_obj:
        if each_student.credit_value is None:
            each_student.credit_value = 0
    db.session.commit()

def create_first_admin_id(username, password, email, first_name, user_country, role):
    """Create an admin id after pushing the code to the server

    Args:
        username (str): string of the username
        password (str): string of the password before being hashed
        email (str): email of the account
        first_name (str): user's first name
        user_country (str): user's country
        role (str): user's role name
    """
    #Query the role and set the user's information
    role = Role.query.filter_by(name=role).first()
    user = User(username=username, email=email, first_name = first_name, user_country=user_country, role_id=role.id, confirmed=True)
    user.set_password(password)
    #Add the user to the database
    db.session.add(user)
    db.session.commit()

def set_vat_rate(country='', vat_rate=0):
    vat_obj = VAT_info(country=country, vat_rate=vat_rate)
    db.session.add(vat_obj)
    db.session.commit()


def create_office_db(country='', info_for_vat=False, title='', company_name='', address_1='', address_2='', vat_tax_id='', email='', phone='', bank_name='', bank_account_name='', bank_account_number='', logo_directory=''):
    """[summary]

    Args:
        country (str, optional): [office country]. Defaults to ''.
        info_for_vat (bool, optional): [boolean which is True if this row is for generating a VAT receipt]. Defaults to False.
        title (str, optional): [document title - used for a VAT receipt]. Defaults to ''.
        company_name (str, optional): [company name - used for a VAT receipt]. Defaults to ''.
        address_1 (str, optional): [first line of office address - if there is only one line, use this one]. Defaults to ''.
        address_2 (str, optional): [second line of office address (optional - now used for only the vat document)]. Defaults to ''.
        vat_tax_id (str, optional): [company's tax id]. Defaults to ''.
        email (str, optional): [company's email address]. Defaults to ''.
        phone (str, optional): [company's contact phone number]. Defaults to ''.
        bank_name (str, optional): [bank name of the company's bank account]. Defaults to ''.
        bank_account_name (str, optional): [bank account's name]. Defaults to ''.
        bank_account_number (str, optional): [bank account number]. Defaults to ''.
        logo_directory (str, optional): [directory of the company's logo file]. Defaults to ''.
    """
    # Create a new office instance and add it to the database
    office_obj = Office(country=country, info_for_vat=info_for_vat, title=title, company_name=company_name, address_1=address_1, address_2=address_2, vat_tax_id=vat_tax_id, email=email, phone=phone, bank_name=bank_name, bank_account_name=bank_account_name, bank_account_number=bank_account_number, logo_directory=logo_directory)
    db.session.add(office_obj)
    db.session.commit()

def fix_missing_address_and_name_th():
    all_account_records = Accounting_record.query.all()
    for each_record in all_account_records:
        if each_record.name_th is None or each_record.name_th == '':
            student_query = Student.query.filter_by(name = each_record.name).first()
            if student_query.name_th is not None and student_query.name_th != 'NaN':
                each_record.name_th = student_query.name_th
        if each_record.address is None or each_record.address == '':
            student_query = Student.query.filter_by(name = each_record.name).first()     
            if student_query.address is not None and student_query.address != 'NaN':
                each_record.address = student_query.address
    
    db.session.commit()

def fix_missing_credit_amount():
    all_student_records = Student.query.all()
    for each_record in all_student_records:
        if each_record.credit_value is None or each_record.credit_value == '':
            each_record.credit_value = 0.0
    
    db.session.commit()

def generate_zip_file(dict_file_in):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for each_key in dict_file_in:
            each_filename = each_key + '.pdf'
            zip_file.writestr(each_filename, dict_file_in[each_key].getvalue())

    return zip_buffer