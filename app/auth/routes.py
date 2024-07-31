from __future__ import print_function

from flask import render_template, redirect, url_for, flash, request, session
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user, login_required
from flask_babel import _
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from app.models import User, UserRecord, Role
from app.decorators import admin_required, permission_required
from app.auth.email import send_password_reset_email
from app.limiter import limiter

from ..email import send_email

import datetime

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("2/second") #Limit the number of login attempts to only 2 per second
def login():
    """Login function for the app

    Returns:
        Flask render_template: Flask render template for the login page
    """
    if current_user.is_authenticated:
        #If the user is already authenticated/logged in, just redriect the user to the main page
        return redirect(url_for('main.index'))
    #Create the login form for logging in
    form = LoginForm()
    if form.validate_on_submit():
        #If the form is validated, check if the user exists and both the username and the password match the record
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            #If the user is None or checking the password returns False, just redirect the user to the login page again
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login'))

        #Otherwise, log the user in
        login_user(user, remember=form.remember_me.data, duration = datetime.timedelta(minutes=30))
        session.permanent = True #Let the session for the user be permanent
        user.last_login = datetime.datetime.utcnow() #Set the last login datetime be the current utc time
        
        #Add the user record to record user login
        user_record = UserRecord(username=user.username, user_country = user.user_country, activity_name='login')
        db.session.add(user_record)
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
            
        return redirect(next_page)
    return render_template('auth/login.html', title=_('Sign In'), form=form)


@bp.route('/logout')
def logout():
    """Log out of the system

    Returns:
        Flask page: redirect to the login page
    """
    #Add to the record about user logout
    user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='logout')
    db.session.add(user_record)
    db.session.commit()
    
    #Logout
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Show the register page and process the input data
    (Only the admin(s) can register for new accounts for any new users)

    Returns:
        Flask render_template: show the app's main index page
    """
    if current_user.is_administrator:
        #Check if the current user is an admin
        form = RegistrationForm() #Show the registration form for the user
        if form.validate_on_submit():
            #If the form is validated on submit, set the role for the user as given in the role field and set the user's information as given in the remaining fields
            role = Role.query.filter_by(name=form.role.data).first()
            user = User(username=form.username.data, email=form.email.data,
                        first_name = form.first_name.data, 
                        user_country=form.country.data, role_id=role.id)
            #Hash the password and set it in the database
            user.set_password(form.password.data)
            #Add the user to the database
            db.session.add(user)

            #Add the record about the registration
            user_record = UserRecord(username=user.username, user_country = user.user_country, activity_name='register id: {}'.format(user.username))
            db.session.add(user_record)
            db.session.commit()

            #Generate the confirmation token to let the user confirm about the registration
            token = user.generate_confirmation_token()
            send_email(user.email, 'Confirm Your Account', 
                    'email/confirm', user=user, token=token)
            flash('A confirmation email has been set to you via email. Please activate your account before using this portal.')
            return redirect(url_for('auth.login'))
        return render_template('auth/register.html', title=_('Register'), form=form)
    else:
        flash('You are not authorized to see this site.')
        return redirect(url_for('main.index'))


@bp.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='valid confirm id: {}'.format(current_user.username))
        db.session.add(user_record)
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        user_record = UserRecord(username=current_user.username, user_country = current_user.user_country, activity_name='invalid confirm id: {}'.format(current_user.username))
        db.session.add(user_record)
        db.session.commit()
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

@bp.before_app_request
def before_request():
    session.permanent = True
    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.blueprint != 'auth' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))

@bp.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous:
        return redirect(url_for('auth.login'))
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@bp.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            user_record = UserRecord(username=user.username, user_country = user.user_country, activity_name='send reset password token id: {}'.format(user.username))
            db.session.add(user_record)
            db.session.commit()

        flash(
            _('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title=_('Reset Password'), form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user_record = UserRecord(username=user.username, user_country = user.user_country, activity_name='reset password id: {}'.format(user.username))
        db.session.add(user_record)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)