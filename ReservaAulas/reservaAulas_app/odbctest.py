import pyodbc
server = 'reserva-aulas.database.windows.net'
database = 'reservaAulas'
username = 'user'
password = 'Password9'
driver= '{ODBC Driver 17 for SQL Server}'
cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)
# cursor = cnxn.cursor()
# cursor.execute("SELECT nombre FROM AULAS")
# row = cursor.fetchall()
# # while row:
# print (row)
    # row = cursor.fetchone()