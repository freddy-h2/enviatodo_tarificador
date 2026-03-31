# -*- coding: utf-8 -*-
"""Configuración y constantes del cotizador."""

import os

# ── Ficha técnica del producto ────────────────────────────────
LARGO = 44   # cm
ANCHO = 33   # cm
ALTO = 11    # cm
PESO = 1.9   # kg
PESO_VOLUMETRICO = round((LARGO * ANCHO * ALTO) / 5000, 2)
PESO_FACTURADO = max(PESO, PESO_VOLUMETRICO)

# ── API EnviaTodo ─────────────────────────────────────────────
BASE_URL = "https://apiqav2.enviatodo.mx/index.php/"
REQUEST_TIMEOUT = 90   # segundos por petición de cotización
CATALOG_TIMEOUT = 15   # segundos para endpoints de catálogo

# Rate limiting: la API permite 120 req/s, máximo 500 por sesión.
# Usamos pausas amplias para garantizar respuestas consistentes.
PAUSA_ENTRE_PETICIONES = 3.0  # segundos entre cada cotización
PAUSA_ENTRE_ZONAS = 5.0      # segundos entre cada zona
MAX_REINTENTOS = 3            # reintentos si la API responde OK pero sin rates
PAUSA_REINTENTO_BASE = 5.0   # segundos base para reintentos (5s, 10s, 15s)

API_HEADERS = {
    "x-api-key": "enviatodo",
    "x-enviatodo-app": "custom",
    "Content-Type": "application/json",
}

# ── Rutas ─────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONAS_CSV = os.path.join(PROJECT_ROOT, "zonas_custerboots", "37000_cp_mx.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env.local")

# ── Zonas válidas ─────────────────────────────────────────────
ZONAS_VALIDAS = {"Zona A", "Zona B", "Zona C"}


def cargar_token():
    """Carga el bearer token desde ENVIATODO_TOKEN o .env.local."""
    token = os.environ.get("ENVIATODO_TOKEN", "")
    if token:
        return token

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, _, valor = linea.partition("=")
                if "TOKEN" in clave.upper() or "SANDBOX" in clave.upper():
                    return valor.strip()
    return ""
