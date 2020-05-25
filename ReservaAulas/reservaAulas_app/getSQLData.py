from reservaAulas_app.odbctest import cnxn


def getTipos():
    #Rellenar tipo
    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT tipos.id_tipo, tipos.descripcion
    FROM tipos;''')
    varTipos = cursor.fetchall()
    listaTipos = []
    for tipo in varTipos:
        listaTipos.append((tipo[0],tipo[1]))
    cursor.close() 
    return listaTipos

def getEdificios():
    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT edificios.id_edificio, edificios.nombre
    FROM edificios;''')
    varEdificios = cursor.fetchall()
    listaEdificios = []
    for edif in varEdificios:
        listaEdificios.append((edif[0],edif[1]))
    cursor.close() 
    return listaEdificios

def getCapacidades():
    cursor = cnxn.cursor()
    cursor.execute('''
    SELECT DISTINCT aulas.capacidad,aulas.capacidad
    FROM aulas;''')
    varCapacidades = cursor.fetchall()
    listaCapacidades = []
    for cap in varCapacidades:
        listaCapacidades.append((cap[0],cap[1]))
    cursor.close() 
    return listaCapacidades

def getPropietarios():
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT propietarios.id_propietario, propietarios.descripcion
        FROM propietarios''')
    varPropietarios = cursor.fetchall()
    cursor.close()
    listaPropietarios = []
    for prop in varPropietarios:
        listaPropietarios.append((prop[0], prop[1]))
    return listaPropietarios