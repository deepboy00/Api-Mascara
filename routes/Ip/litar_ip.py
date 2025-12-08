from flask import Blueprint, request, jsonify
from db import get_db_connection

listar_ip_bp = Blueprint('listar_ip', __name__)

@listar_ip_bp.route('/listar-ip', methods=['GET'])
def listar_ip():
    id_usuario = request.args.get("id_usuario")

    if not id_usuario:
        return jsonify({"error": "Debes enviar id_usuario"}), 400

    # Conexion con base de datos
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

    # Obtener direcciones IP 
    cursor.execute(
        """
        SELECT id_ip, ip, mascara, prefijo, clase, tipo, direccion_red, broadcast,
               primera_ip, ultima_ip, bits_subred, bits_host, hosts_totales, fecha_registro
        FROM direcciones_ip
        WHERE id_usuario = %s
        ORDER BY fecha_registro DESC
        """,
        (id_usuario,)
    )
    ips = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Direcciones IP obtenidas correctamente",
        "total": len(ips),
        "ips": ips
    }), 200
