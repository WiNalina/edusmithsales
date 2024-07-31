from flask import Flask, redirect, request, url_for
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_babel import Babel, lazy_gettext as _l
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from app.limiter import limiter

from elasticsearch import Elasticsearch

import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os

from app.util import datetimefilter, shortdatefilter, booleanfilter, missingfilter, mockfilter

db = SQLAlchemy()
migrate = Migrate()

login = LoginManager()
login.session_protection = "strong"
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')
login.refresh_view = 'auth.login'
login.needs_refresh_message = (u"Session timeout. Please re-login.")
login.needs_refresh_message_category = "info"

mail = Mail()
bootstrap = Bootstrap()
babel = Babel()
admin = Admin(name='EduSmith Admin', template_mode='bootstrap4')

class AdminModelView(ModelView):
    #For admin to see the tables in the database
    def is_accessible(self):
        #Check if the user can accees the page
        if current_user.is_authenticated:
            #This case holds for a logged-in user
            #It will return if the current user is an admin or not
            return current_user.is_administrator
        else:
            #If not, just return False
            return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('auth.login', next=request.url))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    #Configure all of the filters created for displaying all of the data
    app.jinja_env.filters['datetimefilter'] = datetimefilter
    app.jinja_env.filters['shortdatefilter'] = shortdatefilter
    app.jinja_env.filters['booleanfilter'] = booleanfilter
    app.jinja_env.filters['missingfilter'] = missingfilter
    app.jinja_env.filters['mockfilter'] = mockfilter

    #Initiate all of the components in the app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    babel.init_app(app)
    admin.init_app(app)
    limiter.init_app(app)    

    #Import the models that will be displayed in the admin page
    from app.models import User, UserRecord, Role, Student, TestScore, Transaction, Service, QIR_numbers, QIR_numbers_preview, Accounting_record, Sale_record, Office, Refund
    temp_model_list = [User, UserRecord, Role, Student, TestScore, Transaction, Service, QIR_numbers, QIR_numbers_preview, Accounting_record, Sale_record, Office, Refund]
    for each_table in temp_model_list:
        #Add admin model view for all of the bales in the model list
        admin.add_view(AdminModelView(each_table, db.session))
    
    #Configure app's elasticsearch server
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    #Add all of the errors here
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    #Send an email to the admin via email if there exists any app failure
    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='EduSmith Sales App Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

            #Configure the logging process for printing errors
            if app.config['LOG_TO_STDOUT']:
                #This case holds for running on Heroku/ any other cloud platform that we will stream all of the logs in logging panel
                stream_handler = logging.StreamHandler()
                stream_handler.setLevel(logging.INFO)
                app.logger.addHandler(stream_handler)
            else:
                #Otherwise, we will put it in the log files 
                if not os.path.exists('logs'):
                    os.mkdir('logs')
                file_handler = RotatingFileHandler('logs/edusmith_sales.log',
                                                maxBytes=20480, backupCount=10)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s '
                    '[in %(pathname)s:%(lineno)d]'))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('Edusmith Sales Portal startup')
    
    return app

from app import models
