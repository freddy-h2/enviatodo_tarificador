# -*- coding: utf-8 -*-
"""Generación del CSV de cotizaciones."""

import csv
import os
from datetime import datetime

from src.config import ALTO, ANCHO, LARGO, OUTPUT_DIR, PESO, PESO_VOLUMETRICO


def generar_csv(cp_origen, zonas, resultados):
    """Genera el CSV de cotizaciones en output/.

    Args:
        cp_origen: CP de origen.
        zonas: dict de zonas con cp, distancia_km, etc.
        resultados: dict {"Zona A": [cotizaciones], ...}

    Returns:
        str: Ruta absoluta del archivo generado.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ahora = datetime.now()
    nombre = "cotizacion_%s.csv" % ahora.strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(OUTPUT_DIR, nombre)

    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        # Encabezado informativo
        w.writerow(["Cotizaciones EnviaTodo por Zona — Custer Boots"])
        w.writerow(["Fecha de cotización", ahora.strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Fuente", "API EnviaTodo v2 (rates_client)"])
        w.writerow([])

        # Datos del paquete
        w.writerow(["CP Origen", cp_origen])
        w.writerow(["Largo (cm)", LARGO])
        w.writerow(["Ancho (cm)", ANCHO])
        w.writerow(["Alto (cm)", ALTO])
        w.writerow(["Peso (kg)", PESO])
        w.writerow(["Peso volumétrico (kg)", PESO_VOLUMETRICO])
        w.writerow([])

        # Tabla de cotizaciones
        w.writerow([
            "Zona", "CP más lejano", "Distancia (km)", "Ubicación",
            "Paquetería", "Servicio", "Vía",
            "Subtotal (MXN)", "IVA (MXN)", "Total (MXN)",
            "Cargo zona extendida", "Cargo guía",
            "Entrega estimada", "Modo entrega",
        ])

        for zona_key in ["Zona A", "Zona B", "Zona C"]:
            zona_data = zonas.get(zona_key, {})
            cp = zona_data.get("cp", "—")
            dist = zona_data.get("distancia_km", 0)
            ubicacion = "%s, %s, %s" % (
                zona_data.get("colonia", ""),
                zona_data.get("municipio", ""),
                zona_data.get("estado", ""),
            )
            zona_label = zona_key.replace("Zona ", "")
            cotizaciones = resultados.get(zona_key, [])

            for i, c in enumerate(cotizaciones):
                if c["disponible"]:
                    w.writerow([
                        zona_label if i == 0 else "",
                        cp if i == 0 else "",
                        dist if i == 0 else "",
                        ubicacion if i == 0 else "",
                        c["carrier"], c["servicio"], c["via"],
                        "%.2f" % c["subtotal"],
                        "%.2f" % c["iva"],
                        "%.2f" % c["total"],
                        "%.2f" % c["zona_ext"],
                        "%.2f" % c["guia"],
                        c["entrega"], c["modo"],
                    ])
                else:
                    w.writerow([
                        zona_label if i == 0 else "",
                        cp if i == 0 else "",
                        dist if i == 0 else "",
                        ubicacion if i == 0 else "",
                        c["carrier"], c["servicio"], c["via"],
                        "Sin cobertura", "—", "—", "—", "—", "—", "—",
                    ])

    return ruta
