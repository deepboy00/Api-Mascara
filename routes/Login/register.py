from flask import Blueprint, request, jsonify
import bcrypt
from db import get_db_connection

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    username = data.get("usuario")
    password = data.get("password")
    nombre = data.get("nombre")
    apellido = data.get("apellido")

    # Validación de datos
    if not username or not password or not nombre or not apellido:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor(dictionary=True)

    # Verificar si el usuario ya existe
    cursor.execute("SELECT * FROM usuario WHERE username = %s", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        return jsonify({"error": "El usuario ya existe"}), 409

    # Encriptar contraseña
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insertar en usuario
    cursor.execute(
        """
        INSERT INTO usuario (username, password, estado)
        VALUES (%s, %s, 'activo')
        """,
        (username, password_hash.decode('utf-8'))
    )
    conn.commit()

    # Obtener ID del usuario recién creado
    id_usuario = cursor.lastrowid

    # Insertar en persona
    cursor.execute(
        """
        INSERT INTO persona (id_usuario, nombre, apellido)
        VALUES (%s, %s, %s)
        """,
        (id_usuario, nombre, apellido)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Registro exitoso",
        "usuario": {
            "id_usuario": id_usuario,
            "username": username,
            "nombre": nombre,
            "apellido": apellido,
            "estado": "activo"
        }
    }), 201
