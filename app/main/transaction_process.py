import datetime
import numpy as np

from app import db
from app.models import QIR_numbers, QIR_numbers_preview, Sale_record, UserRecord, Transaction, Service, Accounting_record, Student, VAT_info, Refund
from flask_login import current_user
from flask import current_app

from app.util import datetimefilter
import io
import os
import PyPDF2
from app.main.document_gen import create_pdf_document
from sqlalchemy import desc

import math
from app.main.util import my_round
from app.main.refund_and_credit import save_refund_info

def process_weighted_discount(discount_list, price_list, count_list, overall_discount):
    output_discount = list()
    sum_discount = 0
    sum_price = 0

    for i in range(len(discount_list)):
        if discount_list[i] < 1:
            each_discount = discount_list[i] * price_list[i] * count_list[i]
        else:
            each_discount = discount_list[i]

        if overall_discount < 1:
            each_discount += overall_discount * price_list[i] * count_list[i]
        else:
            each_discount += overall_discount
        
        each_discount = my_round(each_discount, 0)
        sum_discount += each_discount
        sum_price += price_list[i] * count_list[i]
    
    for i in range(len(price_list)):
        each_discount = my_round(sum_discount * (price_list[i] * count_list[i])/sum_price, 0)
        output_discount.append(each_discount)

    output_discount = np.array(output_discount)

    if np.sum(output_discount) != sum_discount:
        diff = np.sum(output_discount) - sum_discount
        output_discount[np.argmax(output_discount)] = output_discount[np.argmax(output_discount)] - diff

    return output_discount

def fill_amortize_dict(amortization_type, start_date, end_date, total_hours, monday_hours, tuesday_hours, wednesday_hours, thursday_hours, friday_hours, saturday_hours, sunday_hours, month_1_hrs, month_2_hrs, month_3_hrs, month_4_hrs, month_5_hrs, month_6_hrs):
    """Create a dict to store amortization information for the sake of organizing data for each service

    Args:
        amortization_type (str): A string of amortization type
        start_date (datetime.datetime): datetime object for the beginning date of the service
        end_date (datetime.datetime): datetime object for the ending date of the service
        total_hours (float): The total number of hours used for weekly hours
        month_1_hrs (float): The number of hours spent for the 1st month
        month_2_hrs (float): The number of hours spent for the 2nd month
        month_3_hrs (float): The number of hours spent for the 3rd month
        month_4_hrs (float): The number of hours spent for the 4th month
        month_5_hrs (float): The number of hours spent for the 5th month
        month_6_hrs (float): The number of hours spent for the 6th month

    Returns:
        dict: A dictionary containing all amortization information
    """
    output_dict = dict()

    output_dict['amortization_type'] = amortization_type
    output_dict['start_date'] = start_date
    output_dict['end_date'] = end_date
    output_dict['total_hours'] = total_hours
    output_dict['monday_hours'] = monday_hours
    output_dict['tuesday_hours'] = tuesday_hours
    output_dict['wednesday_hours'] = wednesday_hours
    output_dict['thursday_hours'] = thursday_hours
    output_dict['friday_hours'] = friday_hours
    output_dict['saturday_hours'] = saturday_hours
    output_dict['sunday_hours'] = sunday_hours
    output_dict['month_1_hrs'] = month_1_hrs
    output_dict['month_2_hrs'] = month_2_hrs
    output_dict['month_3_hrs'] = month_3_hrs
    output_dict['month_4_hrs'] = month_4_hrs
    output_dict['month_5_hrs'] = month_5_hrs
    output_dict['month_6_hrs'] = month_6_hrs

    return output_dict

def fill_service_info_to_dict(dict_in, service_name, teacher_name, service_office, service_obj, amortize_dict):
    """Fill the input service_obj's information in a dictionary if the service is not already included in the dictionary

    Args:
        dict_in ([dict]): a dictionary containing every service's information
        service_name ([str]): service name
        service_obj ([sqlalchemy query obj]): query object of the target service

    Returns:
        dict_in [dict]: a dictionary with the new service's information added
    """

    #Check if not included
    if service_name not in dict_in and service_name != '' and service_name is not None:
        #If not, put all information into the dictionary
        dict_in[service_name] = dict()
        dict_in[service_name]['category'] = service_obj.category
        dict_in[service_name]['subcategory'] = service_obj.subcategory
        dict_in[service_name]['display_name'] = service_obj.display_name
        dict_in[service_name]['vat_name'] = service_obj.vat_name
        dict_in[service_name]['non_vat_name'] = service_obj.non_vat_name

        dict_in[service_name]['office'] = service_office
        dict_in[service_name]['teacher'] = teacher_name
        
        #Amortization Part
        dict_in[service_name]['amortization_type'] = amortize_dict['amortization_type']
        dict_in[service_name]['start_date'] = amortize_dict['start_date']
        dict_in[service_name]['end_date'] = amortize_dict['end_date']
        
        dict_in[service_name]['total_hours'] = amortize_dict['total_hours']
        dict_in[service_name]['monday_hours'] = amortize_dict['monday_hours']
        dict_in[service_name]['tuesday_hours'] = amortize_dict['tuesday_hours']
        dict_in[service_name]['wednesday_hours'] = amortize_dict['wednesday_hours']
        dict_in[service_name]['thursday_hours'] = amortize_dict['thursday_hours']
        dict_in[service_name]['friday_hours'] = amortize_dict['friday_hours']
        dict_in[service_name]['saturday_hours'] = amortize_dict['saturday_hours']
        dict_in[service_name]['sunday_hours'] = amortize_dict['sunday_hours']

        dict_in[service_name]['month_1_hrs'] = amortize_dict['month_1_hrs']
        dict_in[service_name]['month_2_hrs'] = amortize_dict['month_2_hrs']
        dict_in[service_name]['month_3_hrs'] = amortize_dict['month_3_hrs']
        dict_in[service_name]['month_4_hrs'] = amortize_dict['month_4_hrs']
        dict_in[service_name]['month_5_hrs'] = amortize_dict['month_5_hrs']
        dict_in[service_name]['month_6_hrs'] = amortize_dict['month_6_hrs']
        
    return dict_in

def fix_array_with_none(array_in):
    """Replace all of the array values that are None with 0.0

    Args:
        array_in (array): An array with float values

    Returns:
        array: An array with the None values replaced by 0.0
    """
    for each_ind in range(len(array_in)):
        if array_in[each_ind] is None:
            array_in[each_ind] = 0.0
    return array_in

def find_service_vat_proportions(service_name_list):
    """Find all of the vat proportions for all services and store them in a list

    Args:
        service_name_list (list): list of service names

    Returns:
        list: list of vat proportions for all services
    """
    output_vat_proportion_list = list()
    
    #Iterate through all of the services and query each service's VAT proportion
    for each_service_name in service_name_list:
        if each_service_name is not None and each_service_name != '':
            each_service_obj = Service.query.filter_by(name=each_service_name, country=current_user.user_country).first_or_404()
            output_vat_proportion_list.append(each_service_obj.vat_proportion)
        else:
            output_vat_proportion_list.append(None)
    return output_vat_proportion_list

def calculate_vat_value_list(service_price_list, service_vat_proportion_list):
    """Calculate all of the VAT values according to the price list and the VAT proportion list

    Args:
        service_price_list (list): List of service prices
        service_vat_proportion_list (list): List of service VAT proportions

    Returns:
        np.array: An array of vat value
    """
    vat_value_list = list()
    assert len(service_price_list) == len(service_vat_proportion_list)

    #Iterate through all of the prices and vat proportions and calculate all vat values
    for i in range(len(service_price_list)):
        if service_price_list[i] is not None and service_vat_proportion_list[i] is not None:
            each_actual_vat_value = float(service_price_list[i]) * service_vat_proportion_list[i]
            vat_value_list.append(each_actual_vat_value)
        else:
            vat_value_list.append(None)
    return np.array(vat_value_list)

def detect_service_change(former_service_names, current_service_names):
    """Check if the services in the 2 input lists are exactly the same

    Args:
        former_service_names (list): a former list of service names
        current_service_names (list): a new list of service names

    Returns:
        list: list of booleans with True being identical, and False being different for each list index
    """
    output_list = list()
    for i in range(len(current_service_names)):
        if current_service_names[i] != former_service_names[i]:
            output_list.append(True)
        else:
            output_list.append(False)
    return output_list

def optimize_transaction_vat(transaction, this_time_payment, this_time_credit_spending, former_service_names, discount_array, new, optimize_vat_flag = False):
    """Minimize the VAT for each transaction

    Args:
        transaction (SQLAlchemy query object): Transaction object
        this_time_payment (float): Payment amount for this transaction
        former_service_names (list): List of strings for service names
        new (boolean): Boolean, which is True if the transaction is new. If this is just for editing, new will be False
    
    Returns:
    array_remaining_value (array): An array of the remaining outstandings of all services 
    array_paid_value (array): An array of the paid values of all services 
    array_this_time_count (array): An array of all service counts in this transaction 
    total_vat_value (float): The total value of VAT payment value 
    dict_all_payment (dict): The dictionary of all payments for all services
    """

    #Create a list of service names
    list_service_names = [transaction.service_1_name, transaction.service_2_name, transaction.service_3_name, transaction.service_4_name, transaction.service_5_name, transaction.service_6_name]
    #Create arrays of service counts, original prices per unit, and final values
    array_service_counts = np.array([transaction.service_1_count, transaction.service_2_count, transaction.service_3_count, transaction.service_4_count, transaction.service_5_count, transaction.service_6_count])
    array_original_prices_per_unit = np.array([transaction.service_1_price, transaction.service_2_price, transaction.service_3_price, transaction.service_4_price, transaction.service_5_price, transaction.service_6_price])
    array_total_original_price = array_service_counts * array_original_prices_per_unit
    array_final_values = array_total_original_price - discount_array
    total_final_values = np.sum(array_final_values)
    
    #Create an array of prices per unit after discounts
    array_prices_after_discounts = list()
    for i in range(len(array_final_values)):
        if array_service_counts[i] == 0:
            array_prices_after_discounts.append(0)
        else:
            array_prices_after_discounts.append((array_total_original_price[i] - discount_array[i])/array_service_counts[i])
    array_prices_after_discounts = np.array(array_prices_after_discounts)

    #Create the array of remaining values with the two cases - if new just let them be the final values from the transaction
    #Otherwise, use the prior values
    if new:
        array_remaining_value = array_final_values
    else:
        service_change_flag_list = detect_service_change(former_service_names, list_service_names)
        array_remaining_value = np.array([transaction.service_1_unpaid_value, transaction.service_2_unpaid_value, transaction.service_3_unpaid_value, transaction.service_4_unpaid_value, transaction.service_5_unpaid_value, transaction.service_6_unpaid_value])
        for i in range(len(service_change_flag_list)):
            if service_change_flag_list[i]:
                array_remaining_value[i] = array_final_values[i]
    
    #Instantiate all of the values and output variables
    array_paid_value = np.array([0.0] * 6)
    array_this_time_count = np.array([0.0] * 6)
    array_credit_value = np.array([0.0] * 6)
    
    dict_vat_proportion = dict()
    total_vat_value = 0.0
    dict_all_payment = dict()
    
    #Query and save all VAT proportions in a dictionary
    for service_num, each_service in enumerate(list_service_names):
        if each_service is None or each_service == '':
            dict_vat_proportion[service_num] = 1.01
        else:
            temp_service = Service.query.filter_by(name=each_service, country=current_user.user_country).first_or_404()
            dict_vat_proportion[service_num] = temp_service.vat_proportion
    
    #Sort the VAT proportion dictionary with the first element being the service with the least VAT 
    sorted_vat_proportions = sorted(dict_vat_proportion.items(), key=lambda x: x[1])
    #Value of the remaining amount of payment from this transaction
    remaining_amount = this_time_payment + this_time_credit_spending
    credit_amount = this_time_credit_spending
    
    if optimize_vat_flag:
        for i in sorted_vat_proportions:
            #Iterate through all of the services to calculate all of the remaining amounts
            #As the dictionary is sorted, the prior index would be spent for less VAT

            if remaining_amount > 0 and np.sum(array_remaining_value) > 0 and list_service_names[i[0]] != '':
                #This case holds only if there still exists any remaining amount of money for the transaction
                if remaining_amount >= array_remaining_value[i[0]]:
                    #If the remaining amount >= this value of service, then we will fully pay for this service
                    array_paid_value[i[0]] = array_remaining_value[i[0]] #The paid amount will be equal to the remaining amount
                    #Calculate for vat and non-vat values
                    vat_value = array_paid_value[i[0]] * dict_vat_proportion[i[0]]
                    non_vat_value = array_paid_value[i[0]] - vat_value
                    total_vat_value += vat_value
                    #Subtract the remaining amount by this service's value
                    remaining_amount -= array_remaining_value[i[0]]
                    #Set the remaining value to be zero
                    array_remaining_value[i[0]] = 0
                else:
                    #This case holds when only the partial amount of money is left
                    #Subtract the service's remaining value by the payment's remaining value 
                    array_remaining_value[i[0]] -= remaining_amount
                    #Find VAT and non-VAT values
                    non_vat_value = remaining_amount * (1 - dict_vat_proportion[i[0]])
                    vat_value = remaining_amount * dict_vat_proportion[i[0]]
                    total_vat_value += vat_value
                    #Paid value equal to the remaining amount for this payment
                    array_paid_value[i[0]] = remaining_amount
                    #Set the remaining amount to be zero
                    remaining_amount = 0
                
                
                #If non-VAT value > 0, we will record all of the services with non-VAT payment > 0
                if list_service_names[i[0]] != '':
                    if list_service_names[i[0]] not in dict_all_payment:
                        dict_all_payment[list_service_names[i[0]]] = dict()
                    
                    dict_all_payment[list_service_names[i[0]]]['vat_proportion'] = dict_vat_proportion[i[0]]
                    dict_all_payment[list_service_names[i[0]]]['total_non_vat_amount'] = non_vat_value
                    dict_all_payment[list_service_names[i[0]]]['total_vat_amount'] = vat_value
                    dict_all_payment[list_service_names[i[0]]]['total_service_count'] = array_service_counts[i[0]]
                    if array_prices_after_discounts[i[0]] > 0:
                        dict_all_payment[list_service_names[i[0]]]['service_count'] = array_paid_value[i[0]]/array_prices_after_discounts[i[0]]
                    else:
                        dict_all_payment[list_service_names[i[0]]]['service_count'] = array_service_counts[i[0]]
                    dict_all_payment[list_service_names[i[0]]]['original_price_per_unit'] = array_original_prices_per_unit[i[0]]
                    dict_all_payment[list_service_names[i[0]]]['final_price_per_unit'] = array_prices_after_discounts[i[0]]
    
    else:
        price_proportion = remaining_amount/total_final_values
        credit_proportion = credit_amount/total_final_values
        if remaining_amount == 0:
            credit_total_payment_ratio = 1
        else:
            credit_total_payment_ratio = credit_amount/remaining_amount

        for i in sorted_vat_proportions:
            if remaining_amount > 0 and np.sum(array_remaining_value) > 0 and list_service_names[i[0]] != '':
                if price_proportion * array_final_values[i[0]] > array_remaining_value[i[0]] and list_service_names[i[0]] != '':
                    array_paid_value[i[0]] = array_remaining_value[i[0]] #The paid amount will be equal to the remaining amount
                    array_credit_value[i[0]] = credit_total_payment_ratio * array_remaining_value[i[0]]
                else:
                    array_paid_value[i[0]] = price_proportion * array_final_values[i[0]]
                    array_credit_value[i[0]] = credit_proportion * array_final_values[i[0]]
                #Calculate for vat and non-vat values
                vat_value = my_round(array_paid_value[i[0]] * dict_vat_proportion[i[0]], 0)
                non_vat_value = array_paid_value[i[0]] - vat_value

                credit_vat_value = my_round(array_credit_value[i[0]] * dict_vat_proportion[i[0]], 0)
                credit_non_vat_value = array_credit_value[i[0]] - credit_vat_value
                
                total_vat_value += vat_value
                #Subtract the remaining amount by this service's value
                remaining_amount -= array_paid_value[i[0]]
                #Set the remaining value to be zero
                array_remaining_value[i[0]] -= array_paid_value[i[0]]

                if list_service_names[i[0]] != '':
                    if list_service_names[i[0]] not in dict_all_payment:
                        dict_all_payment[list_service_names[i[0]]] = dict()
                    
                    dict_all_payment[list_service_names[i[0]]]['vat_proportion'] = dict_vat_proportion[i[0]]
                    dict_all_payment[list_service_names[i[0]]]['total_non_vat_amount'] = non_vat_value
                    dict_all_payment[list_service_names[i[0]]]['total_vat_amount'] = vat_value
                    dict_all_payment[list_service_names[i[0]]]['total_service_count'] = array_service_counts[i[0]]
                    if array_prices_after_discounts[i[0]] > 0:
                        dict_all_payment[list_service_names[i[0]]]['service_count'] = array_paid_value[i[0]]/array_prices_after_discounts[i[0]]
                        dict_all_payment[list_service_names[i[0]]]['service_credit_count'] = array_credit_value[i[0]]/array_prices_after_discounts[i[0]]
                    else:
                        dict_all_payment[list_service_names[i[0]]]['service_count'] = array_service_counts[i[0]]
                        dict_all_payment[list_service_names[i[0]]]['service_credit_count'] = array_credit_value[i[0]]

                    dict_all_payment[list_service_names[i[0]]]['original_price_per_unit'] = array_original_prices_per_unit[i[0]]
                    dict_all_payment[list_service_names[i[0]]]['final_price_per_unit'] = array_prices_after_discounts[i[0]]

    array_this_time_count = list()
    for i in range(len(array_paid_value)):
        if array_paid_value[i] == 0:
            array_this_time_count.append(0.0)
        else:
            array_this_time_count.append(array_paid_value[i]/array_prices_after_discounts[i])
    array_this_time_count = np.array(array_this_time_count)        

    #Check the vat rate for the user's country and calculate the total VAT value
    vat_rate_query = VAT_info.query.filter_by(country=current_user.user_country).first()
    vat_rate = vat_rate_query.vat_rate
    total_vat_value *= vat_rate

    return array_remaining_value, array_paid_value, array_this_time_count, total_vat_value, dict_all_payment

def process_cancelled_transaction(transaction_id, student_query):
    #Process any cancelled transaction by deleting all of the transactions previously added to the accounting_table, qir_numbers_preview, and sale_record tables
    #param transaction_id (int): an id of the cancelled transaction

    #Subtract the cancelled amount from target student's value
    transaction = Transaction.query.filter_by(id=transaction_id).first_or_404()
    paid_amount = transaction.total_value - transaction.remaining_outstanding
    if student_query.total_value and paid_amount is not None:
        student_query.total_value -= paid_amount

    #Delete the rows in Accounting_record
    all_accounting_records = Accounting_record.query.filter_by(transaction_id = transaction_id).all()
    all_sale_records = Sale_record.query.filter_by(transaction_id = transaction_id).all()

    for each_record in all_accounting_records:
        each_record.note = 'Cancelled'
    for each_record in all_sale_records:
        each_record.note = 'Cancelled'
    
    #Go over all files in qir_preview_query and delete both the preview document files and the database entries 
    qir_preview_query_obj = QIR_numbers_preview.query.filter_by(transaction_id = transaction_id)
    all_qir_preview_file_list = qir_preview_query_obj.all()
    if len(all_qir_preview_file_list) > 0:
        qir_preview_query_obj.delete()

    transaction.transaction_status = 'Cancelled'

    #Commit the database
    db.session.commit()

def change_to_3_digit_type(input_num):
    """Change the input number to the three-digit format 

    Args:
        input_num (int): input integer

    Returns:
        [str]: a 3-digit value in the string form
    """
    if input_num < 10:
        return '00' + str(input_num)
    elif input_num < 100:
        return '0' + str(input_num)
    else:
        return str(input_num)

def generate_code_number(last_id = 1, prefix = None, new = False):
    """Generate document code number

    Args:
        last_id (int, optional): The id value of last transaction. Defaults to 1.
        prefix (str, optional): String prefix with of a capital character with length 1. Defaults to None.
        new (bool, optional): Boolean checking whether the code number is the first in this month. Defaults to False.

    Returns:
        str: document code number
    """
    #If prefix is None (which is usually not the case), let it be just blank
    #Otherwise, let the first character being the prefix character
    if prefix is None:
        output_id = ''
    else:
        output_id = prefix

    #Create the three digit code for this month
    datetime_obj = datetime.datetime.now()
    if new:
        this_id = change_to_3_digit_type(1)
    else:
        last_id = int(last_id[-3:])
        this_id = change_to_3_digit_type(last_id + 1)

    #If the month index < 10, we must add '0' to the front of it
    if datetime_obj.month < 10:
        month_str = '0' + str(datetime_obj.month)
    else:
        month_str = str(datetime_obj.month)

    #Combine all subcomponents together
    output_id += str(datetime_obj.year)[2:] + month_str + this_id

    return output_id

def check_same_year_month(datetime_1, datetime_2):
    """Check if the two input datetime objects have the same months and the same years

    Args:
        datetime_1 ([datetime.datetime]): [first datetime]
        datetime_2 ([datetime.datetime]): [second datetime]

    Returns:
        [type]: [True or False boolean]
    """
    if datetime_1.month == datetime_2.month and datetime_1.year == datetime_2.year:
        return True
    else:
        return False

def create_QIR_numbers(prefix_string):
    """Create document number depending on the given type of document

    Args:
        prefix_string (str): A length-one string indicating a document type

    Returns:
        [str]: code number generated from the generate_code_number function
    """
    #Check if there exists a qir object. If so, use the id from the query object to find the next code number
    last_qir_query = QIR_numbers.query.filter_by(code_type=prefix_string, country=current_user.user_country).order_by(desc('date_created')).first()
    if bool(last_qir_query):
        #Find the transaction datetime from the query object
        last_transaction_datetime = last_qir_query.date_created
        if check_same_year_month(last_transaction_datetime, datetime.datetime.utcnow()):
            #If the latest transaction has the same date created, use it to create a new id
            return generate_code_number(last_id = last_qir_query.code_number, prefix = prefix_string, new=False)
        else:
            #Otherwise, just create a new code for this month
            return generate_code_number(prefix = prefix_string, new=True)
    else:
        #If query is None, we will just create a new code number
        return generate_code_number(prefix = prefix_string, new=True)



def save_qir_numbers(transaction, this_transaction_id, qir_in, pdf_binary, pickle_binary, actual_qir_flag=True):
    #Save quotation, invoice, or receipt information to the database
    #param transaction (sqlalchemy object): a transaction object retrieved from the app.models.Transaction class
    #param this_transaction_id (int): a transaction id
    #param qir_in (str): a reference code for this document
    #param doc_directory (str): an absolute path/directory of the stored document
    #param actual_qir_flag (boolean): a boolean indicating if this qir number is for an actual transaction

    #If actual_qir_flag, we will save it to the QIR_numbers table. Else, we will save it to the QIR_numbers_preview table.
    if actual_qir_flag:
        qir_obj = QIR_numbers()
    else:
        qir_obj = QIR_numbers_preview()
    
    #Save user country, transaction id, created date, username of a user creating the document, document type, document code, and the absolute directory.
    qir_obj.country = current_user.user_country
    qir_obj.student_full_name = transaction.student_full_name
    qir_obj.transaction_id = this_transaction_id
    qir_obj.date_created = datetime.datetime.utcnow()
    qir_obj.creating_user = current_user.username
    if actual_qir_flag:
        qir_obj.code_type = qir_in[0]
    qir_obj.code_number = qir_in
    qir_obj.pdf_binary = pdf_binary
    if pickle_binary is not None and actual_qir_flag:
        qir_obj.pickle_binary = pickle_binary


    #If actual_qir_flag, we will add this object as one of the transactions' document numbers
    if actual_qir_flag:
        transaction.document_number.append(qir_obj)
    else:
        QIR_numbers_preview.query.filter_by(code_number=qir_in).delete()
        db.session.commit()

    #Add this object to the database and record the activity in the user record table
    db.session.add(qir_obj)

    user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='create document number {}'.format(qir_in))
    db.session.add(user_record)
    
    db.session.commit()

def check_all_same_service(original_service_list, new_service_list):
    #Utility function checking if all services are the same between the 2 input lists
    #param original_service_list (list of strs): a list containing strings of service names from last transaction
    #param new_service_list (list of strs)L a list containing strings of service names from new transaction 

    #Check if the list lengths are equal
    assert len(original_service_list) == len(new_service_list)
    
    #Iterate through all indices and check if values in the same indices are unequal
    #If any unequal value exists, return False
    same_service_flag = True
    for i in range(len(original_service_list)):
        if original_service_list[i] != new_service_list[i]:
            same_service_flag = False

    return same_service_flag

def combine_pdfs(list_code_number):
    #Merge several PDF files altogether to create one PDF file for previewing
    #param list_code_number: a list of document code strings

    #First, check if list_code_number is not empty
    assert len(list_code_number) > 0
    output_buffer = io.BytesIO()

    #There exist 2 cases here:
    #If there exists only one pdf file, just return the file's name without a file extension
    #Else, combine all of the pdfs in the list altogether before returning the merged file's name in the form of {document_code_1}_{document_code_2}_..._{document_code_[last]}
    
    if len(list_code_number) == 1:
        #With this case, we only return the file name and add the activity to the user record
        output_filename_wo_extension = list_code_number[0]

        user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='preview document code: {}'.format(output_filename_wo_extension))
        db.session.add(user_record)
        
        return output_filename_wo_extension, None
    else:
        #Initialize a pdf writer and an empty string
        pdfWriter = PyPDF2.PdfFileWriter()
        output_filename = ''

        #Iterate through all code numbers and add pages from each file
        for each_ind, each_code in enumerate(list_code_number):
            qir_query = QIR_numbers_preview.query.filter_by(code_number=each_code).first()

            if each_ind == len(list_code_number) - 1:
                output_filename += each_code
            else:
                output_filename += each_code + '_'

            temp_buffer = io.BytesIO(qir_query.pdf_binary)
            temp_buffer.seek(0)
            
            each_pdf_reader = PyPDF2.PdfFileReader(temp_buffer)
            
            #Add page objects to the pdf writer
            for pageNum in range(each_pdf_reader.numPages):
                pageObj = each_pdf_reader.getPage(pageNum)
                pdfWriter.addPage(pageObj)

            #Add a user record
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='preview document code: {}'.format(each_code))
            db.session.add(user_record)
        
        #Save all changes to the database
        db.session.commit()

        #Save the output file to the final directory and return the file name without the file's extension
        
        #Write the file in a binary form
        pdfWriter.write(output_buffer)
        raw_pdf_content = output_buffer.getvalue()

        temp_buffer.close()
        output_buffer.close()

        return output_filename, raw_pdf_content

def add_sale_record(transaction_id, student_query, code_number, payment_method, card_machine, payment_date, payment_time, service_name_array, payment_array, count_array, service_dict):
    #Add a sale record for visualization purpose
    adding_list = list()
    for each_ind, each_val in enumerate(payment_array):
        if each_val > 0:
            sale_obj = Sale_record() #Create a new sales record
            sale_obj.date_created = datetime.datetime.utcnow() #Create the date when the sales occurred
            sale_obj.country = current_user.user_country #Record user country
            sale_obj.office = service_dict[service_name_array[each_ind]]['office']
            sale_obj.code_number = code_number #Document code
            sale_obj.transaction_id = transaction_id #Transaction ID
            sale_obj.student_name = student_query.name #Student's name
            sale_obj.school = student_query.school #Student's school
            sale_obj.graduate_year = student_query.graduate_year
            sale_obj.service_name = service_name_array[each_ind] #Service name
            sale_obj.service_category = service_dict[service_name_array[each_ind]]['category'] #Service category
            sale_obj.service_subcategory = service_dict[service_name_array[each_ind]]['subcategory'] #Service subcategory
            sale_obj.service_count = my_round(count_array[each_ind], 2) #Service count
            sale_obj.price_per_unit = my_round(payment_array[each_ind]/count_array[each_ind], 2) #Price per unit
            sale_obj.total_value = my_round(payment_array[each_ind], 2) #Total sales value
            sale_obj.payment_method = payment_method
            sale_obj.card_machine = card_machine
            sale_obj.payment_date = payment_date
            sale_obj.payment_time = payment_time
            sale_obj.amortization_start_date = service_dict[service_name_array[each_ind]]['start_date']
            sale_obj.teacher_name = service_dict[service_name_array[each_ind]]['teacher']
            adding_list.append(sale_obj)
    
    db.session.add_all(adding_list)
    db.session.commit()

def save_accounting_record(transaction, this_transaction_id, dict_all_payment, receipt_number, vat_invoice_number, payment_method, payment_date, payment_time, card_machine, card_issuer, service_dict):
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
    vat_rate_query = VAT_info.query.filter_by(country=current_user.user_country).first()
    vat_rate = vat_rate_query.vat_rate
    
    if len(dict_all_payment) > 0:
        #This case holds when the non-VAT services exist in the dict_non_vat_payment
        
        total_discount = 0
        for each_service in dict_all_payment:
            #Iterate through all of the services in the dictionary

            #Set the non-VAT record's country, document number, transaction ID, student's name and the date created
            accounting_record = Accounting_record()
            accounting_record.country = current_user.user_country
            accounting_record.code_number = receipt_number
            if vat_invoice_number:
                accounting_record.vat_invoice_code_number = vat_invoice_number
            accounting_record.transaction_id = this_transaction_id
            accounting_record.name = transaction.student_full_name
            accounting_record.date_created = datetimefilter(datetime.datetime.utcnow(), return_string=False)

            if student_query is not None:
                # Fill in student's information if it exists in the database
                if student_query.name_th is None or student_query.name_th == 'NaN':
                    accounting_record.name_th = ''
                else:
                    accounting_record.name_th = student_query.name_th
                
                if student_query.address is None or student_query.address == 'NaN':
                    accounting_record.address = ''
                else:
                    accounting_record.address = student_query.address

            #Set the record's service name - either using the non-VAT name or using the service's usual name
            accounting_record.service = each_service
            accounting_record.service_category = service_dict[each_service]['category']
            accounting_record.service_subcategory = service_dict[each_service]['subcategory']
            accounting_record.payment_method = payment_method #Payment Method
            accounting_record.payment_date = payment_date
            accounting_record.payment_time = payment_time
            accounting_record.card_machine = card_machine
            accounting_record.card_issuer = card_issuer
            accounting_record.amortization_start_date = service_dict[each_service]['start_date']  
            
            #Otherwise, set the count to be the actual value but being rounded to at most 2 decimal values
            accounting_record.total_service_count = my_round(dict_all_payment[each_service]['total_service_count'], 2)
            accounting_record.original_price_per_unit = my_round(dict_all_payment[each_service]['original_price_per_unit'], 2)
            accounting_record.service_count = my_round(dict_all_payment[each_service]['service_count'], 2)
            accounting_record.price_per_unit = my_round(dict_all_payment[each_service]['original_price_per_unit'], 2)

            vat_proportion = dict_all_payment[each_service]['vat_proportion']
            this_installment_amount = dict_all_payment[each_service]['service_count'] * dict_all_payment[each_service]['original_price_per_unit']
            this_installment_vat_amount = my_round(this_installment_amount * vat_proportion, 2)
            this_installment_non_vat_amount = my_round(this_installment_amount - this_installment_vat_amount, 2)

            accounting_record.total_non_vat_amount = my_round(this_installment_non_vat_amount, 2)
            accounting_record.tax_invoice_amount = my_round(this_installment_vat_amount * (1/(1+vat_rate)), 2)
            accounting_record.vat_amount = my_round(this_installment_vat_amount - accounting_record.tax_invoice_amount, 2)
            accounting_record.total_vat_amount = accounting_record.tax_invoice_amount + accounting_record.vat_amount
            accounting_record.total_amount = accounting_record.total_non_vat_amount + accounting_record.total_vat_amount
            
            #Service Part: Amortization Section
            accounting_record.amortization_type = service_dict[each_service]['amortization_type'] #Service amortization type
            accounting_record.start_date = service_dict[each_service]['start_date'] #Service start date
            accounting_record.end_date = service_dict[each_service]['end_date'] #Service end date
            
            accounting_record.total_hours = service_dict[each_service]['total_hours'] #Service hours per week
            accounting_record.monday_hrs = service_dict[each_service]['monday_hours']
            accounting_record.tuesday_hrs = service_dict[each_service]['tuesday_hours']
            accounting_record.wednesday_hrs = service_dict[each_service]['wednesday_hours']
            accounting_record.thursday_hrs = service_dict[each_service]['thursday_hours']
            accounting_record.friday_hrs = service_dict[each_service]['friday_hours']
            accounting_record.saturday_hrs = service_dict[each_service]['saturday_hours']
            accounting_record.sunday_hrs = service_dict[each_service]['sunday_hours']
            
            accounting_record.month_1_hrs = service_dict[each_service]['month_1_hrs'] #Service hours in the 1st month
            accounting_record.month_2_hrs = service_dict[each_service]['month_2_hrs'] #Service hours in the 2nd month
            accounting_record.month_3_hrs = service_dict[each_service]['month_3_hrs'] #Service hours in the 3rd month
            accounting_record.month_4_hrs = service_dict[each_service]['month_4_hrs'] #Service hours in the 4th month
            accounting_record.month_5_hrs = service_dict[each_service]['month_5_hrs'] #Service hours in the 5th month
            accounting_record.month_6_hrs = service_dict[each_service]['month_6_hrs'] #Service hours in the 6th month


            #Add the non-VAT record to the database
            transaction.accounting_record.append(accounting_record)
            db.session.add(accounting_record)
            db.session.commit()

            #Calculate the discount to add the entry to the non-VAT record
            discount_per_unit = dict_all_payment[each_service]['original_price_per_unit'] - dict_all_payment[each_service]['final_price_per_unit']
            each_service_discount = dict_all_payment[each_service]['service_count'] * discount_per_unit
            total_discount += each_service_discount
        
            if each_service_discount > 0:
                #If the total discount > 0, we will create another entry of discount, with the name being 'ส่วนลด nonVAT'
                #For this case, we will repeat all of the processes as before
                accounting_record_discount = Accounting_record()
                accounting_record_discount.country = current_user.user_country
                accounting_record_discount.code_number = receipt_number
                accounting_record_discount.transaction_id = this_transaction_id
                accounting_record_discount.name = transaction.student_full_name
                accounting_record_discount.date_created = datetimefilter(datetime.datetime.utcnow(), return_string=False)
                
                if student_query is not None:
                    if student_query.name_th is None or student_query.name_th == 'NaN':
                        accounting_record_discount.name_th = ''
                    else:
                        accounting_record_discount.name_th = student_query.name_th
                    
                    if student_query.address is None or student_query.address == 'NaN':
                        accounting_record_discount.address = ''
                    else:
                        accounting_record_discount.address = student_query.address

                #Discount Part: Price Information Section
                accounting_record_discount.service = 'Discount: {}'.format(each_service)
                accounting_record_discount.service_category = service_dict[each_service]['category']
                accounting_record_discount.service_subcategory = service_dict[each_service]['subcategory']
                accounting_record_discount.payment_method = payment_method #Payment Method
                accounting_record_discount.payment_date = payment_date
                accounting_record_discount.payment_time = payment_time
                accounting_record_discount.card_machine = card_machine
                accounting_record_discount.card_issuer = card_issuer
                accounting_record_discount.amortization_start_date = service_dict[each_service]['start_date']  

                accounting_record_discount.total_service_count = my_round(dict_all_payment[each_service]['total_service_count'], 2)
                accounting_record_discount.original_price_per_unit = -my_round(dict_all_payment[each_service]['original_price_per_unit'] - dict_all_payment[each_service]['final_price_per_unit'], 2)
                accounting_record_discount.service_count = my_round(dict_all_payment[each_service]['service_count'], 2)
                accounting_record_discount.price_per_unit = -my_round(discount_per_unit, 2)

                each_vat_proportion = dict_all_payment[each_service]['vat_proportion']
                accounting_record_discount.total_non_vat_amount = -my_round(each_service_discount * (1-each_vat_proportion), 2)
                accounting_record_discount.tax_invoice_amount = -my_round(each_service_discount * each_vat_proportion * (1/(1+vat_rate)), 2)
                accounting_record_discount.vat_amount = -my_round(each_service_discount * each_vat_proportion * (vat_rate/(1+vat_rate)), 2)
                accounting_record_discount.total_vat_amount = accounting_record_discount.tax_invoice_amount + accounting_record_discount.vat_amount
                accounting_record_discount.total_amount = accounting_record_discount.total_non_vat_amount + accounting_record_discount.total_vat_amount

                #Discount Part: Amortization Section
                accounting_record_discount.amortization_type = service_dict[each_service]['amortization_type'] #Service amortization type
                accounting_record_discount.start_date = service_dict[each_service]['start_date'] #Service start date
                accounting_record_discount.end_date = service_dict[each_service]['end_date'] #Service end date
                
                accounting_record_discount.total_hours = service_dict[each_service]['total_hours'] #Service hours per week
                accounting_record_discount.monday_hrs = service_dict[each_service]['monday_hours']
                accounting_record_discount.tuesday_hrs = service_dict[each_service]['tuesday_hours']
                accounting_record_discount.wednesday_hrs = service_dict[each_service]['wednesday_hours']
                accounting_record_discount.thursday_hrs = service_dict[each_service]['thursday_hours']
                accounting_record_discount.friday_hrs = service_dict[each_service]['friday_hours']
                accounting_record_discount.saturday_hrs = service_dict[each_service]['saturday_hours']
                accounting_record_discount.sunday_hrs = service_dict[each_service]['sunday_hours']

                accounting_record_discount.month_1_hrs = service_dict[each_service]['month_1_hrs'] #Service hours in the 1st month
                accounting_record_discount.month_2_hrs = service_dict[each_service]['month_2_hrs'] #Service hours in the 2nd month
                accounting_record_discount.month_3_hrs = service_dict[each_service]['month_3_hrs'] #Service hours in the 3rd month
                accounting_record_discount.month_4_hrs = service_dict[each_service]['month_4_hrs'] #Service hours in the 4th month
                accounting_record_discount.month_5_hrs = service_dict[each_service]['month_5_hrs'] #Service hours in the 5th month
                accounting_record_discount.month_6_hrs = service_dict[each_service]['month_6_hrs'] #Service hours in the 6th month

                transaction.accounting_record.append(accounting_record_discount)
                db.session.add(accounting_record_discount)
                db.session.commit()


def save_transaction_changes(transaction, form, new=False, submit=True):
    #Process and save each transaction to the database
    #param transaction (sqlalchemy query object): transaction from app.models.Transaction
    #param new (boolean): a boolean indicating whether invoking this function is for adding a new transaction. If not, it means the program is editing the old transaction
    #param submit (boolean): a boolean indicating whether this function is for an actual submission. If not, it is only for previewing

    #Set vat_rate for the current_user's country
    vat_rate_query = VAT_info.query.filter_by(country=current_user.user_country).first()
    vat_rate = vat_rate_query.vat_rate
    #Set transaction's country
    transaction.country = current_user.user_country
    
    #User Part - record creating and updating usernames
    if new:
        transaction.create_user = current_user.username
        transaction.update_user = current_user.username
    else:
        transaction.update_user = current_user.username

    #Query and set transaction's student info
    transaction.student_full_name = form.student_full_name.data
    print('student_query')
    student_query = Student.query.filter_by(name = form.student_full_name.data, student_country=current_user.user_country).first_or_404()
    transaction.student_id = student_query.id
    if form.use_company_info_flag.data:
        transaction.use_company_info_flag = True
        transaction.company_name = form.client_company_name.data
        transaction.company_tax_id = form.client_tax_id.data
        transaction.company_address = form.client_address.data
    else:
        transaction.use_company_info_flag = False

    #Initialize lists of each service's final price, original service name from last transaction, and the recently edited service name from this transaction
    orig_service_name_list = [transaction.service_1_name, transaction.service_2_name, transaction.service_3_name, transaction.service_4_name, transaction.service_5_name, transaction.service_6_name]
    new_service_name_list = [form.service_1_name.data, form.service_2_name.data, form.service_3_name.data, form.service_4_name.data, form.service_5_name.data, form.service_6_name.data]
    service_dict = dict()
    
    #Price array & discount
    orig_price_list = [form.service_1_price.data, form.service_2_price.data, form.service_3_price.data, form.service_4_price.data, form.service_5_price.data, form.service_6_price.data]
    orig_count_list = [form.service_1_count.data, form.service_2_count.data, form.service_3_count.data, form.service_4_count.data, form.service_5_count.data, form.service_6_count.data]
    orig_price_array, orig_count_array = np.array(orig_price_list), np.array(orig_count_list)
    orig_discount_list = [form.service_1_discount_value.data, form.service_2_discount_value.data, form.service_3_discount_value.data, form.service_4_discount_value.data, form.service_5_discount_value.data, form.service_6_discount_value.data]
    weighted_discount_array = process_weighted_discount(orig_discount_list, orig_price_list, orig_count_list, form.overall_discount.data)
    final_price_array = orig_price_array * orig_count_array - weighted_discount_array
    
    new_service_list = list()
    new_final_price_list = list()

    #Refund Part
    refund_flag_list = [form.service_1_refund_flag.data, form.service_2_refund_flag.data, form.service_3_refund_flag.data, form.service_4_refund_flag.data, form.service_5_refund_flag.data, form.service_6_refund_flag.data]
    refund_amount_list = [form.service_1_refund_amount.data, form.service_2_refund_amount.data, form.service_3_refund_amount.data, form.service_4_refund_amount.data, form.service_5_refund_amount.data, form.service_6_refund_amount.data]

    #Service 1 Section
    #Query first service's information from the database
    service_1 = Service.query.filter_by(name=form.service_1_name.data, country=current_user.user_country).first_or_404()
    service_1_amortize_dict = fill_amortize_dict(form.service_1_amortization_type.data, form.service_1_start_date.data, form.service_1_end_date.data, form.service_1_total_hours.data, form.service_1_monday_hours.data, form.service_1_tuesday_hours.data, form.service_1_wednesday_hours.data, form.service_1_thursday_hours.data, form.service_1_friday_hours.data, form.service_1_saturday_hours.data, form.service_1_sunday_hours.data, form.service_1_month_1_hrs.data, form.service_1_month_2_hrs.data, form.service_1_month_3_hrs.data, form.service_1_month_4_hrs.data, form.service_1_month_5_hrs.data, form.service_1_month_6_hrs.data)
    service_dict = fill_service_info_to_dict(service_dict, form.service_1_name.data, form.service_1_teacher_name.data, form.service_1_office.data, service_1, service_1_amortize_dict)
    transaction.service_1_vat_value = my_round(service_1.vat_proportion * final_price_array[0], 2)
    
    #Save first service name, id, price per unit, count, discount value, final price ((price per unit - discount) * count), vat value, and note to the database
    if transaction.service_1_name == form.service_1_name.data:
        new_service_list.append(False)
    else:
        new_service_list.append(True)
    transaction.service_1_name = form.service_1_name.data
    transaction.service_1_price = form.service_1_price.data
    transaction.service_1_count = form.service_1_count.data
    transaction.service_1_discount_value = weighted_discount_array[0]
    if transaction.service_1_final_price == final_price_array[0]:
        new_final_price_list.append(False)
    else:
        new_final_price_list.append(True)
    transaction.service_1_final_price = final_price_array[0]
    transaction.service_1_note = form.service_1_note.data
    transaction.service_1_teacher_name = form.service_1_teacher_name.data
    transaction.service_1_office = form.service_1_office.data

    transaction.service_1_refund_flag = form.service_1_refund_flag.data
    transaction.service_1_refund_status = form.service_1_refund_status.data
    transaction.service_1_refund_amount = form.service_1_refund_amount.data
    transaction.service_1_refund_date = form.service_1_refund_date.data

    transaction.service_1_amortization_type = form.service_1_amortization_type.data
    transaction.service_1_start_date = form.service_1_start_date.data
    transaction.service_1_end_date = form.service_1_end_date.data
    
    transaction.service_1_total_hours = form.service_1_total_hours.data
    transaction.service_1_monday_hours = form.service_1_monday_hours.data
    transaction.service_1_tuesday_hours = form.service_1_tuesday_hours.data
    transaction.service_1_wednesday_hours = form.service_1_wednesday_hours.data
    transaction.service_1_thursday_hours = form.service_1_thursday_hours.data
    transaction.service_1_friday_hours = form.service_1_friday_hours.data
    transaction.service_1_saturday_hours = form.service_1_saturday_hours.data
    transaction.service_1_sunday_hours = form.service_1_sunday_hours.data

    transaction.service_1_month_1_hrs = form.service_1_month_1_hrs.data
    transaction.service_1_month_2_hrs = form.service_1_month_2_hrs.data
    transaction.service_1_month_3_hrs = form.service_1_month_3_hrs.data
    transaction.service_1_month_4_hrs = form.service_1_month_4_hrs.data
    transaction.service_1_month_5_hrs = form.service_1_month_5_hrs.data
    transaction.service_1_month_6_hrs = form.service_1_month_6_hrs.data
    

    #Service 2 Section
    if form.service_2_name.data is not None and form.service_2_name.data != '':
        #Check if the second service exists by checking the service name
        service_2 = Service.query.filter_by(name=form.service_2_name.data, country=current_user.user_country).first_or_404()
        service_2_amortize_dict = fill_amortize_dict(form.service_2_amortization_type.data, form.service_2_start_date.data, form.service_2_end_date.data, form.service_2_total_hours.data, form.service_2_monday_hours.data, form.service_2_tuesday_hours.data, form.service_2_wednesday_hours.data, form.service_2_thursday_hours.data, form.service_2_friday_hours.data, form.service_2_saturday_hours.data, form.service_2_sunday_hours.data, form.service_2_month_2_hrs.data, form.service_2_month_2_hrs.data, form.service_2_month_3_hrs.data, form.service_2_month_4_hrs.data, form.service_2_month_5_hrs.data, form.service_2_month_6_hrs.data)
        service_dict = fill_service_info_to_dict(service_dict, form.service_2_name.data, form.service_2_teacher_name.data, form.service_2_office.data, service_2, service_2_amortize_dict)
        transaction.service_2_vat_value = my_round(service_2.vat_proportion * final_price_array[1], 2)
        
    #Do the same for the second service. This will happen 4 more times for the remaining services too
    if transaction.service_2_name == form.service_2_name.data:
        new_service_list.append(False)
    else:
        new_service_list.append(True)
    transaction.service_2_name = form.service_2_name.data
    transaction.service_2_price = form.service_2_price.data
    transaction.service_2_count = form.service_2_count.data
    transaction.service_2_discount_value = weighted_discount_array[1]
    if transaction.service_2_final_price == final_price_array[1]:
        new_final_price_list.append(False)
    else:
        new_final_price_list.append(True)
    transaction.service_2_final_price = final_price_array[1]
    transaction.service_2_note = form.service_2_note.data
    transaction.service_2_teacher_name = form.service_2_teacher_name.data
    transaction.service_2_office = form.service_2_office.data

    transaction.service_2_refund_flag = form.service_2_refund_flag.data
    transaction.service_2_refund_status = form.service_2_refund_status.data
    transaction.service_2_refund_amount = form.service_2_refund_amount.data
    transaction.service_2_refund_date = form.service_2_refund_date.data

    transaction.service_2_amortization_type = form.service_2_amortization_type.data
    transaction.service_2_start_date = form.service_2_start_date.data
    transaction.service_2_end_date = form.service_2_end_date.data
    
    transaction.service_2_total_hours = form.service_2_total_hours.data
    transaction.service_2_monday_hours = form.service_2_monday_hours.data
    transaction.service_2_tuesday_hours = form.service_2_tuesday_hours.data
    transaction.service_2_wednesday_hours = form.service_2_wednesday_hours.data
    transaction.service_2_thursday_hours = form.service_2_thursday_hours.data
    transaction.service_2_friday_hours = form.service_2_friday_hours.data
    transaction.service_2_saturday_hours = form.service_2_saturday_hours.data
    transaction.service_2_sunday_hours = form.service_2_sunday_hours.data

    transaction.service_2_month_1_hrs = form.service_2_month_1_hrs.data
    transaction.service_2_month_2_hrs = form.service_2_month_2_hrs.data
    transaction.service_2_month_3_hrs = form.service_2_month_3_hrs.data
    transaction.service_2_month_4_hrs = form.service_2_month_4_hrs.data
    transaction.service_2_month_5_hrs = form.service_2_month_5_hrs.data
    transaction.service_2_month_6_hrs = form.service_2_month_6_hrs.data
        
    
    #Service 3 Section
    if form.service_3_name.data is not None and form.service_3_name.data != '':
        service_3 = Service.query.filter_by(name=form.service_3_name.data, country=current_user.user_country).first_or_404()

        service_3_amortize_dict = fill_amortize_dict(form.service_3_amortization_type.data, form.service_3_start_date.data, form.service_3_end_date.data, form.service_3_total_hours.data, form.service_3_monday_hours.data, form.service_3_tuesday_hours.data, form.service_3_wednesday_hours.data, form.service_3_thursday_hours.data, form.service_3_friday_hours.data, form.service_3_saturday_hours.data, form.service_3_sunday_hours.data, form.service_3_month_3_hrs.data, form.service_3_month_3_hrs.data, form.service_3_month_3_hrs.data, form.service_3_month_4_hrs.data, form.service_3_month_5_hrs.data, form.service_3_month_6_hrs.data)

        service_dict = fill_service_info_to_dict(service_dict, form.service_3_name.data, form.service_3_teacher_name.data, form.service_3_office.data, service_3, service_3_amortize_dict)
        transaction.service_3_vat_value = my_round(service_3.vat_proportion * final_price_array[2], 2)
        
    if transaction.service_3_name == form.service_3_name.data:
        new_service_list.append(False)
    else:
        new_service_list.append(True)
    transaction.service_3_name = form.service_3_name.data
    transaction.service_3_price = form.service_3_price.data
    transaction.service_3_count = form.service_3_count.data
    transaction.service_3_discount_value = weighted_discount_array[2]
    if transaction.service_3_final_price == final_price_array[2]:
        new_final_price_list.append(False)
    else:
        new_final_price_list.append(True)
    transaction.service_3_final_price = final_price_array[2]
    transaction.service_3_note = form.service_3_note.data
    transaction.service_3_teacher_name = form.service_3_teacher_name.data
    transaction.service_3_office = form.service_3_office.data

    transaction.service_3_refund_flag = form.service_3_refund_flag.data
    transaction.service_3_refund_status = form.service_3_refund_status.data
    transaction.service_3_refund_amount = form.service_3_refund_amount.data
    transaction.service_3_refund_date = form.service_3_refund_date.data

    transaction.service_3_amortization_type = form.service_3_amortization_type.data
    transaction.service_3_start_date = form.service_3_start_date.data
    transaction.service_3_end_date = form.service_3_end_date.data
    
    transaction.service_3_total_hours = form.service_3_total_hours.data
    transaction.service_3_monday_hours = form.service_3_monday_hours.data
    transaction.service_3_tuesday_hours = form.service_3_tuesday_hours.data
    transaction.service_3_wednesday_hours = form.service_3_wednesday_hours.data
    transaction.service_3_thursday_hours = form.service_3_thursday_hours.data
    transaction.service_3_friday_hours = form.service_3_friday_hours.data
    transaction.service_3_saturday_hours = form.service_3_saturday_hours.data
    transaction.service_3_sunday_hours = form.service_3_sunday_hours.data

    transaction.service_3_month_1_hrs = form.service_3_month_1_hrs.data
    transaction.service_3_month_2_hrs = form.service_3_month_2_hrs.data
    transaction.service_3_month_3_hrs = form.service_3_month_3_hrs.data
    transaction.service_3_month_4_hrs = form.service_3_month_4_hrs.data
    transaction.service_3_month_5_hrs = form.service_3_month_5_hrs.data
    transaction.service_3_month_6_hrs = form.service_3_month_6_hrs.data

    #Service 4 Section
    if form.service_4_name.data is not None and form.service_4_name.data != '':
        service_4 = Service.query.filter_by(name=form.service_4_name.data, country=current_user.user_country).first_or_404()

        service_4_amortize_dict = fill_amortize_dict(form.service_4_amortization_type.data, form.service_4_start_date.data, form.service_4_end_date.data, form.service_4_total_hours.data, form.service_4_monday_hours.data, form.service_4_tuesday_hours.data, form.service_4_wednesday_hours.data, form.service_4_thursday_hours.data, form.service_4_friday_hours.data, form.service_4_saturday_hours.data, form.service_4_sunday_hours.data, form.service_4_month_4_hrs.data, form.service_4_month_4_hrs.data, form.service_4_month_4_hrs.data, form.service_4_month_4_hrs.data, form.service_4_month_5_hrs.data, form.service_4_month_6_hrs.data)

        service_dict = fill_service_info_to_dict(service_dict, form.service_4_name.data, form.service_4_teacher_name.data, form.service_4_office.data, service_4, service_4_amortize_dict)
        transaction.service_4_vat_value = my_round(service_4.vat_proportion * final_price_array[3], 2)
        
    if transaction.service_4_name == form.service_4_name.data:
        new_service_list.append(False)
    else:
        new_service_list.append(True)
    transaction.service_4_name = form.service_4_name.data
    transaction.service_4_price = form.service_4_price.data
    transaction.service_4_count = form.service_4_count.data
    transaction.service_4_discount_value = weighted_discount_array[3]
    if transaction.service_4_final_price == final_price_array[3]:
        new_final_price_list.append(False)
    else:
        new_final_price_list.append(True)
    transaction.service_4_final_price = final_price_array[3]
    transaction.service_4_note = form.service_4_note.data
    transaction.service_4_teacher_name = form.service_4_teacher_name.data
    transaction.service_4_office = form.service_4_office.data

    transaction.service_4_refund_flag = form.service_4_refund_flag.data
    transaction.service_4_refund_status = form.service_4_refund_status.data
    transaction.service_4_refund_amount = form.service_4_refund_amount.data
    transaction.service_4_refund_date = form.service_4_refund_date.data

    transaction.service_4_amortization_type = form.service_4_amortization_type.data
    transaction.service_4_start_date = form.service_4_start_date.data
    transaction.service_4_end_date = form.service_4_end_date.data
    
    transaction.service_4_total_hours = form.service_4_total_hours.data
    transaction.service_4_monday_hours = form.service_4_monday_hours.data
    transaction.service_4_tuesday_hours = form.service_4_tuesday_hours.data
    transaction.service_4_wednesday_hours = form.service_4_wednesday_hours.data
    transaction.service_4_thursday_hours = form.service_4_thursday_hours.data
    transaction.service_4_friday_hours = form.service_4_friday_hours.data
    transaction.service_4_saturday_hours = form.service_4_saturday_hours.data
    transaction.service_4_sunday_hours = form.service_4_sunday_hours.data

    transaction.service_4_month_1_hrs = form.service_4_month_1_hrs.data
    transaction.service_4_month_2_hrs = form.service_4_month_2_hrs.data
    transaction.service_4_month_3_hrs = form.service_4_month_3_hrs.data
    transaction.service_4_month_4_hrs = form.service_4_month_4_hrs.data
    transaction.service_4_month_5_hrs = form.service_4_month_5_hrs.data
    transaction.service_4_month_6_hrs = form.service_4_month_6_hrs.data

    #Service 5 Section
    if form.service_5_name.data is not None and form.service_5_name.data != '':
        service_5 = Service.query.filter_by(name=form.service_5_name.data, country=current_user.user_country).first_or_404()

        service_5_amortize_dict = fill_amortize_dict(form.service_5_amortization_type.data, form.service_5_start_date.data, form.service_5_end_date.data, form.service_5_total_hours.data, form.service_5_monday_hours.data, form.service_5_tuesday_hours.data, form.service_5_wednesday_hours.data, form.service_5_thursday_hours.data, form.service_5_friday_hours.data, form.service_5_saturday_hours.data, form.service_5_sunday_hours.data, form.service_5_month_5_hrs.data, form.service_5_month_5_hrs.data, form.service_5_month_5_hrs.data, form.service_5_month_5_hrs.data, form.service_5_month_5_hrs.data, form.service_5_month_6_hrs.data)

        service_dict = fill_service_info_to_dict(service_dict, form.service_5_name.data, form.service_5_teacher_name.data, form.service_5_office.data, service_5, service_5_amortize_dict)
        transaction.service_5_vat_value = my_round(service_5.vat_proportion * final_price_array[4], 2)
        
    if transaction.service_5_name == form.service_5_name.data:
        new_service_list.append(False)
    else:
        new_service_list.append(True)
    transaction.service_5_name = form.service_5_name.data
    transaction.service_5_price = form.service_5_price.data
    transaction.service_5_count = form.service_5_count.data
    transaction.service_5_discount_value = weighted_discount_array[4]
    if transaction.service_5_final_price == final_price_array[4]:
        new_final_price_list.append(False)
    else:
        new_final_price_list.append(True)
    transaction.service_5_final_price = final_price_array[4]
    transaction.service_5_note = form.service_5_note.data
    transaction.service_5_teacher_name = form.service_5_teacher_name.data
    transaction.service_5_office = form.service_5_office.data

    transaction.service_5_refund_flag = form.service_5_refund_flag.data
    transaction.service_5_refund_status = form.service_5_refund_status.data
    transaction.service_5_refund_amount = form.service_5_refund_amount.data
    transaction.service_5_refund_date = form.service_5_refund_date.data

    transaction.service_5_amortization_type = form.service_5_amortization_type.data
    transaction.service_5_start_date = form.service_5_start_date.data
    transaction.service_5_end_date = form.service_5_end_date.data
    
    transaction.service_5_total_hours = form.service_5_total_hours.data
    transaction.service_5_monday_hours = form.service_5_monday_hours.data
    transaction.service_5_tuesday_hours = form.service_5_tuesday_hours.data
    transaction.service_5_wednesday_hours = form.service_5_wednesday_hours.data
    transaction.service_5_thursday_hours = form.service_5_thursday_hours.data
    transaction.service_5_friday_hours = form.service_5_friday_hours.data
    transaction.service_5_saturday_hours = form.service_5_saturday_hours.data
    transaction.service_5_sunday_hours = form.service_5_sunday_hours.data

    transaction.service_5_month_1_hrs = form.service_5_month_1_hrs.data
    transaction.service_5_month_2_hrs = form.service_5_month_2_hrs.data
    transaction.service_5_month_3_hrs = form.service_5_month_3_hrs.data
    transaction.service_5_month_4_hrs = form.service_5_month_4_hrs.data
    transaction.service_5_month_5_hrs = form.service_5_month_5_hrs.data
    transaction.service_5_month_6_hrs = form.service_5_month_6_hrs.data

    #Service 6 Section
    if form.service_6_name.data is not None and form.service_6_name.data != '':
        service_6 = Service.query.filter_by(name=form.service_6_name.data, country=current_user.user_country).first_or_404()

        service_6_amortize_dict = fill_amortize_dict(form.service_6_amortization_type.data, form.service_6_start_date.data, form.service_6_end_date.data, form.service_6_total_hours.data, form.service_6_monday_hours.data, form.service_6_tuesday_hours.data, form.service_6_wednesday_hours.data, form.service_6_thursday_hours.data, form.service_6_friday_hours.data, form.service_6_saturday_hours.data, form.service_6_sunday_hours.data, form.service_6_month_6_hrs.data, form.service_6_month_6_hrs.data, form.service_6_month_6_hrs.data, form.service_6_month_6_hrs.data, form.service_6_month_6_hrs.data, form.service_6_month_6_hrs.data)

        service_dict = fill_service_info_to_dict(service_dict, form.service_6_name.data, form.service_6_teacher_name.data, form.service_6_office.data, service_6, service_6_amortize_dict)
        transaction.service_6_vat_value = my_round(service_6.vat_proportion * final_price_array[5], 2)
        
    if transaction.service_6_name == form.service_6_name.data:
        new_service_list.append(False)
    else:
        new_service_list.append(True)
    transaction.service_6_name = form.service_6_name.data
    transaction.service_6_price = form.service_6_price.data
    transaction.service_6_count = form.service_6_count.data
    transaction.service_6_discount_value = weighted_discount_array[5]
    if transaction.service_6_final_price == final_price_array[5]:
        new_final_price_list.append(False)
    else:
        new_final_price_list.append(True)
    transaction.service_6_final_price = final_price_array[5]
    transaction.service_6_note = form.service_6_note.data
    transaction.service_6_teacher_name = form.service_6_teacher_name.data
    transaction.service_6_office = form.service_6_office.data

    transaction.service_6_refund_flag = form.service_6_refund_flag.data
    transaction.service_6_refund_status = form.service_6_refund_status.data
    transaction.service_6_refund_amount = form.service_6_refund_amount.data
    transaction.service_6_refund_date = form.service_6_refund_date.data

    transaction.service_6_amortization_type = form.service_6_amortization_type.data
    transaction.service_6_start_date = form.service_6_start_date.data
    transaction.service_6_end_date = form.service_6_end_date.data
    
    transaction.service_6_total_hours = form.service_6_total_hours.data
    transaction.service_6_monday_hours = form.service_6_monday_hours.data
    transaction.service_6_tuesday_hours = form.service_6_tuesday_hours.data
    transaction.service_6_wednesday_hours = form.service_6_wednesday_hours.data
    transaction.service_6_thursday_hours = form.service_6_thursday_hours.data
    transaction.service_6_friday_hours = form.service_6_friday_hours.data
    transaction.service_6_saturday_hours = form.service_6_saturday_hours.data
    transaction.service_6_sunday_hours = form.service_6_sunday_hours.data

    transaction.service_6_month_1_hrs = form.service_6_month_1_hrs.data
    transaction.service_6_month_2_hrs = form.service_6_month_2_hrs.data
    transaction.service_6_month_3_hrs = form.service_6_month_3_hrs.data
    transaction.service_6_month_4_hrs = form.service_6_month_4_hrs.data
    transaction.service_6_month_5_hrs = form.service_6_month_5_hrs.data
    transaction.service_6_month_6_hrs = form.service_6_month_6_hrs.data

    #The overall_discount will be an extra discount given to all of the services in the transaction
    transaction.overall_discount = 0.0
    #Due date for the payment is set here
    transaction.due_date = form.due_date.data
    #Payment method that the customer uses to pay for our services - may add more in the forms.py later
    transaction.payment_method = form.payment_method.data
    
    print('payment part')
    #Float value of the total payment after discount[s]
    total_payment_value = np.sum(fix_array_with_none(final_price_array))
    #List of VAT proportions for all services
    service_vat_proportion_list = find_service_vat_proportions(new_service_name_list)
    #Array of all VAT values from according to this time payment
    vat_value_array = calculate_vat_value_list(final_price_array, service_vat_proportion_list)
    print('VAT part')

    #The following checks if this total transaction value is different from last time value 
    if new:
        #If the transaction is new, the difference is 0
        payment_difference = 0.0
    else:
        #Else, calculate if there is any difference
        payment_difference = total_payment_value - transaction.total_value #used for the case when some services change relative to the prior value

    #We add one more special case here for the team's convenience.
    #If this_time_payment is 0.0, the generate_receipt_flag is True, and the transaction is submitted, we will set that the customer pays an amount equal to the total value after discount
    if submit and form.generate_receipt_flag.data and form.this_time_payment.data == 0.0 and form.credit_spending_amount.data == 0.0:
        this_time_credit_spending = 0.0
        
        if new:
            #If it is a new transaction, just set it equal to the total value after discount
            this_time_payment = total_payment_value
        else:
            #If not, set it to the remaining value + the new value added to the transaction
            this_time_payment = transaction.remaining_outstanding + payment_difference
    else:
        #If the condition is not met, just let this-time payment value = the value given in the form
        this_time_payment = float(form.this_time_payment.data)
        this_time_credit_spending = float(form.credit_spending_amount.data)
    print('past this time payment')
        
    if np.sum(refund_flag_list) == 0:
        #Calculate the transaction's remaining value, paid value, item counts, vat values, and the non-vat information from the given information
        array_remaining_value, array_paid_value, array_this_time_count, this_time_vat_value, dict_all_payment = optimize_transaction_vat(transaction, this_time_payment=this_time_payment, this_time_credit_spending=this_time_credit_spending, former_service_names=orig_service_name_list, discount_array=weighted_discount_array, new=new)
        print('pass optimize transaction vat')
        if submit:
            if form.generate_receipt_flag.data:
                #Update the unpaid values for all of the services
                for i in range(6):
                    actual_ind = i + 1
                    setattr(transaction, 'service_{}_unpaid_value'.format(actual_ind), array_remaining_value[i])
            else:
                if new:
                    for i in range(6):
                        actual_ind = i + 1
                        setattr(transaction, 'service_{}_unpaid_value'.format(actual_ind), final_price_array[i])
                else:
                    for i in range(6):
                        actual_ind = i + 1
                        if new_service_list[i] or new_final_price_list[i]:
                            setattr(transaction, 'service_{}_unpaid_value'.format(actual_ind), final_price_array[i])
    
    #Overall Information
    #Find the remaining outstanding after accounting for this time payment
    if submit:
        if new:
            if this_time_payment == 0:
                transaction.remaining_outstanding = total_payment_value
            else:
                if form.generate_receipt_flag.data:
                    if this_time_payment > 0:
                        if form.credit_spending_amount.data > 0:
                            transaction.remaining_outstanding = total_payment_value - this_time_payment - form.credit_spending_amount.data
                        else:
                            transaction.remaining_outstanding = total_payment_value - this_time_payment
                    elif form.credit_spending_amount.data > 0:
                        transaction.remaining_outstanding = total_payment_value - form.credit_spending_amount.data
                else:
                    transaction.remaining_outstanding = total_payment_value
        else:
            if form.generate_receipt_flag.data:
                transaction.remaining_outstanding += payment_difference - this_time_payment - form.credit_spending_amount.data
            else:
                transaction.remaining_outstanding += payment_difference

        if transaction.remaining_outstanding < 0:
            transaction.remaining_outstanding = 0
    
    #Calculate total transaction value and total vat value
    transaction.total_value = my_round(total_payment_value, 2)
    transaction.total_vat_value = np.sum(fix_array_with_none(vat_value_array)) * vat_rate
    #Transaction cancel, complete flags and if it is refunded, put in the refund_amount value
    transaction.cancel_flag = form.cancel_flag.data
    transaction.complete_flag = form.complete_flag.data
    #The whole transaction note
    transaction.note = form.note.data

    #Finding transaction id part
    if new:
        #If the transaction is new, find the latest transaction id
        latest_transaction = Transaction.query.order_by(-Transaction.id).first()
        if latest_transaction is None:
            #If None, it means that table doesn't have any entry
            this_transaction_id = 1
        else:
            #Otherwise, add a new id by adding 1 to the value of the latest id 
            this_transaction_id = latest_transaction.id + 1
    else:
        #If not new (editing), we set the same id as before
        this_transaction_id = transaction.id
    
    #Set the transaction status according to the given information
    #The first three conditions are for done transactions
    if submit:
        if form.cancel_flag.data == True:
            transaction.transaction_status = 'Cancelled'

        elif np.sum(refund_flag_list) > 0:
            transaction.transaction_status = 'Refunded'
            print('before_refund')
            save_refund_info(transaction, refund_flag_list, student_query)
            return None, None

        elif form.complete_flag.data == True:
            transaction.transaction_status = 'Completed'
            
        else:
            #The remaining are for different cases as the following
            if this_time_payment > 0:
                #First, if this time payment > 0, the status must be either invoice, or receipt, or completed
                if form.generate_receipt_flag.data:
                    #If the receipt is generated, then the status is completed when the remaining outstanding is 0. Otherwise, the status is receipt
                    if this_time_payment == total_payment_value or transaction.remaining_outstanding == 0.0:
                        transaction.transaction_status = 'Completed'
                        transaction.complete_flag = True
                    else:
                        transaction.transaction_status = 'Receipt'
                else:
                    #If a receipt is not generated, we will make the transaction status invoice
                    if new:
                        transaction.transaction_status = 'Invoice'
                    else:
                        if transaction.transaction_status != 'Receipt':
                            #This case holds when the transaction is edited after having already generated the first receipt
                            transaction.transaction_status = 'Invoice'
            
            elif form.credit_spending_amount.data > 0:
                if form.generate_receipt_flag.data:
                    #If the receipt is generated, then the status is completed when the remaining outstanding is 0. Otherwise, the status is receipt
                    if transaction.remaining_outstanding == 0.0:
                        transaction.transaction_status = 'Completed'
                        transaction.complete_flag = True
                    else:
                        transaction.transaction_status = 'Receipt'
            
            else:
                #If this time payment is equal to 0, we make the transaction status 'quotation'
                if new:
                    transaction.transaction_status = 'Quotation'
                else:
                    if transaction.transaction_status not in {'Invoice', 'Receipt'}:
                        #This case holds when the transaction is edited after having already generated the first receipt
                        transaction.transaction_status = 'Quotation'

    if transaction.cancel_flag and submit:
        #If we cancel the transaction and submit it, cancel this transaction and record it in the UserRecord table
        process_cancelled_transaction(this_transaction_id, student_query)
        activity = 'Transaction cancelled, student name {}, transaction id {}'.format(transaction.student_full_name, this_transaction_id)
        user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name=activity)
        db.session.add(user_record)
        db.session.commit()
        return None, None

    #Record the activity in the UserRecord table
    if submit:
        activity = 'Transaction added, student name {}, transaction id {}'.format(transaction.student_full_name, this_transaction_id)
    else:
        activity = 'Transaction previewed, student name {}, transaction id {}'.format(transaction.student_full_name, this_transaction_id)

    user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name=activity)
    db.session.add(user_record)

    #Instantiate the file name to prepare for previewing
    preview_filename = None
    vat_invoice_number = None
    
    #Document-generating part
    if submit:
        #Quotation Part
        if new:
            #If new, we will generate a new quotation document and save it to the database
            transaction.generate_quotation_flag = True
            quotation_number = create_QIR_numbers('Q')
            pdf_binary, pickle_binary = create_pdf_document(transaction, quotation_number, service_dict, dict_all_payment, 'quotation', credit_spending = form.credit_spending_amount.data)
            save_qir_numbers(transaction, this_transaction_id, quotation_number, pdf_binary, pickle_binary, actual_qir_flag=True)
        else:
            if payment_difference != 0 or check_all_same_service(orig_service_name_list, new_service_name_list):
                #If the services are different, we will generate a new document
                quotation_number = create_QIR_numbers('Q')
                pdf_binary, pickle_binary = create_pdf_document(transaction, quotation_number, service_dict, dict_all_payment, 'quotation', credit_spending = form.credit_spending_amount.data)
                save_qir_numbers(transaction, this_transaction_id, quotation_number, pdf_binary, pickle_binary, actual_qir_flag=True)
            
        #Invoice & Receipt Part
        if this_time_payment > 0 or this_time_credit_spending > 0:
            #If this time payment is greater than 0, we will generate an invoice document
            if form.generate_invoice_flag.data:
                non_vat_invoice_number = create_QIR_numbers('I')
                pdf_binary, pickle_binary = create_pdf_document(transaction, non_vat_invoice_number, service_dict, dict_all_payment, 'invoice', this_time_payment = this_time_payment, credit_spending = this_time_credit_spending)
                save_qir_numbers(transaction, this_transaction_id, non_vat_invoice_number, pdf_binary, pickle_binary, actual_qir_flag=True)

            if form.generate_receipt_flag.data:
                #If generate_receipt_flag is True, we will generate a receipt document
                receipt_number = create_QIR_numbers('R')
                pdf_binary, pickle_binary = create_pdf_document(transaction, receipt_number, service_dict, dict_all_payment, 'receipt', this_time_payment = this_time_payment, credit_spending = this_time_credit_spending)
                save_qir_numbers(transaction, this_transaction_id, receipt_number, pdf_binary, pickle_binary, actual_qir_flag=True)

                if this_time_vat_value > 0:
                    #If this_time_vat_value > 0, we will generate a vat invoice document
                    vat_invoice_number = create_QIR_numbers('T')
                    pdf_binary, pickle_binary = create_pdf_document(transaction, vat_invoice_number, service_dict, dict_all_payment, 'vat_invoice', calculated_count=array_this_time_count, credit_spending = this_time_credit_spending)
                    save_qir_numbers(transaction, this_transaction_id, vat_invoice_number, pdf_binary, pickle_binary, actual_qir_flag=True)
                

                #Add total values to each student's total value
                if student_query.total_value is None:
                    student_query.total_value = this_time_payment - np.sum(refund_amount_list)
                else:
                    student_query.total_value += this_time_payment - np.sum(refund_amount_list)
        
        if form.credit_spending_amount.data > 0 and form.generate_receipt_flag.data:
            student_query.credit_value -= form.credit_spending_amount.data
            student_query.total_value += form.credit_spending_amount.data 

    else:
        #This case holds for just previewing
        list_qir_codes = list()

        #Generate a new quotation document and save it to the database (for previewing)
        quotation_number = create_QIR_numbers('Q')
        list_qir_codes.append(quotation_number)
        pdf_binary, pickle_binary = create_pdf_document(transaction, quotation_number, service_dict, dict_all_payment, 'quotation', credit_spending = form.credit_spending_amount.data)
        save_qir_numbers(transaction, this_transaction_id, quotation_number, pdf_binary, pickle_binary, actual_qir_flag=False)

        if this_time_payment > 0 or this_time_credit_spending > 0:
            #Generate a new invoice document and save it to the database (for previewing)
            non_vat_invoice_number = create_QIR_numbers('I')
            list_qir_codes.append(non_vat_invoice_number)
            pdf_binary, pickle_binary = create_pdf_document(transaction, non_vat_invoice_number, service_dict, dict_all_payment, 'invoice', this_time_payment = this_time_payment, credit_spending = this_time_credit_spending)
            save_qir_numbers(transaction, this_transaction_id, non_vat_invoice_number, pdf_binary, pickle_binary, actual_qir_flag=False)

            if form.generate_receipt_flag.data:
                #Generate a new receipt document and save it to the database (for previewing)
                receipt_number = create_QIR_numbers('R')
                list_qir_codes.append(receipt_number)
                pdf_binary, pickle_binary = create_pdf_document(transaction, receipt_number, service_dict, dict_all_payment, 'receipt', this_time_payment = this_time_payment, credit_spending = this_time_credit_spending)
                save_qir_numbers(transaction, this_transaction_id, receipt_number, pdf_binary, pickle_binary, actual_qir_flag=False)

                if this_time_vat_value > 0:
                    #Generate a new tax invoice document and save it to the database (for previewing)
                    vat_invoice_number = create_QIR_numbers('T')
                    list_qir_codes.append(vat_invoice_number)
                    pdf_binary, pickle_binary = create_pdf_document(transaction, vat_invoice_number, service_dict, dict_all_payment, 'vat_invoice', calculated_count=array_this_time_count, credit_spending = this_time_credit_spending)
                    save_qir_numbers(transaction, this_transaction_id, vat_invoice_number, pdf_binary, pickle_binary, actual_qir_flag=False)
                
        #Combine all of the codes altogether in a new file
        preview_filename, preview_pdf_binary = combine_pdfs(list_qir_codes)
        if preview_pdf_binary is not None:
            save_qir_numbers(transaction, this_transaction_id, preview_filename, preview_pdf_binary, pickle_binary=None, actual_qir_flag=False)

    if new and submit:
        #If submit a new transaction, add it to the database
        db.session.add(transaction)
    
    if submit and (this_time_payment > 0 or form.credit_spending_amount.data > 0) and form.generate_receipt_flag.data:
        #Save accounting records and add all of the sales records in the database
        save_accounting_record(transaction, this_transaction_id, dict_all_payment, receipt_number, vat_invoice_number, form.payment_method.data, form.payment_date.data, form.payment_time.data, form.card_machine.data, form.card_issuer.data, service_dict)
        add_sale_record(this_transaction_id, student_query, receipt_number, form.payment_method.data, form.card_machine.data, form.payment_date.data, form.payment_time.data, new_service_name_list, array_paid_value, array_this_time_count, service_dict)

    if submit:
        #This case holds for previewing, just commit for all of the edits
        db.session.commit()

    #Return two variables - preview filename and this transaction's id
    return preview_filename, this_transaction_id