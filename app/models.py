from datetime import datetime
from time import time
import jwt
from flask import current_app
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from app.search import add_to_index, remove_from_index, query_index
from sqlalchemy.sql import func
import re

def password_check(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        8 characters length or more
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """

    # calculating the length
    length_error = len(password) < 8

    # searching for digits
    digit_error = re.search(r"\d", password) is None

    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # searching for symbols
    symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None

    # overall result
    password_ok = not ( length_error or digit_error or uppercase_error or lowercase_error or symbol_error )

    return {
        'password_ok' : password_ok,
        'length_error' : length_error,
        'digit_error' : digit_error,
        'uppercase_error' : uppercase_error,
        'lowercase_error' : lowercase_error,
        'symbol_error' : symbol_error,
    }


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

@login.user_loader
def load_user(id):
    #Query user by id
    return User.query.get(int(id))

class UserRecord(db.Model):
    #Record user behavior in the database
    id = db.Column(db.Integer, primary_key=True) #Record ID
    user_country = db.Column(db.String(50)) #User Country
    username = db.Column(db.String(25)) #Username
    activity_time = db.Column(db.DateTime, default = datetime.utcnow) #Activity datetime
    activity_name = db.Column(db.Text) #Activity name

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) #User ID
    username = db.Column(db.String(25), index=True, unique=True, nullable=False) #Username
    email = db.Column(db.String(50), index=True, unique=True, nullable=False) #User email
    first_name = db.Column(db.String(25)) #User first name
    password_hash = db.Column(db.String(128), nullable=False) #User's hashed password
    user_country = db.Column(db.String(50), nullable=False) #User's country
    last_seen = db.Column(db.DateTime, default = datetime.utcnow) #User's last seen time
    last_login = db.Column(db.DateTime, default = datetime.utcnow) #User's last login time
    about_me = db.Column(db.String(140)) #User's information
    confirmed = db.Column(db.Boolean, default = False) #User's confirmation - whether the user has already confirmed with the system
    transactions = db.relationship('Transaction', backref='staff', lazy='dynamic') #Transactions that the user has created
    role_id = db.Column(db.Integer, db.ForeignKey('role.id')) #User's role id

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    #Password Part
    def set_password(self, password):
        """Generate hashed and salted password using the input password

        Args:
            password (str): input password
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the input password matches the recorded password

        Args:
            password (str): input password

        Returns:
            boolean: check if the given password matches the recorded password
        """
        return check_password_hash(self.password_hash, password)

    #Reset Password
    def get_reset_password_token(self, expires_in=600):
        """Generate a token for resetting password

        Args:
            expires_in (int, optional): number of seconds that the token will be expired. Defaults to 600.

        Returns:
            str: code for resetting password
        """
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        """Verify if the reset-password token is correct

        Args:
            token (str): input token for resetting password

        Returns:
            SQLAlchemy query obj: query object for the user
        """
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    #User Role Part
    def can(self, perm):
        """Check if the user has permission to do the input permission

        Args:
            perm (Permission object): an input permission

        Returns:
            boolean: boolean indicating if the user has enough permission to do the role
        """
        return self.role is not None and self.role.has_permission(perm)
    
    @property
    def has_basic_view(self):
        return self.can(Permission.BASIC_ACCESS)

    @property
    def is_administrator(self):
        #Check if the user is an administrator
        return self.can(Permission.ADMINISTER)

    @property
    def can_change_service_info(self):
        #Check if the user can change service information
        return self.can(Permission.CHANGE_SERVICE_INFORMATION)

    def generate_confirmation_token(self, expiration=3600):
        """[summary]

        Args:
            expiration (int, optional): [description]. Defaults to 3600.

        Returns:
            [type]: [description]
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

class Permission:
    ACCOUNTING_ACCESS = 1
    BASIC_ACCESS = 2
    CHANGE_SERVICE_INFORMATION = 4
    GLOBAL_ACCESS = 8
    ADMINISTER = 32

class Role(db.Model):
    __table_name__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return '<Role {}>'.format(self.name)

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm
    
    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permissions(self):
        self.permissions = 0
    
    def has_permission(self, perm):
        return self.permissions & perm == perm

    
    @staticmethod
    def insert_roles():
        roles = {
            'accounting_user': [Permission.ACCOUNTING_ACCESS],
            'branch_user': [Permission.ACCOUNTING_ACCESS,
                            Permission.BASIC_ACCESS],
            'super_user': [Permission.ACCOUNTING_ACCESS,
                           Permission.BASIC_ACCESS,
                           Permission.CHANGE_SERVICE_INFORMATION,
                           Permission.GLOBAL_ACCESS],
            'administrator': [Permission.ACCOUNTING_ACCESS,
                              Permission.BASIC_ACCESS,
                              Permission.CHANGE_SERVICE_INFORMATION,
                              Permission.GLOBAL_ACCESS,
                              Permission.ADMINISTER]
        }
        default_role = 'branch_user'

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()
        
    

class Student(SearchableMixin, db.Model):
    __searchable__ = ['name']
    id = db.Column(db.Integer, primary_key=True)
    streak_id = db.Column(db.String(100))
    universal_id = db.Column(db.Integer, unique=True)
    #Student Personal Info
    name = db.Column(db.String(100), nullable=False)
    name_th = db.Column(db.String(100))
    company_name = db.Column(db.String(200))
    company_tax_id = db.Column(db.String(40))
    company_address = db.Column(db.String(200))
    student_country = db.Column(db.String(50), default='Thailand', nullable=False)
    school = db.Column(db.String(100))
    graduate_year = db.Column(db.Integer)
    #Student Contact
    mobile_num = db.Column(db.String(60))
    email = db.Column(db.String(200))
    line = db.Column(db.String(50))
    address = db.Column(db.String(200))
    tax_id = db.Column(db.String(40))
    #Dad Info
    dad_name = db.Column(db.String(100))
    dad_mobile_num = db.Column(db.String(60))
    dad_email = db.Column(db.String(200))
    dad_line = db.Column(db.String(50))
    #Mom Info
    mom_name = db.Column(db.String(100))
    mom_mobile_num = db.Column(db.String(60))
    mom_email = db.Column(db.String(200))
    mom_line = db.Column(db.String(50))
    #Other Info
    know_us_from = db.Column(db.String(200))
    total_value = db.Column(db.Float, default=0.0)
    credit_value = db.Column(db.Float, default=0.0)
    transactions = db.relationship('Transaction', backref='client', lazy='dynamic')
    test_scores = db.relationship('TestScore', backref='tester', lazy='dynamic')
    
    def _repr_(self):
        return '<Student {}>'.format(self.name)
    
    def as_dict(self):
        return {'name': self.name, 'name_th': self.name_th, 
            'student_country': self.student_country, 'school': self.school, 
            'graduate_year': self.graduate_year, 'mobile_num': self.mobile_num,
            'email': self.email, 'line': self.line, 'address': self.address,
            'credit_value': self.credit_value, 'company_name': self.company_name, 
            'company_tax_id': self.company_tax_id, 'company_address': self.company_address,
            'credit_value': self.credit_value
            }

class TestScore(db.Model):
    __tablename__ = "test_score"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable = False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    universal_id = db.Column(db.Integer)
    exam_compare_code = db.Column(db.String(200))
    exam_name = db.Column(db.String(50), nullable = False)
    exam_type = db.Column(db.String(50))
    exam_date = db.Column(db.DateTime, index=True)
    mock_flag = db.Column(db.Boolean)
    cat_1_name = db.Column(db.String(100))
    cat_1_score = db.Column(db.String(100))
    cat_2_name = db.Column(db.String(100))
    cat_2_score = db.Column(db.String(100))
    cat_3_name = db.Column(db.String(100))
    cat_3_score = db.Column(db.String(100))
    cat_4_name = db.Column(db.String(100))
    cat_4_score = db.Column(db.String(100))
    cat_5_name = db.Column(db.String(100))
    cat_5_score = db.Column(db.String(100))
    cat_6_name = db.Column(db.String(100))
    cat_6_score = db.Column(db.String(100))

    def _repr_(self):
        return '<TestScore {}>'.format(self.exam_name) 

class Service(SearchableMixin, db.Model):
    __searchable__ = ['name', 'category']
    __table_args__ = (
        db.UniqueConstraint('name', 'country'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(50))
    name = db.Column(db.String(200), nullable = False)
    display_name = db.Column(db.String(250))
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    vat_proportion = db.Column(db.Float, default = 0.0)
    price = db.Column(db.Float, default = 0.0)
    vat_name = db.Column(db.String(200))
    non_vat_name = db.Column(db.String(200))
    note = db.Column(db.String(200))
    default_amortize_start_day = db.Column(db.Integer)
    default_amortize_start_month = db.Column(db.Integer)
    default_amortize_end_day = db.Column(db.Integer)
    default_amortize_end_month = db.Column(db.Integer)
    default_amortize_duration_month = db.Column(db.Integer)

    def __repr__(self):
        return '<Service {}>'.format(self.name)
    
    def as_dict(self):
        dict_out = {'name': self.name, 'id': self.id, 'price': self.price, 'category': self.category}
        return dict_out

class Transaction(db.Model):
    #Transaction Schema
    __searchable__ = ['student_name']

    #Transaction ID
    id = db.Column(db.Integer, primary_key=True)
    #Transaction Country
    country = db.Column(db.String(50), nullable = False)
    #Timestamps
    create_timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the transaction is created
    latest_timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, onupdate=datetime.utcnow) #Timestamp of when the transaction is edited
    
    #User Part
    #Username of the transaction's creator
    create_user = db.Column(db.String(50), db.ForeignKey('user.username'))
    #Username of the transaction's updater
    update_user = db.Column(db.String(50))
    
    #Student Info
    #Student's full name
    student_full_name = db.Column(db.String(100), nullable = False)
    #Student ID
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    use_company_info_flag = db.Column(db.Boolean)
    company_name = db.Column(db.String(200))
    company_tax_id = db.Column(db.String(40))
    company_address = db.Column(db.String(200))

    #Service Part
    #Each service is consistsed of name, price, count, unpaid value, discount value, final price, vat value, and note
    #Service 1
    service_1_name = db.Column(db.String(100), nullable = False) #Service Name
    service_1_price = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0) #Service Price/Unit
    service_1_count = db.Column(db.Float) #Service Count
    service_1_unpaid_value = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0) #Unpaid Value For The Service
    service_1_discount_value = db.Column(db.Float(asdecimal=False)) #Discount Value Specifically For Service 1
    service_1_final_price = db.Column(db.Float(asdecimal=False)) #Final Price After Discount (Count * Unit Price - Discount)
    service_1_vat_value = db.Column(db.Float) #Vat Value For Service 1
    service_1_note = db.Column(db.String(200)) #Note For Service 1
    service_1_teacher_name = db.Column(db.String(100))
    service_1_office = db.Column(db.String(50))

    service_1_refund_flag = db.Column(db.Boolean, default = False)
    service_1_refund_status = db.Column(db.String(50))
    service_1_credit_note_number = db.Column(db.String(50))
    service_1_refund_amount = db.Column(db.Float, server_default=str(0.0))
    service_1_refund_date = db.Column(db.DateTime, server_default=func.now())

    service_1_amortization_type = db.Column(db.String(50))
    service_1_start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    service_1_end_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) 
    
    service_1_total_hours = db.Column(db.Float)
    service_1_monday_hours = db.Column(db.Float)
    service_1_tuesday_hours = db.Column(db.Float)
    service_1_wednesday_hours = db.Column(db.Float)
    service_1_thursday_hours = db.Column(db.Float)
    service_1_friday_hours = db.Column(db.Float)
    service_1_saturday_hours = db.Column(db.Float)
    service_1_sunday_hours = db.Column(db.Float)

    service_1_month_1_hrs = db.Column(db.Float)
    service_1_month_2_hrs = db.Column(db.Float)
    service_1_month_3_hrs = db.Column(db.Float)
    service_1_month_4_hrs = db.Column(db.Float)
    service_1_month_5_hrs = db.Column(db.Float)
    service_1_month_6_hrs = db.Column(db.Float)

    #Service 2
    service_2_name = db.Column(db.String(100))
    service_2_price = db.Column(db.Float(asdecimal=False), default = 0.0)
    service_2_count = db.Column(db.Float)
    service_2_unpaid_value = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0)
    service_2_discount_value = db.Column(db.Float(asdecimal=False))
    service_2_final_price = db.Column(db.Float(asdecimal=False))
    service_2_vat_value = db.Column(db.Float)
    service_2_note = db.Column(db.String(200))
    service_2_teacher_name = db.Column(db.String(100))
    service_2_office = db.Column(db.String(50))

    service_2_refund_flag = db.Column(db.Boolean, default = False)
    service_2_refund_status = db.Column(db.String(50))
    service_2_credit_note_number = db.Column(db.String(50))
    service_2_refund_amount = db.Column(db.Float, server_default=str(0.0))
    service_2_refund_date = db.Column(db.DateTime, server_default=func.now())

    service_2_amortization_type = db.Column(db.String(50))
    service_2_start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) 
    service_2_end_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) 
    
    service_2_total_hours = db.Column(db.Float)
    service_2_monday_hours = db.Column(db.Float)
    service_2_tuesday_hours = db.Column(db.Float)
    service_2_wednesday_hours = db.Column(db.Float)
    service_2_thursday_hours = db.Column(db.Float)
    service_2_friday_hours = db.Column(db.Float)
    service_2_saturday_hours = db.Column(db.Float)
    service_2_sunday_hours = db.Column(db.Float)
    
    service_2_month_1_hrs = db.Column(db.Float)
    service_2_month_2_hrs = db.Column(db.Float)
    service_2_month_3_hrs = db.Column(db.Float)
    service_2_month_4_hrs = db.Column(db.Float)
    service_2_month_5_hrs = db.Column(db.Float)
    service_2_month_6_hrs = db.Column(db.Float)

    #Service 3
    service_3_name = db.Column(db.String(100))
    service_3_price = db.Column(db.Float(asdecimal=False), default = 0.0)
    service_3_count = db.Column(db.Float)
    service_3_unpaid_value = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0)
    service_3_discount_value = db.Column(db.Float(asdecimal=False))
    service_3_final_price = db.Column(db.Float(asdecimal=False))
    service_3_vat_value = db.Column(db.Float)
    service_3_note = db.Column(db.String(200))
    service_3_teacher_name = db.Column(db.String(100))
    service_3_office = db.Column(db.String(50))

    service_3_refund_flag = db.Column(db.Boolean, default = False)
    service_3_refund_status = db.Column(db.String(50))
    service_3_credit_note_number = db.Column(db.String(50))
    service_3_refund_amount = db.Column(db.Float, server_default=str(0.0))
    service_3_refund_date = db.Column(db.DateTime, server_default=func.now())

    service_3_amortization_type = db.Column(db.String(50))
    service_3_start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 3rd service begins
    service_3_end_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 3rd service ends
    
    service_3_total_hours = db.Column(db.Float)
    service_3_monday_hours = db.Column(db.Float)
    service_3_tuesday_hours = db.Column(db.Float)
    service_3_wednesday_hours = db.Column(db.Float)
    service_3_thursday_hours = db.Column(db.Float)
    service_3_friday_hours = db.Column(db.Float)
    service_3_saturday_hours = db.Column(db.Float)
    service_3_sunday_hours = db.Column(db.Float)
    
    service_3_month_1_hrs = db.Column(db.Float)
    service_3_month_2_hrs = db.Column(db.Float)
    service_3_month_3_hrs = db.Column(db.Float)
    service_3_month_4_hrs = db.Column(db.Float)
    service_3_month_5_hrs = db.Column(db.Float)
    service_3_month_6_hrs = db.Column(db.Float)

    #Service 4
    service_4_name = db.Column(db.String(100))
    service_4_price = db.Column(db.Float(asdecimal=False), default = 0.0)
    service_4_count = db.Column(db.Float)
    service_4_unpaid_value = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0)
    service_4_discount_value = db.Column(db.Float(asdecimal=False))
    service_4_final_price = db.Column(db.Float(asdecimal=False))
    service_4_vat_value = db.Column(db.Float)
    service_4_note = db.Column(db.String(200))
    service_4_teacher_name = db.Column(db.String(100))
    service_4_office = db.Column(db.String(50))

    service_4_refund_flag = db.Column(db.Boolean, default = False)
    service_4_refund_status = db.Column(db.String(50))
    service_4_credit_note_number = db.Column(db.String(50))
    service_4_refund_amount = db.Column(db.Float, server_default=str(0.0))
    service_4_refund_date = db.Column(db.DateTime, server_default=func.now())

    service_4_amortization_type = db.Column(db.String(50))
    service_4_start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 4th service begins
    service_4_end_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 4th service ends
    
    service_4_total_hours = db.Column(db.Float)
    service_4_monday_hours = db.Column(db.Float)
    service_4_tuesday_hours = db.Column(db.Float)
    service_4_wednesday_hours = db.Column(db.Float)
    service_4_thursday_hours = db.Column(db.Float)
    service_4_friday_hours = db.Column(db.Float)
    service_4_saturday_hours = db.Column(db.Float)
    service_4_sunday_hours = db.Column(db.Float)
    
    service_4_month_1_hrs = db.Column(db.Float)
    service_4_month_2_hrs = db.Column(db.Float)
    service_4_month_3_hrs = db.Column(db.Float)
    service_4_month_4_hrs = db.Column(db.Float)
    service_4_month_5_hrs = db.Column(db.Float)
    service_4_month_6_hrs = db.Column(db.Float)

    #Service 5
    service_5_name = db.Column(db.String(100))
    service_5_price = db.Column(db.Float(asdecimal=False), default = 0.0)
    service_5_count = db.Column(db.Float)
    service_5_unpaid_value = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0)
    service_5_discount_value = db.Column(db.Float(asdecimal=False))
    service_5_final_price = db.Column(db.Float(asdecimal=False))
    service_5_vat_value = db.Column(db.Float)
    service_5_note = db.Column(db.String(200))
    service_5_teacher_name = db.Column(db.String(100))
    service_5_office = db.Column(db.String(50))

    service_5_refund_flag = db.Column(db.Boolean, default = False)
    service_5_refund_status = db.Column(db.String(50))
    service_5_credit_note_number = db.Column(db.String(50))
    service_5_refund_amount = db.Column(db.Float, server_default=str(0.0))
    service_5_refund_date = db.Column(db.DateTime, server_default=func.now())

    service_5_amortization_type = db.Column(db.String(50))
    service_5_start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 5th service begins
    service_5_end_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 5th service ends
    
    service_5_total_hours = db.Column(db.Float)
    service_5_monday_hours = db.Column(db.Float)
    service_5_tuesday_hours = db.Column(db.Float)
    service_5_wednesday_hours = db.Column(db.Float)
    service_5_thursday_hours = db.Column(db.Float)
    service_5_friday_hours = db.Column(db.Float)
    service_5_saturday_hours = db.Column(db.Float)
    service_5_sunday_hours = db.Column(db.Float)
    
    service_5_month_1_hrs = db.Column(db.Float)
    service_5_month_2_hrs = db.Column(db.Float)
    service_5_month_3_hrs = db.Column(db.Float)
    service_5_month_4_hrs = db.Column(db.Float)
    service_5_month_5_hrs = db.Column(db.Float)
    service_5_month_6_hrs = db.Column(db.Float)

    #Service 6
    service_6_name = db.Column(db.String(100))
    service_6_price = db.Column(db.Float(asdecimal=False), default = 0.0)
    service_6_count = db.Column(db.Float)
    service_6_unpaid_value = db.Column(db.Float(asdecimal=False), nullable = False, default = 0.0)
    service_6_discount_value = db.Column(db.Float(asdecimal=False))
    service_6_final_price = db.Column(db.Float(asdecimal=False))
    service_6_vat_value = db.Column(db.Float)
    service_6_note = db.Column(db.String(200))
    service_6_teacher_name = db.Column(db.String(100))
    service_6_office = db.Column(db.String(50))

    service_6_refund_flag = db.Column(db.Boolean, default = False)
    service_6_refund_status = db.Column(db.String(50))
    service_6_credit_note_number = db.Column(db.String(50))
    service_6_refund_amount = db.Column(db.Float, server_default=str(0.0))
    service_6_refund_date = db.Column(db.DateTime, server_default=func.now())

    service_6_amortization_type = db.Column(db.String(50))
    service_6_start_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 6th service begins
    service_6_end_date = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Timestamp of when the 6th service ends
    
    service_6_total_hours = db.Column(db.Float)
    service_6_monday_hours = db.Column(db.Float)
    service_6_tuesday_hours = db.Column(db.Float)
    service_6_wednesday_hours = db.Column(db.Float)
    service_6_thursday_hours = db.Column(db.Float)
    service_6_friday_hours = db.Column(db.Float)
    service_6_saturday_hours = db.Column(db.Float)
    service_6_sunday_hours = db.Column(db.Float)
    
    service_6_month_1_hrs = db.Column(db.Float)
    service_6_month_2_hrs = db.Column(db.Float)
    service_6_month_3_hrs = db.Column(db.Float)
    service_6_month_4_hrs = db.Column(db.Float)
    service_6_month_5_hrs = db.Column(db.Float)
    service_6_month_6_hrs = db.Column(db.Float)

    #Overall Information
    total_value = db.Column(db.Float(asdecimal=False)) #Total transaction value after discounts
    remaining_outstanding = db.Column(db.Float(asdecimal=False)) #Remaining outstanding for the transaction
    overall_discount = db.Column(db.Float(asdecimal=False)) #Overall discount for all services in the transaction
    total_vat_value = db.Column(db.Float) #Total amount of VAT value paid for the transaction
    #Payment Date & Methods
    due_date = db.Column(db.DateTime, index=True) #Transaction Due Date
    payment_method = db.Column(db.String(50)) #Payment Method
    #Status Flags
    refund_flag = db.Column(db.Boolean, default = False) #Refund Flag - if true - the system will be refunded with the indicated amount the refund amount field
    refund_amount = db.Column(db.Float(asdecimal=False), default = 0.0) #Refund amount 
    cancel_flag = db.Column(db.Boolean, default = False) #Cancel flag - if true - the transaction will be cancelled
    complete_flag = db.Column(db.Boolean, default = False) #Complete flag - if true, the transaction will be completed

    #Quotation, Invoice, Receipt
    generate_invoice_flag = db.Column(db.Boolean, default = False) #Generate invoice flag - if true - the transaction will generate an invoice
    generate_receipt_flag = db.Column(db.Boolean, default = False) #Generate receipt flag - if true - the transaction will generate a receipt
    
    #Transaction Status
    transaction_status = db.Column(db.String(20), nullable=False, default='Quotation') #Transaction status

    #note
    note = db.Column(db.Text) #Note for overall transaction

    document_number = db.relationship('QIR_numbers', cascade='all, delete', backref='transaction', lazy='dynamic') #Documents embedded with the transaction
    accounting_record = db.relationship('Accounting_record', cascade='all, delete', backref='transaction', lazy='dynamic')

    def __repr__(self):
        return '<Transaction {}>'.format(self.id)

class Sale_record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default = datetime.utcnow)
    country = db.Column(db.String(50))
    office = db.Column(db.String(50))
    code_number = db.Column(db.String(10))
    transaction_id = db.Column(db.Integer)
    student_name = db.Column(db.String(200))
    school = db.Column(db.String(200))
    graduate_year = db.Column(db.Integer)
    service_name = db.Column(db.String(200))
    service_category = db.Column(db.String(50))
    service_subcategory = db.Column(db.String(50))
    service_count = db.Column(db.Float)
    price_per_unit = db.Column(db.Float)
    total_value = db.Column(db.Float)
    payment_method = db.Column(db.String(50)) #Payment Method
    payment_date = db.Column(db.Date)
    payment_time = db.Column(db.Time)
    card_machine = db.Column(db.String(100))
    card_issuer = db.Column(db.String(100))
    amortization_start_date = db.Column(db.DateTime)
    teacher_name = db.Column(db.String(100))
    refund_status = db.Column(db.String(20))
    refund_amount = db.Column(db.Float)
    refund_date = db.Column(db.Date)
    note = db.Column(db.String(20))

class Accounting_record(db.Model):
    #Records of all accounting information
    id = db.Column(db.Integer, primary_key=True) #Non-VAT transaction ID
    country = db.Column(db.String(50)) #Transaction country
    code_number = db.Column(db.String(10)) #Transaction document code number
    vat_invoice_code_number = db.Column(db.String(10)) #VAT invoice code
    receipt_pm_code = db.Column(db.String(20)) #Transaction code for EduSmith staff
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id')) #Transaction ID
    name = db.Column(db.String(100)) #Student's English name
    name_th = db.Column(db.String(100)) #Student's Thai name
    address = db.Column(db.String(200)) #Student's Address
    date_created = db.Column(db.DateTime, default = datetime.utcnow) #Transaction's datetime created
    service = db.Column(db.String(200)) #Transaction's service name
    service_category = db.Column(db.String(50))
    service_subcategory = db.Column(db.String(50))
    payment_method = db.Column(db.String(50)) #Payment Method
    payment_date = db.Column(db.Date)
    payment_time = db.Column(db.Time, default = datetime.now)
    card_machine = db.Column(db.String(100))
    card_issuer = db.Column(db.String(100))
    amortization_start_date = db.Column(db.DateTime)
    total_service_count = db.Column(db.Float)
    original_price_per_unit = db.Column(db.Float)
    service_count = db.Column(db.Float) #Transaction's service count
    price_per_unit = db.Column(db.Float) #Transaction's service price per unit
    total_non_vat_amount = db.Column(db.Float) #Transaction's service total non-VAT value
    tax_invoice_amount = db.Column(db.Float) #Transaction's value as appeared in the VAT invoice
    vat_amount = db.Column(db.Float) #Transaction's VAT value
    total_vat_amount = db.Column(db.Float) #Transaction's VAT-part's value
    total_amount = db.Column(db.Float) #Transaction's service total value
    amortization_type = db.Column(db.String(50))
    start_date = db.Column(db.DateTime, default = datetime.utcnow) #Transaction's start date
    end_date = db.Column(db.DateTime, default = datetime.utcnow) #Transaction's end date
    
    total_hours = db.Column(db.Float)
    monday_hrs = db.Column(db.Float)
    tuesday_hrs = db.Column(db.Float)
    wednesday_hrs = db.Column(db.Float)
    thursday_hrs = db.Column(db.Float)
    friday_hrs = db.Column(db.Float)
    saturday_hrs = db.Column(db.Float)
    sunday_hrs = db.Column(db.Float)
   
    month_1_hrs = db.Column(db.Float)
    month_2_hrs = db.Column(db.Float)
    month_3_hrs = db.Column(db.Float)
    month_4_hrs = db.Column(db.Float)
    month_5_hrs = db.Column(db.Float)
    month_6_hrs = db.Column(db.Float)

    former_amortization_info = db.Column(db.String(3000))
    refund_status = db.Column(db.String(20))
    refund_amount = db.Column(db.Float)
    refund_date = db.Column(db.Date)

    note = db.Column(db.String(20))


class QIR_numbers(db.Model):
    #Actual uploaded document information
    id = db.Column(db.Integer, primary_key=True) #Document ID
    country = db.Column(db.String(50), nullable = False) #Document country
    student_full_name = db.Column(db.String(100))
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id')) #Transaction ID for the document
    date_created = db.Column(db.DateTime, default = datetime.utcnow) #Datetime when the document is created
    creating_user = db.Column(db.String(25)) #User who created the document
    code_type = db.Column(db.String(1)) #String of document type - 'Q'/'I'/'R'/'V'
    code_number = db.Column(db.String(10), unique=True) #Document code number string
    pdf_binary = db.Column(db.LargeBinary)
    pickle_binary = db.Column(db.LargeBinary)


class QIR_numbers_preview(db.Model):
    #Preview uploaded document information
    id = db.Column(db.Integer, primary_key=True) #Document ID
    country = db.Column(db.String(50), nullable = False) #Document country
    student_full_name = db.Column(db.String(100))
    transaction_id = db.Column(db.Integer) #Transaction ID for the document
    date_created = db.Column(db.DateTime, default = datetime.utcnow) #Datetime when the document is created
    code_number = db.Column(db.String(50), unique=False) #Document code number string
    pdf_binary = db.Column(db.LargeBinary) #Binary of the document PDF

class Office(db.Model):
    #Office information - for example contact info for the office in Thailand
    id = db.Column(db.Integer, primary_key=True) #Office ID
    name = db.Column(db.String(200), unique=True) #Office Name
    country = db.Column(db.String(50)) #Office country
    info_for_vat = db.Column(db.Boolean) #A flag indicating if the indicated information is for VAT
    title = db.Column(db.String(200)) #Title for referencing to the office
    company_name = db.Column(db.String(200)) #Company Name
    address_1 = db.Column(db.String(200)) #First line of address information
    address_2 = db.Column(db.String(200)) #Second line of address information
    vat_tax_id = db.Column(db.String(30)) #VAT tax ID for the office - used for VAT invoice
    email = db.Column(db.String(50)) #Contact email for the office
    phone = db.Column(db.String(20)) #Contact phone number for the office
    bank_name = db.Column(db.String(20)) #Contact bank name for the office
    bank_account_name = db.Column(db.String(100)) #Bank account name 
    bank_account_number = db.Column(db.String(20)) #Bank account number
    logo_directory = db.Column(db.String(250)) #Logo directory

class VAT_info(db.Model):
    country = db.Column(db.String(100), primary_key=True)
    vat_rate = db.Column(db.Float)

class Refund(db.Model):
    id = db.Column(db.Integer, primary_key=True) #Office ID
    date_refund = db.Column(db.DateTime, default = datetime.utcnow)
    country = db.Column(db.String(100))
    office = db.Column(db.String(50))
    student_name = db.Column(db.String(100)) #Student's English name
    graduate_year = db.Column(db.Integer)
    credit_note_number = db.Column(db.String(50))
    type_of_refund = db.Column(db.String(50))
    refund_amount = db.Column(db.Float)
    service_name = db.Column(db.String(200))
    service_category = db.Column(db.String(50))
    service_subcategory = db.Column(db.String(50))
    receipt_number = db.Column(db.String(100))
    receipt_value = db.Column(db.Float)

class Teacher(db.Model):
    name = db.Column(db.String(100), primary_key=True)
    nationality = db.Column(db.String(100))
    country = db.Column(db.String(100))

    def as_dict(self):
        dict_out = {'name': self.name}
        return dict_out

class Card_machine(db.Model):
    machine_code_number = db.Column(db.Integer, primary_key=True)
    reference_name = db.Column(db.String(20))
    bank_name = db.Column(db.String(20))
    country = db.Column(db.String(100))

    def as_dict(self):
        dict_out = {'card_machine_ref': self.bank_name + ' / ' + self.reference_name + ' / ' + str(self.machine_code_number)}
        return dict_out