# Zero-Padding de Códigos Postales para Odoo

## Contexto del problema

Los códigos postales mexicanos son de **5 dígitos** (e.g. `01000`, `06600`, `07239`).
Sin embargo, en el catálogo SEPOMEX (`input/cp_mx.csv`) la columna `d_codigo` se
almacena como entero, por lo que pandas la lee como `int64`. Esto provoca que CPs
como `01000` se representen internamente como `1000`, perdiendo el cero inicial.

Hay **685 CPs únicos** con menos de 5 dígitos numéricos (rango `01000`–`09999`).

### ¿Por qué importa?

Odoo v19 interpreta los prefijos de C.P. como **cadenas de texto**. Si se importa
`7239` en lugar de `07239`, Odoo puede:

1. **Hacer match incorrecto**: `7239` coincidiría con CPs que empiezan con `7239x`
   (e.g. `72390`, `72391`, …) en vez de con el CP `07239`.
2. **No hacer match**: El CP real `07239` nunca coincidiría con el prefijo `7239`.

La regla es simple: **todo CP en la exportación Odoo debe tener exactamente 5 dígitos,
con ceros a la izquierda cuando sea necesario**.

---

## Estado actual del código (verificado)

### ✅ Exportador Odoo — YA FUNCIONA CORRECTAMENTE

El archivo `src/io/odoo_exporter.py` ya implementa el zero-padding:

```python
# src/io/odoo_exporter.py, línea 66-74
def _format_cp(cp: int) -> str:
    """Zero-pad a postal code to 5 digits."""
    return str(cp).zfill(5)
```

Esta función se invoca en `_build_zone_rows()` (línea 101):

```python
sorted_cps = [_format_cp(cp) for cp in sorted(cps)]
```

Y los CPs pasan por `.astype(int)` antes de llegar ahí (línea 156 de
`export_odoo_delivery_carrier()`), así que el flujo es:

```
CSV (int) → pandas int64 → _format_cp() → str con zfill(5) → CSV Odoo
```

**Resultado**: `7239` → `"07239"`, `1000` → `"01000"`, `44100` → `"44100"`. ✅

### ⚠️ CSV clasificado intermedio — SIN PADDING

El archivo `src/io/writer.py` escribe el CSV clasificado con `df.to_csv()` sin
transformar `d_codigo`, por lo que los CPs cortos se escriben sin cero:

```
d_codigo,Zona,Distancia_km,...
1000,Zona A,5.2,...        ← debería ser 01000
7239,Zona A,12.1,...       ← debería ser 07239
44100,Zona B,450.3,...     ← OK (ya tiene 5 dígitos)
```

Esto **no afecta** la exportación Odoo (porque `_format_cp` re-agrega los ceros),
pero sí puede causar confusión si alguien abre el CSV intermedio y lo importa
manualmente a Odoo sin pasar por el exportador.

### ⚠️ Reader — Lee como int

El archivo `src/io/reader.py` lee `d_codigo` como `int64` (comportamiento por
defecto de pandas). Esto es correcto para cálculos, pero pierde el cero inicial.

---

## Qué implementar en futuras sesiones

### Tarea 1: Asegurar padding en el CSV clasificado (`writer.py`)

**Archivo**: `src/io/writer.py` (modificar)

**Qué hacer**: Antes de escribir el CSV, convertir `d_codigo` a string con
zero-padding de 5 dígitos para que el archivo intermedio también sea correcto.

```python
# En write_classified(), antes de df.to_csv():
df = df.copy()
df["d_codigo"] = df["d_codigo"].astype(str).str.zfill(5)
```

**Criterio de aceptación**:
- Todos los valores de `d_codigo` en el CSV de salida tienen exactamente 5 caracteres.
- CPs como `1000` se escriben como `01000`.
- No se altera el DataFrame original (usar `.copy()`).

### Tarea 2: Leer `d_codigo` como string en `reader.py`

**Archivo**: `src/io/reader.py` (modificar)

**Qué hacer**: Forzar que `d_codigo` se lea como string y aplicar zero-padding
inmediatamente, para que todo el pipeline trabaje con strings de 5 dígitos.

```python
df = pd.read_csv(filepath, encoding="utf-8", dtype={"d_codigo": str})
df["d_codigo"] = df["d_codigo"].str.zfill(5)
```

**Impacto**: Esto cambia el tipo de `d_codigo` de `int64` a `object` (string) en
todo el pipeline. Hay que verificar que:
- `src/geo/geocoder.py` funcione con strings (pgeocode acepta strings).
- `src/classifier/zones.py` no dependa de que sea int.
- `src/io/odoo_exporter.py` — la línea `.astype(int)` seguiría funcionando, pero
  ya no sería necesaria. `_format_cp` debería aceptar `str | int`.
- Todos los tests se actualicen para usar strings en vez de ints para `d_codigo`.

**Nota**: Esta tarea es más invasiva. Evaluar si el beneficio justifica el cambio
en todo el pipeline, o si es suficiente con solo hacer padding en la escritura
(Tarea 1).

### Tarea 3: Agregar test explícito de zero-padding en Odoo export

**Archivo**: `tests/test_odoo_exporter.py` (modificar)

**Qué hacer**: Agregar un test que verifique explícitamente que CPs de 4 dígitos
o menos se exportan con exactamente 5 dígitos en el CSV de Odoo.

```python
def test_export_short_cps_are_zero_padded(tmp_path):
    """CPs with fewer than 5 digits are zero-padded in Odoo export."""
    df = pd.DataFrame({
        "d_codigo": [7239, 1000, 100],
        "Zona": ["Zona A", "Zona A", "Zona A"],
    })
    out = tmp_path / "odoo_export.csv"
    export_odoo_delivery_carrier(df, out)
    with out.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cp_values = {
            row["Prefijos de C.P."] for row in reader if row["Prefijos de C.P."]
        }
    assert "07239" in cp_values
    assert "01000" in cp_values
    assert "00100" in cp_values
    # Verify all CPs are exactly 5 digits
    for cp in cp_values:
        assert len(cp) == 5, f"CP {cp!r} no tiene 5 dígitos"
```

**Criterio de aceptación**: El test pasa y valida que ningún CP en la exportación
Odoo tenga menos de 5 dígitos.

---

## Prioridad recomendada

| Tarea | Prioridad | Riesgo si no se hace |
|-------|-----------|---------------------|
| Tarea 3 (test) | **Alta** | Sin test explícito, una regresión futura podría romper el padding silenciosamente |
| Tarea 1 (writer) | **Media** | El CSV intermedio tiene CPs sin padding, confuso pero no afecta Odoo si se usa el exportador |
| Tarea 2 (reader) | **Baja** | Cambio invasivo en todo el pipeline; el padding ya se aplica donde importa |

## Archivos relevantes

| Archivo | Rol | Estado actual |
|---------|-----|---------------|
| `src/io/odoo_exporter.py` | Exportación Odoo | ✅ Zero-padding correcto via `_format_cp()` |
| `src/io/writer.py` | CSV clasificado | ⚠️ Escribe `d_codigo` como int (sin padding) |
| `src/io/reader.py` | Lectura CSV entrada | ⚠️ Lee `d_codigo` como int64 |
| `src/odoo_export.py` | CLI standalone Odoo | ✅ Lee CSV y delega a `export_odoo_delivery_carrier()` |
| `tests/test_odoo_exporter.py` | Tests exportador | ⚠️ No tiene test explícito de zero-padding para CPs cortos |
