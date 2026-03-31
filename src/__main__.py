# -*- coding: utf-8 -*-
"""
Cotizador por Zonas — Custer Boots × EnviaTodo
===============================================
Uso:
    python -m src --cp 37000
    python -m src 37000
    python -m src                  # usa 37000 por defecto
"""

import argparse
import os
import sys
import time

from src.api import EnviaTodoClient
from src.config import (
    ALTO,
    ANCHO,
    LARGO,
    ODOO_OUTPUT_DIR,
    ODOO_TEMPLATE_PATH,
    OUTPUT_DIR,
    PAUSA_ENTRE_ZONAS,
    PESO,
    PESO_VOLUMETRICO,
    ZONAS_CSV,
    cargar_token,
)
from src.csv_writer import generar_csv
from src.odoo_exporter import generar_odoo_csv
from src.quotation_reader import leer_cotizacion
from src.zonas import encontrar_cp_mas_lejano


def odoo_export(args):
    """Genera el CSV de delivery carrier de Odoo a partir de una cotización.

    Args:
        args: Namespace de argparse con atributo input_file.
    """
    if not args.input_file:
        print("❌ Se requiere --input con el nombre del archivo de cotización.")
        print(
            "   Ejemplo: python -m src --odoo-export --input cotizacion_20260330_231047.csv"
        )
        sys.exit(1)

    # Resolver ruta de entrada (buscar en OUTPUT_DIR si no es absoluta)
    input_path = args.input_file
    if not os.path.isabs(input_path):
        input_path = os.path.join(OUTPUT_DIR, input_path)

    if not os.path.exists(input_path):
        print("❌ Archivo no encontrado: %s" % input_path)
        sys.exit(1)

    # Derivar nombre de salida: stem del input + '_delivery_carrier.csv'
    stem = os.path.splitext(os.path.basename(args.input_file))[0]
    output_path = os.path.join(ODOO_OUTPUT_DIR, stem + "_delivery_carrier.csv")

    print("╔══════════════════════════════════════════════════════════╗")
    print("║  📦 EXPORTADOR ODOO — CUSTER BOOTS                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("📄 Leyendo cotización: %s" % input_path)

    precios = leer_cotizacion(input_path)

    for zona_key in ["Zona A", "Zona B", "Zona C"]:
        p = precios[zona_key]
        print(
            "   %s: $%.2f MXN (%s %s)"
            % (zona_key, p["precio_base"], p["carrier"], p["servicio"])
        )

    print()
    print("📝 Generando plantilla Odoo...")
    ruta = generar_odoo_csv(precios, ODOO_TEMPLATE_PATH, output_path)
    print("   ✅ %s" % ruta)


def main():
    parser = argparse.ArgumentParser(
        description="Cotiza envíos por zona con la API de EnviaTodo.",
    )
    parser.add_argument(
        "cp_origen",
        nargs="?",
        default=None,
        help="Código postal de origen (5 dígitos). Default: 37000.",
    )
    parser.add_argument(
        "--cp",
        default=None,
        help="Código postal de origen (alternativa a argumento posicional).",
    )
    parser.add_argument(
        "--odoo-export",
        action="store_true",
        help="Genera el CSV de delivery carrier de Odoo a partir de una cotización.",
    )
    parser.add_argument(
        "--input",
        "-input",
        dest="input_file",
        default=None,
        help="Nombre del archivo de cotización CSV (buscado en el directorio output/).",
    )
    args = parser.parse_args()

    if args.odoo_export:
        odoo_export(args)
        return

    cp_origen = args.cp or args.cp_origen or "37000"
    cp_origen = cp_origen.strip().lstrip("-")

    if len(cp_origen) != 5 or not cp_origen.isdigit():
        print(
            "❌ CP de origen inválido: '%s' — debe ser exactamente 5 dígitos."
            % cp_origen
        )
        sys.exit(1)

    # ── Banner ────────────────────────────────────────────────
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  📦 COTIZADOR POR ZONAS — CUSTER BOOTS                 ║")
    print("║  Origen: CP %s                                     ║" % cp_origen)
    print(
        "║  Paquete: %s×%s×%s cm, %s kg                          ║"
        % (LARGO, ANCHO, ALTO, PESO)
    )
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # ── Token ─────────────────────────────────────────────────
    token = cargar_token()
    if not token:
        print("❌ No se encontró token de EnviaTodo.")
        print("   Configura ENVIATODO_TOKEN como variable de entorno")
        print("   o colócalo en .env.local")
        sys.exit(1)
    print("✅ Token cargado (…%s)" % token[-20:])

    # ── Zonas ─────────────────────────────────────────────────
    print("\n📊 Analizando zonas desde CSV...")
    zonas = encontrar_cp_mas_lejano(ZONAS_CSV, cp_origen)

    if not zonas:
        print("❌ No se encontraron zonas en el CSV.")
        sys.exit(1)

    for zona_key in sorted(zonas.keys()):
        z = zonas[zona_key]
        print(
            "   %s: CP %s — %.1f km — %s, %s, %s"
            % (
                zona_key,
                z["cp"],
                z["distancia_km"],
                z["colonia"],
                z["municipio"],
                z["estado"],
            )
        )

    # ── Cliente API ───────────────────────────────────────────
    client = EnviaTodoClient(token)

    # ── Servicios disponibles ─────────────────────────────────
    print("\n🔍 Consultando servicios disponibles...")
    proveedores = client.obtener_servicios()

    if not proveedores:
        print("❌ No se pudieron obtener los servicios. Verifica el token.")
        sys.exit(1)

    # Aplanar servicios para iterar
    servicios = []
    for p in proveedores:
        for s in p["services"]:
            servicios.append(
                {
                    "id": s["id"],
                    "label": s["label"],
                    "provider": p["provider"],
                    "via": s["via"],
                }
            )
            print("   ✅ %s — %s (%s)" % (p["provider"], s["label"], s["via"]))

    # ── Datos de CPs ──────────────────────────────────────────
    print("\n🔍 Consultando datos de códigos postales...")
    datos_origen = client.obtener_datos_cp(cp_origen)
    if datos_origen:
        print(
            "   ✅ Origen CP %s: %s, %s"
            % (
                cp_origen,
                datos_origen["municipality"],
                datos_origen["state"],
            )
        )
    else:
        print("   ⚠️  Origen: usando valores por defecto")
        datos_origen = {
            "suburb": "Centro",
            "municipality": "León",
            "state": "Guanajuato",
            "city": "León de los Aldama",
            "state_code": "GT",
        }

    datos_destinos = {}
    for zona_key in sorted(zonas.keys()):
        cp = zonas[zona_key]["cp"]
        datos = client.obtener_datos_cp(cp)
        if datos:
            datos_destinos[zona_key] = datos
            print(
                "   ✅ %s CP %s: %s, %s"
                % (
                    zona_key,
                    cp,
                    datos["municipality"],
                    datos["state"],
                )
            )
        else:
            datos_destinos[zona_key] = {
                "suburb": zonas[zona_key]["colonia"],
                "municipality": zonas[zona_key]["municipio"],
                "state": zonas[zona_key]["estado"],
                "city": zonas[zona_key]["ciudad"],
                "state_code": "",
            }
            print("   ⚠️  %s CP %s: usando datos del CSV" % (zona_key, cp))

    # ── Cotizar ───────────────────────────────────────────────
    total_servicios = len(servicios) * 3
    print(
        "\n💰 Cotizando envíos (%d peticiones, ~%.0fs estimado)..."
        % (
            total_servicios,
            total_servicios * 1.5 + 2 * PAUSA_ENTRE_ZONAS,
        )
    )

    def on_progress(carrier, servicio, resultado):
        """Callback para mostrar progreso en tiempo real."""
        if isinstance(resultado, str):
            # Es un mensaje de reintento
            print("   🔄 %-10s %-25s → %s" % (carrier, servicio, resultado))
        elif resultado is not None:
            print(
                "   ✅ %-10s %-25s → $%8.2f MXN (%s)"
                % (
                    carrier,
                    servicio,
                    resultado["total"],
                    resultado["modo"],
                )
            )
        else:
            print("   ❌ %-10s %-25s → Sin cobertura" % (carrier, servicio))

    resultados = {}
    zona_keys = ["Zona A", "Zona B", "Zona C"]

    for i, zona_key in enumerate(zona_keys):
        z = zonas[zona_key]
        print(
            "\n   ━━━ %s → CP %s (%.1f km) ━━━"
            % (
                zona_key,
                z["cp"],
                z["distancia_km"],
            )
        )

        cotizaciones = client.cotizar_zona(
            cp_origen,
            z["cp"],
            datos_origen,
            datos_destinos[zona_key],
            servicios,
            on_progress=on_progress,
        )
        resultados[zona_key] = cotizaciones

        # Pausa entre zonas para no saturar la API
        if i < len(zona_keys) - 1:
            time.sleep(PAUSA_ENTRE_ZONAS)

    # ── CSV ───────────────────────────────────────────────────
    print("\n📄 Generando CSV...")
    ruta_csv = generar_csv(cp_origen, zonas, resultados)
    print("   ✅ %s" % ruta_csv)

    # ── Resumen ───────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("📊 RESUMEN")
    print("═" * 60)
    print("   Origen:  CP %s" % cp_origen)
    print(
        "   Paquete: %s×%s×%s cm, %s kg (vol: %s kg)"
        % (
            LARGO,
            ANCHO,
            ALTO,
            PESO,
            PESO_VOLUMETRICO,
        )
    )
    print("   Archivo: %s" % ruta_csv)
    print()

    for zona_key in zona_keys:
        z = zonas[zona_key]
        cotizaciones = resultados.get(zona_key, [])
        disponibles = [c for c in cotizaciones if c["disponible"]]
        if disponibles:
            mejor = min(disponibles, key=lambda c: c["total"])
            print(
                "   %s: CP %s (%6.1f km) → $%.2f MXN (%s %s)"
                % (
                    zona_key,
                    z["cp"],
                    z["distancia_km"],
                    mejor["total"],
                    mejor["carrier"],
                    mejor["servicio"],
                )
            )
        else:
            print(
                "   %s: CP %s (%6.1f km) → Sin cotizaciones disponibles"
                % (
                    zona_key,
                    z["cp"],
                    z["distancia_km"],
                )
            )

    print("═" * 60)


if __name__ == "__main__":
    main()
