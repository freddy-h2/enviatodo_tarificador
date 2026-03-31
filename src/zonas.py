# -*- coding: utf-8 -*-
"""Análisis de zonas: encuentra el CP más lejano por zona."""

import csv

from src.config import ZONAS_VALIDAS


def encontrar_cp_mas_lejano(csv_path, cp_origen):
    """Lee el CSV de zonas y devuelve el CP con mayor distancia por zona.

    Args:
        csv_path: Ruta al archivo 37000_cp_mx.csv.
        cp_origen: CP de origen (para validación / log).

    Returns:
        dict: {"Zona A": {cp, distancia_km, colonia, municipio, estado, ciudad}, ...}
    """
    zonas = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zona = row.get("Zona", "").strip()
            if zona not in ZONAS_VALIDAS:
                continue
            try:
                dist = float(row.get("Distancia_km", 0))
            except (ValueError, TypeError):
                continue

            cp = str(row.get("d_codigo", "")).strip().zfill(5)
            if not cp:
                continue

            if zona not in zonas or dist > zonas[zona]["distancia_km"]:
                zonas[zona] = {
                    "cp": cp,
                    "distancia_km": dist,
                    "colonia": row.get("d_asenta", ""),
                    "municipio": row.get("D_mnpio", ""),
                    "estado": row.get("d_estado", ""),
                    "ciudad": row.get("d_ciudad", ""),
                }

    return zonas
