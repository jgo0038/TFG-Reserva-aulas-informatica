from . import app, db#, connection, engine
import flask
from reservaAulas_app.models import User, Eventos, Edificios
from sqlalchemy.exc import OperationalError
from .oauth_helpers import (
    datetime_from_timestamp,
    get_oauth_token,
    get_jwt_from_id_token,
    sign_in_url,
    get_events,
    refresh_oauth_token,
    get_calendars,
    create_events,
    get_calendarsGroups,
    get_calendarsFromGroup,
    get_user,
    create_aulas,
    upload_calendar,
    delete_calendar,
    send_email,
    share_calendar,
    get_events_from_calendar,
    delete_event,
    modificar_evento
    )
from reservaAulas_app.forms import createEventForm, selectCalendar, selectGroupCalendar, filterAulasForm, createNewAula, modificarAulasForm, filterAulasForm2, modificarEvent,modificarPropietarioForm, anadirPropietarioForm,filtrarHoras,filtrarAulas
import json
from flask import flash, request, redirect, url_for
from datetime import datetime, timedelta  
from flask_wtf.csrf import CSRFProtect
from reservaAulas_app.config import ADMIN_USERS
from reservaAulas_app.odbctest import cnxn
from reservaAulas_app.getSQLData import getCapacidades,getEdificios,getPropietarios,getTipos,getEdificiosProp,getPropietariosEmail
import logging
import requests
import re
import webbrowser

@app.route('/')
def inicio():
    try:
        logging.basicConfig(filename='log_web_app.log', format='[|%(asctime)s| - %(name)s - %(levelname)s] - %(message)s', level=logging.INFO)
    except Exception as ex:
        logging.warning('Fallo en la conexion: ' + ex) 
    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT propietarios.email
    FROM propietarios;
    ''' )
    usuariosReservar = cursor.fetchall()
    listaUsuariosReservar = []
    for us in usuariosReservar:
        listaUsuariosReservar.append(us[0].strip())
    print("LISTA RESERVADORES")
    print(listaUsuariosReservar)
    flask.session['listaUsuariosPropietarios'] = listaUsuariosReservar
    cursor.close()  
    return flask.render_template('home.html', o365_sign_in_url=sign_in_url(), ADMIN_USERS=ADMIN_USERS)


@app.route('/cerrarSesion')
def cerrarSesion():
    flask.session.clear()
    return flask.render_template('home.html', o365_sign_in_url=sign_in_url())

@app.route('/connect/get_token')
def connect_o365_token():
    try:
        logging.basicConfig(filename='log_web_app.log', format='[|%(asctime)s| - %(name)s - %(levelname)s] - %(message)s', level=logging.INFO)
        logging.info('\n')
        logging.info('Redirect para coger token ')
    except Exception as ex:
        logging.warning('Fallo en la conexion: ' + ex)
    code = flask.request.args.get('code')

    if not code:
        logging.error("NO SE HA RECIBIDO EL 'code'")
        return flask.Response(status=400)

    token = get_oauth_token(code)
    jwt = get_jwt_from_id_token(token['id_token']) #JSON Web Token
    logging.info("EMAIL:")
    logging.info(jwt)
    logging.info(jwt['email'])
    # oauth_token = User.query.filter(User.email == jwt['email']).first() #Si existe token para un usuario, se obtiene de DB el modelo user correspondiente
    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT [dbo].[user].[access_token],[dbo].[user].[refresh_token],[dbo].[user].[email],[dbo].[user].[expires_on]
    FROM [dbo].[user]
    WHERE [dbo].[user].[email] = ?; 
    ''' , jwt['email'])
    oauth_token = cursor.fetchall()
    cursor.close()    
    logging.info('Oauth token:')
    logging.info(oauth_token)   
    if not oauth_token:
        logging.info('CREATING new O365OAuthToken for {}'.format(jwt['email']))

        expires_on = datetime_from_timestamp(token['expires_in'])
        cursor = cnxn.cursor()
        cursor.execute('''
        INSERT into [dbo].[user] (access_token, refresh_token, email, expires_on)
        values(?, ?, ?, ?); 
        ''' , token['access_token'], token['refresh_token'], jwt['email'], expires_on )
        cursor.commit()
        cursor.close()    
        flask.session['user_email'] = jwt['email']
        flask.session['refresh_token'] = token['refresh_token']      
        flask.session['access_token'] = token['access_token']
        flask.session['invitado'] = False

    else:
        ref_token = refresh_oauth_token(token['refresh_token'])
        jwtToken = get_jwt_from_id_token(ref_token['id_token'])
        flask.session['user_email'] = jwtToken['email']
        flask.session['refresh_token'] = ref_token['refresh_token']       
        flask.session['access_token'] = ref_token['access_token']
        flask.session['invitado'] = False

    listaProv = []
    flask.session['listaAulasReservar'] = listaProv
    return flask.redirect('/')

@app.route('/events', methods=['GET', 'POST'])
def events():

    selectEdificioForm = selectGroupCalendar() 
    filterForm = filterAulasForm2()
    modificarEventForm = modificarEvent()
    filterForm.tipo.choices = getTipos()
    cursor = cnxn.cursor()

    queryEdificios = '''
    SELECT id_edificio
    FROM edificios;
    '''
    cursor.execute(queryEdificios)
    varEdif = cursor.fetchall()
    cursor.close()
    listaGruposCalendarios = []
    for cal in varEdif:
        listaGruposCalendarios.append(cal[0])
    selectEdificioForm.select.choices = listaGruposCalendarios

    #sacamos los propietarios para pasarlos al cliente
    propietarios = getPropietariosEmail()
    print(propietarios)
    varPropEventos = ['notienepropietario@a.es']
    listaAulasProp = ['aulaquenopertenece']

    eventosExistentes = {}
    fechaActual = datetime.now()
    
    #Variables para mostrar el resultado de la modificación
    error_solapamiento = False
    modif = False
    #Modificar eventos
    if request.method == 'POST' and modificarEventForm.submit.data :
        temaNuevo = request.form["tema"]
        userNuevo = request.form["user"]
        fechaIniNueva = request.form["fechaIni"]
        horaIniNueva = request.form["horaIni"]
        horaFinNueva = request.form["horaFin"]
        fechaIniNuevaFinal = datetime.strptime(fechaIniNueva + " "  + horaIniNueva ,'%Y-%m-%d %H:%M') #Convertirlo la fecha y hora en datetime
        fechaFinNuevaFinal = datetime.strptime(fechaIniNueva + " "  + horaFinNueva ,'%Y-%m-%d %H:%M')
        if horaIniNueva < horaFinNueva:
            if flask.session['fechaIniEventMod'] != fechaIniNuevaFinal or flask.session['fechaFinEventMod'] != fechaFinNuevaFinal:
                cursor = cnxn.cursor()
                cursor.execute('''SELECT count(*)
                FROM eventos
                WHERE eventos.aula = ?
                AND eventos.inicio < ?
                AND eventos.fin > ?
                EXCEPT SELECT count(*)
                FROM eventos
                WHERE eventos.aula = ?
                AND eventos.inicio = ?
                ''',flask.session['aulaEventMod'],fechaFinNuevaFinal, fechaIniNuevaFinal,flask.session['aulaEventMod'],flask.session['fechaIniEventMod'])
                varAulas = cursor.fetchall()
                print(varAulas)
                #Si no hay solapamientos
                if varAulas == [] or varAulas[0][0] == 0:
                    modificar_evento(flask.session['access_token'],flask.session['id_evento_modificar'],flask.session['id_aula_modificar'],temaNuevo, horaIniNueva, horaFinNueva)
                    modif = True
                    cursor = cnxn.cursor()
                    cursor.execute('''
                        UPDATE eventos
                        SET eventos.evento = ?, eventos.inicio = ?, eventos.fin = ?, eventos.profesor = ?
                        WHERE eventos.aula = ? AND eventos.inicio = ? AND eventos.fin = ?'''
                        , temaNuevo, fechaIniNuevaFinal, fechaFinNuevaFinal, userNuevo, flask.session['aulaEventMod'], flask.session['fechaIniEventMod'], flask.session['fechaFinEventMod'])
                    cnxn.commit()

                    cursor = cnxn.cursor()
                    cursor.execute('''
                    SELECT id
                    FROM eventos
                    WHERE aula = ? AND inicio = ? AND fin = ?
                    ''', flask.session['aulaEventMod'],fechaIniNuevaFinal,fechaFinNuevaFinal)
                    varIdEvento = cursor.fetchall()
                    cursor.close()

                    cursor = cnxn.cursor()
                    cursor.execute('''
                    INSERT INTO
                    auditoria(id_evento,usuario,fecha_modif,identificador) 
                    VALUES
                    (?,?,?,?)''', varIdEvento[0][0], flask.session['user_email'],datetime.now(),'MODIF')
                    cnxn.commit()
                    cursor.close()
                    db.session.commit()
                    
                else:
                    error_solapamiento = True
                    modif = False  
                if error_solapamiento == True:
                    return flask.render_template('errorModificarEvento.html')
                elif modif == True:
                    return flask.render_template('events.html',modif=True, dictEvents = eventosExistentes,formEdificio = selectEdificioForm, fechaActual = fechaActual, filterForm = filterForm, modEventForm= modificarEventForm )

            else:
                modificar_evento(flask.session['access_token'],flask.session['id_evento_modificar'],flask.session['id_aula_modificar'],temaNuevo, fechaIniNuevaFinal, fechaFinNuevaFinal)
                cursor = cnxn.cursor()
                cursor.execute('''
                    UPDATE eventos
                    SET eventos.evento = ?, eventos.inicio = ?, eventos.fin = ?, eventos.profesor = ?
                    WHERE eventos.aula = ? AND eventos.inicio = ? AND eventos.fin = ?'''
                    , temaNuevo, fechaIniNuevaFinal, fechaFinNuevaFinal, userNuevo, flask.session['aulaEventMod'], flask.session['fechaIniEventMod'], flask.session['fechaFinEventMod'])
                cnxn.commit() 
                cursor = cnxn.cursor()
                cursor.execute('''
                SELECT id
                FROM eventos
                WHERE aula = ? AND inicio = ? AND fin = ?
                ''', flask.session['aulaEventMod'],fechaIniNuevaFinal,fechaFinNuevaFinal)
                varIdEvento = cursor.fetchall()
                cursor.close()
                cursor = cnxn.cursor()
                cursor.execute('''
                INSERT INTO
                auditoria(id_evento,usuario,fecha_modif,identificador) 
                VALUES
                (?,?,?,?)''', varIdEvento[0][0], flask.session['user_email'],datetime.now(),'MODIF')
                cnxn.commit()
                cursor.close()
                db.session.commit()

                modif = True   
                error_solapamiento = False
                if error_solapamiento == True:
                    return flask.render_template('errorModificarEvento.html')
                elif modif == True:
                    return flask.render_template('events.html',modif=True, dictEvents = eventosExistentes,formEdificio = selectEdificioForm, fechaActual = fechaActual, filterForm = filterForm, modEventForm= modificarEventForm )
        else:
            return flask.render_template('errorModificarEvento.html')

    #Primera eleccion (edificio)
    if selectEdificioForm.submit and request.method == 'POST' and "submitEdif" in request.form:

        edificioId = request.form['select']
        flask.session['edifEventos'] = edificioId

        cursor = cnxn.cursor()
        cursor.execute('''SELECT aulas.nombre
        FROM aulas
        WHERE aulas.edificio = ? ''',edificioId)
        varAulas = cursor.fetchall()
        cursor.close()  
        nombreAulas = [] 
        nombreAulas.append(('Cualquiera','Cualquiera'))
        for elem in varAulas:        
            nombreAulas.append((elem[0],elem[0]))
        filterForm.select.choices = nombreAulas
        return flask.render_template('events.html',edificioId = edificioId, dictEvents = eventosExistentes,formEdificio = selectEdificioForm,fechaActual = fechaActual, filterForm =filterForm)

    #Segunda eleccion(aula)
    # if selectForm.submit and request.method == 'POST' and "submitAula" in request.form:
    if filterForm.submit and request.method == 'POST':

        capacidad = request.form["capacidad"]
        n_ord = request.form["n_ord"]
        tipo = request.form["tipo"]
        fechaIni = request.form["startDate"]
        fechaF = request.form["endDate"]
        horaIni = request.form["startTime"]
        horaFin = request.form["endTime"]
        if fechaIni != "":
            fechaInicio = datetime.strptime(fechaIni + " "  + horaIni ,'%Y-%m-%d %H:%M') #Convertirlo la fecha y hora en datetime
            fechaFin = datetime.strptime(fechaIni + " "  + horaFin ,'%Y-%m-%d %H:%M')
            fechaInicioDiv = fechaIni.split("-")
            fechaFinDiv = fechaF.split("-")
            mesI = fechaInicioDiv[1]
            diaI = fechaInicioDiv[2]
            mesF = fechaFinDiv[1]
            diaF = fechaFinDiv[2]
        horaInicio = horaIni.split(":")
        horaFinal = horaFin.split(":")    
        calendarioId = request.form["select"] #Recoger el calendario id del calendario elegido
        
        if calendarioId != "Cualquiera":
            cursor = cnxn.cursor()
            cursor.execute('''
            SELECT aulas.nombre
            FROM aulas
            JOIN propietarios ON aulas.propietario = propietarios.id_propietario
            WHERE propietarios.email = ?;''',flask.session['user_email'])
            vasAulasProp = cursor.fetchall()
            cursor.close()
            listaAulasProp = []
            for var in vasAulasProp:
                listaAulasProp.append(var[0])
        # CAMBIO DE CONEXION BD AZURE, AL TENER PARAMETROS HAY QUE CAMBIAR LA FOMRA EN QUE SE EJECUTA
            cursor = cnxn.cursor()
            cursor.execute('''
            SELECT *
            FROM eventos
            WHERE eventos.aula = ?;''',calendarioId)
            varEventos = cursor.fetchall()
            cursor.close() 

            cursor = cnxn.cursor()
            cursor.execute('''
            SELECT propietarios.email
            FROM propietarios 
            JOIN aulas ON propietarios.id_propietario = aulas.propietario
            WHERE aulas.nombre = ?;''',calendarioId)
            varPropEventos = cursor.fetchall()
            cursor.close() 
            varEventos = tuple(sorted(varEventos, key=lambda item: item[4])) #Ordenar segun la fecha
    #Filtros

            cursor = cnxn.cursor()

            if fechaIni != "":
                fechaF = datetime.strptime(fechaF ,'%Y-%m-%d')
                fechaF = fechaF + timedelta(days=1)
                cursor.execute('''
                SELECT * from eventos
                WHERE eventos.aula = ?
                AND cast(eventos.inicio as time) < ? AND ? < cast(eventos.fin as time)
                AND eventos.inicio BETWEEN ? AND  ?;
                ''', calendarioId, horaFin ,horaIni,fechaIni, fechaF)

                varEventos = cursor.fetchall()
                cursor.close() 

                varEventos = tuple(sorted(varEventos, key=lambda item: item[4]))
            return flask.render_template('eventsTable.html',target="_blank",listaProp = propietarios, propietario = varPropEventos,aulasProp = listaAulasProp, dictEvents = varEventos,formEdificio = selectEdificioForm, fechaActual = fechaActual, filterForm=filterForm, modEventForm= modificarEventForm )
        elif calendarioId == "Cualquiera":

            cursor = cnxn.cursor()
            cursor.execute('''
            SELECT aulas.nombre
            FROM aulas
            JOIN propietarios ON aulas.propietario = propietarios.id_propietario
            WHERE propietarios.email = ?;''',flask.session['user_email'])
            vasAulasProp = cursor.fetchall()
            cursor.close()
            listaAulasProp = []
            for var in vasAulasProp:
                listaAulasProp.append(var[0])
            edificioIdQuery = flask.session['edifEventos']+"%"
            if fechaIni != "":
                print(tipo)
                fechaInicio = datetime.strptime(fechaIni + " "  + horaIni ,'%Y-%m-%d %H:%M') #Convertirlo la fecha y hora en datetime
                fechaFin = datetime.strptime(fechaIni + " "  + horaFin ,'%Y-%m-%d %H:%M')
                fechaF = datetime.strptime(fechaF ,'%Y-%m-%d')
                fechaF = fechaF + timedelta(days=1)
                cursor = cnxn.cursor()
                cursor.execute('''
                SELECT * from eventos 
                JOIN aulas ON eventos.aula = aulas.nombre
                where aulas.capacidad >= ?
                
                AND aulas.edificio = ?
                AND aulas.n_ordenadores >= ?
                AND aulas.tipo = ?
                AND cast(eventos.inicio as time) < ? AND ? < cast(eventos.fin as time)
                AND eventos.inicio BETWEEN ? AND  ?;''',capacidad,flask.session['edifEventos'], n_ord, tipo,horaFin ,horaIni,fechaIni, fechaF)
                varEventos = cursor.fetchall()
                cursor.close() 
            
                varEventos = tuple(sorted(varEventos, key=lambda item: item[4]))
            return flask.render_template('eventsTable.html',target="_blank", listaProp = propietarios,propietario = varPropEventos,aulasProp = listaAulasProp, dictEvents = varEventos,formEdificio = selectEdificioForm, fechaActual = fechaActual, filterForm=filterForm, modEventForm= modificarEventForm )

    if error_solapamiento == True:
        return flask.render_template('errorModificarEvento.html')
    elif modif == True:
        return flask.render_template('events.html',modif=True, dictEvents = eventosExistentes,formEdificio = selectEdificioForm, fechaActual = fechaActual, filterForm = filterForm, modEventForm= modificarEventForm )
    else:
        return flask.render_template('events.html', dictEvents = eventosExistentes,formEdificio = selectEdificioForm, fechaActual = fechaActual, filterForm = filterForm)

@app.route('/errorModificarEvento')
def errorModificarEvento():
    return flask.render_template('errorModificarEvento.html')

@app.route('/modificarEvento', methods=['POST'])
def modificarEvento():
    modificarEventForm = modificarEvent()
    data = flask.request.get_json()

    
    if data:
        flask.session['aulaEventMod'] = data['aula']
    # flask.session['fechaIniEventMod'] = data['fechaIni']
    # flask.session['fechaFinEventMod'] = data['fechaF']
        flask.session['fechaIniEventMod'] = datetime.strptime(data['fechaIni'] + " "  + data['horaIni'] ,'%Y-%m-%d %H:%M')
        flask.session['fechaFinEventMod'] = datetime.strptime(data['fechaIni'] + " "  + data['horaFin'] ,'%Y-%m-%d %H:%M')

    nuevoToken = refresh_oauth_token(flask.session['refresh_token'])
    flask.session['access_token'] = nuevoToken['access_token']
    calendarios = get_calendars(flask.session['access_token'])
    calendarios = calendarios['value']
    
    for cal in calendarios:
        if cal['name'] == data['aula']:
            id_cal = cal['id']
            flask.session['id_aula_modificar'] = id_cal
    eventos = get_events_from_calendar(flask.session['access_token'], id_cal)
    print(eventos)
    eventos = eventos['value']
    
    for eve in eventos:
        fecha = eve['start']['dateTime'].split("T")
        dia = fecha[0]
        fechaFormat = fecha[1].split(".")
        fechaI = datetime.strptime(dia + " "  + fechaFormat[0] ,'%Y-%m-%d %H:%M:%S')

        print(flask.session['fechaIniEventMod'])
        if fechaI == flask.session['fechaIniEventMod']:
            id_evento = eve['id']
            flask.session['id_evento_modificar'] = id_evento
        
    return json.dumps(data)
    

@app.route('/borrarEvento',methods=['POST'])
def borrarEvento():
    data = flask.request.get_json()
    if data:
        listaBorrar = data['listaBorrar']

        nuevoToken = refresh_oauth_token(flask.session['refresh_token'])
        flask.session['access_token'] = nuevoToken['access_token']
        calendarios = get_calendars(flask.session['access_token'])
        calendarios = calendarios['value']

        for eventoBorrar in listaBorrar:
            cursor = cnxn.cursor()
            cursor.execute('''
            INSERT INTO
            auditoria(id_evento,usuario,fecha_modif,identificador) 
            VALUES
            (?,?,?,?)''', eventoBorrar, flask.session['user_email'],datetime.now(),'BAJA')
            cnxn.commit()
            cursor.close()
            db.session.commit()

            #Borrar de BD
            cursor = cnxn.cursor()
            cursor.execute('''
                DELETE
                FROM eventos
                WHERE eventos.id = ? ''', eventoBorrar)
            cnxn.commit()
            borrado = True

        if borrado == True:
            return json.dumps({'success':True}), 200
    return json.dumps({'success':False}), 404

@app.route('/showReservar',methods=['POST'])
def showReservar():
    #Distinta consulta SQL si es admin o responsable
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT propietarios.email
        FROM propietarios;
    ''')
    varEmailPropietarios = cursor.fetchall()
    listaEmailsProp = []
    # listaAulas = [var for var in varAulas]
    for var in varEmailPropietarios:
        listaEmailsProp.append(var[0].strip())
    print("PROPIETARIOS")
    print(listaEmailsProp)
    data = flask.request.get_json()
    print(data)
    capacidad = data['capacidad']
    ordenadores = data['n_ord']
    edificio = data['edificio']
    tipo = data['tipo']
    #Si es admin, mostrar las aulas con las caracteristicas pedidas
    if flask.session['user_email'] in ADMIN_USERS:
        if tipo != "Vacio":
            cursor = cnxn.cursor()
            cursor.execute('''
                SELECT aulas.nombre
                FROM aulas
                WHERE aulas.capacidad >= ? AND aulas.edificio = ? AND aulas.tipo = ? AND aulas.n_ordenadores >= ?;
            ''',capacidad, edificio, tipo, ordenadores)
            varAulas = cursor.fetchall()
        elif tipo == "Vacio":
            cursor = cnxn.cursor()
            cursor.execute('''
                SELECT aulas.nombre
                FROM aulas
                WHERE aulas.capacidad >= ? AND aulas.edificio = ? AND aulas.n_ordenadores >= ?;
            ''',capacidad, edificio, ordenadores)
            varAulas = cursor.fetchall()
        listaAulas = []
        if len(varAulas) > 1:
            listaAulas.append(('Cualquiera','Cualquiera'))
        for var in varAulas:
            listaAulas.append((var[0],var[0]))
        print("VAR A RESERVAR")
        print(listaAulas)
        if varAulas:
            flask.session['listaAulasReservar'] = listaAulas
            # return json.dumps({'success':True}), 200
            return json.dumps(listaAulas)
        else:
            return json.dumps({'success':False}), 404
    #Si es responsable, consulta para ver las aulas que puede reservar si coinciden con las caracteristicas pedidas
    elif flask.session['user_email'] in listaEmailsProp :
        print("Somos propietario")
        #Aulas segun las caracteristicas
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT aulas.nombre
            FROM aulas
            WHERE aulas.capacidad >= ? AND aulas.edificio = ? AND aulas.tipo = ? AND aulas.n_ordenadores >= ?;
        ''',capacidad, edificio, tipo, ordenadores)
        varAulasCaract = cursor.fetchall()
        listaAulasCaract = []
        if len(varAulasCaract) > 1:
            listaAulasCaract.append(('Cualquiera','Cualquiera'))
        for var in varAulasCaract:
            listaAulasCaract.append((var[0],var[0]))
        #Aulas según el responsable
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT aulas.nombre
            FROM aulas
            JOIN edificios ON aulas.edificio = edificios.id_edificio
            JOIN propietarios ON aulas.propietario = propietarios.id_propietario
            WHERE propietarios.email= ?
            UNION 
            SELECT responsables.nombre
            FROM responsables
            JOIN propietarios ON responsables.id_propietario = propietarios.id_propietario
            WHERE propietarios.email = ?;''',flask.session['user_email'],flask.session['user_email'])
        varAulasResp = cursor.fetchall()
        listaAulasResp = []
        for var in varAulasResp:
            listaAulasResp.append((var[0],var[0]))
        #Comprobar que aulas puede reservar y coincide con las caracteristicas
        listaAulasReservar = []
        print(listaAulasResp)
        print(listaAulasCaract)
        for aulaR in listaAulasResp:
            if aulaR in listaAulasCaract:
                listaAulasReservar.append(aulaR)
        if listaAulasReservar:
            flask.session['listaAulasReservar'] = listaAulasReservar
            return json.dumps(listaAulasReservar)
        else:
            return json.dumps({'success':False}), 404


@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    #PRIMER FORMULARIO
    logging.info("Entramos a reservar") 
    filterForm = filterAulasForm()
    #Rellenar capacidades
    filterForm.capacidad.choices = getCapacidades()

    #Rellenar edificios
    if flask.session['user_email'] in ADMIN_USERS:
        filterForm.edificio.choices = getEdificios()
    else:
        filterForm.edificio.choices = getEdificiosProp(flask.session['user_email'])

    #Rellenar tipo
    filterForm.tipo.choices = getTipos()

    valorRadio = None
    if flask.request.get_json():
        data = flask.request.get_json()
        valorRadio = data['valorRadio']
        print("VALOR RADIO")
        print(valorRadio)

    #SEGUNDO FORMULARIO

    if(flask.request.args.get("response")):
        param = flask.request.args.get("response")
        listaParametros = list(param.keys())
        listaAulas = []
        for p in listaParametros:
            listaAulas=json.loads(p)

        
    eventForm = createEventForm()
    listaDias = [(None,"Selecciona un día"),(0,"Lunes"),(1,"Martes"),(2,"Miercoles"),(3,"Jueves"),(4,"Viernes"),(5,"Sabado"),(6,"Domingo")]
    eventForm.day.choices = listaDias
    logging.info("RESERVAR")
    try:
        calendars = get_calendars(flask.session['access_token']) #Reocgemos todos los calendarios
        logging.info(calendars)
        valores = calendars['value']  #Sacamos sus valores del diccionario recibido

        listaCalendarios = []
        for cal in valores:
            #Añadir todos los calendarios menos los que venian predefinidos en outlook (no se pueden borrar)
            if cal['name'] != "Calendario" and cal['name'] != "Días festivos de España" and cal['name'] != "Cumpleaños":
                listaCalendarios.append((cal['id'],cal['name'])) 
    except Exception:
        nuevoToken = refresh_oauth_token(flask.session['refresh_token'])
        flask.session['access_token'] = nuevoToken['access_token']
        return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)
    diccCalendarios = dict(listaCalendarios) #Creamos un diccionario para poder sacar el nombre del aula a partir del aulaId
    keys_dicc = list(diccCalendarios.keys()) 
    vals_dicc= list(diccCalendarios.values()) 

    
    logging.info(flask.session['listaAulasReservar']) 
    eventForm.selectAula.choices = flask.session['listaAulasReservar']
    if request.method == 'POST': #Si se da al boton submit se recogen los datos y depende los campos llenos se llama a create_events de una u otra forma

            aulaId = request.form["selectAula"]
            tema = request.form["subject"]
            profesor = request.form["teacher"]
            email_prof = request.form["email"]
            fechaIni = request.form["startDate"]
            horaIni = request.form["startTime"]
            horaFin = request.form["endTime"]
            diaSemana = request.form["day"]
            fechaFin = request.form["startDate"] #La fecha fin será la misma que la fecha inicio (mismo dia la reserva)

            if request.form["endDate"] != "":
                fechaFin = request.form["endDate"]

            if fechaIni and fechaFin and horaFin and horaIni:
                print("asignamos fechainicio")
                fechaInicio = datetime.strptime(fechaIni + " "  + horaIni ,'%Y-%m-%d %H:%M') #Convertirlo la fecha y hora en datetime
                fechaFin = datetime.strptime(fechaFin + " "  + horaFin ,'%Y-%m-%d %H:%M') #Convertirlo la fecha y hora en datetime
            
            # Comprobar si el email es valido
            regex = '^[^@]+@[^@]+\.[a-zA-Z]{2,}$'
            if(re.search(regex,email_prof)): 
                print("Email valido")
            else:
                print("Email no valido")
                # return flask.render_template('reservar.html', form = eventForm, form1 = filterForm, emailVal = False,validate = False)

            
            
            if aulaId != 'Cualquiera':
                aula = aulaId
                print(keys_dicc[vals_dicc.index(aulaId)])
                print(keys_dicc)
                if keys_dicc[vals_dicc.index(aulaId)] in keys_dicc:
                    aulaId = keys_dicc[vals_dicc.index(aulaId)]
                else:
                    return flask.render_template('errorPermisos.html')
            else:
                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm, aula = False, validate= False)



            #Si el cuestionario es valido y la fechaFin ni el dia existen -> Reservar solo para un día
            # if eventForm.validate_on_submit() and request.form["endDate"] == None and diaSemana == None:
            
            eventForm.validate_on_submit()
            #reserva simple
            if aulaId != "" and aulaId != "Cualquiera" and tema!= "" and profesor!= "" and fechaIni!= "" and horaIni!= "" and horaFin!= "" and request.form["endDate"] == "" and diaSemana == "None":
                print("Reserva Simple")
                cursor = cnxn.cursor()
                cursor.execute('''
                SELECT nombre
                FROM aulas WITH (HOLDLOCK)
                WHERE nombre = ?; ''', aula)
                varBloqueo = cursor.fetchall()
                cursor.close()
                
                cursor = cnxn.cursor()
                cursor.execute('''
                SELECT count(*)
                FROM eventos 
                WHERE aula = ?
                AND ( inicio < ? )
                AND ( fin > ? );
                ''', aula, fechaFin, fechaInicio)
                varSolapamiento = cursor.fetchall()
                cursor.close()
                


                if(varSolapamiento[0][0] == 0):   #Si devuelve 0 filas, es que la hora esta libre
                    #Pasar el id del aula
                    evento = create_events(flask.session['access_token'], aulaId, tema, fechaInicio, fechaFin)
                    try:
                        cursor = cnxn.cursor()
                        cursor.execute('''
                        INSERT INTO
                        eventos(aula,evento,email,inicio,fin,creacion,profesor) 
                        VALUES
                        (?,?,?,?,?,?,?)''', aula, tema, flask.session['user_email'],fechaInicio,fechaFin,datetime.now(),profesor)
                        cnxn.commit()
                        cursor.close()
                        db.session.commit()
                        #Tabla auditoria

                        cursor = cnxn.cursor()
                        cursor.execute('''
                        SELECT id
                        FROM eventos
                        WHERE aula = ? AND evento = ? AND inicio = ? AND fin = ?
                        ''', aula, tema, fechaInicio,fechaFin)
                        varIdEvento = cursor.fetchall()
                        cursor.close()

                        cursor = cnxn.cursor()
                        cursor.execute('''
                        INSERT INTO
                        auditoria(id_evento,usuario,fecha_modif,identificador) 
                        VALUES
                        (?,?,?,'ALTA')''', varIdEvento[0][0], flask.session['user_email'],datetime.now())
                        cnxn.commit()
                        cursor.close()
                        db.session.commit()
                        db.session.close()
                        #Enviar mensaje
                        em = send_email(flask.session['access_token'], email_prof, aula, tema, fechaInicio, fechaFin )
                    except OperationalError:
                        db.session.rollback()
                        cnxn.rollback()
                        db.session.close()
                        return '<h1> Transaccion bloqueada demasiado tiempo </h1>'
                    flash(u'Se ha creado correctamente el evento', 'message')
                    print("AffffSDAS")

                    return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)
                else:
                    db.session.rollback()
                    cnxn.rollback()
                    # connection.rollback()
                    db.session.close()
                    # engine.dispose()
                    flash(u'No se ha podido crear el evento', 'error')
                    return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)
            #Reserva multiple
            elif aulaId != "Cualquiera" and tema!= None and profesor!= None and fechaIni!= None and horaIni!= None and horaFin!= None and request.form["endDate"] != "" and diaSemana == "None":
                #Hacer un bucle desde inicio a findate reservando 
                #FOR UPDATE
                print("Reserva multiple")

                cursor = cnxn.cursor()
                cursor.execute('''
                SELECT nombre
                FROM aulas WITH (HOLDLOCK)
                WHERE nombre = ?; ''', aula)
                varBloqueo = cursor.fetchall()
                cursor.close()
                flag = True
                listaFechasReserva = []
                horasFin = horaFin.split(':')
                horaF = int(horasFin[0])
                minF = int(horasFin[1])
                print("DATOS HORAS")
                print(horaFin)
                print(horasFin)
                print(horaF)
                print(minF)
                fechaInicioMultiple = fechaInicio
                fechaFinMultiple = fechaInicio.replace(hour=horaF,minute=minF)
                print(fechaFinMultiple)
                while fechaInicioMultiple <= fechaFin and flag == True:
                    print("MULTIPLE")
                    print(fechaFinMultiple)
                    print(fechaInicioMultiple)
                    #Consulta de solapamiento de horas para todos los dias
                    cursor = cnxn.cursor()
                    cursor.execute('''
                    SELECT count(*)
                    FROM eventos 
                    WHERE aula = ?
                    AND ( inicio < ? )
                    AND ( fin > ? );
                    ''', aula, fechaFinMultiple, fechaInicioMultiple)
                    varSolapamiento = cursor.fetchall()
                    print(varSolapamiento)
                    cursor.close()
                    #Si devuelve 0 es que esta libre la hora
                    if(varSolapamiento[0][0] == 0):
                        listaFechasReserva.append(fechaInicioMultiple)
                        fechaInicioMultiple = fechaInicioMultiple + timedelta(days=1)
                        fechaFinMultiple = fechaFinMultiple + timedelta(days=1)
                    else:#Si no esta libre, la bandera se pone a false y no se ejecuta la reserva
                        flag = False

                #Fuera del while, ver si la bandera es true o false
                if flag == True:#Reservar 

                    for fechaIniReserva in listaFechasReserva:
                        hora = int(str(fechaFin.time())[0:2]) #Sacamos la hora
                        min = int(str(fechaFin.time())[3:5]) #Sacamos los minutos
                        fechaFinReserva = fechaIniReserva.replace(hour=hora, minute = min)#Formamos la fechaFin de cada dia (el dia de reserva con la hora de fin)
                        #Se crean los eventos en el calendario
                        evento = create_events(flask.session['access_token'], aulaId, tema, fechaIniReserva, fechaFinReserva)
                        #Se guarda en eventos en BD
                        try:
                            cursor = cnxn.cursor()
                            cursor.execute('''
                            INSERT INTO
                            eventos(aula,evento,email,inicio,fin,creacion,profesor) 
                            VALUES
                            (?,?,?,?,?,?,?)''', aula, tema, flask.session['user_email'],fechaIniReserva,fechaFinReserva,datetime.now(),profesor)
                            # var = cursor.fetchall()
                            cnxn.commit()
                            cursor.close()
                            db.session.commit()
                                
                            #Tabla auditoria
                            cursor = cnxn.cursor()
                            cursor.execute('''
                            SELECT id
                            FROM eventos
                            WHERE aula = ? AND evento = ? AND inicio = ?
                            ''', aula, tema, fechaIniReserva)
                            varIdEvento = cursor.fetchall()
                            cursor.close()

                            cursor = cnxn.cursor()
                            cursor.execute('''
                            INSERT INTO
                            auditoria(id_evento,usuario,fecha_modif,identificador) 
                            VALUES
                            (?,?,?,'ALTA')''', varIdEvento[0][0], flask.session['user_email'],datetime.now())
                            cnxn.commit()
                            cursor.close()
                            db.session.commit()
                            db.session.close()
                            #Enviar mensaje
                            em = send_email(flask.session['access_token'], email_prof, aula, tema, fechaIniReserva, fechaFinReserva )


                        except OperationalError:
                            db.session.rollback()
                            # connection.rollback()
                            cnxn.rollback()
                            db.session.close()
                    flash(u'Las horas han sido reservadas', 'message')
                else:
                    flash(u'Las horas estan ocupadas', 'error')
                # flash(u'Se han creado correctamente los eventos', 'message')

                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)
            #reserva periodica
            elif aulaId != "Cualquiera" and tema!= None and profesor!= None and fechaIni!= None and horaIni!= None and horaFin!= None and request.form["endDate"] != "" and diaSemana != "None":

                fechaIni = datetime.strptime(fechaIni,'%Y-%m-%d')

                #FOR UPDATE
                cursor = cnxn.cursor()
                cursor.execute('''
                SELECT nombre
                FROM aulas WITH (HOLDLOCK)
                WHERE nombre = ?; ''', aula)
                varBloqueo = cursor.fetchall()
                cursor.close()
                flagC = True
                listaFechasReserva = []
                fechaInicioPeriodica = fechaIni
                diaSemana = int(diaSemana)
                horasIni = horaIni.split(':')
                horaI = int(horasIni[0])
                minI = int(horasIni[1])
                fechaInicioPeriodica = fechaInicioPeriodica.replace(hour=horaI, minute = minI)

                while fechaInicioPeriodica.weekday() != diaSemana:
                    fechaInicioPeriodica = fechaInicioPeriodica + timedelta(days=1) 

                while fechaInicioPeriodica <= fechaFin and flagC == True:

                    hora = int(str(fechaFin.time())[0:2])
                    min = int(str(fechaFin.time())[3:5])
                    fechaFinPeriodica = fechaInicioPeriodica
                    fechaFinPeriodica = fechaFinPeriodica.replace(hour=hora, minute = min)
                    # Comprobar que estan libres
                    cursor = cnxn.cursor()
                    cursor.execute('''
                    SELECT count(*)
                    FROM eventos 
                    WHERE aula = ?
                    AND ( inicio < ? )
                    AND ( fin > ? );
                    ''', aula, fechaFinPeriodica, fechaInicioPeriodica)
                    varSolapamiento = cursor.fetchall()
                    cursor.close()
                    #Si devuelve 0 es que esta libre la hora
                    if(varSolapamiento[0][0] == 0):
                        listaFechasReserva.append(fechaInicioPeriodica)
                        fechaInicioPeriodica = fechaInicioPeriodica + timedelta(days=7)
                    else:#Si no esta libre, la bandera se pone a false y no se ejecuta la reserva
                        flagC = False
                #Fuera del while, ver si la bandera es true o false
                if flagC == True:#Reservar 

                    for fechaIniReserva in listaFechasReserva:
                        hora = int(str(fechaFin.time())[0:2]) #Sacamos la hora
                        min = int(str(fechaFin.time())[3:5]) #Sacamos los minutos
                        fechaFinReserva = fechaIniReserva.replace(hour=hora, minute = min)#Formamos la fechaFin de cada dia (el dia de reserva con la hora de fin)
                        #Se crean los eventos en el calendario
                        evento = create_events(flask.session['access_token'], aulaId, tema, fechaIniReserva, fechaFinReserva)
                        #Se guarda en eventos en BD
                        try:
                            cursor = cnxn.cursor()
                            cursor.execute('''
                            INSERT INTO
                            eventos(aula,evento,email,inicio,fin,creacion,profesor) 
                            VALUES
                            (?,?,?,?,?,?,?)''', aula, tema, flask.session['user_email'],fechaIniReserva,fechaFinReserva,datetime.now(),profesor)
                            cnxn.commit()
                            cursor.close()
                            db.session.commit()
                            #Tabla auditoria
                            cursor = cnxn.cursor()
                            cursor.execute('''
                            SELECT id
                            FROM eventos
                            WHERE aula = ? AND evento = ? AND inicio = ?
                            ''', aula, tema, fechaIniReserva)
                            varIdEvento = cursor.fetchall()
                            cursor.close()

                            
                            cursor = cnxn.cursor()
                            cursor.execute('''
                            INSERT INTO
                            auditoria(id_evento,usuario,fecha_modif,identificador) 
                            VALUES
                            (?,?,?,'ALTA')''', varIdEvento[0][0], flask.session['user_email'],datetime.now())
                            cnxn.commit()
                            cursor.close()
                            db.session.commit()
                            #Enviar mensaje
                            em = send_email(flask.session['access_token'], email_prof, aula, tema, fechaInicio, fechaFin )
                        except OperationalError:
                            db.session.rollback()
                            cnxn.rollback()
                            db.session.close()
                    flash(u'Se han creado correctamente los eventos', 'message')    
                else:
                    flash(u'Las horas estan ocupadas', 'error')

                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)
            else:
                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm, validate = False, valorRadio=valorRadio)

    else:
        return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)





@app.route('/anadirAulas', methods=['GET', 'POST'])
def anadirAulas():

    createAulasForm = createNewAula()
    #Añadir los grupos de calendarios (edificios) a la opcion edificio
    calendarGroups = get_calendarsGroups(flask.session['access_token'])
    valCalendarGroups = calendarGroups['value']
    listaCalendarGroups = []
    for val in valCalendarGroups:
        if val['name'] != 'Mis calendarios' and val['name'] != 'Other Calendars':
            listaCalendarGroups.append((val['id'],val['name']))
    createAulasForm.edificio.choices = listaCalendarGroups
    #Añadir los tipos
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT tipos.id_tipo, tipos.descripcion
        FROM tipos''')
    varTipos = cursor.fetchall()
    cursor.close()
    listaTipos = []
    for tipos in varTipos:
        listaTipos.append((tipos[0], tipos[1]))
    createAulasForm.tipo.choices = listaTipos
    #Añadir los propietarios
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT propietarios.id_propietario, propietarios.descripcion
        FROM propietarios''')
    varPropietarios = cursor.fetchall()
    cursor.close()
    listaPropietarios = []
    for prop in varPropietarios:
        listaPropietarios.append((prop[0], prop[1]))
    createAulasForm.propietario.choices = listaPropietarios

    if request.method == 'POST' and createAulasForm.validate_on_submit():
        edificio = request.form["edificio"]
        nombreAula = request.form["nombreAula"]
        tipo = request.form["tipo"]
        capacidad = request.form["capacidad"]
        propietario = request.form["propietario"]
        n_ord = request.form["n_ordenadores"]

        nombreEdificio = dict(listaCalendarGroups).get(edificio)
        print(nombreEdificio)

        create_aulas(flask.session['access_token'], edificio, nombreAula)
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT propietarios.email
            FROM propietarios
            WHERE propietarios.id_propietario = ?; 
        ''' ,propietario)
        varPropietarioEmail = cursor.fetchall()
        print("EL EMAIL AL QUE SE TIENE QUE AVISAR")
        print(varPropietarioEmail[0][0])

        try:
            cursor = cnxn.cursor()
            cursor.execute('''
                INSERT into aulas (nombre, edificio, tipo, capacidad, propietario, n_ordenadores)
                values(?, ?, ?, ?, ?, ?); 
            ''' , nombreAula, nombreEdificio, tipo, capacidad, propietario, n_ord)
            cursor.commit()
            cursor.close()  
            return flask.render_template('anadirAulas.html', form = createAulasForm, created = True, prop = varPropietarioEmail[0][0])
        except Exception:  
            db.session.rollback()
            cnxn.rollback()
            db.session.close()

            return flask.render_template('anadirAulas.html', form = createAulasForm, created = False)


    return flask.render_template('anadirAulas.html', form = createAulasForm)


@app.route('/verAulas', methods=['GET', 'POST'])
def verAulas():
    selectAulasForm = selectGroupCalendar()
    modAulaForm = modificarAulasForm()
    filterForm = filtrarAulas()
    #Añadir los grupos de calendarios (edificios) a la opcion edificio
    valCalendarGroups = getEdificios()
    listaCalendarGroups = []
    for val in valCalendarGroups:
        listaCalendarGroups.append((val[0],val[1]))
    selectAulasForm.select.choices = listaCalendarGroups

    
    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT propietarios.email
    FROM propietarios;
    ''' )
    usersPropietarios = cursor.fetchall()
    listaUsuariosPropietarios = []
    for us in usersPropietarios:
        listaUsuariosPropietarios.append(us[0])
    #Formulario para modificar
    modAulaForm.edificio.choices = getEdificios()
    modAulaForm.tipo.choices = getTipos()
    modAulaForm.propietario.choices = getPropietarios()

    
    if flask.request.get_json():
        data = flask.request.get_json()
        flask.session['aulaActualizar'] = data['aula']
        flask.session['propActualizar'] = data['prop']
        
        return json.dumps(data)
        # modAulaForm.nombreAula.data = data['aula']
    #Coger todas las aulas del edificio pedido en el form
    print(selectAulasForm.validate_on_submit())
    if request.method == 'POST' and selectAulasForm.validate_on_submit():
        edificio = request.form["select"]
        flask.session['edifFiltrar'] = edificio
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT aulas.nombre, edificios.nombre, tipos.descripcion, aulas.capacidad, aulas.propietario, aulas.n_ordenadores
            FROM aulas 
            JOIN edificios ON aulas.edificio = edificios.id_edificio
            JOIN tipos ON aulas.tipo = tipos.id_tipo
            JOIN propietarios ON aulas.propietario = propietarios.id_propietario
            WHERE aulas.edificio = ?''', edificio)
        varAulas = cursor.fetchall()
        cursor.close()

        return flask.render_template('verAulas.html', filterForm = filterForm, form = selectAulasForm, form2 = modAulaForm, aulas = varAulas, user = flask.session['user_email'], listaPropietarios = listaUsuariosPropietarios)
    


    #Formulario para actualizar los datos
    if request.method == 'POST' and modAulaForm.validate_on_submit():
        
        print("Aula que hemos modificado:::")
        print(modAulaForm.capacidad)
        aulaNueva = request.form["nombreAula"]
        edificioNuevo = request.form["edificio"]
        tipoNuevo = request.form["tipo"]
        capacidadNueva = request.form["capacidad"]
        n_ordNuevo = request.form["n_ordenadores"]
        propietarioNuevo = request.form["propietario"]

        #Actualizar los datos en la BD
        cursor = cnxn.cursor()
        cursor.execute('''
            UPDATE aulas
            SET aulas.nombre = ?, aulas.edificio = ?, aulas.tipo = ?, aulas.capacidad = ?, aulas.propietario = ?, aulas.n_ordenadores = ?
            WHERE aulas.nombre = ?''', aulaNueva, edificioNuevo, tipoNuevo, capacidadNueva, propietarioNuevo, n_ordNuevo, flask.session['aulaActualizar'])
        cnxn.commit()

        

        #Si se ha cambiado el nombre del aula, actualizarlo en el calendario de outlook tambien
        if(aulaNueva != flask.session['aulaActualizar']):
            calendars = get_calendars(flask.session['access_token']) #Reocgemos todos los calendarios
            valores = calendars['value']  #Sacamos sus valores del diccionario recibido
            listaCalendarios = []
            for cal in valores:
                listaCalendarios.append((cal['name'],cal['id']))
            diccCalendarios = dict(listaCalendarios) #Diccionario con clave valor para sacar el id_calendar de outlook

            calendarioAct = diccCalendarios.get(flask.session['aulaActualizar']) #Calendario a actualizar

            upload_calendar(flask.session['access_token'], calendarioAct, aulaNueva)  
        
        #Si se actualiza el propietario mostrar un mensaje avisando para los permisos
        if propietarioNuevo.strip() != flask.session['propActualizar'].strip():
            # return flask.render_template('verAulas.html', form = selectAulasForm, form2 = modAulaForm, cambio = True, cambioProp = True, prop = propietarioNuevo)
            return flask.render_template('mensajePropietario.html')
        return flask.render_template('verAulas.html',filterForm = filterForm, form = selectAulasForm, form2 = modAulaForm, cambio = True)


    return flask.render_template('verAulas.html',filterForm = filterForm, form = selectAulasForm, form2 = modAulaForm)
    
@app.route('/eliminarAula',methods=['POST','GET'])
def eliminarAula():
    if flask.request.get_json():
        data = flask.request.get_json()
        print("DAta que nos llega:::")
        print(data['aula'])
        cursor = cnxn.cursor()
        cursor.execute('''
            DELETE
            FROM aulas
            WHERE aulas.nombre = ?''',data['aula'] )
        cnxn.commit()

        calendars = get_calendars(flask.session['access_token']) #Recogemos todos los calendarios
        valores = calendars['value']  #Sacamos sus valores del diccionario recibido
        listaCalendarios = []
        for cal in valores:
            listaCalendarios.append((cal['name'],cal['id']))
        diccCalendarios = dict(listaCalendarios)
        
        calendarioBorrar = diccCalendarios.get(data['aula']) #Calendario a borrar

        delete_calendar(flask.session['access_token'], calendarioBorrar)
        return json.dumps(data)

@app.route('/getEventsTable',methods=['POST','GET'])
def getEventsTable():
    data = flask.request.get_json()

    aulaNombre = data['aula']
    flask.session['tablaEvents'] = aulaNombre
    return json.dumps({'success':True}), 200
    
@app.route('/showEventsTable',methods=['POST','GET'])
def showEventsTable():
    modEventForm = modificarEvent()

    #Si no se elige la opción de cualquier aula, se muestran solo los eventos de la pedida
    if flask.session['tablaEvents'] != 'Cualquiera':
        cursor = cnxn.cursor()
        cursor.execute('''
        SELECT *
        FROM eventos
        WHERE eventos.aula = ?;''',flask.session['tablaEvents'])
        varEventos = cursor.fetchall()
        cursor.close() 
    else:
        varEventos = []
        varEventosFinal = []
        for aula in flask.session['listaAulasReservar']:
            cursor = cnxn.cursor()
            cursor.execute('''
            SELECT *
            FROM eventos
            WHERE eventos.aula = ?;''',aula[0])
            varEventos.append(cursor.fetchall())
            cursor.close()
        for evAula in varEventos:
            if evAula: 
                for ev in evAula:
                    varEventosFinal.append(ev)
        
        return flask.render_template('showEventsTable.html',dictEvents = varEventosFinal, fechaActual = datetime.now())


    # varEventos = tuple(sorted(varEventos, key=lambda item: item[2])) #Ordenar segun la fecha    
    fechaActual = datetime.now()
    return flask.render_template('showEventsTable.html',dictEvents = varEventos, fechaActual = fechaActual)

@app.route('/auditoria',methods=['POST','GET'])
def auditoria():
    filterForm = filtrarHoras()

    if filterForm.submit() and filterForm.validate_on_submit():
        fechaIni = request.form['fechaInicio']
        fechaFin = request.form['fechaFin']
        fechaIni = datetime.strptime(fechaIni,'%Y-%m-%d')
        fechaFin = datetime.strptime(fechaFin,'%Y-%m-%d')
        año = fechaIni.year
        mes = fechaIni.month
        diaI = fechaIni.day
        diaF = fechaFin.day
        fechaFinR = fechaFin.replace(hour=23, minute=59)
        print(fechaIni)
        print(diaF)
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT *
            FROM auditoria
            WHERE auditoria.fecha_modif >= ?
            AND auditoria.fecha_modif <= ? ;''', fechaIni, fechaFinR)
        #  cursor.execute('''
        # SELECT *
        # FROM auditoria
        # WHERE DATEPART(yy, auditoria.fecha_modif) = ?
        # AND DATEPART(mm, auditoria.fecha_modif) >= ?
        # AND DATEPART(dd, auditoria.fecha_modif) >= ?
        # AND DATEPART(dd, auditoria.fecha_modif) <= ?
        # ;''', año, mes, diaI, diaF)
        varAuditoria =cursor.fetchall()
        print(varAuditoria)
        cursor.close()
    else:
        cursor = cnxn.cursor()
        cursor.execute('''
        SELECT *
        FROM auditoria
        ;''')
        varAuditoria =cursor.fetchall()
        cursor.close()
    return flask.render_template('auditoria.html', varAuditoria = varAuditoria, form=filterForm)


@app.route('/verPropietarios',methods=['POST','GET'])
def verPropietarios():

    modifProp = modificarPropietarioForm()

    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT *
    FROM propietarios
    ;''')
    varPropietarios =cursor.fetchall()
    cursor.close()


    #Modificar propietario
    if flask.request.get_json():
        data = flask.request.get_json()
        flask.session['IdPropActualizar'] = data['id']
        
        return json.dumps(data)
        # modAulaForm.nombreAula.data = data['aula']
    #Coger todas las aulas del edificio pedido en el form
    if request.method == 'POST' and modifProp.validate_on_submit():
        
        descripcionNueva = request.form["descripcion"]
        responsableNuevo = request.form["responsable"]
        emailNuevo = request.form["email"]

        #Actualizar los datos en la BD
        cursor = cnxn.cursor()
        cursor.execute('''
            UPDATE propietarios
            SET  propietarios.descripcion = ?, propietarios.responsable = ?, propietarios.email = ?
            WHERE propietarios.id_propietario = ?''',  descripcionNueva, responsableNuevo, emailNuevo, flask.session['IdPropActualizar'])
        cnxn.commit()
        
        flash(u'Se ha modificado correctamente el propietario', 'message')
        return redirect(url_for('verPropietarios'))
    return flask.render_template('verPropietarios.html',form = modifProp, varPropietarios = varPropietarios)


@app.route('/anadirPropietarios',methods=['POST','GET'])
def anadirPropietarios():
    addPropForm = anadirPropietarioForm()
    
    if request.method == 'POST' and addPropForm.validate_on_submit():
        id_propietario = request.form["id_propietario"]
        descripcion = request.form["descripcion"]
        responsable = request.form["responsable"]
        email = request.form["email"]
        if id_propietario!="" and descripcion!="" and responsable!="" and email!="":
            try:
                cursor = cnxn.cursor()
                cursor.execute('''
                INSERT into propietarios (id_propietario, descripcion, responsable, email)
                values(?, ?, ?, ?); 
                ''' , id_propietario, descripcion, responsable, email)
                cursor.commit()
                cursor.close()  
                flash('Propietario creado','message')
                return flask.redirect(url_for('mensajePropietario'))
            except Exception as exc: 
                flash(exc,'error') 
    return flask.render_template('anadirPropietarios.html',form = addPropForm)

@app.route('/mensajePropietario',methods=['POST','GET'])
def mensajePropietario():
    return flask.render_template('mensajePropietario.html')


@app.route('/eliminarPropietario',methods=['POST','GET'])
def eliminarPropietario():
    if flask.request.get_json():
        data = flask.request.get_json()

        cursor = cnxn.cursor()
        cursor.execute('''
            DELETE
            FROM propietarios
            WHERE propietarios.id_propietario = ?''',data['idProp'] )
        cnxn.commit()

        return json.dumps(data)

@app.route('/invitado',methods=['POST','GET'])
def invitado():
    flask.session['invitado'] = True
    flask.session['user_email'] = 'usuarioSinRegistrarOculto'
    flask.session['listaUsuariosPropietarios'] = 'ninguno,es un invitado'
    return flask.render_template('homeInvitado.html')
