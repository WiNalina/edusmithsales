from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from app import mail


def send_async_email(app, msg):
    """Send an asynchronous email

    Args:
        app (Flask application object): the application used for sending a message
        msg (str): message in the email to be sent
    """
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    """Send email using the template using the specified subject to the target email

    Args:
        to (str): recipient's email address
        subject (str): email's subject
        template (str): template's filename

    Returns:
        thread obj: thread running the email sending process
    """
    app = current_app._get_current_object()
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr