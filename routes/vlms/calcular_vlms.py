from flask import Blueprint, request, jsonify

calcular_vlms_bp = Blueprint('calcular_vlms', __name__)


# -------------------------------------------
# UTILIDADES
# -------------------------------------------

def ip_to_int(ip):
    a, b, c, d = map(int, ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


def int_to_ip(num):
    return ".".join(str((num >> shift) & 255) for shift in (24, 16, 8, 0))


def prefix_to_mask(prefix):
    mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return int_to_ip(mask_int)


def next_power_of_two(n):
    p = 1
    while p < n:
        p *= 2
    return p


def hosts_to_prefix(hosts_needed):
    total_needed = hosts_needed + 2
    block_size = next_power_of_two(total_needed)
    host_bits = block_size.bit_length() - 1
    return 32 - host_bits


# -------------------------------------------
# API PRINCIPAL
# -------------------------------------------

@calcular_vlms_bp.route('/calcular-vlms', methods=['POST'])
def calcular_vlms():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Debe enviar JSON"}), 400

    ip_base = data.get("ip")
    prefijo = data.get("prefijo")
    hosts = data.get("hosts")

    # ---------------------------------------------
    # VALIDACIONES BÁSICAS
    # ---------------------------------------------
    if not ip_base or prefijo is None or not hosts:
        return jsonify({"error": "Debe enviar ip, prefijo y hosts"}), 400

    try:
        ip_base_int = ip_to_int(ip_base)
    except:
        return jsonify({"error": "IP inválida"}), 400

    if not (0 <= prefijo <= 32):
        return jsonify({"error": "Prefijo inválido"}), 400

    if not isinstance(hosts, list) or not all(isinstance(h, int) and h > 0 for h in hosts):
        return jsonify({"error": "hosts debe ser lista de enteros positivos"}), 400

    # ---------------------------------------------
    # VALIDACIÓN: LA IP BASE DEBE PERTENECER A SU SUBRED
    # (permite dirección de red o broadcast)
    # ---------------------------------------------
    mask_int = (0xFFFFFFFF << (32 - prefijo)) & 0xFFFFFFFF
    network_int = ip_base_int & mask_int
    broadcast_int = network_int | (~mask_int & 0xFFFFFFFF)

    # Si la IP NO pertenece a la subred → ERROR
    if not (network_int <= ip_base_int <= broadcast_int):
        return jsonify({
            "error": "La IP no pertenece a la subred definida por el prefijo"
        }), 400

    # ---------------------------------------------
    # ORDENAR HOSTS Y PROCEDER CON VLSM
    # ---------------------------------------------
    hosts = sorted(hosts, reverse=True)

    resultados = []
    current_ip = network_int  # empezamos en la IP de red
    subnet_number = 1

    for h in hosts:
        new_prefix = hosts_to_prefix(h)
        block_size = 2 ** (32 - new_prefix)

        network_address = current_ip
        broadcast_address = current_ip + block_size - 1

        first_usable = network_address + 1
        last_usable = broadcast_address - 1

        resultados.append({
            "subred_numero": subnet_number,
            "host_solicitados": h,
            "host_asignados": block_size - 2,
            "direccion_red": int_to_ip(network_address),
            "prefijo": new_prefix,
            "mascara": prefix_to_mask(new_prefix),
            "primer_ip_util": int_to_ip(first_usable),
            "ultima_ip_util": int_to_ip(last_usable),
            "broadcast": int_to_ip(broadcast_address)
        })

        current_ip = broadcast_address + 1
        subnet_number += 1

    return jsonify({
        "ip_base": ip_base,
        "prefijo_inicial": prefijo,
        "resultado": resultados
    })
