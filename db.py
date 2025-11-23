import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="shinkansen.proxy.rlwy.net",
            user="root",
            password="RuIqTtonyjAcPAfaFFsoEMEKtKzHItYh",
            database="railway",
            port=3306
        )
        return conn
    except Error as e:
        print(f"Error de conexión a MySQL: {e}")
        return None