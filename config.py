# import os
# from dotenv import load_dotenv
# from datetime import timedelta

# basedir = os.path.abspath(os.path.dirname(__file__))
# load_dotenv(os.path.join(basedir, '.env'))

# class Config(object):
#     SECRET_KEY = os.environ.get('SECRET_KEY') or 'f2e21dd86c6089e8f8522516dfacd82ab559786e2f70c1a9'
#     SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
#         'postgresql://postgres:ForTesting!@localhost/test'
#     SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    
#     #For error reporting
#     MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
#     MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
#     MAIL_USE_TLS = True
#     MAIL_USERNAME = 'edusmith.sales@gmail.com'
#     MAIL_PASSWORD = 'BestSolutionAdmin2!'
#     ADMINS = ['edusmith.sales@gmail.com']

#     #For Emailing
#     MAIL_SUBJECT_PREFIX = '[EduSmith-Admin]'
#     MAIL_SENDER = 'EduSmith IT Admin <edusmith.sales@gmail.com>'

#     #Elasticsearch
#     ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

#     LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
#     #Upload & Preview Folder
#     UPLOAD_FOLDER = 'upload'
#     PREVIEW_FOLDER = 'preview'

#     #Logout after inactivity
#     PERMANENT_SESSION_LIFETIME =  timedelta(minutes=30)

#     #Vat Rate
#     VAT_RATE = {'Thailand': 0.07, 'Myanmar': 0.05}


import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    #Secret key used for resetting passwords
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'f2e21dd86c6089e8f8522516dfacd82ab559786e2f70c1a9'
    
    #SQLALCHEMY part
    #SQLALCHEMY database URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgres://ua8uu8j50qs6j4:p9f6484f13f74aa8307e4b8959771017fb20e3aaf9dc3e44e17902992c92f1b48@ec2-3-225-30-246.compute-1.amazonaws.com:5432/d8k5456v2egpvr'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    #Mailing Information
    #For error reporting
    #Google Server Info
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    #Admin email - needed to 
    MAIL_USERNAME = 'edusmith.sales@gmail.com'
    MAIL_PASSWORD = 'BestSolutionAdmin!!'
    #Admin's email(s) - needed to add more admin emails in the list below
    ADMINS = ['edusmith.sales@gmail.com']

    #Email subject and sender parts
    MAIL_SUBJECT_PREFIX = '[EduSmith-Admin]'
    MAIL_SENDER = 'EduSmith IT Admin <edusmith.sales@gmail.com>'

    #Elasticsearch server
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL') or \
        'https://paas:b908ea5b21df2f5f6383ff7dd4463423@oin-us-east-1.searchly.com'
    
    #Upload & Preview Folder
    UPLOAD_FOLDER = 'upload'
    PREVIEW_FOLDER = 'preview'

    #Logout after inactivity
    PERMANENT_SESSION_LIFETIME =  timedelta(minutes=30)

    #Print to STDOUT
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    #Vat Rate
    VAT_RATE = {'Thailand': 0.07, 'Myanmar': 0.05}