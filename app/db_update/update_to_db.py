import pickle
import pandas as pd
import numpy as np
from app import db
from app.models import Student, TestScore, QIR_numbers_preview
from flask import current_app, app
from sqlalchemy import func
import datetime

import sys
import os

from app.db_update.load_from_streak import load_from_streak
from app.db_update.universal_id_update import update_streak_data

from InvoiceGenerator.api import Client
import gc


#Set up the dictionary for Thailand's Streak information
streak_info_dict_thailand = dict()
streak_info_dict_thailand['BASE_URL'] = "https://www.streak.com/api/v1/"
streak_info_dict_thailand['STUDENT_PIPELINE_KEY'] = 'agxzfm1haWxmb29nYWVyOAsSDE9yZ2FuaXphdGlvbiIRcmFwaXNhdEBnbWFpbC5jb20MCxIIV29ya2Zsb3cYgICAgICumQoM'
streak_info_dict_thailand['SALES_PIPELINE_KEY'] = 'agxzfm1haWxmb29nYWVyPgsSDE9yZ2FuaXphdGlvbiIXamlyYXBhdC50dGFuYUBnbWFpbC5jb20MCxIIV29ya2Zsb3cYgICAgIDyiAoM'
streak_info_dict_thailand['STUDENT_BOX_URL'] = streak_info_dict_thailand['BASE_URL'] + "pipelines/" + streak_info_dict_thailand['STUDENT_PIPELINE_KEY'] + "/boxes"
streak_info_dict_thailand['STUDENT_PIPELINE_URL'] = streak_info_dict_thailand['BASE_URL'] + "pipelines/" + streak_info_dict_thailand['STUDENT_PIPELINE_KEY']
streak_info_dict_thailand['SALES_BOX_URL'] = streak_info_dict_thailand['BASE_URL'] + "pipelines/" + streak_info_dict_thailand['SALES_PIPELINE_KEY'] + "/boxes"
streak_info_dict_thailand['SALES_PIPELINE_URL'] = streak_info_dict_thailand['BASE_URL'] + "pipelines/" + streak_info_dict_thailand['SALES_PIPELINE_KEY']
streak_info_dict_thailand['HEADERS'] = {'content-type': 'application/json'}
streak_info_dict_thailand['STREAK_AUTH_KEY'] = 'a29b8cff6bc944ee8b409c00b4ef8a4d'
streak_info_dict_thailand['FIELD_KEYNAME'] = 'fields'

streak_info_dict_thailand['universal_id_colname'] = 'universal_id'
streak_info_dict_thailand['student_country'] = 'Thailand'


def fill_student_id(df_in, student_name_colname, output_colname):
    """Fill student id in the input data frame

    Args:
        df_in (pd.DataFrame): input student data frame
        student_name_colname (str): student column name
        output_colname (str): output column name

    Returns:
        pd.DataFrame: output data frame with ids filled in the data frame
    """
    #Create an output list and create a new column in the input data frame using the output list

    list_output = list()
    for each_name in df_in[student_name_colname].iteritems():
        found_student = Student.query.filter_by(name = each_name[1]).first()
        if found_student is None:
            list_output.append(None)
        else:
            list_output.append(found_student.id)
    
    df_in[output_colname] = list_output
    return df_in

def check_student_already_exists(df_in, student_name_colname):
    """Check each student already exists in the table and return a list of student names that are not in the database yet

    Args:
        df_in (pd.DataFrame): An input data frame of students' information
        student_name_colname (str): the student name's column name

    Returns:
        list: list of non-existing names
    """
    list_non_existing = list()
    for each_row in df_in[student_name_colname].iteritems():
        found_obj = Student.query.filter_by(name=each_row[1]).first()
        if found_obj is None:
            list_non_existing.append(each_row[0])

    return list_non_existing

def upload_new_student_info(excel_file, target_table_name, drop_colname_list = ['previous_scores'], add_student_country = True):
    """Upload new students' information into the database

    Args:
        excel_file (str/pd.DataFrame): directory of the student excel file or the student data frame object to be read as reference for updating the students' information
        target_table_name (str): target table name to be updated
        drop_colname_list (list, optional): list of column names to be dropped from our program. Defaults to ['previous_scores'].
        add_student_country (bool, optional): A flag telling the program whether to add another column about the student's country. Defaults to True.
    """
    assert isinstance(excel_file, str) or isinstance(excel_file, pd.DataFrame)
    
    if isinstance(excel_file, str):
        df = pd.read_excel(excel_file, index_col=None)
    else:
        df = excel_file

    #Drop the specified column
    df = df.drop(drop_colname_list, axis=1)

    #Check for the case when the student table is empty. If so, we will assign all ids to the table using a range of values
    student_query = Student.query.first()
    if student_query is None:
        if add_student_country:
            df['student_country'] = 'Thailand'
            num_students = df.shape[0]
            df.loc[:, 'id'] = np.arange(0, num_students)
            print('Process DF', file = sys.stderr)
            df.to_sql(target_table_name, con = db.engine, index=False, if_exists = 'append')
            print('Done with Process DF', file = sys.stderr)
    else:
        #Otherwise, we will add ids to just new rows (checked to be new by finding if names already exist in the name set from the original database)
        existing_student_query = Student.query.all()
        existing_name_set = set()
        if len(existing_student_query) > 1:
            for each_student in existing_student_query:
                existing_name_set.add(each_student.name)
        else:
            existing_name_set.add(existing_student_query.name)
        new_df = df[~df['name'].isin(existing_name_set)]
        new_df['credit_value'] = 0
        
        #Add new ids to the new rows and upload the rows to the SQL
        latest_student_id = db.session.query(func.max(Student.id)).scalar()
        num_new_students = new_df.shape[0]
        new_df.loc[:,'id'] = np.arange(latest_student_id + 1, latest_student_id + 1 + num_new_students)
        print('Process DF', file = sys.stderr)
        new_df.to_sql(target_table_name, con = db.engine, index=False, if_exists = 'append')
        print('Done with Process DF', file = sys.stderr)
    
    db.session.commit()
    #Collect the garbage from the operations using the garbage collector package
    gc.collect()

def add_new_test_score(excel_file, target_table_name):
    """Add new test scores into the database

    Args:
        excel_file (str/pd.DataFrame): the directory of the test score excel file or the pd.DataFrame of the test score data frame
        target_table_name (str): target test score data frame name
    """
    if isinstance(excel_file, str):
        df = pd.read_excel(excel_file, index_col=None)
    elif isinstance(excel_file, pd.DataFrame):
        df = excel_file

    #Add rwos of data that still don't exist in the database by looking up from the exam_compare_code column
    df = fill_student_id(df, 'name', 'student_id')
    ind_include_list = list()

    for ind, row in df.iterrows():
        each_query = TestScore.query.filter_by(exam_compare_code=row['exam_compare_code']).first()
        if each_query is None:
            ind_include_list.append(ind)

    #Filter only the data frame with the indices matching the ind_include_list and add the data frame to the database
    included_df = df.loc[ind_include_list,:]

    included_df.to_sql(target_table_name, con = db.engine, index=False, if_exists = 'append')
    db.session.commit()

def table_exists(name):
    """Check if the table exists by looking at the table name

    Args:
        name (str): table name

    Returns:
        boolean: Boolean, which is true if the the table already exists in the database
    """
    ret = db.engine.dialect.has_table(db.engine, name)
    return ret

def update_existing_rows(df_in, target_table_name, temp_table_name = 'temptable', exempt_set = {}):
    """Update the existing rows in the student table in the database

    Args:
        df_in (pd.DataFrame): student data frame
        target_table_name (str): Target student table name
        temp_table_name (str, optional): Temporary table's name. Defaults to 'temptable'.
        exempt_set (set, optional): A set of columns to be exempted from updating. Defaults to {}.

    Returns:
        list: list of ids that have different information from before
    """
    #Add the temporary table to the database
    df_in.to_sql(temp_table_name, con = db.engine, if_exists='replace', schema='public')

    #Prepare the SQL statement for checking changes in the database
    num_cols = len(df_in.columns)
    temp_sql_check_any_difference = 'SELECT f.universal_id FROM {} AS f INNER JOIN {} AS t ON f.universal_id = t.universal_id WHERE'.format(target_table_name, temp_table_name)
    #Go over all columns and add more statements to the original statement
    for each_ind, each_col in enumerate(df_in.columns):
        if each_col not in exempt_set:
            temp_sql_check_any_difference += ' f.{} != t.{}'.format(each_col, each_col)
            
            if each_ind < num_cols - 1:
                temp_sql_check_any_difference += ' OR'

    #Handle the case that the statement ends with OR without having any statement following it
    if temp_sql_check_any_difference[-3:] == ' OR':
        temp_sql_check_any_difference = temp_sql_check_any_difference[:-3]
    
    #Create the SQL statement for updating the target table in the database
    temp_sql_target = 'UPDATE {} AS f'.format(target_table_name)
    temp_sql_column_1 = 'SET {} = t.{}'
    temp_sql_column_2 = '{} = t.{}'
    temp_sql_from_where = 'FROM {} AS t WHERE f.universal_id = t.universal_id'.format(temp_table_name)

    #Set the column part for the SQL statement
    all_sql_columns = ''
    
    each_ind_include = 0 #Set the variable for the index of each column in the data table

    #Go over each column in the data table and add the new columns to the output SQL statement
    for each_ind, each_col in enumerate(df_in.columns):
        if each_col not in exempt_set:
            if each_ind_include == 0:
                all_sql_columns += temp_sql_column_1.format(each_col,each_col)
            else:
                all_sql_columns += temp_sql_column_2.format(each_col,each_col)
            
            if each_ind < num_cols - 1:
                all_sql_columns += ','
            all_sql_columns += '\n'
            
            each_ind_include += 1
    
    #Handle the case when the last value in the all_sql_columns is a comma
    if all_sql_columns[-2:] == ',\n':
        all_sql_columns = all_sql_columns[:-2] + '\n'
                
    #Combine all parts of the SQL statement altogether in a variable final_sql_command
    final_sql_command = temp_sql_target + '\n' + all_sql_columns + temp_sql_from_where

    #If the temp table exists, execute the SQL statement
    if table_exists(temp_table_name):
        with db.engine.begin() as conn:
            res_any_diff = conn.execute(temp_sql_check_any_difference)
            list_id_difference = res_any_diff.fetchall()

            #Check if the number of different rows is greater than 0. This means we need to fix the different rows
            if len(list_id_difference) > 0:
                list_id_difference = [each_tuple[0] for each_tuple in list_id_difference]
                conn.execute(final_sql_command)
    else:
        list_id_difference = []

    return list_id_difference
    
def cast_for_null(df_in, col_name):
    """Replace the null values as -1 and change the data type to integer

    Args:
        df_in (pd.DataFrame): Input data frame
        col_name (str): String of target column name 

    Returns:
        pd.DataFrame: data frame of the output
    """
    df_in.loc[:,col_name] = df_in.loc[:,col_name].replace({np.nan: -1})
    df_in.loc[:,col_name] = df_in.loc[:,col_name].replace({'': -1})
    df_in.loc[:,col_name] = df_in.loc[:,col_name].replace({'NaN': -1})
    df_in.loc[:,col_name] = df_in.loc[:,col_name].astype(int)
    return df_in

def append_test_score():
    """
    Append test scores to each student's row in the database
    """
    all_students = Student.query.all()
    for each_student in all_students:
        #Go over all students in the database and query test scores related to the student
        temp_query = TestScore.query.filter_by(student_id = each_student.id).all()
        if temp_query is not None:
            for each_test_score_1 in temp_query:
                replace_flag = True
                #Go over all test scores in each student's test score relationship, and find if any test score matches the input test score by finding if the exam_compare_code is the identical to the checking value
                for each_test_score_2 in each_student.test_scores:
                    if each_test_score_1.exam_compare_code == each_test_score_2.exam_compare_code:
                        replace_flag = False
                if replace_flag:
                    each_student.test_scores.append(each_test_score_1)

    db.session.commit()
    gc.collect()

def update_recent_document(diff_id_list):
    """Update documents that have any changes

    Args:
        diff_id_list (list): list of student's universal id that has different column values
    """
    for each_id in diff_id_list:
        #Go over each id from the ids with different column values
        all_diff_students = Student.query.filter_by(universal_id = each_id).all()
        for each_student in all_diff_students:
            #Check if each student has any transaction
            if each_student.transactions:
                #Go over each transaction in the relationships and check if there exists any document
                for each_transaction in each_student.transactions:
                    if each_transaction.document_number is not None:
                        for each_qir_obj in each_transaction.document_number:
                            #Use the invoice's pickle binary from each qir object
                            if each_qir_obj.pickle_binary:
                                #Change the invoice's client information
                                invoice = pickle.loads(each_qir_obj.pickle_binary)
                                new_client_obj = Client(each_student.name, address=each_student.address)
                                invoice.client = new_client_obj
                                
                                #Generate the pdf's binary and assign the new binary to the database
                                if each_qir_obj.code_type == 'T':
                                    from InvoiceGenerator.pdf_vat import VatInvoice
                                    pdf = VatInvoice(invoice)
                                else:
                                    from InvoiceGenerator.pdf import SimpleInvoice
                                    pdf = SimpleInvoice(invoice)
                                pdf_binary = pdf.gen()
                                each_qir_obj.pdf_binary = pdf_binary
    db.session.commit()

def update_and_add_streak_info(app):
    """Update and add new information from Streak to the database

    Args:
        app (Flask app): Flask app
    """
    with app.app_context():
        #Update ids and info in the student pipeline
        streak_id_student_updater = update_streak_data(streak_info_dict_thailand['BASE_URL'], streak_info_dict_thailand['STREAK_AUTH_KEY'], streak_info_dict_thailand['STUDENT_PIPELINE_KEY'])
        streak_id_student_updater.retrieve_student_boxes()
        student_max_id = streak_id_student_updater.find_pipeline_max_id(streak_info_dict_thailand['universal_id_colname'])
        
        #Update ids and info in the sales pipeline
        streak_id_sales_updater = update_streak_data(streak_info_dict_thailand['BASE_URL'], streak_info_dict_thailand['STREAK_AUTH_KEY'], streak_info_dict_thailand['SALES_PIPELINE_KEY'])
        streak_id_sales_updater.retrieve_student_boxes()
        sales_max_id = streak_id_sales_updater.find_pipeline_max_id(streak_info_dict_thailand['universal_id_colname'])

        #Run updates on adding new ids on the sales pipeline and the student pipeline
        country_max_id = np.max([student_max_id, sales_max_id])
        streak_id_student_updater.run_main(streak_info_dict_thailand['universal_id_colname'], country_max_id)
        streak_id_sales_updater.run_main(streak_info_dict_thailand['universal_id_colname'], country_max_id + streak_id_student_updater.id_added_num)

        del streak_id_student_updater, streak_id_sales_updater, country_max_id #Delete the updaters and the max id to free up memory
        print('Done with ID updates', file = sys.stderr)

        #Create student info and test score info from the student pipeline
        streak_student_loader = load_from_streak(streak_info_dict_thailand['STUDENT_BOX_URL'], streak_info_dict_thailand['STUDENT_PIPELINE_URL'], streak_info_dict_thailand['HEADERS'], streak_info_dict_thailand['STREAK_AUTH_KEY'], streak_info_dict_thailand['FIELD_KEYNAME'])
        streak_student_loader.create_student_df(streak_info_dict_thailand['student_country'], 'student_country')
        streak_student_loader.create_test_score_df()

        #Create student info from the sales pipeline
        streak_sales_loader = load_from_streak(streak_info_dict_thailand['SALES_BOX_URL'], streak_info_dict_thailand['SALES_PIPELINE_URL'], streak_info_dict_thailand['HEADERS'], streak_info_dict_thailand['STREAK_AUTH_KEY'], streak_info_dict_thailand['FIELD_KEYNAME'])
        streak_sales_loader.create_student_df(streak_info_dict_thailand['student_country'], 'student_country')

        print('Done with Streak', file = sys.stderr)
        #Concatenate the student data frame with the sales data frame
        student_df = pd.concat([streak_student_loader.student_df, streak_sales_loader.student_df], axis = 0)
        test_score_df = streak_student_loader.test_score_df

        #Delete the streak loader to optimize the memory
        del streak_student_loader, streak_sales_loader #Delete the loaders to free up memory

        print('Done with loading Data Frames', file = sys.stderr)
        #Handle null values in the student_df
        student_df = cast_for_null(student_df, 'graduate_year')
        
        #Update all information in all rows when the student table isn't empty
        if Student.query.first() is not None:
            diff_id_list = update_existing_rows(student_df, target_table_name='student', temp_table_name = 'temptable', exempt_set={'id', 'previous_scores'})
            print('Done with updating existing rows')
            if len(diff_id_list) > 0:
                update_recent_document(diff_id_list)
            del diff_id_list

        #Upload new student information and add new test scores
        upload_new_student_info(student_df, target_table_name='student')
        print('Done with upload_new_student_info', file = sys.stderr)
        add_new_test_score(test_score_df, target_table_name='test_score')
        print('Done with add_new_test_score', file = sys.stderr)

        append_test_score()

        del student_df, test_score_df
        print('SQL Update Done!', file = sys.stderr)
        db.session.close()
        gc.collect()

def delete_preview_files():
    #Delete old documents for preview that are older than the given threshold (now set to 1 day before)
    threshold = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    old_preview_files = db.session.query(QIR_numbers_preview).filter(QIR_numbers_preview.date_created < threshold).all()
    if old_preview_files is not None:
        for each_qir_preview in old_preview_files:
            db.session.delete(each_qir_preview)
            db.session.commit()
