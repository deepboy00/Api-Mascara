from flask import Blueprint, request, jsonify

calcular_vlms_bp = Blueprint('calcular_vlms', __name__)

# Utilidades basicas
def ip_to_int(ip):
    a, b, c, d = map(int, ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d

def int_to_ip(num):
    return ".".join(str((num >> shift) & 255) for shift in (24, 16, 8, 0))

def prefix_to_mask(prefix):
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return int_to_ip(mask)

def block_size_for_hosts(hosts):
    needed = hosts + 2
    p = 1
    while p < needed:
        p <<= 1
    return p

def hosts_to_prefix(hosts):
    block = block_size_for_hosts(hosts)
    host_bits = block.bit_length() - 1
    return 32 - host_bits

# Validaciones
def validar_ip(octs):
    if len(octs) != 4:
        return False, "La IP debe tener 4 octetos"

    # verificar vacíos
    if any(o == "" or o is None for o in octs):
        return False, "Completa los 4 octetos de la IP"

    try:
        o1, o2, o3, o4 = map(int, octs)
    except:
        return False, "Los octetos deben ser números"

    # primer octeto 1–223
    if o1 < 1 or o1 > 223:
        return False, "Primer octeto inválido (1–223)"

    if o1 == 127:
        return False, "127.x.x.x es reservado (loopback)"

    # octetos 2–4 (0–255)
    if any(v < 0 or v > 255 for v in (o2, o3, o4)):
        return False, "Los octetos 2–4 deben estar entre 0–255"

    # reservadas globales
    if o1 == 0 and o2 == 0 and o3 == 0 and o4 == 0:
        return False, "0.0.0.0 es una dirección reservada"

    if o1 == 255 and o2 == 255 and o3 == 255 and o4 == 255:
        return False, "255.255.255.255 es broadcast global"

    return True, ""


def validar_hosts_lista(lista):
    if not isinstance(lista, list) or len(lista) == 0:
        return False, "Debe enviar al menos un host", None

    hosts = []
    for h in lista:
        if not isinstance(h, int) or h < 1:
            return False, "Cada host debe ser un número mayor a 0", None
        hosts.append(h)

    return True, "", hosts


def validar_caben(hosts, prefijo):
    capacidad = 2 ** (32 - prefijo)
    usado = sum(block_size_for_hosts(h) for h in hosts)
    return usado <= capacidad, capacidad, usado

# Endpoint 
@calcular_vlms_bp.route('/calcular-vlms', methods=['POST'])
def calcular_vlms():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Debe enviar JSON"}), 400

    ip = data.get("ip")
    prefijo = data.get("prefijo")
    hosts_lista = data.get("hosts")

    if not ip or prefijo is None or hosts_lista is None:
        return jsonify({"error": "Debe enviar ip, prefijo y hosts"}), 400

    # Validacion
    try:
        octs = ip.split(".")
    except:
        return jsonify({"error": "IP inválida"}), 400

    ok, err = validar_ip(octs)
    if not ok:
        return jsonify({"error": err}), 400

    try:
        prefijo = int(prefijo)
    except:
        return jsonify({"error": "Prefijo inválido"}), 400

    if prefijo < 8 or prefijo > 30:
        return jsonify({"error": "Prefijo permitido: /8 hasta /30"}), 400

    ok, err, hosts = validar_hosts_lista(hosts_lista)
    if not ok:
        return jsonify({"error": err}), 400

    # ordenar hosts como VLSM
    hosts.sort(reverse=True)

    # verificar que quepan dentro del prefijo mayor
    cabe, capacidad, usado = validar_caben(hosts, prefijo)
    if not cabe:
        return jsonify({
            "error": f"Las subredes NO caben en /{prefijo}",
            "capacidad": capacidad,
            "requerido": usado
        }), 400


    # Logica para el vlsm

    base_int = ip_to_int(ip)
    current_ip = base_int
    resultados = []
    numero = 1

    for h in hosts:
        new_prefix = hosts_to_prefix(h)
        block = 2 ** (32 - new_prefix)

        red = current_ip
        broadcast = red + block - 1
        first = red + 1
        last = broadcast - 1

        resultados.append({
            "subred_numero": numero,
            "host_solicitados": h,
            "host_asignados": block - 2,
            "direccion_red": int_to_ip(red),
            "prefijo": new_prefix,
            "mascara": prefix_to_mask(new_prefix),
            "primer_ip_util": int_to_ip(first),
            "ultima_ip_util": int_to_ip(last),
            "broadcast": int_to_ip(broadcast)
        })

        current_ip = broadcast + 1
        numero += 1

    return jsonify({
        "ip_base": ip,
        "prefijo_inicial": prefijo,
        "resultado": resultados
    })
