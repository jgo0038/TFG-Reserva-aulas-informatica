import os
BASEDIR = os.path.abspath(os.path.dirname(__file__))
SERVER_ADDRESS = 'http://localhost:5000/'

DEBUG = True
SECRET_KEY = 'claveSecreta'

SQLALCHEMY_TRACK_MODIFICATIONS = False

O365_APP_ID = '0f0cdc95-e08f-4b67-9cb8-62b4350aa9a2'
O365_APP_KEY = 'yvTRWIcnmT@nY4?zIA?=N2yc5yeIA0o_'
O365_REDIRECT_URI = os.path.join(SERVER_ADDRESS, 'connect/get_token')
O365_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
O365_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

scopes = ['openid',
           'User.Read',
           'Mail.Read',
           'profile',
           'email',
           'offline_access',
           'Calendars.Read',
           'calendars.readwrite']