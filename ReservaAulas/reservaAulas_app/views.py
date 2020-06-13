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
from reservaAulas_app.forms import createEventForm, selectCalendar, selectGroupCalendar, filterAulasForm, createNewAula, modificarAulasForm, filterAulasForm2, modificarEvent
import json
from flask import flash, request, redirect, url_for
from datetime import datetime, timedelta  
from flask_wtf.csrf import CSRFProtect
from reservaAulas_app.config import ADMIN_USERS
from reservaAulas_app.odbctest import cnxn
from reservaAulas_app.getSQLData import getCapacidades,getEdificios,getPropietarios,getTipos
import logging
import requests
import re


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
        listaUsuariosReservar.append(us[0])
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
    print('code: '+code)
    if not code:
        logging.error("NO 'code' VALUE RECEIVED")
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
        # oauth_token = User(
        #     access_token = token['access_token'],
        #     refresh_token = token['refresh_token'],
        #     email = jwt['email'],
        #     expires_on = datetime_from_timestamp(token['expires_in']),
        # )
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
        # db.session.add(oauth_token)
        # connection.commit()
    # else:
    #     app.logger.info('UPDATING existing O365OAuthToken for {}'.format(jwt['email']))
    #     oauth_token.access_token = token['access_token']
    #     # oauth_token.access_token = token[0]
    #     oauth_token.refresh_token = token['refresh_token']
    #     # oauth_token.refresh_token = token[1]
    #     oauth_token.expires_on = datetime_from_timestamp(token['expires_in'])
    #     # oauth_token.expires_on = datetime_from_timestamp(token[3])
    #     # oauth_token.email = token[2]
    #     #oauth_token.token_type = token['token_type']
    #     #oauth_token.scope = token['scope']
    #     # db.session.rollback()
    #     # connection.rollback()
    # db.session.commit()
    else:
        
        ref_token = refresh_oauth_token(token['refresh_token'])
        jwtToken = get_jwt_from_id_token(ref_token['id_token'])
        flask.session['user_email'] = jwtToken['email']
        flask.session['refresh_token'] = ref_token['refresh_token']       
        flask.session['access_token'] = ref_token['access_token']
    #Guardar variables en la sesion activa
    #CAMBIO DE CONEXION BD
    # # flask.session['user_email'] = oauth_token.email
    # # flask.session['access_token'] = oauth_token.access_token
    # # flask.session['refresh_token'] = oauth_token.refresh_token 
    listaProv = []
    flask.session['listaAulasReservar'] = listaProv
    return flask.redirect('/')

@app.route('/events', methods=['GET', 'POST'])
def events():
    acc_token = flask.session['access_token']

    selectEdificioForm = selectGroupCalendar() #Crear primer desplegable
    selectForm = selectCalendar()   #Crear segundo desplegable
    filterForm = filterAulasForm2()
    modificarEventForm = modificarEvent()
    # CAMBIO DE CONEXION BD AZURE
    filterForm.tipo.choices = getTipos()
    cursor = cnxn.cursor()
    # CAMBIO DE CONEXION BD AZURE
    # connection.begin()
    # cursor = connection.cursor()
    #Consulta para bloquear el aula que se queire reservas
    queryEdificios = '''
    SELECT id_edificio
    FROM edificios;
    '''
    cursor.execute(queryEdificios)
    varEdif = cursor.fetchall()
    cursor.close()
    listaGruposCalendarios = []
    # for cal in valoresGrupos:
    #     listaGruposCalendarios.append((cal['id'],cal['name']))
    for cal in varEdif:
        listaGruposCalendarios.append(cal[0])
    selectEdificioForm.select.choices = listaGruposCalendarios

    #Sacar los calendarios distintos
    # calendars = get_calendars(flask.session['access_token']) #Reocgemos todos los calendarios
    # valores = calendars['value']  #Sacamos sus valores del diccionario recibido
    # listaCalendarios = []
    # for cal in valores:
    #     listaCalendarios.append((cal['id'],cal['name']))
    # diccCalendarios = dict(listaCalendarios) #Introducimos en un diccionario (clave,valor) -> (id,nombre de cada calendario) para obtener el id de la eleccion
    
    
    # selectForm.select.choices = listaCalendarios
    eventosExistentes = {}
    fechaActual = datetime.now()
    # fechaActual = fechaActual.strftime('%Y-%m-%dT%H:%M')
    #Variables para mostrar el resultado de la modificación
    error_solapamiento = False
    modif = False
    #Modificar eventos
    if request.method == 'POST' and modificarEventForm.submit.data and modificarEventForm.validate_on_submit():
        temaNuevo = request.form["tema"]
        userNuevo = request.form["user"]
        horaIniNueva = request.form["fechaIni"]
        horaFinNueva = request.form["fechaFin"]
        print("Estamos")
        if flask.session['fechaIniEventMod'] != horaIniNueva or flask.session['fechaFinEventMod'] != horaFinNueva:
            print("Cambiamos hora")
            cursor = cnxn.cursor()
            cursor.execute('''SELECT count(*)
            FROM eventos
            WHERE eventos.aula = ?
            AND eventos.inicio != ?
            AND eventos.inicio < ?
            AND eventos.fin > ?
             ''',flask.session['aulaEventMod'], flask.session['fechaIniEventMod'],horaFinNueva, horaIniNueva)
            varAulas = cursor.fetchall()
            #Si no hay solapamientos
            if varAulas[0][0] == 0:
                modificar_evento(flask.session['access_token'],flask.session['id_evento_modificar'],flask.session['id_aula_modificar'],temaNuevo, horaIniNueva, horaFinNueva)
                modif = True
                cursor = cnxn.cursor()
                cursor.execute('''
                    UPDATE eventos
                    SET eventos.evento = ?, eventos.inicio = ?, eventos.fin = ?, eventos.profesor = ?
                    WHERE eventos.aula = ? AND eventos.inicio = ? AND eventos.fin = ?'''
                    , temaNuevo, horaIniNueva, horaFinNueva, userNuevo, flask.session['aulaEventMod'], flask.session['fechaIniEventMod'], flask.session['fechaFinEventMod'])
                cnxn.commit()
            else:
                error_solapamiento = True
                modif = False  
        else:
            modificar_evento(flask.session['access_token'],flask.session['id_evento_modificar'],flask.session['id_aula_modificar'],temaNuevo, horaIniNueva, horaFinNueva)
            cursor = cnxn.cursor()
            cursor.execute('''
                UPDATE eventos
                SET eventos.evento = ?, eventos.inicio = ?, eventos.fin = ?, eventos.profesor = ?
                WHERE eventos.aula = ? AND eventos.inicio = ? AND eventos.fin = ?'''
                , temaNuevo, horaIniNueva, horaFinNueva, userNuevo, flask.session['aulaEventMod'], flask.session['fechaIniEventMod'], flask.session['fechaFinEventMod'])
            cnxn.commit() 
            modif = True   
            error_solapamiento = False

    #Primera eleccion (edificio)
    if selectEdificioForm.submit and request.method == 'POST' and "submitEdif" in request.form:
        # primerForm = True   #Primer desplegable elegido
        edificioId = request.form['select']
        print(edificioId)

        cursor = cnxn.cursor()
        cursor.execute('''SELECT aulas.nombre
        FROM aulas
        WHERE aulas.edificio = ? ''',edificioId)
        varAulas = cursor.fetchall()
        cursor.close()  
        nombreAulas = [] 
        for elem in varAulas:        
            nombreAulas.append(elem[0])
        selectForm.select.choices = nombreAulas
        return flask.render_template('events.html',edificioId = edificioId, dictEvents = eventosExistentes,formEdificio = selectEdificioForm, formAula = selectForm, fechaActual = fechaActual, filterForm =filterForm)

    #Segunda eleccion(aula)
    if selectForm.submit and request.method == 'POST' and "submitAula" in request.form:
        print("segunda eleccion")
        # edificioId = selectEdificioForm.select.data
        # print("En el ultimo momento")
        # print(edificioId)
        segundoForm = True  #Segundo desplegable elegido
        calendarioId = request.form["select"] #Recoger el calendario id del calendario elegido

        # CAMBIO DE CONEXION BD AZURE, AL TENER PARAMETROS HAY QUE CAMBIAR LA FOMRA EN QUE SE EJECUTA
        cursor = cnxn.cursor()
        cursor.execute('''
        SELECT *
        FROM eventos
        WHERE eventos.aula = ?;''',calendarioId)
        varEventos = cursor.fetchall()
        cursor.close() 
        print("LA INFO DE LOS EVENTOS")
        print(varEventos)
        cursor = cnxn.cursor()
        cursor.execute('''
        SELECT propietarios.email
        FROM propietarios 
        JOIN aulas ON propietarios.id_propietario = aulas.propietario
        WHERE aulas.nombre = ?;''',calendarioId)
        varPropEventos = cursor.fetchall()
        cursor.close() 
        print("PROP")
        print(varPropEventos)
        varEventos = tuple(sorted(varEventos, key=lambda item: item[4])) #Ordenar segun la fecha
        return flask.render_template('eventsTable.html',propietario = varPropEventos, dictEvents = varEventos,formEdificio = selectEdificioForm, formAula = selectForm, fechaActual = fechaActual, filterForm = filterForm, modEventForm= modificarEventForm )
    #Filtros
    elif filterForm.submit and request.method == 'POST' and filterForm.validate_on_submit():
        capacidad = request.form["capacidad"]
        n_ord = request.form["n_ord"]
        tipo = request.form["tipo"]
        fechaIni = request.form["startDate"]
        # fechaFin = request.form["endDate"]
        horaIni = request.form["startTime"]
        horaFin = request.form["endTime"]
        
        fechaInicio = datetime.strptime(fechaIni + " "  + horaIni ,'%Y-%m-%d %H:%M') #Convertirlo la fecha y hora en datetime
        fechaFin = datetime.strptime(fechaIni + " "  + horaFin ,'%Y-%m-%d %H:%M')
        cursor = cnxn.cursor()
        cursor.execute('''
        SELECT * from eventos 
        JOIN aulas ON eventos.aula = aulas.nombre
        where aulas.capacidad >= ?
        AND aulas.n_ordenadores >= ?
        AND aulas.tipo = ?
        AND eventos.inicio >= ? 
        AND eventos.inicio <= ?
        AND (eventos.fin <= ? OR eventos.fin >= ?);''',capacidad, n_ord, tipo, fechaInicio, fechaFin, fechaFin, fechaFin)
        varEventos = cursor.fetchall()
        cursor.close() 
        varEventos = tuple(sorted(varEventos, key=lambda item: item[4]))

        return flask.render_template('eventsTable.html', dictEvents = varEventos,formEdificio = selectEdificioForm, formAula = selectForm, fechaActual = fechaActual, filterForm=filterForm, modEventForm= modificarEventForm )
    else:
        if error_solapamiento == True:
            return flask.render_template('errorModificarEvento.html')
        elif modif == True:
            return flask.render_template('events.html',modif=True, dictEvents = eventosExistentes,formEdificio = selectEdificioForm, formAula = selectForm, fechaActual = fechaActual, filterForm = filterForm, modEventForm= modificarEventForm )
        else:
            return flask.render_template('events.html', dictEvents = eventosExistentes,formEdificio = selectEdificioForm, formAula = selectForm, fechaActual = fechaActual, filterForm = filterForm)

@app.route('/errorModificarEvento')
def errorModificarEvento():
    return flask.render_template('errorModificarEvento.html')

@app.route('/modificarEvento', methods=['POST'])
def modificarEvento():
    modificarEventForm = modificarEvent()
    data = flask.request.get_json()
    print("LA DATA::")
    print(data)
    
    if data:
        flask.session['aulaEventMod'] = data['aula']
        flask.session['fechaIniEventMod'] = data['fechaIni']
        flask.session['fechaFinEventMod'] = data['fechaF']
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
            fechaI = dia +" "+ fechaFormat[0]
            print(fechaI)
            print(data['fechaIni'])
            if fechaI == data['fechaIni']:
                id_evento = eve['id']
                flask.session['id_evento_modificar'] = id_evento
            
        return json.dumps(data)
    

@app.route('/borrarEvento',methods=['POST'])
def borrarEvento():
    data = flask.request.get_json()
    if data:
        aula = data['aula']
        fechaIni = data['fechaIni']
        fechaFin = data['fechaF']
        nuevoToken = refresh_oauth_token(flask.session['refresh_token'])
        flask.session['access_token'] = nuevoToken['access_token']
        calendarios = get_calendars(flask.session['access_token'])
        calendarios = calendarios['value']
        
        for cal in calendarios:
            if cal['name'] == data['aula']:
                id_cal = cal['id']

        eventos = get_events_from_calendar(flask.session['access_token'], id_cal)
        eventos = eventos['value']
        for eve in eventos:
            fecha = eve['start']['dateTime'].split("T")
            dia = fecha[0]
            fechaFormat = fecha[1].split(".")
            fechaI = dia +" "+ fechaFormat[0]
            print(fechaI)
            print(data['fechaIni'])
            if fechaI == data['fechaIni']:
                id_evento = eve['id']
        delete_event(flask.session['access_token'],id_cal , id_evento)
        cursor = cnxn.cursor()
        cursor.execute('''
            DELETE
            FROM eventos
            WHERE eventos.aula = ? AND eventos.inicio = ? AND eventos.fin = ?''', aula, fechaIni, fechaFin)
        cnxn.commit()
        return json.dumps(data)

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
        listaEmailsProp.append(var[0])
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
    filterForm.edificio.choices = getEdificios()

    #Rellenar tipo
    filterForm.tipo.choices = getTipos()

    #SEGUNDO FORMULARIO

    if(flask.request.args.get("response")):
        param = flask.request.args.get("response")
        listaParametros = list(param.keys())
        listaAulas = []
        for p in listaParametros:
            listaAulas=json.loads(p)
        print(listaAulas)

        
    eventForm = createEventForm()
    listaDias = [(None,"Selecciona un día"),("Lunes","Lunes"),("Martes","Martes"),("Miercoles","Miercoles"),("Jueves","Jueves"),("Viernes","Viernes"),("Sabado","Sabado"),("Domingo","Domingo")]
    eventForm.day.choices = listaDias
    logging.info("RESERVAR")
    try:
        print("IMPRIMIMOS CALENDARIOS")
        calendars = get_calendars(flask.session['access_token']) #Reocgemos todos los calendarios
        logging.info(calendars)
        print(calendars)
        valores = calendars['value']  #Sacamos sus valores del diccionario recibido

        listaCalendarios = []
        for cal in valores:
            #Añadir todos los calendarios menos los que venian predefinidos en outlook (no se pueden borrar)
            if cal['name'] != "Calendario" and cal['name'] != "Días festivos de España" and cal['name'] != "Cumpleaños":
                listaCalendarios.append((cal['id'],cal['name'])) 
    except Exception:
        print(flask.session['access_token'])
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
                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm, emailVal = False,validate = False)

            
            
            if aulaId != 'Cualquiera':
                aula = aulaId
                aulaId = keys_dicc[vals_dicc.index(aulaId)]
            # CAMBIO DE CONEXION BD AZURE
            # aula = diccCalendarios.get(aulaId)
            # connection.begin()
            # cursor = connection.cursor()
            # #Consulta para bloquear el aula que se queire reservar
            # queryBloqueo = '''
            # SELECT nombre
            # FROM outlook.aulas
            # WHERE nombre = %s
            # FOR UPDATE;
            # '''
            # paramsBloqueo = [aula]
            # cursor.execute(queryBloqueo, paramsBloqueo)


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
                
                # Consulta para comprobar solapamiento
                # CAMBIO DE CONEXION BD AZURE

                # cursor = connection.cursor()
                # querySolapamiento = '''
                # SELECT count(*)
                # FROM outlook.eventos 
                # WHERE aula = %s
                # AND ( inicio < %s )
                # AND ( fin > %s );
                # '''
                # paramsSolapamiento = [aula, fechaFin, fechaInicio]
                # cursor.execute(querySolapamiento, paramsSolapamiento)
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
                        # CAMBIO DE CONEXION BD AZURE
                        # cursor = connection.cursor()
                        # query3 = '''
                        # INSERT INTO
                        # outlook.eventos(aula,evento,email,inicio,fin,creacion) 
                        # VALUES
                        # (%s,%s,%s,%s,%s,%s)
                        # '''
                        # params3 = [aula, tema, flask.session['user_email'],fechaInicio,fechaFin,datetime.now()]
                        # cursor.execute(query3, params3)

                        cursor = cnxn.cursor()
                        cursor.execute('''
                        INSERT INTO
                        eventos(aula,evento,email,inicio,fin,creacion,profesor) 
                        VALUES
                        (?,?,?,?,?,?,?)''', aula, tema, flask.session['user_email'],fechaInicio,fechaFin,datetime.now(),profesor)
                        # var = cursor.fetchall()
                        cnxn.commit()
                        cursor.close()
                        db.session.commit()
                        # connection.commit()
                        db.session.close()
                        # engine.dispose()
                        #Enviar mensaje
                        em = send_email(flask.session['access_token'], email_prof, aula)
                    except OperationalError:
                        db.session.rollback()
                        # connection.rollback()
                        cnxn.rollback()
                        db.session.close()
                        # engine.dispose()
                        return '<h1> Transaccion bloqueada demasiado tiempo </h1>'
                    flash(u'Se ha creado correctamente el evento', 'message')
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
                fechaInicioMultiple = fechaInicio
                while fechaInicioMultiple <= fechaFin and flag == True:
                    #Consulta de solapamiento de horas para todos los dias
                    cursor = cnxn.cursor()
                    cursor.execute('''
                    SELECT count(*)
                    FROM eventos 
                    WHERE aula = ?
                    AND ( inicio < ? )
                    AND ( fin > ? );
                    ''', aula, fechaFin, fechaInicioMultiple)
                    varSolapamiento = cursor.fetchall()
                    cursor.close()
                    #Si devuelve 0 es que esta libre la hora
                    if(varSolapamiento[0][0] == 0):
                        listaFechasReserva.append(fechaInicioMultiple)
                        fechaInicioMultiple = fechaInicioMultiple + timedelta(days=1)
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
                            #Enviar mensaje
                            em = send_email(flask.session['access_token'], email_prof, aula)

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
                
                print("Reserva periodica")
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
                fechaInicioPeriodica = fechaInicio

                while fechaInicioPeriodica <= fechaFin and flagC == True:
                    # Comprobar que estan libres
                    cursor = cnxn.cursor()
                    cursor.execute('''
                    SELECT count(*)
                    FROM eventos 
                    WHERE aula = ?
                    AND ( inicio < ? )
                    AND ( fin > ? );
                    ''', aula, fechaFin, fechaInicioPeriodica)
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
                            #Enviar mensaje
                            em = send_email(flask.session['access_token'], email_prof, aula)
                        except OperationalError:
                            db.session.rollback()
                            cnxn.rollback()
                            db.session.close()
                    flash(u'Se han creado correctamente los eventos', 'message')    
                else:
                    flash(u'Las horas estan ocupadas', 'error')
                
                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm)
                # return redirect(url_for('reservar'),form = eventForm, form1 = filterForm )
            
            else:
                return flask.render_template('reservar.html', form = eventForm, form1 = filterForm, validate = False)

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

        return flask.render_template('verAulas.html', form = selectAulasForm, form2 = modAulaForm, aulas = varAulas, user = flask.session['user_email'], listaPropietarios = listaUsuariosPropietarios)
    
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
            return flask.render_template('verAulas.html', form = selectAulasForm, form2 = modAulaForm, cambio = True, cambioProp = True, prop = propietarioNuevo)

        return flask.render_template('verAulas.html', form = selectAulasForm, form2 = modAulaForm, cambio = True)


    return flask.render_template('verAulas.html', form = selectAulasForm, form2 = modAulaForm)
    
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
    print("Lo que nos llega aqui:::")
    print(data)
    aulaNombre = data['aula']
    print(aulaNombre)
    flask.session['tablaEvents'] = aulaNombre
    return json.dumps({'success':True}), 200
    
@app.route('/showEventsTable',methods=['POST','GET'])
def showEventsTable():
    print("La lista completa:::")
    print(flask.session['listaAulasReservar'])
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
        
        return flask.render_template('eventsTable.html', dictEvents = varEventosFinal, fechaActual = datetime.now())


    # varEventos = tuple(sorted(varEventos, key=lambda item: item[2])) #Ordenar segun la fecha    
    fechaActual = datetime.now()
    return flask.render_template('eventsTable.html', dictEvents = varEventos, fechaActual = fechaActual)
