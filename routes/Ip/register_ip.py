from flask import Blueprint, request, jsonify
from db import get_db_connection

ip_bp = Blueprint('ip', __name__)


# ---------------------------------------------------------
#   FUNCIONES AUXILIARES
# ---------------------------------------------------------
def validar_ip(ip):
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
    p1, p2, _, _ = map(int, ip.split("."))

    if p1 == 10:
        return "Privada"
    if p1 == 172 and 16 <= p2 <= 31:
        return "Privada"
    if p1 == 192 and p2 == 168:
        return "Privada"
    return "Pública"


def mascara_a_prefijo(mascara):
    bits = "".join([bin(int(o))[2:].zfill(8) for o in mascara.split(".")])
    return bits.count("1")


def calcular_red(ip, mascara):
    ip_bin = "".join([bin(int(o))[2:].zfill(8) for o in ip.split(".")])
    mask_bin = "".join([bin(int(o))[2:].zfill(8) for o in mascara.split(".")])

    red_bin = "".join([
        "1" if ip_bin[i] == "1" and mask_bin[i] == "1" else "0"
        for i in range(32)
    ])

    return ".".join([str(int(red_bin[i:i+8], 2)) for i in range(0, 32, 8)])


def sumar_uno(ip):
    """Suma 1 a una IP decimal"""
    octetos = list(map(int, ip.split(".")))
    for i in reversed(range(4)):
        if octetos[i] < 255:
            octetos[i] += 1
            break
        else:
            octetos[i] = 0
    return ".".join(map(str, octetos))


def restar_uno(ip):
    """Resta 1 a una IP decimal"""
    octetos = list(map(int, ip.split(".")))
    for i in reversed(range(4)):
        if octetos[i] > 0:
            octetos[i] -= 1
            break
        else:
            octetos[i] = 255
    return ".".join(map(str, octetos))


def calcular_broadcast(red, prefijo):
    bits_red = prefijo
    bits_host = 32 - bits_red

    red_bin = "".join([bin(int(o))[2:].zfill(8) for o in red.split(".")])
    broadcast_bin = red_bin[:bits_red] + ("1" * bits_host)

    return ".".join([str(int(broadcast_bin[i:i+8], 2)) for i in range(0, 32, 8)])



# ---------------------------------------------------------
#   ENDPOINT PRINCIPAL
# ---------------------------------------------------------
@ip_bp.route('/registrar-ip', methods=['POST'])
def registrar_ip():
    data = request.get_json()

    id_usuario = data.get("id_usuario")
    ip = data.get("ip")
    mascara = data.get("mascara")

    if not id_usuario or not ip or not mascara:
        return jsonify({"error": "Faltan datos (id_usuario, ip, mascara)"}), 400

    # -------------------------------------------------------------
    # VALIDAR IP
    # -------------------------------------------------------------
    if not validar_ip(ip):
        return jsonify({"error": "IP inválida"}), 400

    # -------------------------------------------------------------
    # PROCESAR MÁSCARA (puede venir /24 o 255.255.255.0)
    # -------------------------------------------------------------
    if mascara.startswith("/"):
        prefijo = int(mascara[1:])
        if not 0 <= prefijo <= 32:
            return jsonify({"error": "Prefijo inválido"}), 400

        bits = ("1" * prefijo).ljust(32, "0")
        mascara_decimal = ".".join([str(int(bits[i:i+8], 2)) for i in range(0, 32, 8)])

    else:
        mascara_decimal = mascara
        if not validar_ip(mascara_decimal):
            return jsonify({"error": "Máscara inválida"}), 400

        prefijo = mascara_a_prefijo(mascara_decimal)

    # -------------------------------------------------------------
    # CLASE, TIPO, DIRECCIÓN DE RED
    # -------------------------------------------------------------
    clase = clase_ip(ip)
    tipo = tipo_ip(ip)
    red = calcular_red(ip, mascara_decimal)

    # -------------------------------------------------------------
    # BROADCAST
    # -------------------------------------------------------------
    broadcast = calcular_broadcast(red, prefijo)

    # -------------------------------------------------------------
    # PRIMERA Y ÚLTIMA UTILIZABLE
    # -------------------------------------------------------------
    primera_ip = sumar_uno(red)
    ultima_ip = restar_uno(broadcast)

    # -------------------------------------------------------------
    # HOSTS
    # -------------------------------------------------------------
    bits_host = 32 - prefijo
    total_hosts = (2 ** bits_host) - 2
    bits_subred = prefijo  # cantidad de bits usados para red

    # -------------------------------------------------------------
    # GUARDAR EN BD
    # -------------------------------------------------------------
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No hay conexión con la BD"}), 500

    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.close()
        conn.close()
        return jsonify({"error": "Usuario no existe"}), 404

    cursor.execute(
        "INSERT INTO direcciones_ip (id_usuario, ip) VALUES (%s, %s)",
        (id_usuario, ip)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": "IP registrada exitosamente",
        "data": {
            "ip": ip,
            "mascara": mascara_decimal,
            "prefijo": f"/{prefijo}",
            "clase": clase,
            "tipo": tipo,
            "direccion_red": red,
            "broadcast": broadcast,
            "primer_ip_utilizable": primera_ip,
            "ultima_ip_utilizable": ultima_ip,
            "bits_subred": bits_subred,
            "bits_host": bits_host,
            "hosts_totales": total_hosts
        }
    }), 201
