from flask import Blueprint, request, jsonify

calcular_vlsm_bp = Blueprint('calcular_vlsm', __name__)


# ==================================================
# FUNCIONES DE APOYO (LÓGICA PURA)
# ==================================================

def validar_ip(octs):
    if len(octs) != 4:
        return False, "La IP debe tener 4 octetos"

    o1 = int(octs[0])
    o2 = int(octs[1])
    o3 = int(octs[2])
    o4 = int(octs[3])

    if o1 < 1 or o1 > 223:
        return False, "Primer octeto inválido (1–223)"

    if o1 == 127:
        return False, "127.x.x.x está reservado para loopback"

    for v in [o2, o3, o4]:
        if v < 0 or v > 255:
            return False, "Los octetos 2–4 deben estar entre 0–255"

    if o1 == 0 and o4 == 0:
        return False, "0.0.0.0 es una IP reservada"

    if o1 == 255 and o2 == 255 and o3 == 255 and o4 == 255:
        return False, "255.255.255.255 es broadcast global"

    return True, ""


def ip_to_int(o1, o2, o3, o4):
    return (o1 << 24) | (o2 << 16) | (o3 << 8) | o4


def int_to_ip(n):
    return f"{(n >> 24) & 255}.{(n >> 16) & 255}.{(n >> 8) & 255}.{n & 255}"


def mask_from_prefix(pref):
    mask = (0xFFFFFFFF << (32 - pref)) & 0xFFFFFFFF
    return mask


def mask_to_decimal(mask):
    return int_to_ip(mask)


def subred_minima(hosts):
    needed = hosts + 2
    bits = (needed - 1).bit_length()
    return 2 ** bits


def capacidad_prefijo(pref):
    return 2 ** (32 - pref)


# ==================================================
#                 API VLSM
# ==================================================
@calcular_vlsm_bp.route('/calcular-vlsm', methods=['POST'])
def calcular_vlsm():

    data = request.json

    # ----------------------
    # VALIDAR ENTRADA
    # ----------------------
    if "ip" not in data or "prefijo" not in data or "hosts" not in data:
        return jsonify({"error": "Debes enviar ip, prefijo y hosts"}), 400

    ip = data["ip"]
    prefijo = int(data["prefijo"])
    hosts = data["hosts"]

    # validar estructura de IP
    try:
        octs = [int(x) for x in ip.split(".")]
    except:
        return jsonify({"error": "IP inválida"}), 400

    ok, err = validar_ip(octs)
    if not ok:
        return jsonify({"error": err}), 400

    # validar prefijo
    if prefijo < 8 or prefijo > 30:
        return jsonify({"error": "Prefijo debe estar entre 8 y 30"}), 400

    # validar hosts
    if not isinstance(hosts, list) or len(hosts) == 0:
        return jsonify({"error": "Debes enviar una lista de hosts"}), 400

    for h in hosts:
        if type(h) != int or h < 1:
            return jsonify({"error": "Cada host debe ser un entero mayor que 0"}), 400

    # ordenar de mayor a menor
    hosts_sorted = sorted(hosts, reverse=True)

    # -------------------------
    # VALIDAR QUE QUEPAN
    # -------------------------
    total_capacidad = capacidad_prefijo(prefijo)
    requerido = sum(subred_minima(h) for h in hosts_sorted)

    if requerido > total_capacidad:
        return jsonify({
            "error": f"Las subredes NO caben en /{prefijo}. Capacidad: {total_capacidad}, requerido: {requerido}"
        }), 400

    # -------------------------
    # *** VALIDACIÓN REMOVIDA ***
    #     Se permite red y broadcast
    # -------------------------

    ip_num = ip_to_int(*octs)
    mask = mask_from_prefix(prefijo)
    network = ip_num & mask

    # -------------------------
    # CALCULAR VLSM
    # -------------------------
    resultados = []
    inicio = network  # comenzamos desde la red (correcto incluso si la ip ingresada es red o broadcast)

    num_subred = 1

    for h in hosts_sorted:

        size = subred_minima(h)
        pref = 32 - (size.bit_length() - 1)

        red = inicio
        first = red + 1
        last = red + size - 2
        bc = red + size - 1
        mascara = mask_from_prefix(pref)

        resultados.append({
            "subred": num_subred,
            "hosts_solicitados": h,
            "tamaño_real": size,
            "direccion_red": int_to_ip(red),
            "prefijo": f"/{pref}",
            "primer_ip_util": int_to_ip(first),
            "ultima_ip_util": int_to_ip(last),
            "broadcast": int_to_ip(bc),
            "mascara_decimal": mask_to_decimal(mascara)
        })

        inicio += size
        num_subred += 1

    # -------------------------
    # RESPUESTA FINAL
    # -------------------------
    return jsonify({
        "ip_base": ip,
        "prefijo": f"/{prefijo}",
        "hosts_ordenados": hosts_sorted,
        "subredes": resultados
    })
