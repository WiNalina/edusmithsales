from __future__ import print_function
from os import name

from app import db
from flask import render_template, flash, redirect, request, \
    jsonify, send_file, abort, make_response, url_for, session
from app.main.forms import ServiceForm_global, ServiceForm_lookup, StudentForm_lookup, TeacherForm_lookup, TeacherForm_global, \
    EmptyForm, TransactionForm, Document_lookup, Amortize_lookup, \
    OfficeForm, OfficeForm_lookup, AmortizeEditForm, MachineForm_global, MachineForm_lookup, CreditTransferForm
from flask_login import current_user, login_required
from decimal import *
from app.models import User, UserRecord, Permission, Transaction, Accounting_record, TestScore, Service, \
    Student, Teacher, QIR_numbers, QIR_numbers_preview, Office, Card_machine
from app.main import bp
from app.main.transaction_process import save_transaction_changes
from app.main.util import convert_local_to_utc_time, retrieve_service_dict, generate_zip_file
from sqlalchemy import desc

from app.main.amortize_process import process_and_download_accounting_query, fill_amortization_form, \
    save_amortization_record, fill_amortization_slots

from app.main.refund_and_credit import save_credit_transfer, process_and_download_refund_query

import datetime
import io

import pandas as pd

import logging

logging.basicConfig(level = logging.DEBUG)

@bp.before_request
def before_request():
    session.permanent = True
    if current_user.is_authenticated:
        current_user.last_seen = datetime.datetime.utcnow()
        db.session.commit()

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    #Index page for the website
    #If the user has a permission to change service information, the index page will show the two related links too
    download_accounting_permission = current_user.can(Permission.ACCOUNTING_ACCESS)
    change_service_permission = current_user.can(Permission.CHANGE_SERVICE_INFORMATION)
    basic_access_permission = current_user.can(Permission.BASIC_ACCESS)

    if current_user.has_basic_view:
        return render_template('index.html', title='Home Page', download_accounting_permission = download_accounting_permission, 
        basic_access_permission = basic_access_permission, change_service_permission = change_service_permission)
    else:    
        return render_template('index.html', title='Home Page', download_accounting_permission = download_accounting_permission, 
        basic_access_permission = basic_access_permission, change_service_permission = change_service_permission)

@bp.route('/user/<username>')
@login_required
def user(username):
    if current_user.has_basic_view:
        #User page containing the transactions made by each user
        #param username (str): a username string 

        #Query each user's transactions ordered by latest updated dates
        user = User.query.filter_by(username=username).first_or_404()
        transactions = user.transactions.order_by(desc('latest_timestamp'))
        form = EmptyForm() 
        return render_template('user.html', user=user, transactions=transactions,
                                form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/local_transactions')
@login_required
def local_transactions():
    if current_user.has_basic_view:
        #Transaction page filtered for all transactions made by clients in current user's country
        #Query all transactions in each country ordered by latest updated dates
        transactions = Transaction.query.filter(Transaction.country == current_user.user_country).order_by(desc('latest_timestamp'))
        form = EmptyForm() 
        return render_template('transaction/transaction_table.html', transactions=transactions,
                                form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/global_transactions')
@login_required
def global_transactions():
    if current_user.has_basic_view:
        #Transaction page filtered for all transactions made by clients in all countries
        #Query all transactions in all countries ordered by latest updated dates
        transactions = Transaction.query.order_by(desc('latest_timestamp'))
        form = EmptyForm() 
        return render_template('transaction/transaction_table.html', transactions=transactions,
                                form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/students_local', methods = ['GET', 'POST'])
@login_required
def students_local():
    if current_user.has_basic_view:
        #JSON page containing a dictionary of all students' information in the same country as the logged in user
        student_res = Student.query.filter_by(student_country=current_user.user_country)
        list_students = list()
        list_key_student_info = ['name', 'company_name', 'company_tax_id', 'company_address', 'credit_value']

        for r in student_res:
            temp_dict_display = dict()
            temp_dict = r.as_dict()
            for each_key in list_key_student_info:
                if each_key in temp_dict:
                    temp_dict_display[each_key] = temp_dict[each_key]
                else:
                    temp_dict_display[each_key] = ''
            list_students.append(temp_dict_display)
        
        return jsonify(list_students)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/local_student_lookup', methods = ['GET', 'POST'])
@login_required
def local_student_lookup():
    if current_user.has_basic_view:
        #A lookup page used to query a local student by name
        form = StudentForm_lookup()

        if form.validate_on_submit():
            #If found, redirect to the student's page
            student = Student.query.filter_by(name=form.name.data).first_or_404()
            student_link = '/student/' + str(student.id)

            return redirect(student_link)

        return render_template('student/student_lookup.html', form=form, title='Student Lookup')
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/teachers_local', methods = ['GET', 'POST'])
@login_required
def teachers_local():
    if current_user.has_basic_view:
        #JSON page containing a dictionary of all students' information in the same country as the logged in user
        teacher_res = Teacher.query.filter_by(country=current_user.user_country)
        list_teachers = list()
        list_teacher_info = ['name']

        for r in teacher_res:
            temp_dict_display = dict()
            temp_dict = r.as_dict()
            for each_key in list_teacher_info:
                if each_key in temp_dict:
                    temp_dict_display[each_key] = temp_dict[each_key]
                else:
                    temp_dict_display[each_key] = ''
            list_teachers.append(temp_dict_display)
        
        return jsonify(list_teachers)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/teacher_lookup', methods = ['GET', 'POST'])
@login_required
def teacher_lookup():
    """ A page for looking up for services with the service lookup form

    Returns:
        Flask redirect page: Service lookup page
    """
    if current_user.has_basic_view:
        form = TeacherForm_lookup()

        if form.validate_on_submit():
            teacher = Teacher.query.filter_by(name=form.name.data).first_or_404()
            teacher_link = '/teacher/' + teacher.name

            return redirect(teacher_link)

        return render_template('teacher/teacher_lookup.html', form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

def save_teacher_changes(teacher, form, new=False):
    """ Save service changes to the database

    Args:
        service (SQLAlchemy query object): Service SQLAlchemy object  
        form (Flask form): Input Flask form for editing services
        new (bool, optional): True if it is for adding services. Otherwise, False for editing services. Defaults to False.
    """
    if current_user.has_basic_view:
        #Teacher category and subcategory
        teacher.name = form.name.data
        teacher.country = form.country.data
        if new:
            #If new, add the service to the database and prepare for the user record of adding a new service
            db.session.add(teacher)
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='add teacher {}, for country {}'.format(form.name.data, form.country.data))
        else:
            #Prepare for the user record of editing a new service
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='edit teacher {}, for country {}'.format(form.name.data, form.country.data))
        #Add a user record
        db.session.add(user_record)
        db.session.commit()
        
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/add_teacher_global', methods=['GET', 'POST'])
@login_required
def add_teacher_global():
    """Add a new teacher for the global level

    Returns:
        Flask render_template page: The page of teacher adding form
    """
    #First, check if the current user has the permission to change service information
    if current_user.can_change_service_info:
        #If the user can change service information, proceed to the next steps
        form = TeacherForm_global()
        
        if form.validate_on_submit():
            teacher = Teacher()
            
            save_teacher_changes(teacher, form, new = True)
            flash('Congratulations, you have already added a new teacher!')

        return render_template('teacher/teacher.html', title = 'Teacher', action = "Add", form = form)
    else:
        abort(403)

@bp.route('/teacher/<teacher_name>', methods = ['GET', 'POST'])
@login_required
def edit_teacher(teacher_name):
    """Edit service information's according to the given id

    Args:
        service_id (int): Target service's id

    Returns:
        Flask render_template: form for editing services
    """
    if current_user.can_change_service_info:
        #Check if the current user has the permission to change service information
        #If so, query the target service's information and find all of the categories and subcategories based on the given input
        teacher = Teacher.query.filter_by(name=teacher_name).first_or_404()
        form = TeacherForm_global(obj=teacher)

        if form.validate_on_submit():
            save_teacher_changes(teacher, form)
            flash('Congratulations, you have already edited the teacher!')
            
        return render_template('teacher/teacher.html', title = 'Teacher', action = "Edit", form = form)
    else:
        abort(403)

@bp.route('/student/<id>')
@login_required
def student(id):
    #A student page containing all prior transactions and test scores
    #param id (int): a student id
    if current_user.has_basic_view:
        #Query student information, transactions, and test scores
        student = Student.query.filter_by(id=id).first_or_404()
        #Order the queries by latest transaction dates and exam dates
        transactions = student.transactions.order_by(Transaction.latest_timestamp.desc())
        test_scores = student.test_scores.order_by(TestScore.exam_date.desc())
        form = EmptyForm()
        return render_template('student/student_profile.html', student=student, transactions=transactions,
                            test_scores = test_scores, form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/transaction/<int:transaction_id>', methods = ['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    """Edit the existing transaction using the given transaction id

    Args:
        transaction_id ([int]): the transaction id

    Returns:
        [flask render_template]: Show the transaction page with all of the information edited as specified
    """
    if current_user.has_basic_view:
        #Query the the formerly given information and the documents of the transaction
        transaction = Transaction.query.filter_by(id=transaction_id).first_or_404()
        form = TransactionForm(obj=transaction)

        qir_numbers = QIR_numbers.query.filter_by(transaction_id=transaction_id).order_by(desc('date_created')).all()
        accounting_records = transaction.accounting_record.order_by(desc('date_created'))
        
        list_card_machines = ['Unknown']
        card_machines = Card_machine.query.filter_by(country=current_user.user_country).all()
        for each_card_machine in card_machines:
            list_card_machines.append(each_card_machine.as_dict()['card_machine_ref'])
        form.card_machine.choices = list_card_machines

        
        #Then create a form with the given transaction's information
        
        default_amortization_choices = ['Constant', 'Fixed Hrs/Week', 'Custom']
        amortization_set = {'Constant', 'Fixed Hrs/Week', 'Custom'}

        if transaction.service_1_amortization_type is not None:
            service_1_amortization_choices = [transaction.service_1_amortization_type]
            service_1_amortization_choices = fill_amortization_slots(service_1_amortization_choices, amortization_set)
        else:
            service_1_amortization_choices = default_amortization_choices

        if transaction.service_2_amortization_type is not None:
            service_2_amortization_choices = [transaction.service_2_amortization_type]
            service_2_amortization_choices = fill_amortization_slots(service_2_amortization_choices, amortization_set)
        else:
            service_2_amortization_choices = default_amortization_choices

        if transaction.service_3_amortization_type is not None:
            service_3_amortization_choices = [transaction.service_3_amortization_type]
            service_3_amortization_choices = fill_amortization_slots(service_3_amortization_choices, amortization_set)
        else:
            service_3_amortization_choices = default_amortization_choices

        if transaction.service_4_amortization_type is not None:
            service_4_amortization_choices = [transaction.service_4_amortization_type]
            service_4_amortization_choices = fill_amortization_slots(service_4_amortization_choices, amortization_set)
        else:
            service_4_amortization_choices = default_amortization_choices

        if transaction.service_5_amortization_type is not None:
            service_5_amortization_choices = [transaction.service_5_amortization_type]
            service_5_amortization_choices = fill_amortization_slots(service_5_amortization_choices, amortization_set)
        else:
            service_5_amortization_choices = default_amortization_choices

        if transaction.service_6_amortization_type is not None:
            service_6_amortization_choices = [transaction.service_6_amortization_type]
            service_6_amortization_choices = fill_amortization_slots(service_6_amortization_choices, amortization_set)
        else:
            service_6_amortization_choices = default_amortization_choices
        

        #Set the form's categories and subcategories based on the given inputs
        form.service_1_amortization_type.choices = service_1_amortization_choices
        form.service_2_amortization_type.choices = service_2_amortization_choices
        form.service_3_amortization_type.choices = service_3_amortization_choices
        form.service_4_amortization_type.choices = service_4_amortization_choices
        form.service_5_amortization_type.choices = service_5_amortization_choices
        form.service_6_amortization_type.choices = service_6_amortization_choices
        
        

        #If the form is validated, then process the changes and redirect to the target website
        if form.validate_on_submit():
            if 'preview' in request.form:
                #If for previewing, the website will redirect the user to the page of the PDF file
                preview_filename, this_transaction_id = save_transaction_changes(transaction, form, new=False, submit=False)
                preview_link = '/previews/' + preview_filename

                return redirect(preview_link)

            else:
                #If for submission, the website will redirect the user to the transaction's page
                preview_filename, this_transaction_id = save_transaction_changes(transaction, form, new=False, submit=True)
                transaction_link = '/transaction/' + str(transaction_id)
                flash('Transaction successfully updated!')

                return redirect(transaction_link)
                
            
        return render_template('transaction/transaction.html', title = 'Transaction', action = "Edit", form = form, qir_numbers = qir_numbers, accounting_records = accounting_records)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/add_transaction', methods = ['GET', 'POST'])
@login_required
def add_transaction():
    """Add a new transaction to the system

    Returns:
        [flask render_template]: Show the transaction page with all of the information added as specified
    """
    if current_user.has_basic_view:
        form = TransactionForm()

        list_card_machines = ['Unknown']
        card_machines = Card_machine.query.filter_by(country=current_user.user_country).all()
        for each_card_machine in card_machines:
            list_card_machines.append(each_card_machine.as_dict()['card_machine_ref'])
        form.card_machine.choices = list_card_machines

        default_amortization_choices = ['Constant', 'Fixed Hrs/Week', 'Custom']
        form.service_1_amortization_type.choices = default_amortization_choices
        form.service_2_amortization_type.choices = default_amortization_choices
        form.service_3_amortization_type.choices = default_amortization_choices
        form.service_4_amortization_type.choices = default_amortization_choices
        form.service_5_amortization_type.choices = default_amortization_choices
        form.service_6_amortization_type.choices = default_amortization_choices
        
        if form.validate_on_submit():
            transaction = Transaction()
            if 'preview' in request.form:
                #If for previewing, the website will redirect the user to the page of the PDF file
                preview_filename, this_transaction_id = save_transaction_changes(transaction, form, new=True, submit=False)
                preview_link = '/previews/' + preview_filename

                return redirect(preview_link)
            else:
                #If for submission, the website will redirect the user to the transaction's page
                preview_filename, this_transaction_id = save_transaction_changes(transaction, form, new=True)
                flash('Transaction successfully added!')
                transaction_link = '/transaction/' + str(this_transaction_id)
                return redirect(transaction_link)
            
        return render_template('transaction/transaction.html', title = 'Transaction', action = "Add", form = form, qir_numbers = None)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))
        
def update_service_from_csv(input_filename):
    df_service = pd.read_excel(input_filename)
    df_service.to_sql(name='service', con=db.engine, index=False)

@bp.route('/offices_global', methods = ['GET', 'POST'])
@login_required
def offices_global():
    """ A page with a json of all office names

    Returns:
        json: all office information
    """
    if current_user.has_basic_view:
        office_res = Office.query.all()

        list_offices = list()
        for each_office in office_res:
            temp_dict_name = dict()
            temp_dict_name['name'] = each_office.name
            list_offices.append(temp_dict_name)

        return jsonify(list_offices)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

def save_office_changes(office, form, new=False):
    """ Save office changes to the database

    Args:
        office (SQLAlchemy query object): Office SQLAlchemy object  
        form (Flask form): Input Flask form for editing offices
        new (bool, optional): True if it is for adding offices. Otherwise, False for editing offices. Defaults to False.
    """
    if current_user.has_basic_view:
        office.name = form.name.data #Office name
        office.country = form.country.data #Office country
        office.info_for_vat = form.info_for_vat.data #A flag indicating if the indicated information is for VAT
        office.title = form.title.data #Title for referencing to the office
        office.company_name = form.company_name.data #Company Name
        office.address_1 = form.address_1.data #First line of address information
        office.address_2 = form.address_2.data #Second line of address information
        office.vat_tax_id = form.vat_tax_id.data #VAT tax ID for the office - used for VAT invoice
        office.email = form.email.data #Contact email for the office
        office.phone = form.phone.data #Contact phone number for the office
        office.bank_name = form.bank_name.data #Contact bank name for the office
        office.bank_account_name = form.bank_account_name.data #Bank account name 
        office.bank_account_number = form.bank_account_number.data #Bank account number
        office.logo_directory = form.logo_directory.data #Logo directory

        if new:
            #If new, add the office to the database and prepare for the user record of adding a new office
            db.session.add(office)
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='add office {}'.format(form.name.data))
        else:
            #Prepare for the user record of editing a new service
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='edit office {}'.format(form.name.data))
        #Add a user record
        db.session.add(user_record)
        db.session.commit()
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/office_lookup', methods = ['GET', 'POST'])
@login_required
def office_lookup():
    """ A page for looking up for offices with the office lookup form

    Returns:
        Flask redirect page: Office lookup page
    """
    if current_user.has_basic_view:
        form = OfficeForm_lookup()
        #OfficeForm, OfficeForm_lookup

        if form.validate_on_submit():
            office = Office.query.filter_by(name=form.name.data).first_or_404()
            office_link = '/office/' + str(office.id)

            return redirect(office_link)

        return render_template('office/office_lookup.html', form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/add_office', methods=['GET', 'POST'])
@login_required
def add_office():
    """Add office's information

    Returns:
        Flask render_template page: The page of office adding form
    """
    #First, check if the current user has the permission to change office/service information
    if current_user.can_change_service_info:
        #If the user can change office information, proceed to the next steps
        form = OfficeForm()
        
        if form.validate_on_submit():
            office = Office()
            save_office_changes(office, form, new = True)
            flash('Congratulations, you have already added the new office information!')

        return render_template('office/office.html', title = 'Office', action = "Add", form = form)
    else:
        abort(403)

@bp.route('/office/<int:office_id>', methods = ['GET', 'POST'])
@login_required
def edit_office(office_id):
    """Edit office information's according to the given id

    Args:
        office_id (int): Target office's id

    Returns:
        Flask render_template: form for editing office information
    """
    if current_user.can_change_service_info:
        #Check if the current user has the permission to change office information
        office = Office.query.filter_by(id=office_id).first_or_404()
        form = OfficeForm(obj=office)

        if form.validate_on_submit():
            save_office_changes(office, form, new=False)
            flash('Congratulations, you have already edited the office information!')
            
        return render_template('office/office.html', title = 'Office', action = "Edit", form = form)
    else:
        abort(403)


@bp.route('/service_lookup', methods = ['GET', 'POST'])
@login_required
def service_lookup():
    """ A page for looking up for services with the service lookup form

    Returns:
        Flask redirect page: Service lookup page
    """
    if current_user.has_basic_view:
        form = ServiceForm_lookup()

        if form.validate_on_submit():
            service = Service.query.filter_by(name=form.name.data).first_or_404()
            service_link = '/service/' + str(service.id)

            return redirect(service_link)

        return render_template('service/service_lookup.html', form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))
    

@bp.route('/services_local', methods = ['GET', 'POST'])
@login_required
def services_local():
    """ A page with a json of all local services

    Returns:
        json: all local service information
    """
    if current_user.has_basic_view:
        service_res = Service.query.filter_by(country=current_user.user_country)
        list_services = list()

        for r in service_res:
            temp_dict_name = dict()
            temp_dict = r.as_dict()
            temp_dict_name['name'], temp_dict_name['price'], temp_dict_name['category'] = temp_dict['name'], temp_dict['price'], temp_dict['category']
            list_services.append(temp_dict_name)
        
        return jsonify(list_services)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/services_global', methods = ['GET', 'POST'])
@login_required
def services_global():
    """ A page with a json of all global services

    Returns:
        json: all global service information
    """
    if current_user.has_basic_view:
        service_res = Service.query.all()
        list_services = [r.as_dict() for r in service_res]
        return jsonify(list_services)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

def save_service_changes(service, form, new=False):
    """ Save service changes to the database

    Args:
        service (SQLAlchemy query object): Service SQLAlchemy object  
        form (Flask form): Input Flask form for editing services
        new (bool, optional): True if it is for adding services. Otherwise, False for editing services. Defaults to False.
    """
    if current_user.has_basic_view:
        new_service = Service.query.filter_by(
            name = form.name.data, category = form.category.data, subcategory = form.subcategory.data,
            vat_name = form.vat_name.data, non_vat_name = form.non_vat_name.data, display_name = form.display_name.data,
            country = form.country.data, vat_proportion = form.vat_proportion.data, price = form.price.data
        ).first()
        if new_service is None:
            #Service category and subcategory
            service.category = form.category.data 
            service.subcategory = form.subcategory.data
            #Service name
            service.name = form.name.data
            service.vat_name = form.vat_name.data
            service.non_vat_name = form.non_vat_name.data
            if form.display_name.data is not None and form.display_name.data != '':
                service.display_name = form.display_name.data
            else:
                if service.category == 'Private':
                    category_prefix = 'Private Class: '
                else:
                    category_prefix = service.category + ': '
                service.display_name = category_prefix + service.name
            service.country = form.country.data
            service.vat_proportion = form.vat_proportion.data
            service.price = form.price.data
            if new:
                #If new, add the service to the database and prepare for the user record of adding a new service
                db.session.add(service)
                user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='add service {}, for country {}, price = {}'.format(form.name.data, form.country.data, form.price.data))
            else:
                #Prepare for the user record of editing a new service
                user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='edit service {}, for country {}, price = {}'.format(form.name.data, form.country.data, form.price.data))
            #Add a user record
            db.session.add(user_record)
            db.session.commit()
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/get_service_subcategory/<service_category>', methods = ['GET', 'POST'])
@login_required
def get_service_subcategory(service_category):
    """Load the service category's subcategories and store them in the json form

    Args:
        service_category (str): service category

    Returns:
        list: list of service categories
    """
    if current_user.has_basic_view:
        service_dict = retrieve_service_dict()

        if service_category not in service_dict:                                                                 
            return jsonify([])
        else:                                                                                    
            return jsonify(service_dict[service_category])
    
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

def fill_service_form(service):
    if service is None:
        form = ServiceForm_global()
    else:
        form = ServiceForm_global(obj=service)
    service_dict = retrieve_service_dict()
    if service.category is not None:
        category_choices = [service.category]
        for each_category in service_dict.keys():
            if each_category != service.category:
                category_choices.append(each_category)

        if service.subcategory is not None:
            subcategory_choices = [service.subcategory]
            for each_subcategory in service_dict[service.category]:
                if each_subcategory != service.subcategory:
                    subcategory_choices.append(each_subcategory)
        else:
            subcategory_choices = []
    else:
        category_choices = list(service_dict.keys())
        subcategory_choices = []

    #Set the form's categories and subcategories based on the given inputs
    form.category.choices = category_choices
    form.subcategory.choices = subcategory_choices

    return form

@bp.route('/add_service_global', methods=['GET', 'POST'])
@login_required
def add_service_global():
    """Add a new service for the global level

    Returns:
        Flask render_template page: The page of service adding form
    """
    #First, check if the current user has the permission to change service information
    if current_user.can_change_service_info:
        #If the user can change service information, proceed to the next steps
        form = ServiceForm_global()
        service = Service()
        
        if form.validate_on_submit():
            if request.method == 'GET':
                form = fill_service_form(service)
            save_service_changes(service, form, new = True)

            service_item = Service.query.filter_by(name = form.name.data).first()
            flash('Congratulations, you have already added a new service!')
            service_link = '/service/' + str(service_item.id)
            return redirect(service_link)

        return render_template('service/service.html', title = 'Service', action = "Add", form = form)
    else:
        abort(403)

@bp.route('/service/<int:service_id>', methods = ['GET', 'POST'])
@login_required
def edit_service(service_id):
    """Edit service information's according to the given id

    Args:
        service_id (int): Target service's id

    Returns:
        Flask render_template: form for editing services
    """
    if current_user.can_change_service_info:
        #Check if the current user has the permission to change service information
        #If so, query the target service's information and find all of the categories and subcategories based on the given input
        service = Service.query.filter_by(id=service_id).first_or_404()
        form = ServiceForm_global(obj=service)
        if request.method == 'GET':
            form = fill_service_form(service)
        
        if form.validate_on_submit():
            save_service_changes(service, form)
            flash('Congratulations, you have already edited the service!')
            service_link = '/service/' + str(service_id)
            return redirect(service_link)
            
        return render_template('service/service.html', title = 'Service', action = "Edit", form = form)
    else:
        abort(403)

@bp.route('/card_machine_lookup', methods = ['GET', 'POST'])
@login_required
def card_machine_lookup():
    """ A page for looking up for credit/debit card machines with the card machine lookup form

    Returns:
        Flask redirect page: Card machine lookup page
    """

    if current_user.has_basic_view:
        form = MachineForm_lookup()
        all_local_machines = Card_machine.query.filter_by(country = current_user.user_country).all()
        list_dropdown = ['Unknown']
        
        for each_machine in all_local_machines:
            temp_dict = each_machine.as_dict()
            list_dropdown.append(temp_dict['card_machine_ref'])
        form.machine_select.choices = list_dropdown

        if form.validate_on_submit():
            dropdown_str = form.machine_select.data
            temp_list = dropdown_str.split('/')
            ref_number = temp_list[2].strip()
            card_machine = Card_machine.query.filter_by(machine_code_number=int(ref_number)).first_or_404()
            machine_link = '/card_machine/' + str(card_machine.machine_code_number)

            return redirect(machine_link)

        return render_template('card_machine/card_machine_lookup.html', form=form)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

def save_card_machine_changes(card_machine, form, new=False):
    """ Save service changes to the database

    Args:
        service (SQLAlchemy query object): Service SQLAlchemy object  
        form (Flask form): Input Flask form for editing services
        new (bool, optional): True if it is for adding services. Otherwise, False for editing services. Defaults to False.
    """
    if current_user.has_basic_view:
        #Teacher category and subcategory
        card_machine.machine_code_number = form.machine_code_number.data
        card_machine.reference_name = form.reference_name.data
        card_machine.bank_name = form.bank_name.data
        card_machine.country = form.country.data
        if new:
            #If new, add the service to the database and prepare for the user record of adding a new service
            db.session.add(card_machine)
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='add card machine {}, for country {}'.format(form.machine_code_number.data, form.country.data))
        else:
            #Prepare for the user record of editing a new service
            user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='edit card machine {}, for country {}'.format(form.machine_code_number.data, form.country.data))
        #Add a user record
        db.session.add(user_record)
        db.session.commit()
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))

@bp.route('/add_card_machine_global', methods=['GET', 'POST'])
@login_required
def add_card_machine_global():
    """
    Add a new card machine for the global level

    Returns:
        Flask render_template page: The page of card adding form
    """
    #First, check if the current user has the permission to change service information
    if current_user.can_change_service_info:
        #If the user can change service information, proceed to the next steps
        form = MachineForm_global()
        
        if form.validate_on_submit():
            card_machine = Card_machine()
            
            save_card_machine_changes(card_machine, form, new = True)
            flash('Congratulations, you have already added a new card machine!')

        return render_template('card_machine/card_machine.html', title = 'Card Machine', action = "Add", form = form)
    else:
        abort(403)

@bp.route('/card_machine/<int:machine_code_number>', methods = ['GET', 'POST'])
@login_required
def edit_card_machine(machine_code_number):
    """Edit credit/debit card machine information's according to the given id

    Args:
        machine_code_number (int): Target credit/debit card machine's id

    Returns:
        Flask render_template: form for editing services
    """
    if current_user.can_change_service_info:
        #Check if the current user has the permission to change service information
        #If so, query the target service's information and find all of the categories and subcategories based on the given input
        card_machine = Card_machine.query.filter_by(machine_code_number=machine_code_number).first_or_404()
        form = MachineForm_global(obj=card_machine)

        if form.validate_on_submit():
            save_card_machine_changes(card_machine, form)
            flash('Congratulations, you have already edited the credit/debit card machine!')
            
        return render_template('card_machine/card_machine.html', title = 'Card Machine', action = "Edit", form = form)
    else:
        abort(403)


@bp.route('/uploads/<path:code_number>', methods=['GET', 'POST'])
@login_required
def download_document(code_number):
    """Download a document based on the given code number in the function

    Args:
        code_number (str): string of document code

    Returns:
        send_from_directory: download the target file based on the code number
    """
    if current_user.has_basic_view:
        #Query the target file's directory
        qir_query = QIR_numbers.query.filter_by(code_number=code_number).first()
        transaction_query = Transaction.query.filter_by(id=qir_query.transaction_id).first()
        student_name = transaction_query.student_full_name
        filename = code_number + '_' + student_name + '.pdf'
        
        #Create a new user record to save the document's information
        user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='download document code: {}'.format(code_number))
        #Add the user record to the database
        db.session.add(user_record)
        db.session.commit()

        io_file = io.BytesIO(qir_query.pdf_binary)
        io_file.name=filename

        return send_file(io_file, as_attachment=True, attachment_filename=filename)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))
    

@bp.route('/previews/<path:code_number>', methods=['GET', 'POST'])
@login_required
def preview_document(code_number):
    """ Create a preview PDF file of the given code number's document

    Args:
        code_number (str): document code number

    Returns:
        send_from_directory: Show the website of the preview file
    """
    if current_user.has_basic_view:
        #Find the preview file directory
        qir_preview_query = QIR_numbers_preview.query.filter_by(code_number=code_number).order_by(desc('date_created')).first()
        filename = code_number + '.pdf'

        #Record the preview part in the user record
        user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='preview document code: {}'.format(code_number))
        #Add the user record to the database
        db.session.add(user_record)
        db.session.commit()

        io_file = io.BytesIO(qir_preview_query.pdf_binary)
        io_file.name=filename

        return send_file(io_file, attachment_filename=filename)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))
    

@bp.route('/accounting_record_download_accounting', methods=['GET', 'POST'])
@login_required
def accounting_record_download_accounting():
    """Call for the non-VAT record form, process all of the input information from a user, and download the relevant data entries 

    Returns:
        Flask render_template: Render the website for downloading the non-VAT record
    """
    #Find the oldest record and the newest record, and find the available time frame for downloading
    #List all of the years in a list
    form = Amortize_lookup()

    if form.validate_on_submit():
        #Process all inputs and let the user download the output with the filename given as '[starting_month]_[starting_year]_to_[ending_month]_[ending_year]_nonvat.xlsx'
        start_datetime = form.start_date_select.data
        end_datetime = form.end_date_select.data
        filename = '{}_{}_to_{}_{}_accounting_amortize.xlsx'.format(start_datetime.month, start_datetime.year, end_datetime.month, end_datetime.year)
        
        if form.amortize_date_flag.data:
            amortize_date_flag = True
        else:
            amortize_date_flag = False

        return process_and_download_accounting_query(filename, start_datetime, end_datetime, False, amortize_date_flag)
    
    return render_template('accounting/accounting_record_download_accounting.html', title='Accounting Record Download', form = form)


@bp.route('/accounting_record_download_sales', methods=['GET', 'POST'])
@login_required
def accounting_record_download_sales():
    """Call for the non-VAT record form, process all of the input information from a user, and download the relevant data entries 

    Returns:
        Flask render_template: Render the website for downloading the non-VAT record
    """
    #Find the oldest record and the newest record, and find the available time frame for downloading
    #List all of the years in a list
    form = Document_lookup()

    if form.validate_on_submit():
        start_datetime = form.start_date_select.data
        form_end_datetime = form.end_date_select.data
        end_datetime = datetime.datetime(minute=59, hour=23, day=form_end_datetime.day, month=form_end_datetime.month, year=form_end_datetime.year)
        filename = '{}_{}_{}_to_{}_{}_{}_'.format(start_datetime.day, start_datetime.month, start_datetime.year, end_datetime.day, end_datetime.month, end_datetime.year)

        if 'excel' in request.form:
            #Process all inputs and let the user download the output with the filename given as '[starting_month]_[starting_year]_to_[ending_month]_[ending_year]_nonvat.xlsx'
            filename += 'accounting_sales.xlsx'
            return process_and_download_accounting_query(filename, start_datetime, end_datetime, True)
        else:
            dict_output = dict()
            if 'receipt' in request.form:
                filename += 'receipts.zip'
                receipt_query = QIR_numbers.query.filter(QIR_numbers.country == current_user.user_country, QIR_numbers.code_type == 'R', QIR_numbers.date_created >= start_datetime, QIR_numbers.date_created <= end_datetime).order_by(QIR_numbers.id).all()
                
                for each_query in receipt_query:
                    dict_output[each_query.code_number + '_' + each_query.student_full_name] = io.BytesIO(each_query.pdf_binary)
                
            if 'invoice' in request.form:
                filename += 'vat_invoices.zip'
                vat_invoice_query = QIR_numbers.query.filter(QIR_numbers.country == current_user.user_country, QIR_numbers.code_type == 'T', QIR_numbers.date_created >= start_datetime, QIR_numbers.date_created <= end_datetime).order_by(QIR_numbers.id).all()
                
                for each_query in vat_invoice_query:
                    dict_output[each_query.code_number + '_' + each_query.student_full_name] = io.BytesIO(each_query.pdf_binary)

            zip_buffer = generate_zip_file(dict_output)
            zip_buffer.name=filename

            zip_buffer.seek(0)
            resp = make_response(zip_buffer.getvalue())
            resp.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
            resp.headers['Content-Type'] = 'application/zip'
            
            return resp

    return render_template('accounting/accounting_record_download_sales.html', title='Accounting Record Download', form = form)


@bp.route('/amortization_edit/<int:accounting_id>', methods=['GET', 'POST'])
@login_required
def amortization_edit(accounting_id):
    if current_user.has_basic_view:
        accounting_record = Accounting_record.query.filter_by(id=accounting_id).first_or_404()
        form = AmortizeEditForm()
        if request.method == 'GET':
            form = fill_amortization_form(accounting_record)
        if form.validate_on_submit():
            this_account_id = save_amortization_record(accounting_record, form)
            amortization_link = '/amortization_edit/' + str(this_account_id)
            flash('Congratulations, you have already edited the amortization information!')

            return redirect(amortization_link)
        return render_template('transaction/amortization_record.html', title='Accounting Record Download', form = form, accounting_record = accounting_record)
    else:
        flash('You are not authorized to see this page')
        return redirect(url_for('main.index'))
    
@bp.route('/credit_transfer/', methods=['GET', 'POST'])
@login_required
def credit_transfer():
    if current_user.has_basic_view:
        form = CreditTransferForm()
        if form.validate_on_submit():
            save_credit_transfer(form)
            flash('Congratulations, credit transfer completed')
            
            return redirect('/credit_transfer/')

        return render_template('credit/credit_transfer.html', title='Credit Transfer', form = form)

@bp.route('/refund_download', methods=['GET', 'POST'])
@login_required
def refund_download():
    """Download refund-related documents

    Returns:
        Flask render_template: Render the website for downloading the refund record
    """
    #Find the oldest record and the newest record, and find the available time frame for downloading
    #List all of the years in a list
    form = Document_lookup()

    if form.validate_on_submit():
        #Process all inputs and let the user download the output with the filename given as '[starting_month]_[starting_year]_to_[ending_month]_[ending_year]_nonvat.xlsx'
        start_datetime = form.start_date_select.data
        end_datetime = form.end_date_select.data
        filename = '{}_{}_to_{}_{}_refund_record.xlsx'.format(start_datetime.month, start_datetime.year, end_datetime.month, end_datetime.year)
        
        return process_and_download_refund_query(filename, start_datetime, end_datetime)
    
    return render_template('credit/credit_record_download.html', title='Accounting Record Download', form = form)