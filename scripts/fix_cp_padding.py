#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el zero-padding de códigos postales en el CSV de zonas.

Los códigos postales mexicanos deben tener exactamente 5 dígitos.
Este script agrega ceros a la izquierda en las columnas d_codigo,
d_CP y c_oficina del CSV de zonas.

Uso:
    python scripts/fix_cp_padding.py
    python scripts/fix_cp_padding.py --dry-run
"""

import argparse
import csv
import os

# Columnas que contienen códigos postales y deben tener 5 dígitos
CP_COLUMNS = ["d_codigo", "d_CP", "c_oficina"]

DEFAULT_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "zonas_custerboots",
    "37000_cp_mx.csv",
)


def zpad(value: str, width: int = 5) -> str:
    """Zero-pad a numeric string to the given width.

    Args:
        value: The string value to pad.
        width: Target width (default 5 for Mexican postal codes).

    Returns:
        str: Zero-padded string, or original value if not numeric.
    """
    stripped = value.strip()
    if stripped and stripped.isdigit():
        return stripped.zfill(width)
    return value


def fix_csv_padding(csv_path: str, dry_run: bool = False) -> dict:
    """Apply zero-padding to postal code columns in a CSV file.

    Args:
        csv_path: Path to the CSV file.
        dry_run: If True, only report changes without writing.

    Returns:
        dict: Summary with keys 'total_rows', 'rows_changed',
              'changes_per_column'.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError("CSV no encontrado: %s" % csv_path)

    # Read all rows
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise ValueError("CSV sin encabezados: %s" % csv_path)

    # Verify which CP columns exist in this CSV
    cols_to_fix = [col for col in CP_COLUMNS if col in fieldnames]

    if not cols_to_fix:
        print("⚠️  Ninguna columna de CP encontrada en el CSV.")
        return {"total_rows": len(rows), "rows_changed": 0, "changes_per_column": {}}

    # Apply padding
    changes_per_column = {col: 0 for col in cols_to_fix}
    rows_changed = 0

    for row in rows:
        row_changed = False
        for col in cols_to_fix:
            original = row.get(col, "")
            padded = zpad(original)
            if padded != original:
                row[col] = padded
                changes_per_column[col] += 1
                row_changed = True
        if row_changed:
            rows_changed += 1

    summary = {
        "total_rows": len(rows),
        "rows_changed": rows_changed,
        "changes_per_column": changes_per_column,
    }

    if dry_run:
        return summary

    # Write back
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Corrige zero-padding de CPs en el CSV de zonas.",
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help="Ruta al CSV de zonas (default: zonas_custerboots/37000_cp_mx.csv).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo reportar cambios sin escribir.",
    )
    args = parser.parse_args()

    print("📋 Verificando zero-padding en: %s" % args.csv)
    if args.dry_run:
        print("   (modo dry-run — no se escribirán cambios)")

    summary = fix_csv_padding(args.csv, dry_run=args.dry_run)

    print()
    print("📊 Resumen:")
    print("   Total filas:     %d" % summary["total_rows"])
    print("   Filas corregidas: %d" % summary["rows_changed"])
    for col, count in summary["changes_per_column"].items():
        print("   %-15s %d valores corregidos" % (col + ":", count))

    if summary["rows_changed"] == 0:
        print("\n✅ Todos los CPs ya tienen 5 dígitos.")
    elif args.dry_run:
        print("\n⚠️  Ejecuta sin --dry-run para aplicar los cambios.")
    else:
        print("\n✅ CSV actualizado correctamente.")


if __name__ == "__main__":
    main()
