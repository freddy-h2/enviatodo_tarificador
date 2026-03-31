# -*- coding: utf-8 -*-
"""Transformador de plantilla CSV de Odoo para portador de entrega EnviaTodo.

Genera un CSV de delivery carrier de Odoo con precios actualizados por zona,
basándose en los datos de cotización del cotizador EnviaTodo.
"""

import csv
import os
import sys

# Increase CSV field size limit for compact format (25k+ CPs in one cell)
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

# Índices de columnas en el CSV de plantilla
_COL_NOMBRE = 1
_COL_PRICE_RULE = 5
_COL_CP_PREFIX = 6


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------


def _format_price(amount: float) -> str:
    """Format a price in Odoo locale (dot=thousands, comma=decimal).

    Args:
        amount: Price as a float.

    Returns:
        str: Formatted price string, e.g. ``1.234,56``.
    """
    # Round to 2 decimal places to avoid floating-point drift
    rounded = round(amount, 2)
    # Format with 2 decimal places using standard locale
    formatted = "{:,.2f}".format(rounded)
    # Python uses comma for thousands and dot for decimals → swap
    # "1,234.56" → "1.234,56"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def _build_price_rule(weight: float, price: float) -> str:
    """Build a single Odoo price rule string.

    Args:
        weight: Maximum weight threshold in kg.
        price: Fixed price for this tier.

    Returns:
        str: Rule string like ``if weight <= 20.00 then fixed price $ 137,88``.
    """
    return "if weight <= %.2f then fixed price $ %s" % (weight, _format_price(price))


def _generate_price_rules(precio_base: float) -> list:
    """Generate the 12 price rules for a zone given a base price.

    Tiers 1-11 are linear: weight <= 20*n, price = precio_base * n.
    Tier 12 is bulk: weight <= 980.00, price = precio_base * 49.

    Args:
        precio_base: Base price for ≤20 kg (tier 1).

    Returns:
        list[str]: List of 12 price rule strings.
    """
    rules = []
    for n, weight in enumerate(_LINEAR_TIERS, start=1):
        rules.append(_build_price_rule(float(weight), precio_base * n))
    # Bulk tier
    rules.append(_build_price_rule(_BULK_WEIGHT, precio_base * _BULK_MULTIPLIER))
    return rules


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------


def generar_odoo_csv(
    precios_por_zona: dict,
    plantilla_path: str,
    output_path: str,
) -> str:
    """Generate an Odoo delivery carrier CSV with updated prices.

    Reads the Odoo delivery carrier template CSV (compact format: all CP
    prefixes comma-separated in a single cell) and produces a new version
    with price rules recalculated from the provided zone prices.

    The compact format expected by Odoo is::

        "Secuencia","Método de entrega",...,"Reglas de precios","Prefijos de C.P."
        "10","Envío a domicilio - Zona A",...,"if weight <= ...","01000,01010,..."
        "","","","","","if weight <= 40.00 ...",""
        ...

    Args:
        precios_por_zona: dict from leer_cotizacion(), e.g.::

            {
                'Zona A': {'precio_base': 137.88, ...},
                'Zona B': {'precio_base': 150.00, ...},
                'Zona C': {'precio_base': 200.00, ...},
            }

        plantilla_path: Path to the template CSV
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

    output_rows = []

    with open(plantilla_path, newline="", encoding="utf-8") as f_in:
        reader = csv.reader(f_in)

        # --- State machine ---
        # current_rules: list of new price rules for the active zone (or None)
        # rules_written: how many price rules have been written for current zone
        current_rules: list | None = None
        rules_written: int = 0

        for row_idx, row in enumerate(reader):
            # Line 1 (row_idx == 0): CSV header — copy verbatim
            if row_idx == 0:
                output_rows.append(row)
                continue

            # Detect zone header row: column 1 contains the zone marker
            if len(row) > _COL_NOMBRE and _ZONA_MARKER in row[_COL_NOMBRE]:
                # Extract zone letter from e.g. "Envío a domicilio - Zona A"
                zona_nombre = "Zona " + row[_COL_NOMBRE].split("Zona ")[-1].strip()
                precio_base = precios_por_zona[zona_nombre]["precio_base"]
                current_rules = _generate_price_rules(precio_base)
                rules_written = 0

                # Build the zone header row: preserve cols 0-4 and 6,
                # replace col 5 with first price rule.
                # Col 6 contains all CP prefixes comma-separated — copy verbatim.
                new_row = list(row)
                new_row[_COL_PRICE_RULE] = current_rules[0]
                rules_written = 1
                output_rows.append(new_row)
                continue

            # Inside a zone block: price rule continuation rows
            if current_rules is not None:
                col5 = row[_COL_PRICE_RULE] if len(row) > _COL_PRICE_RULE else ""

                if col5.startswith("if weight"):
                    if rules_written < _NUM_PRICE_RULES:
                        new_row = list(row)
                        new_row[_COL_PRICE_RULE] = current_rules[rules_written]
                        rules_written += 1
                        output_rows.append(new_row)
                    else:
                        # More rules in template than expected — copy as-is
                        output_rows.append(row)
                    continue

            # Any other row — copy verbatim
            output_rows.append(row)

    # Write output
    with open(output_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(
            f_out,
            quoting=csv.QUOTE_ALL,
            lineterminator="\n",
        )
        writer.writerows(output_rows)

    return os.path.abspath(output_path)
