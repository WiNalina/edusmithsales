
from app.models import Student, QIR_numbers, Service, Accounting_record, Sale_record, Refund
from app import db

import io
import numpy as np
import pandas as pd
from pandas import ExcelWriter
from flask_login import current_user
from flask import make_response

from app.models import Student, QIR_numbers, Service, Accounting_record, Sale_record, Refund

def save_credit_transfer(form):
    sender_student = Student.query.filter_by(name=form.sender_name.data).first_or_404()
    recipient_student = Student.query.filter_by(name=form.recipient_name.data).first_or_404()
    
    sender_student.credit_value -= form.transfer_amount.data
    recipient_student.credit_value += form.transfer_amount.data

    db.session.commit()

def save_refund_info(transaction, refund_flag_list, student_query):
    num_service = len(refund_flag_list)
    all_receipt_query = QIR_numbers.query.filter_by(transaction_id = transaction.id, code_type = 'R').all()
    print('all_receipt_query part')
    sum_value_loss = 0
    sum_credit_gain = 0

    if all_receipt_query is not None:
        list_code_number = list()
        if len(all_receipt_query) >= 1:
            for each_query in all_receipt_query:
                list_code_number.append(each_query.code_number)
            
        elif len(all_receipt_query) == 1:
            list_code_number = [all_receipt_query[0].code_number]
        
        list_code_number = str(list_code_number)

    for i in range(num_service):
        if refund_flag_list[i]:
            actual_ind = i + 1
            each_service_name = getattr(transaction, 'service_{}_name'.format(actual_ind))
            service_query = Service.query.filter_by(name = each_service_name).first()
            print('service_query part')
            each_discount_name = 'Discount: {}'.format(each_service_name)

            sum_value_loss += getattr(transaction, 'service_{}_refund_amount'.format(actual_ind))
            if getattr(transaction, 'service_{}_refund_status'.format(actual_ind)) == 'Credit':
                sum_credit_gain += getattr(transaction, 'service_{}_refund_amount'.format(actual_ind))

            service_accounting_list = Accounting_record.query.filter_by(transaction_id = transaction.id, service = each_service_name).all()
            service_discount_list = Accounting_record.query.filter_by(transaction_id = transaction.id, service = each_discount_name).all()
            all_accounting_list = service_accounting_list + service_discount_list
            print(all_accounting_list)
            print('all_accounting_list part')
            service_sales_list = Sale_record.query.filter_by(transaction_id = transaction.id, service_name = each_service_name).all()

            for each_accounting in all_accounting_list:
                each_accounting.refund_status = getattr(transaction, 'service_{}_refund_status'.format(actual_ind))
                print('refund_status part')
                each_accounting.refund_amount = getattr(transaction, 'service_{}_refund_amount'.format(actual_ind))
                print('refund_amount part')
                each_accounting.refund_date = getattr(transaction, 'service_{}_refund_date'.format(actual_ind))
                print('refund_date part')
            
            for each_sales in service_sales_list:
                each_sales.refund_status = getattr(transaction, 'service_{}_refund_status'.format(actual_ind))
                print('refund_status service_sales_list part')
                each_sales.refund_amount = getattr(transaction, 'service_{}_refund_amount'.format(actual_ind))
                print('refund_amount service_sales_list part')
                each_sales.refund_date = getattr(transaction, 'service_{}_refund_date'.format(actual_ind))
                print('refund_date service_sales_list part')

            
            refund_obj = Refund()
            refund_obj.date_refund = getattr(transaction, 'service_{}_refund_date'.format(actual_ind))
            refund_obj.country = transaction.country
            refund_obj.office = getattr(transaction, 'service_{}_office'.format(actual_ind))
            refund_obj.student_name = student_query.name
            refund_obj.graduate_year = student_query.graduate_year
            refund_obj.credit_note_number = getattr(transaction, 'service_{}_credit_note_number'.format(actual_ind))
            refund_obj.type_of_refund = getattr(transaction, 'service_{}_refund_status'.format(actual_ind))
            refund_obj.refund_amount = getattr(transaction, 'service_{}_refund_amount'.format(actual_ind))
            refund_obj.service_name = each_service_name
            refund_obj.service_category = service_query.category
            refund_obj.service_subcategory = service_query.subcategory
            refund_obj.receipt_number = list_code_number
            refund_obj.receipt_value = transaction.total_value - transaction.remaining_outstanding

            db.session.add(refund_obj)
            
    student_query.total_value -= sum_value_loss
    student_query.credit_value += sum_credit_gain
    db.session.commit()

def process_all_refund_records(start_date_filter=None, end_date_filter=None):
    refund_query = Refund.query.filter(Refund.country == current_user.user_country, Refund.date_refund >= start_date_filter, Refund.date_refund <= end_date_filter).order_by(Refund.id)
    student_with_credit_query = Student.query.filter(Student.student_country == current_user.user_country, Student.credit_value > 0)
    list_student_col = ['name', 'school', 'credit_value']

    refund_df = pd.read_sql(refund_query.statement, refund_query.session.bind)
    refund_df = refund_df.replace([np.nan, 'null'], ['', ''])

    student_df = pd.read_sql(student_with_credit_query.statement, student_with_credit_query.session.bind)
    student_df = student_df.replace([np.nan, 'null'], ['', ''])
    student_df = student_df.loc[:,list_student_col]

    output_dict = dict()
    output_dict['Refund Record'] = refund_df
    output_dict['Student Credit Record'] = student_df

    return output_dict


def process_and_download_refund_query(output_filename, start_date=None, end_date=None):
    """Process the given non-VAT query and download the files given matching the descriptions in the query

    Args:
        query_obj (SQLAlchemy query object): A query object for accounting documents
        output_filename (str): string of the output filename

    Returns:
        Flask response: Response object for the Excel file
    """
    #Create a writer to write a PDF file in a form of binaries 
    out = io.BytesIO()
    writer = ExcelWriter(out, engine='openpyxl')
    
    refund_dict = process_all_refund_records(start_date, end_date)
    #Save the data frame in a form of an excel file
    for each_sheet_name in refund_dict:
        refund_dict[each_sheet_name].to_excel(writer, sheet_name = each_sheet_name, index=False)
    writer.save()
    out.seek(0)
    resp = make_response(out.getvalue())
    resp.headers['Content-Disposition'] = 'attachment; filename={}'.format(output_filename)
    resp.headers['Content-Type'] = 'application/vnd.ms-excel; charset=utf-8'

    return resp