# -*- coding: utf-8 -*-
"""Tests de zero-padding para códigos postales mexicanos.

Verifica que todos los CPs en el pipeline se escriben con exactamente
5 dígitos, con ceros a la izquierda cuando sea necesario.
"""

import csv
import os
import sys
import tempfile

import pytest

# Increase CSV field size limit for compact format (25k+ CPs in one cell)
csv.field_size_limit(sys.maxsize)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONAS_CSV = os.path.join(PROJECT_ROOT, "zonas_custerboots", "37000_cp_mx.csv")
ODOO_TEMPLATE = os.path.join(
    PROJECT_ROOT, "zonas_custerboots", "37000_odoo_delivery_carrier.csv"
)

# Column index for CP in the Odoo import format
_COL_CP = 11  # "Prefijos de C.P."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_cps_from_odoo_csv(csv_path: str) -> list:
    """Extract all individual CPs from an Odoo CSV (compact or import format).

    Handles both:
    - Compact format: CPs comma-separated in one cell
    - Import format: CPs comma-separated in one cell on zone header row

    Returns:
        list[str]: All individual CP strings found.
    """
    all_cps = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            cell = row[_COL_CP].strip() if len(row) > _COL_CP else ""
            if not cell:
                # Try column 6 (compact template format)
                cell = row[6].strip() if len(row) > 6 else ""
            if cell:
                for cp in cell.split(","):
                    cp = cp.strip()
                    if cp:
                        all_cps.append(cp)
    return all_cps


# ---------------------------------------------------------------------------
# Tests para el CSV fuente (37000_cp_mx.csv)
# ---------------------------------------------------------------------------


class TestCSVFuentePadding:
    """Verifica que el CSV fuente tiene CPs con zero-padding correcto."""

    def test_d_codigo_has_5_digits(self):
        """Todos los d_codigo en el CSV fuente tienen exactamente 5 dígitos."""
        if not os.path.exists(ZONAS_CSV):
            pytest.skip("CSV fuente no encontrado: %s" % ZONAS_CSV)

        with open(ZONAS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            short_cps = []
            for i, row in enumerate(reader):
                cp = row.get("d_codigo", "").strip()
                if cp and cp.isdigit() and len(cp) != 5:
                    short_cps.append((i + 2, cp))
                    if len(short_cps) >= 10:
                        break

        assert not short_cps, (
            "CPs con menos de 5 dígitos en d_codigo (primeros %d): %s"
            % (len(short_cps), short_cps)
        )

    def test_d_CP_has_5_digits(self):
        """Todos los d_CP en el CSV fuente tienen exactamente 5 dígitos."""
        if not os.path.exists(ZONAS_CSV):
            pytest.skip("CSV fuente no encontrado: %s" % ZONAS_CSV)

        with open(ZONAS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            short_cps = []
            for i, row in enumerate(reader):
                cp = row.get("d_CP", "").strip()
                if cp and cp.isdigit() and len(cp) != 5:
                    short_cps.append((i + 2, cp))
                    if len(short_cps) >= 10:
                        break

        assert not short_cps, "CPs con menos de 5 dígitos en d_CP (primeros %d): %s" % (
            len(short_cps),
            short_cps,
        )

    def test_c_oficina_has_5_digits(self):
        """Todos los c_oficina en el CSV fuente tienen exactamente 5 dígitos."""
        if not os.path.exists(ZONAS_CSV):
            pytest.skip("CSV fuente no encontrado: %s" % ZONAS_CSV)

        with open(ZONAS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            short_cps = []
            for i, row in enumerate(reader):
                cp = row.get("c_oficina", "").strip()
                if cp and cp.isdigit() and len(cp) != 5:
                    short_cps.append((i + 2, cp))
                    if len(short_cps) >= 10:
                        break

        assert not short_cps, (
            "CPs con menos de 5 dígitos en c_oficina (primeros %d): %s"
            % (len(short_cps), short_cps)
        )


# ---------------------------------------------------------------------------
# Tests para la plantilla Odoo compacta (37000_odoo_delivery_carrier.csv)
# ---------------------------------------------------------------------------


class TestOdooTemplatePadding:
    """Verifica que la plantilla Odoo compacta tiene CPs con zero-padding."""

    def test_odoo_template_cps_have_5_digits(self):
        """Todos los CPs en la plantilla compacta tienen exactamente 5 dígitos."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        with open(ODOO_TEMPLATE, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            short_cps = []
            for row in reader:
                col6 = row[6].strip() if len(row) > 6 else ""
                if col6:
                    for cp in col6.split(","):
                        cp = cp.strip()
                        if cp and cp.isdigit() and len(cp) != 5:
                            short_cps.append(cp)
                            if len(short_cps) >= 10:
                                break

        assert not short_cps, (
            "CPs con menos de 5 dígitos en plantilla Odoo (%d): %s"
            % (len(short_cps), short_cps[:10])
        )

    def test_odoo_template_has_compact_format(self):
        """La plantilla tiene formato compacto (< 50 filas)."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        with open(ODOO_TEMPLATE, newline="", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f)

        assert total_rows <= 50, (
            "Plantilla tiene %d filas — debería ser formato compacto (< 50)"
            % total_rows
        )


# ---------------------------------------------------------------------------
# Tests para zonas.py
# ---------------------------------------------------------------------------


class TestZonasPadding:
    """Verifica que zonas.py aplica zero-padding al leer CPs."""

    def test_zonas_pads_short_cps(self):
        """zonas.py debe aplicar zfill(5) a CPs cortos del CSV."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "d_codigo",
                    "d_asenta",
                    "d_tipo_asenta",
                    "D_mnpio",
                    "d_estado",
                    "d_ciudad",
                    "d_CP",
                    "c_estado",
                    "c_oficina",
                    "c_CP",
                    "c_tipo_asenta",
                    "c_mnpio",
                    "id_asenta_cpcons",
                    "d_zona",
                    "c_cve_ciudad",
                    "Distancia_km",
                    "Zona",
                    "Metodo_Distancia",
                ]
            )
            writer.writerow(
                [
                    "1000",
                    "San Ángel",
                    "Colonia",
                    "Álvaro Obregón",
                    "Ciudad de México",
                    "Ciudad de México",
                    "1001",
                    "9",
                    "1001",
                    "",
                    "9",
                    "10",
                    "1",
                    "Urbano",
                    "1.0",
                    "320.0",
                    "Zona A",
                    "osrm",
                ]
            )
            writer.writerow(
                [
                    "44100",
                    "Centro",
                    "Colonia",
                    "Guadalajara",
                    "Jalisco",
                    "Guadalajara",
                    "44101",
                    "14",
                    "44101",
                    "",
                    "9",
                    "39",
                    "100",
                    "Urbano",
                    "1.0",
                    "450.0",
                    "Zona B",
                    "osrm",
                ]
            )
            writer.writerow(
                [
                    "100",
                    "Test",
                    "Colonia",
                    "Test",
                    "Test",
                    "Test",
                    "101",
                    "1",
                    "101",
                    "",
                    "9",
                    "1",
                    "1",
                    "Urbano",
                    "1.0",
                    "500.0",
                    "Zona C",
                    "osrm",
                ]
            )
            tmp_path = f.name

        try:
            from src.zonas import encontrar_cp_mas_lejano

            result = encontrar_cp_mas_lejano(tmp_path, "37000")
            assert result["Zona A"]["cp"] == "01000"
            assert result["Zona B"]["cp"] == "44100"
            assert result["Zona C"]["cp"] == "00100"
        finally:
            os.unlink(tmp_path)

    def test_zonas_all_cps_are_5_digits(self):
        """Todos los CPs devueltos por encontrar_cp_mas_lejano tienen 5 dígitos."""
        if not os.path.exists(ZONAS_CSV):
            pytest.skip("CSV fuente no encontrado: %s" % ZONAS_CSV)

        from src.zonas import encontrar_cp_mas_lejano

        result = encontrar_cp_mas_lejano(ZONAS_CSV, "37000")
        for zona_key, zona_data in result.items():
            cp = zona_data["cp"]
            assert len(cp) == 5, "%s: CP '%s' no tiene 5 dígitos" % (zona_key, cp)


# ---------------------------------------------------------------------------
# Tests para csv_writer.py — _format_cp
# ---------------------------------------------------------------------------


class TestCsvWriterPadding:
    """Verifica que csv_writer.py aplica zero-padding."""

    def test_format_cp_pads_short_int(self):
        from src.csv_writer import _format_cp

        assert _format_cp(1000) == "01000"
        assert _format_cp(7239) == "07239"
        assert _format_cp(100) == "00100"

    def test_format_cp_preserves_5_digit(self):
        from src.csv_writer import _format_cp

        assert _format_cp(44100) == "44100"
        assert _format_cp("01000") == "01000"

    def test_format_cp_handles_whitespace(self):
        from src.csv_writer import _format_cp

        assert _format_cp(" 1000 ") == "01000"


# ---------------------------------------------------------------------------
# Tests para fix_cp_padding.py
# ---------------------------------------------------------------------------


class TestFixCpPaddingScript:
    """Verifica que el script fix_cp_padding.py funciona correctamente."""

    def test_zpad_pads_short_values(self):
        from scripts.fix_cp_padding import zpad

        assert zpad("1000") == "01000"
        assert zpad("7239") == "07239"

    def test_zpad_preserves_5_digit_values(self):
        from scripts.fix_cp_padding import zpad

        assert zpad("44100") == "44100"
        assert zpad("01000") == "01000"

    def test_zpad_preserves_non_numeric(self):
        from scripts.fix_cp_padding import zpad

        assert zpad("") == ""
        assert zpad("abc") == "abc"

    def test_fix_csv_padding_corrects_short_cps(self):
        from scripts.fix_cp_padding import fix_csv_padding

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["d_codigo", "d_asenta", "d_CP", "c_oficina"])
            writer.writerow(["1000", "San Ángel", "1001", "1001"])
            writer.writerow(["44100", "Centro", "44101", "44101"])
            tmp_path = f.name

        try:
            summary = fix_csv_padding(tmp_path)
            assert summary["rows_changed"] == 1
            assert summary["changes_per_column"]["d_codigo"] == 1

            with open(tmp_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            assert rows[0]["d_codigo"] == "01000"
            assert rows[1]["d_codigo"] == "44100"
        finally:
            os.unlink(tmp_path)

    def test_fix_csv_padding_idempotent(self):
        from scripts.fix_cp_padding import fix_csv_padding

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["d_codigo", "d_asenta"])
            writer.writerow(["1000", "San Ángel"])
            tmp_path = f.name

        try:
            fix_csv_padding(tmp_path)
            summary = fix_csv_padding(tmp_path)
            assert summary["rows_changed"] == 0
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Tests para odoo_exporter.py — formato de importación
# ---------------------------------------------------------------------------


class TestOdooExporterImportFormat:
    """Verifica que el exportador genera CSV en formato de importación Odoo."""

    def test_export_has_correct_header(self):
        """El CSV tiene subcampos expandidos para reglas y campo directo para CPs."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada")

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 100.00},
            "Zona B": {"precio_base": 200.00},
            "Zona C": {"precio_base": 300.00},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)

            assert "Reglas de precios/Variable" in header
            assert "Reglas de precios/Operador" in header
            assert "Reglas de precios/Valor máximo" in header
            assert "Reglas de precios/Precio de venta base" in header
            assert "Prefijos de C.P." in header
            # Must NOT have /Nombre suffix
            assert "Prefijos de C.P./Nombre" not in header
        finally:
            os.unlink(tmp_path)

    def test_export_cps_comma_separated_in_first_row(self):
        """Los CPs van todos separados por coma en la primera fila de cada zona."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada")

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 100.00},
            "Zona B": {"precio_base": 200.00},
            "Zona C": {"precio_base": 300.00},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header

                zones_with_cps = 0
                for row in reader:
                    nombre = row[1].strip()
                    cp_cell = row[_COL_CP].strip() if len(row) > _COL_CP else ""

                    if "Zona" in nombre:
                        # Zone header row must have CPs
                        assert "," in cp_cell, (
                            "%s: CPs should be comma-separated, got: %s..."
                            % (nombre, cp_cell[:50])
                        )
                        zones_with_cps += 1
                    elif cp_cell:
                        # Non-header rows must NOT have CPs
                        pytest.fail("CP found in non-header row: %s" % cp_cell[:50])

            assert zones_with_cps == 3
        finally:
            os.unlink(tmp_path)

    def test_export_compact_output(self):
        """La exportación tiene formato compacto (< 50 filas)."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada")

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 100.00},
            "Zona B": {"precio_base": 200.00},
            "Zona C": {"precio_base": 300.00},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                total_rows = sum(1 for _ in f)

            # 1 header + 3 zones × 12 rules = 37 rows
            assert total_rows == 37, "Expected 37 rows, got %d" % total_rows
        finally:
            os.unlink(tmp_path)

    def test_export_has_12_rules_per_zone(self):
        """Cada zona tiene exactamente 12 reglas de precio."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada")

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 100.00},
            "Zona B": {"precio_base": 200.00},
            "Zona C": {"precio_base": 300.00},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header

                rules_per_zone = {}
                current_zone = None
                for row in reader:
                    nombre = row[1].strip()
                    variable = row[5].strip() if len(row) > 5 else ""

                    if "Zona" in nombre:
                        current_zone = nombre
                        rules_per_zone[current_zone] = 0

                    if current_zone and variable:
                        rules_per_zone[current_zone] += 1

            for zone, count in rules_per_zone.items():
                assert count == 12, "%s tiene %d reglas, esperadas 12" % (zone, count)
        finally:
            os.unlink(tmp_path)

    def test_export_cps_all_have_5_digits(self):
        """Todos los CPs en la exportación tienen exactamente 5 dígitos."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada")

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 137.88},
            "Zona B": {"precio_base": 150.00},
            "Zona C": {"precio_base": 200.00},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            all_cps = _extract_cps_from_odoo_csv(tmp_path)
            assert len(all_cps) > 0

            short_cps = [cp for cp in all_cps if cp.isdigit() and len(cp) != 5]
            assert not short_cps, "CPs sin 5 dígitos (%d): %s" % (
                len(short_cps),
                short_cps[:10],
            )
        finally:
            os.unlink(tmp_path)

    def test_export_prices_are_correct(self):
        """Los precios se calculan correctamente (base * n para tier n)."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada")

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 100.00},
            "Zona B": {"precio_base": 200.00},
            "Zona C": {"precio_base": 300.00},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                row1 = next(reader)  # Zona A, tier 1
                row2 = next(reader)  # Zona A, tier 2

            # Tier 1: weight <= 20, price = 100.00
            assert row1[7] == "20.00"
            assert row1[8] == "100.00"
            # Tier 2: weight <= 40, price = 200.00
            assert row2[7] == "40.00"
            assert row2[8] == "200.00"
        finally:
            os.unlink(tmp_path)
