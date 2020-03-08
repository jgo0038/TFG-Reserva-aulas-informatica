from config import (
    O365_APP_ID,
    O365_APP_KEY,
    O365_AUTH_URL,
    O365_TOKEN_URL,
    O365_REDIRECT_URI,
    scopes
)
import base64
import datetime
import json
import requests
import urllib
import uuid


def datetime_from_timestamp(timestamp):
    timestamp = float(timestamp)
    return datetime.datetime.utcfromtimestamp(timestamp)


def sign_in_url():
    url_parts = list(urllib.parse.urlparse(O365_AUTH_URL))
    auth_params = {
        'scope' : ' '.join(str(i) for i in scopes),
        'response_type': 'code',
        'redirect_uri': O365_REDIRECT_URI,
        'client_id': O365_APP_ID
    }

    url_parts[4] = urllib.parse.urlencode(auth_params)
    return urllib.parse.urlunparse(url_parts)


def get_oauth_token(code):
    token_params = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': O365_REDIRECT_URI,
        'scope': ' '.join(str(i) for i in scopes),
        'client_id': O365_APP_ID,
        'client_secret': O365_APP_KEY
    }

    print(token_params.values())

    r = requests.post(O365_TOKEN_URL, data=token_params)

    return r.json()


def get_jwt_from_id_token(id_token):
    encoded_jwt = id_token.split('.')[1]
    if len(encoded_jwt) % 4 == 2:
        encoded_jwt += '=='
    else:
        encoded_jwt += '='

    return json.loads(base64.b64decode(encoded_jwt))


def refresh_oauth_token(refresh_token):
    refresh_params = {
        'grant_type': 'refresh_token',
        'redirect_uri': O365_REDIRECT_URI,
        'client_id': O365_APP_ID,
        'client_secret': O365_APP_KEY,
        'refresh_token': refresh_token,
        'scope': ' '.join(str(i) for i in scopes),

    }

    r = requests.post(O365_TOKEN_URL, data=refresh_params)
    return r.json()

def make_api_call(method, url, token, payload = None, parameters = None):
    headers = {'Authorization' : 'Bearer {0}'.format(token),
              'Accept' : 'application/json',
              'Prefer' : 'outlook.body-content-type="text"',
              'Prefer' : 'outlook.timezone="W. Europe Standard Time"'
               }
    request_id = str(uuid.uuid4())  #Crear UUID aleatorio
    instrumentation = { 'client-request-id' : request_id,
                      'return-client-request-id' : 'true' }

    headers.update(instrumentation)

    response = None


    if (method.upper() == 'GET'):
      response = requests.get(url, headers = headers, params = parameters)
    elif (method.upper() == 'DELETE'):
      response = requests.delete(url, headers = headers, params = parameters)
    elif (method.upper() == 'PATCH'):
      headers.update({ 'Content-Type' : 'application/json' })
      response = requests.patch(url, headers = headers, data = json.dumps(payload), params = parameters)
    elif (method.upper() == 'POST'):
      headers.update({ 'Content-Type' : 'application/json' })
      response = requests.post(url, headers = headers, data = json.dumps(payload), params = parameters)

    return response

def get_events(access_token):
    #graph_endpoint = 'https://outlook.office.com/api/v2.0{}'
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    get_events_url = graph_endpoint.format('/me/events')    #Ruta para obtener info de los eventos
    parameters = {'$top': '10',
                      '$select': 'subject,start,end',
                      '$orderby': 'start/dateTime ASC'
                       }
    
    r = make_api_call('GET', get_events_url, access_token, parameters = parameters)
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)
