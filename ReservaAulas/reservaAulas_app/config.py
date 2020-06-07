import os
#Ejecutar en local
# SERVER_ADDRESS = 'http://localhost:5000/'
#Ejecutar en Azure
SERVER_ADDRESS = 'https://reservaaulas.azurewebsites.net/'
DEBUG = True
global ADMIN_USERS
ADMIN_USERS = ('gestCalendar@outlook.com')



O365_APP_ID = '0f0cdc95-e08f-4b67-9cb8-62b4350aa9a2'
O365_APP_KEY = 'yvTRWIcnmT@nY4?zIA?=N2yc5yeIA0o_'
O365_REDIRECT_URI = os.path.join(SERVER_ADDRESS, 'connect/get_token')
O365_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
O365_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

scopes = ['openid',
           'User.Read',
           'profile',
           'email',
           'offline_access',
           'Calendars.Read',
           'calendars.readwrite',
           'calendars.read.shared',
           'mail.send',
           'mail.send.shared',
           'https://graph.microsoft.com/calendars.read.shared',
           'https://graph.microsoft.com/Calendars.Read',
           'https://graph.microsoft.com/User.Read',
           'https://graph.microsoft.com/calendars.readwrite']


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY')
