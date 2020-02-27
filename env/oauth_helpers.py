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


def datetime_from_timestamp(timestamp):
    timestamp = float(timestamp)
    return datetime.datetime.utcfromtimestamp(timestamp)


def sign_in_url():
    url_parts = list(urllib.parse.urlparse(O365_AUTH_URL))
    for i in url_parts:
        print(i)
    auth_params = {
        'scope' : ' '.join(str(i) for i in scopes),
        'response_type': 'code',
        'redirect_uri': O365_REDIRECT_URI,
        'client_id': O365_APP_ID
    }

    print(auth_params)
    url_parts[4] = urllib.parse.urlencode(auth_params)
    print('ESTO ES:' + urllib.parse.urlencode(auth_params))
    return urllib.parse.urlunparse(url_parts)


def get_oauth_token(code):
    """token_params = {
        'grant_type': 'authorization_code',
        'redirect_uri': O365_REDIRECT_URI,
        'client_id': O365_APP_ID,
        'client_secret': O365_APP_KEY,
        'code': code,
        'resource': 'https://graph.microsoft.com/'
    }"""
    token_params = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': O365_REDIRECT_URI,
        'scope': ' '.join(str(i) for i in scopes),
        'client_id': O365_APP_ID,
        'client_secret': O365_APP_KEY
    }

    print('SE VIENE')
    print(O365_TOKEN_URL)
    print(token_params)

    r = requests.post(O365_TOKEN_URL, data=token_params)
    print(r.json())
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
        'resource': 'https://graph.microsoft.com/'
    }

    r = requests.post(O365_TOKEN_URL, data=refresh_params)
    print('QUE PASAAA' + r)
    return r.json()