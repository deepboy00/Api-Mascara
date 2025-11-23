from flask import Blueprint, request, jsonify
from db import get_db_connection

ip_bp = Blueprint('ip', __name__)

def validar_ip(ip):
    """Valida que una IP sea IPv4 correcta manualmente"""
    partes = ip.split(".")
    if len(partes) != 4:
        return False
    try:
        for p in partes:
            if not 0 <= int(p) <= 255:
                return False
        return True
    except:
        return False

def clase_ip(ip):
    """Obtiene la clase de la IP mediante el primer octeto"""
    primer = int(ip.split(".")[0])
    
    if 1 <= primer <= 126:
        return "Clase A"
    elif 128 <= primer <= 191:
        return "Clase B"
    elif 192 <= primer <= 223:
        return "Clase C"
    elif 224 <= primer <= 239:
        return "Clase D (Multicast)"
    else:
        return "Clase E (Experimental)"

def tipo_ip(ip):
    """Determina si es pública o privada"""
    p1, p2, _, _ = map(int, ip.split("."))

    # Rangos privados
    if p1 == 10:
        return "Privada"
    if p1 == 172 and 16 <= p2 <= 31:
        return "Privada"
    if p1 == 192 and p2 == 168:
        return "Privada"
    
    return "Pública"

def mascara_a_prefix(mascara):
    """Convierte máscara decimal a prefijo (/24, /16, etc)"""
    bits = "".join([bin(int(octeto))[2:].zfill(8) for octeto in mascara.split(".")])
    return bits.count("1")

def calcular_red(ip, mascara):
    """Calcula dirección de red manualmente"""
    ip_bin = "".join([bin(int(o))[2:].zfill(8) for o in ip.split(".")])
    mask_bin = "".join([bin(int(o))[2:].zfill(8) for o in mascara.split(".")])

    # AND bit a bit
    red_bin = "".join(["1" if ip_bin[i] == "1" and mask_bin[i] == "1" else "0" for i in range(32)])
    
    return ".".join([str(int(red_bin[i:i+8], 2)) for i in range(0, 32, 8)])



@ip_bp.route('/registrar-ip', methods=['POST'])
def registrar_ip():
    data = request.get_json()

    id_usuario = data.get("id_usuario")
    ip = data.get("ip")
    mascara = data.get("mascara")  # Puede venir en /25 o 255.255.255.0

    if not id_usuario or not ip or not mascara:
        return jsonify({"error": "Faltan datos (id_usuario, ip, mascara)"}), 400

    # -------------------------------------------------------------
    # VALIDAR IP
    # -------------------------------------------------------------
    if not validar_ip(ip):
        return jsonify({"error": "La IP ingresada no es válida"}), 400

    # -------------------------------------------------------------
    # CONVERTIR MÁSCARA A DECIMAL SI VIENE COMO /26
    # -------------------------------------------------------------
    if mascara.startswith("/"):
        prefijo = int(mascara[1:])
        if not 0 <= prefijo <= 32:
            return jsonify({"error": "Prefijo inválido"}), 400
        # Convertir bits a máscara decimal
        bits = ("1" * prefijo).ljust(32, "0")
        mascara_decimal = ".".join([str(int(bits[i:i+8], 2)) for i in range(0, 32, 8)])
    else:
        mascara_decimal = mascara
        if not validar_ip(mascara_decimal):
            return jsonify({"error": "Máscara inválida"}), 400
        prefijo = mascara_a_prefix(mascara_decimal)

    # -------------------------------------------------------------
    # OBTENER CLASE Y TIPO
    # -------------------------------------------------------------
    clase = clase_ip(ip)
    tipo = tipo_ip(ip)

    # -------------------------------------------------------------
    # CALCULAR DIRECCIÓN DE RED
    # -------------------------------------------------------------
    red = calcular_red(ip, mascara_decimal)

    # -------------------------------------------------------------
    # GUARDAR EN BD
    # -------------------------------------------------------------
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.close()
        conn.close()
        return jsonify({"error": "Usuario no existe"}), 404

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
            "ip": ip,
            "mascara": mascara_decimal,
            "prefijo": f"/{prefijo}",
            "clase": clase,
            "tipo": tipo,
            "direccion_red": red
        }
    }), 201
