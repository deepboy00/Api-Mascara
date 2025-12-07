from flask import Blueprint, request, jsonify
from db import get_db_connection

ip_bp = Blueprint('ip', __name__)

#   FUNCIONES AUXILIARES
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
    octetos = list(map(int, ip.split(".")))
    for i in reversed(range(4)):
        if octetos[i] < 255:
            octetos[i] += 1
            break
        else:
            octetos[i] = 0
    return ".".join(map(str, octetos))


def restar_uno(ip):
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


#   FUNCIÓN PARA PROCESAR LA MÁSCARA O PREFIJO
def obtener_mascara_y_prefijo(mascara_input):

    # Caso: viene /24 (prefijo)
    if isinstance(mascara_input, str) and mascara_input.startswith("/"):
        prefijo = int(mascara_input[1:])
    else:
        # Caso: se espera máscara decimal
        if not validar_ip(mascara_input):
            return None, None
        prefijo = mascara_a_prefijo(mascara_input)

    if not 0 <= prefijo <= 32:
        return None, None

    # Convertir prefijo a máscara decimal
    bits = ("1" * prefijo).ljust(32, "0")
    mascara_decimal = ".".join([str(int(bits[i:i+8], 2)) for i in range(0, 32, 8)])

    return mascara_decimal, prefijo

#   ENDPOINT PRINCIPAL
@ip_bp.route('/registrar-ip', methods=['POST'])
def registrar_ip():
    data = request.get_json()

    id_usuario = data.get("id_usuario")
    ip = data.get("ip")
    mascara = data.get("mascara")

    if not id_usuario or not ip or not mascara:
        return jsonify({"error": "Faltan datos (id_usuario, ip, mascara)"}), 400

    # VALIDAR IP
    if not validar_ip(ip):
        return jsonify({"error": "IP inválida"}), 400

    # PROCESAR MÁSCARA O PREFIJO
    mascara_decimal, prefijo = obtener_mascara_y_prefijo(mascara)

    if mascara_decimal is None:
        return jsonify({"error": "Máscara o prefijo inválido"}), 400

    # CALCULOS
    clase = clase_ip(ip)
    tipo = tipo_ip(ip)
    red = calcular_red(ip, mascara_decimal)
    broadcast = calcular_broadcast(red, prefijo)
    primera_ip = sumar_uno(red)
    ultima_ip = restar_uno(broadcast)

    bits_host = 32 - prefijo
    total_hosts = (2 ** bits_host) - 2
    bits_subred = prefijo

    # CONEXIÓN BD
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

    # ----------------- VALIDAR DUPLICADO -----------------
    cursor.execute(
        "SELECT * FROM direcciones_ip WHERE id_usuario = %s AND ip = %s AND mascara = %s",
        (id_usuario, ip, mascara_decimal)
    )
    existe = cursor.fetchone()
    if existe:
        cursor.close()
        conn.close()
        return jsonify({"error": "Esta IP con la misma máscara ya está registrada"}), 400

    # ----------------- INSERTAR -----------------
    cursor.execute(
        """INSERT INTO direcciones_ip 
        (id_usuario, ip, mascara, prefijo, clase, tipo, direccion_red, broadcast,
        primera_ip, ultima_ip, bits_subred, bits_host, hosts_totales)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            id_usuario, ip, mascara_decimal, prefijo, clase, tipo, red, broadcast,
            primera_ip, ultima_ip, bits_subred, bits_host, total_hosts
        )
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
            "primera_ip": primera_ip,
            "ultima_ip": ultima_ip,
            "bits_subred": bits_subred,
            "bits_host": bits_host,
            "hosts_totales": total_hosts
        }
    }), 201

