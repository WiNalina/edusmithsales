from flask import render_template, current_app
from flask_babel import _
from app.email import send_email


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(user.email, '[EduSmith-Sales] Reset Your Password',
               'email/reset_password', user = user, token = token)

