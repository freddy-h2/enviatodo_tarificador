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
# Tests para el CSV fuente (37000_cp_mx.csv)
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONAS_CSV = os.path.join(PROJECT_ROOT, "zonas_custerboots", "37000_cp_mx.csv")
ODOO_TEMPLATE = os.path.join(
    PROJECT_ROOT, "zonas_custerboots", "37000_odoo_delivery_carrier.csv"
)


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
# Tests para la plantilla Odoo (37000_odoo_delivery_carrier.csv)
# ---------------------------------------------------------------------------


def _extract_cps_from_odoo_csv(csv_path: str) -> list:
    """Extract all individual CPs from an Odoo delivery carrier CSV.

    In the compact format, CPs are comma-separated in a single cell
    per zone (column "Prefijos de C.P.").

    Returns:
        list[str]: All individual CP strings found.
    """
    all_cps = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cell = row.get("Prefijos de C.P.", "").strip()
            if cell:
                for cp in cell.split(","):
                    cp = cp.strip()
                    if cp:
                        all_cps.append(cp)
    return all_cps


class TestOdooTemplatePadding:
    """Verifica que la plantilla Odoo tiene CPs con zero-padding correcto."""

    def test_odoo_template_cps_have_5_digits(self):
        """Todos los CPs en 'Prefijos de C.P.' tienen exactamente 5 dígitos."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        all_cps = _extract_cps_from_odoo_csv(ODOO_TEMPLATE)
        assert len(all_cps) > 0, "No se encontraron CPs en la plantilla Odoo"

        short_cps = [cp for cp in all_cps if cp.isdigit() and len(cp) != 5]
        assert not short_cps, (
            "CPs con menos de 5 dígitos en plantilla Odoo (%d encontrados): %s"
            % (len(short_cps), short_cps[:10])
        )

    def test_odoo_template_cps_are_comma_separated(self):
        """Los CPs están en formato compacto (separados por coma en una celda)."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        with open(ODOO_TEMPLATE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            zones_with_cps = 0
            for row in reader:
                cell = row.get("Prefijos de C.P.", "").strip()
                if cell and "," in cell:
                    zones_with_cps += 1

        assert zones_with_cps == 3, (
            "Se esperaban 3 zonas con CPs separados por coma, encontradas: %d"
            % zones_with_cps
        )

    def test_odoo_template_has_compact_format(self):
        """La plantilla tiene formato compacto (< 50 filas, no miles)."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        with open(ODOO_TEMPLATE, newline="", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f)

        # 1 header + 3 zonas × (1 header + 11 reglas) = 37 filas
        assert total_rows <= 50, (
            "Plantilla tiene %d filas — debería ser formato compacto (< 50)"
            % total_rows
        )


# ---------------------------------------------------------------------------
# Tests para zonas.py — _format_cp via zfill
# ---------------------------------------------------------------------------


class TestZonasPadding:
    """Verifica que zonas.py aplica zero-padding al leer CPs."""

    def test_zonas_pads_short_cps(self):
        """zonas.py debe aplicar zfill(5) a CPs cortos del CSV."""
        # Crear un CSV temporal con CPs cortos
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
            # CP corto: 1000 → debe convertirse a 01000
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
            # CP largo: 44100 → debe quedarse como 44100
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
            # CP muy corto: 100 → debe convertirse a 00100
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

            # Verify zero-padding
            assert result["Zona A"]["cp"] == "01000", (
                "Expected '01000', got '%s'" % result["Zona A"]["cp"]
            )
            assert result["Zona B"]["cp"] == "44100", (
                "Expected '44100', got '%s'" % result["Zona B"]["cp"]
            )
            assert result["Zona C"]["cp"] == "00100", (
                "Expected '00100', got '%s'" % result["Zona C"]["cp"]
            )
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
            assert cp.isdigit(), "%s: CP '%s' no es numérico" % (zona_key, cp)


# ---------------------------------------------------------------------------
# Tests para csv_writer.py — _format_cp
# ---------------------------------------------------------------------------


class TestCsvWriterPadding:
    """Verifica que csv_writer.py aplica zero-padding."""

    def test_format_cp_pads_short_int(self):
        """_format_cp convierte enteros cortos a strings de 5 dígitos."""
        from src.csv_writer import _format_cp

        assert _format_cp(1000) == "01000"
        assert _format_cp(7239) == "07239"
        assert _format_cp(100) == "00100"
        assert _format_cp(1) == "00001"

    def test_format_cp_preserves_5_digit_int(self):
        """_format_cp no altera enteros de 5 dígitos."""
        from src.csv_writer import _format_cp

        assert _format_cp(44100) == "44100"
        assert _format_cp(37000) == "37000"
        assert _format_cp(99999) == "99999"

    def test_format_cp_pads_short_string(self):
        """_format_cp convierte strings cortos a 5 dígitos."""
        from src.csv_writer import _format_cp

        assert _format_cp("1000") == "01000"
        assert _format_cp("7239") == "07239"
        assert _format_cp("100") == "00100"

    def test_format_cp_preserves_5_digit_string(self):
        """_format_cp no altera strings de 5 dígitos."""
        from src.csv_writer import _format_cp

        assert _format_cp("44100") == "44100"
        assert _format_cp("01000") == "01000"
        assert _format_cp("07239") == "07239"

    def test_format_cp_handles_whitespace(self):
        """_format_cp maneja strings con espacios."""
        from src.csv_writer import _format_cp

        assert _format_cp(" 1000 ") == "01000"
        assert _format_cp(" 44100 ") == "44100"


# ---------------------------------------------------------------------------
# Tests para fix_cp_padding.py — zpad
# ---------------------------------------------------------------------------


class TestFixCpPaddingScript:
    """Verifica que el script fix_cp_padding.py funciona correctamente."""

    def test_zpad_pads_short_values(self):
        """zpad agrega ceros a la izquierda."""
        from scripts.fix_cp_padding import zpad

        assert zpad("1000") == "01000"
        assert zpad("7239") == "07239"
        assert zpad("100") == "00100"
        assert zpad("1") == "00001"

    def test_zpad_preserves_5_digit_values(self):
        """zpad no altera valores de 5 dígitos."""
        from scripts.fix_cp_padding import zpad

        assert zpad("44100") == "44100"
        assert zpad("01000") == "01000"
        assert zpad("99999") == "99999"

    def test_zpad_preserves_non_numeric(self):
        """zpad no altera valores no numéricos."""
        from scripts.fix_cp_padding import zpad

        assert zpad("") == ""
        assert zpad("abc") == "abc"
        assert zpad("—") == "—"

    def test_fix_csv_padding_corrects_short_cps(self):
        """fix_csv_padding corrige CPs cortos en un CSV temporal."""
        from scripts.fix_cp_padding import fix_csv_padding

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["d_codigo", "d_asenta", "d_CP", "c_oficina"])
            writer.writerow(["1000", "San Ángel", "1001", "1001"])
            writer.writerow(["44100", "Centro", "44101", "44101"])
            writer.writerow(["7239", "Test", "7240", "7240"])
            tmp_path = f.name

        try:
            summary = fix_csv_padding(tmp_path)

            assert summary["rows_changed"] == 2
            assert summary["changes_per_column"]["d_codigo"] == 2
            assert summary["changes_per_column"]["d_CP"] == 2
            assert summary["changes_per_column"]["c_oficina"] == 2

            # Verify the file was actually corrected
            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert rows[0]["d_codigo"] == "01000"
            assert rows[0]["d_CP"] == "01001"
            assert rows[0]["c_oficina"] == "01001"
            assert rows[1]["d_codigo"] == "44100"
            assert rows[2]["d_codigo"] == "07239"
        finally:
            os.unlink(tmp_path)

    def test_fix_csv_padding_dry_run_does_not_modify(self):
        """fix_csv_padding en dry-run no modifica el archivo."""
        from scripts.fix_cp_padding import fix_csv_padding

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["d_codigo", "d_asenta"])
            writer.writerow(["1000", "San Ángel"])
            tmp_path = f.name

        try:
            summary = fix_csv_padding(tmp_path, dry_run=True)
            assert summary["rows_changed"] == 1

            # File should NOT be modified
            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert rows[0]["d_codigo"] == "1000"  # Still unpadded
        finally:
            os.unlink(tmp_path)

    def test_fix_csv_padding_idempotent(self):
        """Ejecutar fix_csv_padding dos veces no cambia nada la segunda vez."""
        from scripts.fix_cp_padding import fix_csv_padding

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["d_codigo", "d_asenta"])
            writer.writerow(["1000", "San Ángel"])
            tmp_path = f.name

        try:
            # First run
            fix_csv_padding(tmp_path)
            # Second run
            summary = fix_csv_padding(tmp_path)
            assert summary["rows_changed"] == 0
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Tests para odoo_exporter.py — CPs en la salida
# ---------------------------------------------------------------------------


class TestOdooExporterPadding:
    """Verifica que el exportador Odoo produce CPs con zero-padding correcto."""

    def test_odoo_export_preserves_padded_cps(self):
        """Los CPs de la plantilla Odoo se copian con padding intacto."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 137.88, "carrier": "Test", "servicio": "Test"},
            "Zona B": {"precio_base": 150.00, "carrier": "Test", "servicio": "Test"},
            "Zona C": {"precio_base": 200.00, "carrier": "Test", "servicio": "Test"},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            # Extract all CPs from the output (compact format)
            all_cps = _extract_cps_from_odoo_csv(tmp_path)
            assert len(all_cps) > 0, "No se encontraron CPs en la exportación"

            short_cps = [cp for cp in all_cps if cp.isdigit() and len(cp) != 5]
            assert not short_cps, (
                "CPs con menos de 5 dígitos en exportación Odoo (%d): %s"
                % (len(short_cps), short_cps[:10])
            )
        finally:
            os.unlink(tmp_path)

    def test_odoo_export_compact_format(self):
        """La exportación Odoo usa formato compacto (CPs separados por coma)."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 137.88, "carrier": "Test", "servicio": "Test"},
            "Zona B": {"precio_base": 150.00, "carrier": "Test", "servicio": "Test"},
            "Zona C": {"precio_base": 200.00, "carrier": "Test", "servicio": "Test"},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                total_rows = sum(1 for _ in f)

            assert total_rows <= 50, (
                "Exportación tiene %d filas — debería ser formato compacto (< 50)"
                % total_rows
            )
        finally:
            os.unlink(tmp_path)

    def test_odoo_export_updates_prices(self):
        """La exportación Odoo actualiza las reglas de precios correctamente."""
        if not os.path.exists(ODOO_TEMPLATE):
            pytest.skip("Plantilla Odoo no encontrada: %s" % ODOO_TEMPLATE)

        from src.odoo_exporter import generar_odoo_csv

        precios = {
            "Zona A": {"precio_base": 100.00, "carrier": "Test", "servicio": "Test"},
            "Zona B": {"precio_base": 200.00, "carrier": "Test", "servicio": "Test"},
            "Zona C": {"precio_base": 300.00, "carrier": "Test", "servicio": "Test"},
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            tmp_path = f.name

        try:
            generar_odoo_csv(precios, ODOO_TEMPLATE, tmp_path)

            with open(tmp_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                rows = list(reader)

            # Zona A first rule should have price 100.00
            zona_a_row = rows[0]
            assert "100,00" in zona_a_row[5], (
                "Zona A primera regla debería contener 100,00: %s" % zona_a_row[5]
            )

            # Zona B first rule (row 12) should have price 200.00
            zona_b_row = rows[12]
            assert "200,00" in zona_b_row[5], (
                "Zona B primera regla debería contener 200,00: %s" % zona_b_row[5]
            )
        finally:
            os.unlink(tmp_path)
