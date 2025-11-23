from flask import Blueprint, request, jsonify
import bcrypt
from db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("usuario")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Faltan datos"}), 400

    password_bytes = password.encode('utf-8')

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_usuario, id_empresa, id_trabajador, password, rol, estado FROM usuario WHERE usuario = %s",
        (username,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password_bytes, user["password"].encode('utf-8')):
        user_safe = {k: v for k, v in user.items() if k != 'password'}
        return jsonify({"message": "Login exitoso", "user": user_safe})

    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401