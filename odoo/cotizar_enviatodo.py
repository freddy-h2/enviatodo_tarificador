#!/usr/bin/env python3
"""
Cotizador EnviaTodo — Custer Boots
===================================
Script standalone para cotizar envíos con la API de EnviaTodo.

Uso:
    python cotizar_enviatodo.py                     # interactivo
    python cotizar_enviatodo.py 06600               # CP destino directo
    python cotizar_enviatodo.py 06600 --peso 2.5    # con peso custom

Configuración:
    Crea un archivo .env en la misma carpeta con:
        ENVIATODO_API_KEY=tu_api_key
        ENVIATODO_USER_ID=tu_user_id

    O pásalas como variables de entorno:
        ENVIATODO_API_KEY=xxx python cotizar_enviatodo.py 06600
"""

import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("❌ Falta el módulo 'requests'. Instálalo con:")
    print("   pip install requests")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN — Custer Boots
# ══════════════════════════════════════════════════════════════

CONFIG = {
    # Credenciales (se sobreescriben con .env o variables de entorno)
    "api_key": "",
    "user_id": "",

    # API
    "base_url": "https://apiqav2.enviatodo.mx/index.php",
    "timeout": 30,

    # Origen — León, Guanajuato
    "origen_cp": "37000",
    "origen_nombre": "Custer Boots",
    "origen_ciudad": "León",
    "origen_estado": "Guanajuato",

    # Paquete predeterminado — caja de botas
    "largo": 44,    # cm
    "ancho": 11,    # cm
    "alto": 33,     # cm
    "peso": 1.9,    # kg

    # Servicio
    "servicio": "express",
}


# ══════════════════════════════════════════════════════════════
# CARGAR CREDENCIALES
# ══════════════════════════════════════════════════════════════

def cargar_env():
    """Carga credenciales desde archivo .env o variables de entorno."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    # Leer .env si existe
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, _, valor = linea.partition("=")
                    os.environ.setdefault(clave.strip(), valor.strip())

    CONFIG["api_key"] = os.environ.get("ENVIATODO_API_KEY", CONFIG["api_key"])
    CONFIG["user_id"] = os.environ.get("ENVIATODO_USER_ID", CONFIG["user_id"])


def validar_credenciales():
    """Verifica que las credenciales estén configuradas."""
    if not CONFIG["api_key"]:
        print("❌ Falta ENVIATODO_API_KEY")
        print("")
        print("   Opción 1: Crea un archivo .env en esta carpeta:")
        print("       ENVIATODO_API_KEY=tu_clave_aqui")
        print("       ENVIATODO_USER_ID=tu_usuario_aqui")
        print("")
        print("   Opción 2: Pásala como variable de entorno:")
        print("       ENVIATODO_API_KEY=xxx ENVIATODO_USER_ID=yyy python cotizar_enviatodo.py 06600")
        return False
    if not CONFIG["user_id"]:
        print("❌ Falta ENVIATODO_USER_ID")
        return False
    return True


# ══════════════════════════════════════════════════════════════
# VALIDACIONES
# ══════════════════════════════════════════════════════════════

def validar_cp(cp, etiqueta="CP"):
    """Valida que un CP mexicano tenga 5 dígitos."""
    cp = str(cp).strip()
    if len(cp) != 5 or not cp.isdigit():
        print("❌ %s inválido: '%s' — debe ser exactamente 5 dígitos" % (etiqueta, cp))
        return None
    return cp


# ══════════════════════════════════════════════════════════════
# COTIZACIÓN
# ══════════════════════════════════════════════════════════════

def cotizar(cp_destino, peso=None, largo=None, ancho=None, alto=None, servicio=None):
    """
    Cotiza un envío con la API de EnviaTodo.

    Args:
        cp_destino: Código postal de destino (5 dígitos)
        peso: Peso en kg (default: 1.9)
        largo: Largo en cm (default: 44)
        ancho: Ancho en cm (default: 11)
        alto: Alto en cm (default: 33)
        servicio: Tipo de servicio (default: express)

    Returns:
        dict con la respuesta de la API, o None si falló
    """
    cp_destino = validar_cp(cp_destino, "CP destino")
    if not cp_destino:
        return None

    payload = {
        "api_key": CONFIG["api_key"],
        "user_id": CONFIG["user_id"],
        "origen": {
            "cp": CONFIG["origen_cp"],
        },
        "destino": {
            "cp": cp_destino,
        },
        "paquete": {
            "largo": largo or CONFIG["largo"],
            "ancho": ancho or CONFIG["ancho"],
            "alto": alto or CONFIG["alto"],
            "peso": peso or CONFIG["peso"],
        },
        "servicio": servicio or CONFIG["servicio"],
    }

    url = CONFIG["base_url"].rstrip("/") + "/cotizar"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + CONFIG["api_key"],
        "X-User-Id": str(CONFIG["user_id"]),
    }

    print("")
    print("━" * 60)
    print("📦  COTIZACIÓN ENVIATODO")
    print("━" * 60)
    print("   Origen:   CP %s (%s, %s)" % (CONFIG["origen_cp"], CONFIG["origen_ciudad"], CONFIG["origen_estado"]))
    print("   Destino:  CP %s" % cp_destino)
    print("   Paquete:  %s×%s×%s cm, %.1f kg" % (
        payload["paquete"]["largo"],
        payload["paquete"]["ancho"],
        payload["paquete"]["alto"],
        payload["paquete"]["peso"],
    ))
    print("   Servicio: %s" % payload["servicio"])
    print("   URL:      %s" % url)
    print("━" * 60)
    print("")

    # Mostrar payload
    print("📋 Payload JSON:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("")

    # Hacer la petición
    print("⏳ Enviando petición...")
    inicio = time.time()

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=CONFIG["timeout"],
        )
        duracion = time.time() - inicio
    except requests.exceptions.Timeout:
        print("❌ Timeout — la API no respondió en %s segundos" % CONFIG["timeout"])
        return None
    except requests.exceptions.ConnectionError as e:
        print("❌ Error de conexión: %s" % str(e))
        return None
    except requests.exceptions.RequestException as e:
        print("❌ Error HTTP: %s" % str(e))
        return None

    # Mostrar respuesta
    print("")
    print("━" * 60)
    print("📨  RESPUESTA (HTTP %s — %.2f s)" % (response.status_code, duracion))
    print("━" * 60)

    # Intentar parsear JSON
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except ValueError:
        print("⚠️  La respuesta no es JSON válido:")
        print(response.text[:1000])
        data = None

    print("━" * 60)

    # Interpretar resultado
    if response.status_code == 200 and data:
        precio = (
            data.get("precio")
            or data.get("costo")
            or data.get("price")
            or data.get("total")
        )
        if precio:
            print("")
            print("✅ Cotización exitosa:")
            print("   💰 Precio: $%.2f MXN" % float(precio))
            if data.get("tiempo_entrega"):
                print("   🕐 Entrega: %s" % data["tiempo_entrega"])
            if data.get("carrier"):
                print("   🚚 Carrier: %s" % data["carrier"])
            print("")
        else:
            print("")
            print("⚠️  Respuesta exitosa pero sin campo de precio reconocido.")
            print("   Campos disponibles: %s" % ", ".join(data.keys()))
            print("")
    elif response.status_code == 401:
        print("")
        print("❌ Credenciales inválidas (HTTP 401)")
        print("   Verifica tu API Key y User ID con EnviaTodo.")
        print("")
    elif response.status_code == 403:
        print("")
        print("❌ Acceso denegado (HTTP 403)")
        print("   Tu cuenta no tiene permisos para este endpoint.")
        print("")
    elif response.status_code == 404:
        print("")
        print("❌ Endpoint no encontrado (HTTP 404)")
        print("   Verifica la URL base: %s" % CONFIG["base_url"])
        print("")
    elif response.status_code >= 500:
        print("")
        print("❌ Error del servidor EnviaTodo (HTTP %s)" % response.status_code)
        print("   Intenta más tarde o contacta soporte@enviatodo.com")
        print("")
    else:
        print("")
        print("⚠️  Respuesta inesperada (HTTP %s)" % response.status_code)
        print("")

    return data


# ══════════════════════════════════════════════════════════════
# COTIZACIÓN MÚLTIPLE
# ══════════════════════════════════════════════════════════════

def cotizar_varios(codigos_postales, **kwargs):
    """Cotiza envíos a múltiples destinos."""
    resultados = []
    for cp in codigos_postales:
        resultado = cotizar(cp, **kwargs)
        resultados.append({"cp": cp, "resultado": resultado})
        if len(codigos_postales) > 1:
            time.sleep(0.5)  # pausa entre peticiones
    return resultados


def mostrar_resumen(resultados):
    """Muestra tabla resumen de cotizaciones múltiples."""
    print("")
    print("═" * 60)
    print("📊  RESUMEN DE COTIZACIONES")
    print("═" * 60)
    print("   %-10s  %-15s  %s" % ("CP", "Precio", "Estado"))
    print("   " + "─" * 45)

    for r in resultados:
        cp = r["cp"]
        data = r["resultado"]
        if data and isinstance(data, dict):
            precio = (
                data.get("precio")
                or data.get("costo")
                or data.get("price")
                or data.get("total")
            )
            if precio:
                print("   %-10s  $%-14.2f  ✅" % (cp, float(precio)))
            else:
                print("   %-10s  %-15s  ⚠️  Sin precio" % (cp, "—"))
        else:
            print("   %-10s  %-15s  ❌ Error" % (cp, "—"))

    print("   " + "─" * 45)
    print("═" * 60)
    print("")


# ══════════════════════════════════════════════════════════════
# MODO INTERACTIVO
# ══════════════════════════════════════════════════════════════

def modo_interactivo():
    """Modo interactivo para cotizar envíos."""
    print("")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     📦  COTIZADOR ENVIATODO — CUSTER BOOTS             ║")
    print("║     León, GTO → Cualquier CP de México                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")
    print("   Origen:  CP 37000 (León, Guanajuato)")
    print("   Paquete: 44×11×33 cm, 1.9 kg")
    print("   Escribe 'salir' para terminar")
    print("")

    while True:
        try:
            entrada = input("🔹 CP destino (o varios separados por coma): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 ¡Hasta luego!")
            break

        if not entrada or entrada.lower() in ("salir", "exit", "q", "quit"):
            print("\n👋 ¡Hasta luego!")
            break

        # Parsear múltiples CPs
        codigos = [cp.strip() for cp in entrada.replace(" ", ",").split(",") if cp.strip()]

        if len(codigos) == 1:
            cotizar(codigos[0])
        elif len(codigos) > 1:
            resultados = cotizar_varios(codigos)
            mostrar_resumen(resultados)
        print("")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    cargar_env()

    if not validar_credenciales():
        sys.exit(1)

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {sys.argv[i]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith("--")}

    kwargs = {}
    if "--peso" in flags:
        kwargs["peso"] = float(flags["--peso"])
    if "--largo" in flags:
        kwargs["largo"] = float(flags["--largo"])
    if "--ancho" in flags:
        kwargs["ancho"] = float(flags["--ancho"])
    if "--alto" in flags:
        kwargs["alto"] = float(flags["--alto"])
    if "--servicio" in flags:
        kwargs["servicio"] = flags["--servicio"]

    if not args:
        # Modo interactivo
        modo_interactivo()
    elif len(args) == 1:
        # Un solo CP
        cotizar(args[0], **kwargs)
    else:
        # Múltiples CPs
        resultados = cotizar_varios(args, **kwargs)
        mostrar_resumen(resultados)


if __name__ == "__main__":
    main()
