# -*- coding: utf-8 -*-
"""Transformador de plantilla CSV de Odoo para portador de entrega EnviaTodo.

Genera un CSV de delivery carrier de Odoo con precios actualizados por zona,
listo para importar directamente en Odoo 19.

El formato usa:
  - Subcampos expandidos para One2many (reglas de precio):
    ``Reglas de precios/Variable``, ``Reglas de precios/Operador``, etc.
  - Valores separados por coma para Many2many (prefijos de CP):
    ``Prefijos de C.P.`` con todos los CPs en una sola celda.
"""

import csv
import os
import sys

# Increase CSV field size limit for reading/writing compact format
# (25k+ CPs comma-separated in one cell can exceed 131KB default)
csv.field_size_limit(sys.maxsize)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Número de reglas de precio por zona (11 lineales + 1 bulk = 12 total)
_NUM_PRICE_RULES = 12

# Pesos para los tiers lineales (n=1..11 → 20*n kg)
_LINEAR_TIERS = [20 * n for n in range(1, 12)]

# Peso del tier bulk
_BULK_WEIGHT = 980.0

# Multiplicador del tier bulk: ceil(980/20) = 49
_BULK_MULTIPLIER = 49

# Marcador de zona en columna 1 del CSV de plantilla
_ZONA_MARKER = "Envío a domicilio - Zona"

# Encabezado del CSV de importación Odoo
_ODOO_IMPORT_HEADER = [
    "Secuencia",
    "Método de entrega",
    "Proveedor",
    "Está publicado",
    "Reglas de precios/Variable",
    "Reglas de precios/Operador",
    "Reglas de precios/Valor máximo",
    "Reglas de precios/Precio de venta base",
    "Reglas de precios/Precio de venta",
    "Reglas de precios/Factor variable",
    "Prefijos de C.P.",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_price_rules(precio_base: float) -> list:
    """Generate the 12 price rule tuples for a zone given a base price.

    Each tuple is (variable, operator, max_value, list_base_price,
    list_price, variable_factor).

    Tiers 1-11 are linear: weight <= 20*n, price = precio_base * n.
    Tier 12 is bulk: weight <= 980.00, price = precio_base * 49.

    Args:
        precio_base: Base price for ≤20 kg (tier 1).

    Returns:
        list[tuple]: List of 12 rule tuples.
    """
    rules = []
    for n, weight in enumerate(_LINEAR_TIERS, start=1):
        rules.append(
            (
                "weight",
                "<=",
                "%.2f" % float(weight),
                "%.2f" % round(precio_base * n, 2),
                "0.00",
                "weight",
            )
        )
    # Bulk tier
    rules.append(
        (
            "weight",
            "<=",
            "%.2f" % _BULK_WEIGHT,
            "%.2f" % round(precio_base * _BULK_MULTIPLIER, 2),
            "0.00",
            "weight",
        )
    )
    return rules


def _parse_template(plantilla_path: str) -> list:
    """Parse the compact template CSV and extract zone data.

    Args:
        plantilla_path: Path to the compact template CSV.

    Returns:
        list[dict]: List of zone dicts with keys:
            seq, name, provider, published, cps (list[str]).
    """
    zones = []
    current_zone = None

    with open(plantilla_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        for row in reader:
            nombre = row[1].strip() if len(row) > 1 else ""
            col6 = row[6].strip() if len(row) > 6 else ""

            if _ZONA_MARKER in nombre:
                current_zone = {
                    "seq": row[0].strip(),
                    "name": nombre,
                    "provider": row[2].strip() if len(row) > 2 else "",
                    "published": row[3].strip() if len(row) > 3 else "",
                    "cps": [],
                }
                zones.append(current_zone)
                if col6:
                    current_zone["cps"] = [
                        cp.strip() for cp in col6.split(",") if cp.strip()
                    ]

    return zones


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------


def generar_odoo_csv(
    precios_por_zona: dict,
    plantilla_path: str,
    output_path: str,
) -> str:
    """Generate an Odoo delivery carrier import CSV.

    Reads the compact template CSV (CPs comma-separated in one cell) and
    produces a CSV ready for Odoo's import wizard:

    - **One2many** (price rules): expanded into subfield columns, one rule
      per row (12 rows per zone).
    - **Many2many** (zip prefixes): all CPs comma-separated in a single
      cell on the first row of each zone.

    Output format::

        "Secuencia","Método de entrega",...,"Reglas de precios/Variable",
        "Reglas de precios/Operador",...,"Prefijos de C.P."
        "10","Envío a domicilio - Zona A","Por reglas","True",
        "weight","<=","20.00","137.88","0.00","weight","01000,01010,..."
        "","","","","weight","<=","40.00","275.76","0.00","weight",""
        ... (10 more rule rows with empty CP column)

    Args:
        precios_por_zona: dict from leer_cotizacion(), e.g.::

            {
                'Zona A': {'precio_base': 137.88, ...},
                'Zona B': {'precio_base': 150.00, ...},
                'Zona C': {'precio_base': 200.00, ...},
            }

        plantilla_path: Path to the compact template CSV
            (``zonas_custerboots/37000_odoo_delivery_carrier.csv``).
        output_path: Path where the output CSV will be written.

    Returns:
        str: Absolute path of the generated file.

    Raises:
        FileNotFoundError: If ``plantilla_path`` does not exist.
        KeyError: If a zone found in the template is not in ``precios_por_zona``.
    """
    if not os.path.exists(plantilla_path):
        raise FileNotFoundError("Plantilla de Odoo no encontrada: %s" % plantilla_path)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Parse template
    zones = _parse_template(plantilla_path)

    # Build output rows
    output_rows = [_ODOO_IMPORT_HEADER]

    for zone in zones:
        zona_nombre = "Zona " + zone["name"].split("Zona ")[-1].strip()
        precio_base = precios_por_zona[zona_nombre]["precio_base"]
        rules = _generate_price_rules(precio_base)
        cps_joined = ",".join(zone["cps"])

        for i, rule in enumerate(rules):
            if i == 0:
                # First row: carrier info + first rule + ALL CPs comma-separated
                carrier_cols = [
                    zone["seq"],
                    zone["name"],
                    zone["provider"],
                    zone["published"],
                ]
                cp_col = cps_joined
            else:
                # Continuation rows: empty carrier + rule + empty CP
                carrier_cols = ["", "", "", ""]
                cp_col = ""

            output_rows.append(carrier_cols + list(rule) + [cp_col])

    # Write output
    with open(output_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(
            f_out,
            quoting=csv.QUOTE_ALL,
            lineterminator="\n",
        )
        writer.writerows(output_rows)

    return os.path.abspath(output_path)
