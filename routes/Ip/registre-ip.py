from flask import Blueprint, request, jsonify
from db import get_db_connection
import ipaddress

ip_bp = Blueprint('ip', __name__)

@ip_bp.route('/registrar-ip', methods=['POST'])
def registrar_ip():
    data = request.get_json()

    id_usuario = data.get("id_usuario")
    ip = data.get("ip")

    # Validación de datos
    if not id_usuario or not ip:
        return jsonify({"error": "Faltan datos"}), 400

    # Validar que sea una IP válida
    try:
        ipaddress.IPv4Address(ip)
    except:
        return jsonify({"error": "La IP proporcionada no es válida"}), 400

    # Conexión a BD
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor(dictionary=True)

    # Verificar usuario existente
    cursor.execute(
        "SELECT id_usuario FROM usuario WHERE id_usuario = %s",
        (id_usuario,)
    )
    usuario = cursor.fetchone()

    if not usuario:
        cursor.close()
        conn.close()
        return jsonify({"error": "El usuario no existe"}), 404

    # Insertar IP
    cursor.execute(
        """
        INSERT INTO direcciones_ip (id_usuario, ip)
        VALUES (%s, %s)
        """,
        (id_usuario, ip)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": "IP registrada exitosamente",
        "data": {
            "id_usuario": id_usuario,
            "ip": ip
        }
    }), 201
