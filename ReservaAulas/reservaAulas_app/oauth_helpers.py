from reservaAulas_app.config import (
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
import logging
from flask import request


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
    logging.info("Superamos el refresh oauth token")

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

def get_events(access_token, calendarioId, grupoCalId):
    #graph_endpoint = 'https://outlook.office.com/api/v2.0{}'
    #graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar eventos del calendario predeterminado
    #graph_endpoint = 'https://graph.microsoft.com/v1.0/me/calendarGroup/calendars/{}'.format(calendarioId)
    #graph_endpoint = 'https://outlook.office.com/api/v2.0/me/calendars/'+calendarioId+'/calendarview?startDateTime=2019-12-31T15:54:42.915204&endDateTime=2020-12-31T15:54:42.915204'
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'
    get_events_url = graph_endpoint.format('/me/calendarGroups/'+grupoCalId+'/calendars/'+calendarioId+'/events') 
    #get_events_url = graph_endpoint.format('/me/events')    #Ruta para obtener info de los eventos
    parameters = {'$top': '50',
                      '$select': 'subject,start,end',
                      '$orderby': 'start/dateTime ASC'
                       }
    

    r = make_api_call('GET', get_events_url, access_token, parameters = parameters)
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def get_events_from_calendar(access_token, calendarId):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'
    get_events_url = graph_endpoint.format('/me/calendars/'+calendarId+'/events') 
    #get_events_url = graph_endpoint.format('/me/events')    #Ruta para obtener info de los eventos
    parameters = {'$top': '50',
                      '$select': 'subject,start,end',
                      '$orderby': 'start/dateTime ASC'
                       }
    

    r = make_api_call('GET', get_events_url, access_token, parameters = parameters)
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def get_calendarsGroups(access_token):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    get_calendar_url = graph_endpoint.format('/me/calendarGroups')    #Ruta para obtener info de los eventos

    r = make_api_call('GET', get_calendar_url, access_token)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)


def get_calendarsFromGroup(access_token, calendarGroup):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    get_calendar_url = graph_endpoint.format('/me/calendarGroups/')+calendarGroup+'/calendars'    #Ruta para obtener los calendarios

    parameters = {'$select':'name'}
    r = make_api_call('GET', get_calendar_url, access_token, parameters = parameters)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)




def get_calendars(access_token):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    get_calendar_url = graph_endpoint.format('/me/calendars')    #Ruta para obtener los calendarios

    params = {"$top":'50'}

    r = make_api_call('GET', get_calendar_url, access_token, parameters=params)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)


def create_events(access_token, calendario, subject, start, end):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    create_events_url = graph_endpoint.format('/me/calendars/') + calendario + '/events'   #Ruta para crear los eventos en el calendario especificado
    

    print('PARAMS')
    print(create_events_url)
    print(subject)
    print(start)

    payload = {'Subject': '{}'.format(subject),
                    'Start': 
                      {
                          'DateTime': '{}'.format(start),
                          'TimeZone': 'W. Europe Standard Time'
                      },
                    'End': 
                      {
                          'DateTime': '{}'.format(end),
                          'TimeZone': 'W. Europe Standard Time'
                      }                       }


    print(payload)
    #param = json.dumps(parameters)
    #print(param)

    r = make_api_call('POST', create_events_url , access_token , payload = payload )

    print(r)
    if (r.status_code == requests.codes.ok):
            return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)



def get_user(access_token):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    get_calendar_url = graph_endpoint.format('/me')    #Ruta para obtener informacion sobre el usuario

    parameters = {'$select': 'id_token' }

    r = make_api_call('GET', get_calendar_url, access_token, parameters = parameters)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def create_aulas(access_token, edificio, nombre):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    create_calendar_url = graph_endpoint.format('/me/calendarGroups/')+edificio+'/calendars'   #Ruta para obtener informacion sobre el usuario   

    # headers = {'Content-type': 'application/json'}
    payload = {"name": nombre }

    r = make_api_call('POST', create_calendar_url, access_token, payload = payload)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

    
def upload_calendar(access_token, aulaId, nuevoNombre):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    upload_calendar_url = graph_endpoint.format('/me/calendars/')+aulaId  #Ruta para obtener informacion sobre el usuario   

    payload = {"Name": nuevoNombre }

    r = make_api_call('PATCH', upload_calendar_url, access_token, payload = payload)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def delete_calendar(access_token, aulaId):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    delete_calendar_url = graph_endpoint.format('/me/calendars/')+aulaId  #Ruta para obtener informacion sobre el usuario   


    r = make_api_call('DELETE', delete_calendar_url, access_token)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def delete_event(access_token, aulaId, eventId):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    delete_event_url = graph_endpoint.format('/me/calendars/')+aulaId+'/events/'+eventId  #Ruta para obtener informacion sobre el usuario   

    r = make_api_call('DELETE', delete_event_url, access_token)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def send_email(access_token, email, aula, tema, inicio, fin):
     
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    send_email_url = graph_endpoint.format('/me/sendMail')  #Ruta para obtener informacion sobre el usuario   

    payload = {
        "message": {
            "subject": "Reserva de aula",
            "body": {
                "contentType": "Text",
                "content": "Se ha realizado una reserva sobre el aula " + aula + " con la descripción '"+tema+"', el día "+str(inicio)+" hasta "+str(fin)
            },
            "toRecipients": [
            {
                "emailAddress": {
                    "address": email
                }
            }],
               
        }
    }

    r = make_api_call('POST', send_email_url, access_token, payload)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)


def share_calendar(access_token):
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    share_calendar_url = graph_endpoint.format('/users/gestCalendar@outlook.com/calendar/calendarPermissions')  #Ruta para obtener informacion sobre el usuario   
    
    r = make_api_call('GET', share_calendar_url, access_token)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)

def modificar_evento(access_token, evento_id, calendario_id, tema, fechaIni, fechaFin):
    print("FECHIT")
    print(fechaIni)
    print(fechaFin)
    graph_endpoint = 'https://graph.microsoft.com/v1.0{}'   #Ruta para solicitar info a la API
    modificar_evento_url = graph_endpoint.format('/me/calendars/'+ calendario_id+'/events/'+evento_id)  #Ruta para obtener informacion sobre el usuario   
    
    payload = {
        "subject":tema,
        "start": {'DateTime': '{}'.format(fechaIni),
                          'TimeZone': 'W. Europe Standard Time' 
        },
        "end": {'DateTime': '{}'.format(fechaFin),
                          'TimeZone': 'W. Europe Standard Time' }
               
    }

    r = make_api_call('PATCH', modificar_evento_url, access_token, payload = payload)
    
    if (r.status_code == requests.codes.ok):
        return r.json()
    else:
        return "{0}: {1}".format(r.status_code, r.text)