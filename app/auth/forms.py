from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from flask_babel import _, lazy_gettext as _l
from app.models import User, Role
from app import db

class LoginForm(FlaskForm):
    #Login form for users
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    #Registration form for users
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators= [DataRequired()]) #User first name
    password = PasswordField('Password', validators=[DataRequired()]) 
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")]) #Field for repeating the password - the value in this field must match the value in the password field
    country = SelectField('User Country', choices = ['Thailand', 'Myanmar']) #A dropdown field to select user's country
    role = SelectField('User Role', choices = [('accounting_user', 'Accounting User'), ('branch_user', 'Branch User'), ('super_user', 'Super User'), ('administrator', 'Administrator')]) #A dropdown field to select user's role
    
    submit = SubmitField('Register') #Submit field

    def validate_username(self, username):
        """Validate if the input user name matches any existing username in the database

        Args:
            username (str): string of the username

        Raises:
            ValidationError: Raised if the duplicate username is used
        """
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        """Validate if the input email matches any existing email in the database

        Args:
            email (str): string of the email

        Raises:
            ValidationError: Raised if the duplicate email is used
        """
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ResetPasswordRequestForm(FlaskForm):
    #Reset Password Request Form - used for submitting a reset-password request via email
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))


class ResetPasswordForm(FlaskForm):
    #Reset Password Form - used for changing password to the new password
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))