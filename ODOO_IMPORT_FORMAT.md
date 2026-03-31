# Formato CSV para Importar Métodos de Envío en Odoo 19

## Resumen

Este documento describe el formato CSV que Odoo 19 acepta para importar
registros de `delivery.carrier` (Métodos de envío) con reglas de precios
por peso y prefijos de código postal.

El CSV combina dos tipos de campos relacionales:

| Campo | Tipo Odoo | Formato en CSV |
|-------|-----------|----------------|
| Reglas de precios (`price_rule_ids`) | One2many | Subcampos expandidos, **una regla por fila** |
| Prefijos de C.P. (`zip_prefix_ids`) | Many2many | Todos los valores **separados por coma en una sola celda** |

---

## Columnas del CSV

El CSV tiene **12 columnas**:

| # | Columna | Descripción | Ejemplo |
|---|---------|-------------|---------|
| 1 | `Secuencia` | Orden de visualización | `10` |
| 2 | `Método de entrega` | Nombre del carrier | `Envío a domicilio - Zona A` |
| 3 | `Proveedor` | Tipo de cálculo de precio | `Por reglas` |
| 4 | `Está publicado` | Visible en tienda web | `True` |
| 5 | `Producto de envío` | Producto de servicio asociado | `Envío a domicilio - Zona A` |
| 6 | `Reglas de precios/Variable` | Variable de la regla | `weight` |
| 7 | `Reglas de precios/Operador` | Operador de comparación | `<=` |
| 8 | `Reglas de precios/Valor máximo` | Umbral de la regla | `20.00` |
| 9 | `Reglas de precios/Precio de venta base` | Precio fijo del tier | `137.88` |
| 10 | `Reglas de precios/Precio de venta` | Precio variable (0 para fijo) | `0.00` |
| 11 | `Reglas de precios/Factor variable` | Factor para precio variable | `weight` |
| 12 | `Prefijos de C.P.` | CPs separados por coma | `01000,01010,01020,...` |

---

## Estructura por Zona

Cada zona (carrier) ocupa **12 filas** en el CSV:

- **Fila 1**: Datos del carrier + primera regla de precio + **todos los CPs**
- **Filas 2–12**: Solo la regla de precio (las demás columnas vacías)

### Ejemplo: Zona A con precio base $137.88 MXN

```csv
"Secuencia","Método de entrega","Proveedor","Está publicado","Producto de envío","Reglas de precios/Variable","Reglas de precios/Operador","Reglas de precios/Valor máximo","Reglas de precios/Precio de venta base","Reglas de precios/Precio de venta","Reglas de precios/Factor variable","Prefijos de C.P."
"10","Envío a domicilio - Zona A","Por reglas","True","Envío a domicilio - Zona A","weight","<=","20.00","137.88","0.00","weight","01000,01010,01020,01030,..."
"","","","","","weight","<=","40.00","275.76","0.00","weight",""
"","","","","","weight","<=","60.00","413.64","0.00","weight",""
"","","","","","weight","<=","80.00","551.52","0.00","weight",""
"","","","","","weight","<=","100.00","689.40","0.00","weight",""
"","","","","","weight","<=","120.00","827.28","0.00","weight",""
"","","","","","weight","<=","140.00","965.16","0.00","weight",""
"","","","","","weight","<=","160.00","1103.04","0.00","weight",""
"","","","","","weight","<=","180.00","1240.92","0.00","weight",""
"","","","","","weight","<=","200.00","1378.80","0.00","weight",""
"","","","","","weight","<=","220.00","1516.68","0.00","weight",""
"","","","","","weight","<=","980.00","6756.12","0.00","weight",""
```

> **Nota**: Los CPs (`01000,01010,01020,...`) van **todos en una sola celda**
> separados por coma, **solo en la primera fila** de cada zona.
> Las filas 2–12 dejan esa columna vacía.

---

## Reglas de Precios

Las reglas siguen un esquema de **tiers lineales por peso**:

| Tier | Peso máximo (kg) | Precio | Fórmula |
|------|-------------------|--------|---------|
| 1 | 20.00 | $137.88 | base × 1 |
| 2 | 40.00 | $275.76 | base × 2 |
| 3 | 60.00 | $413.64 | base × 3 |
| ... | ... | ... | ... |
| 11 | 220.00 | $1,516.68 | base × 11 |
| 12 (bulk) | 980.00 | $6,756.12 | base × 49 |

Cada regla se descompone en subcampos:

| Subcampo | Valor | Significado |
|----------|-------|-------------|
| `Variable` | `weight` | Evaluar por peso |
| `Operador` | `<=` | Si el peso es menor o igual a... |
| `Valor máximo` | `20.00` | ...este umbral en kg |
| `Precio de venta base` | `137.88` | Cobrar este precio fijo |
| `Precio de venta` | `0.00` | Sin componente variable |
| `Factor variable` | `weight` | (no aplica cuando precio de venta = 0) |

---

## Prefijos de C.P.

Los códigos postales mexicanos tienen **exactamente 5 dígitos** con ceros
a la izquierda cuando es necesario:

| ❌ Incorrecto | ✅ Correcto |
|---------------|-------------|
| `1000` | `01000` |
| `7239` | `07239` |
| `44100` | `44100` |

En el CSV, todos los CPs de una zona van **separados por coma en una sola
celda**, sin espacios:

```
"01000,01010,01020,01030,01040,01049,01050,..."
```

> **Importante**: Si los CPs se ponen uno por fila, Odoo lanza el error:
> *"Para importar varios valores, sepárelos con una coma."*

---

## Cómo Importar en Odoo

1. Ve a **Inventario → Configuración → Métodos de envío**
2. Haz clic en **⚙️ → Importar registros**
3. Sube el archivo CSV
4. Verifica que Odoo mapee correctamente las 12 columnas
5. **Activa "Crear nuevos registros"** — esto es obligatorio para que Odoo
   cree automáticamente:
   - Los productos de envío (`product.product`)
   - Los prefijos de CP (`delivery.zip.prefix`)
   - Las reglas de precio (`delivery.price.rule`)
6. Haz clic en **Probar** para validar
7. Si no hay errores, haz clic en **Importar**

### Errores comunes y solución

| Error | Causa | Solución |
|-------|-------|----------|
| *"Para importar varios valores, sepárelos con una coma"* | CPs en filas separadas en vez de una celda | Poner todos los CPs separados por coma en la celda de la primera fila |
| *"No se encontraron registros que coincidan..."* en Prefijos de C.P. | No está activado "Crear nuevos registros" | Activar la opción en el importador |
| *"Field has no SQL representation"* en Reglas de precios | Usando el formato display (`if weight <= 20.00 then...`) en vez de subcampos | Usar columnas expandidas: `Reglas de precios/Variable`, `/Operador`, etc. |
| *"Falta el valor requerido para 'Producto de envío'"* | Falta la columna `Producto de envío` | Agregar la columna con el nombre del producto de servicio |

---

## Generar el CSV Automáticamente

El proyecto incluye un exportador que genera este CSV a partir de una
cotización de EnviaTodo:

```bash
# 1. Cotizar (genera output/cotizacion_YYYYMMDD_HHMMSS.csv)
python -m src

# 2. Exportar para Odoo (genera output/odoo/..._delivery_carrier.csv)
python -m src --odoo-export --input cotizacion_YYYYMMDD_HHMMSS.csv
```

El archivo generado en `output/odoo/` está listo para importar directamente
en Odoo sin modificaciones.

---

## Referencia: Estructura Completa del CSV

Para 3 zonas (A, B, C), el CSV tiene:

```
1 fila de encabezado
+ 12 filas × 3 zonas
= 37 filas totales
```

```
Fila  1:  Encabezado (12 columnas)
Fila  2:  Zona A — carrier + regla 1 + CPs
Fila  3:  Zona A — regla 2
...
Fila 13:  Zona A — regla 12
Fila 14:  Zona B — carrier + regla 1 + CPs
Fila 15:  Zona B — regla 2
...
Fila 25:  Zona B — regla 12
Fila 26:  Zona C — carrier + regla 1 + CPs
Fila 27:  Zona C — regla 2
...
Fila 37:  Zona C — regla 12
```
