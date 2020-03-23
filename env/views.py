from __init__ import app,db
import flask
from models import user, eventos
from oauth_helpers import (
    datetime_from_timestamp,
    get_oauth_token,
    get_jwt_from_id_token,
    sign_in_url,
    get_events,
    refresh_oauth_token,
    get_calendars,
    create_events
    )
import forms
import json
from flask import flash, request, redirect
from datetime import datetime

@app.route('/')
def hello_world():
    return flask.render_template('home.html', o365_sign_in_url=sign_in_url())


@app.route('/connect/get_token/')
def connect_o365_token():
    code = flask.request.args.get('code')
    print('code: '+code)
    if not code:
        app.logger.error("NO 'code' VALUE RECEIVED")
        return flask.Response(status=400)

    token = get_oauth_token(code)
    print(token.keys())
    jwt = get_jwt_from_id_token(token['id_token']) #JSON Web Token

    #oauth_token = O365OAuthToken.query.filter(O365OAuthToken.user_email == jwt['email']).first()
    oauth_token = user.query.filter(user.email == jwt['email']).first() #Si existe token para un usuario, se obtiene de DB el modelo user correspondiente
    

    if not oauth_token:
        app.logger.info('CREATING new O365OAuthToken for {}'.format(jwt['email']))
        oauth_token = user(
            access_token = token['access_token'],
            refresh_token = token['refresh_token'],
            email = jwt['email'],
            expires_on = datetime_from_timestamp(token['expires_in']),
        )
        db.session.add(oauth_token)
    else:
        app.logger.info('UPDATING existing O365OAuthToken for {}'.format(jwt['email']))
        oauth_token.access_token = token['access_token']
        oauth_token.refresh_token = token['refresh_token']
        oauth_token.expires_on = datetime_from_timestamp(token['expires_in'])
        #oauth_token.token_type = token['token_type']
        #oauth_token.scope = token['scope']
    
    db.session.commit()

    flask.session['user_email'] = oauth_token.email
    flask.session['access_token'] = oauth_token.access_token
    flask.session['refresh_token'] = oauth_token.refresh_token
    return flask.redirect('/')

@app.route('/events')
def events():
    acc_token = flask.session['access_token']
    last_url = request.referrer
    print(last_url)
    if not acc_token:
        return flask.redirect('/')
    else:
        info = get_events(acc_token)
        print(info)
        context = { 'events': info['value'] } #Obtener solo los eventos    
        eventosExistentes = context['events']
        json1_data = json.dumps(eventosExistentes) #Transformar los datos del JSON en un dict
        print(json1_data)

        return flask.render_template('events.html', dictEvents = eventosExistentes, last_url = last_url)


@app.route('/calendars', methods=['GET', 'POST'])
def calendars():

    calendars = get_calendars(flask.session['access_token'])
    valores = calendars['value']  

    createEventForm = forms.createEventForm()

    listaCalendarios = []
    for cal in valores:
        listaCalendarios.append((cal['id'],cal['name']))
    diccCalendarios = dict(listaCalendarios)
       

    createEventForm.selectCalendar.choices = listaCalendarios
    if request.method == 'POST':
        calendario = request.form["selectCalendar"]
        tema = request.form["subject"]
        horaIni = request.form["start"]
        horaFin = request.form["end"]
        evento = create_events(flask.session['access_token'], calendario, tema, horaIni, horaFin)

        evento = eventos(
            calendario = diccCalendarios[calendario],
            email = flask.session['user_email'],
            inicio = request.form["start"],
            fin = request.form["end"],
            creacion = datetime.now(),
        )
        db.session.add(evento)
        db.session.commit()

        return flask.render_template('calendars.html', form = createEventForm)
    else:
        return flask.render_template('calendars.html', form = createEventForm)




if __name__ == '__main__':
    db.init_app(app)

    with app.app_context():
        db.create_all()
    app.run()