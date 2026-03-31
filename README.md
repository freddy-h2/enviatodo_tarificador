# Cotizador por Zonas — Custer Boots × EnviaTodo

Cotiza envíos desde un CP de origen hacia el código postal más lejano de cada zona (A, B, C) usando la API de EnviaTodo, y genera plantillas de importación para Odoo.

## Requisitos

- Python 3.10+
- `requests`

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

## Configuración

El token de la API de EnviaTodo se lee de (en orden de prioridad):

1. Variable de entorno `ENVIATODO_TOKEN`
2. Archivo `.env.local` en la raíz del proyecto (cualquier línea que contenga `TOKEN` o `SANDBOX` en el nombre de la variable)

> **Nota:** El token solo es necesario para cotizar (`python -m src`). La exportación a Odoo (`--odoo-export`) trabaja offline sin token.

## Uso

### Cotizar envíos (requiere token)

```bash
# Activar el entorno virtual
source .venv/bin/activate

# Cotizar desde CP 37000 (León, GTO) — valor por defecto
python -m src

# Especificar CP de origen
python -m src 37000
python -m src --cp 37000

# O usar el wrapper (activa el venv automáticamente)
./run.sh 37000
```

### Exportar plantilla para Odoo (offline)

A partir de un CSV de cotización ya generado, produce una plantilla de delivery carrier lista para importar en Odoo con los precios actualizados:

```bash
# Generar plantilla Odoo a partir de una cotización existente
python -m src --odoo-export --input cotizacion_20260330_231047.csv
```

La salida se escribe en:

```
output/odoo/cotizacion_20260330_231047_delivery_carrier.csv
```

El archivo `--input` se busca en la carpeta `output/` por defecto. También acepta rutas absolutas.

#### ¿Qué hace?

1. Lee el CSV de cotización y encuentra el **servicio más barato** por zona (A, B, C)
2. Lee la plantilla base de Odoo (`zonas_custerboots/37000_odoo_delivery_carrier.csv`)
3. Recalcula las **12 reglas de precio por peso** de cada zona usando el precio más barato como base:
   - Tiers 1–11: `precio_base × n` para ≤20kg, ≤40kg, ..., ≤220kg
   - Tier 12 (bulk): `precio_base × 49` para ≤980kg
4. Genera el CSV de salida preservando todos los prefijos de CP y el formato de importación de Odoo

#### Ejemplo de salida

```
╔══════════════════════════════════════════════════════════╗
║  📦 EXPORTADOR ODOO — CUSTER BOOTS                     ║
╚══════════════════════════════════════════════════════════╝

📄 Leyendo cotización: output/cotizacion_20260330_231047.csv
   Zona A: $137.88 MXN (ESTAFETA Terrestre)
   Zona B: $137.88 MXN (ESTAFETA Terrestre)
   Zona C: $300.28 MXN (ESTAFETA Terrestre)

📝 Generando plantilla Odoo...
   ✅ output/odoo/cotizacion_20260330_231047_delivery_carrier.csv
```

#### Flujo de trabajo típico

```bash
# 1. Cotizar con la API (genera output/cotizacion_YYYYMMDD_HHMMSS.csv)
python -m src 37000

# 2. Revisar los precios en el CSV generado

# 3. Generar la plantilla de Odoo con esos precios
python -m src --odoo-export --input cotizacion_YYYYMMDD_HHMMSS.csv

# 4. Importar output/odoo/cotizacion_..._delivery_carrier.csv en Odoo
```

## Salida

### CSV de cotización

Los archivos CSV se generan en la carpeta `output/` con el nombre:

```
output/cotizacion_YYYYMMDD_HHMMSS.csv
```

Cada CSV contiene:

- **Encabezado:** fecha, fuente, datos del paquete (CP origen, dimensiones, peso)
- **Tabla de cotizaciones:** una fila por combinación zona × paquetería × servicio

#### Columnas del CSV

| Columna | Descripción |
|---|---|
| Zona | A, B o C |
| CP más lejano | Código postal con mayor distancia al origen dentro de la zona |
| Distancia (km) | Distancia por carretera desde el CP de origen |
| Ubicación | Colonia, municipio, estado del CP destino |
| Paquetería | DHL, ESTAFETA, SENDEX, etc. |
| Servicio | Nombre del servicio (Terrestre, Aéreo, Día Sig., etc.) |
| Vía | TERRESTRE o AEREO |
| Cargo guía | Costo base de la guía |
| Cargo zona extendida | Sobrecargo por zona remota |
| Subtotal (MXN) | Precio antes de IVA |
| IVA (MXN) | Impuesto |
| Total (MXN) | Precio final con IVA |
| Modo entrega | En domicilio, En sucursal, etc. |
| Entrega estimada | Fecha estimada de entrega |

### CSV de delivery carrier para Odoo

Los archivos se generan en `output/odoo/` con el nombre:

```
output/odoo/cotizacion_YYYYMMDD_HHMMSS_delivery_carrier.csv
```

El formato sigue la estructura de importación de Odoo para `delivery.carrier`:

| Columna | Descripción |
|---|---|
| Secuencia | Orden de prioridad del método de entrega |
| Método de entrega | Nombre (ej. "Envío a domicilio - Zona A") |
| Proveedor | Siempre "Por reglas" |
| Está publicado | Siempre "True" |
| Peso máximo | Siempre "0.0" |
| Reglas de precios | Regla de peso (ej. `if weight <= 20.00 then fixed price $ 137,88`) |
| Prefijos de C.P. | Códigos postales asignados a la zona |

Los precios usan formato Odoo: `$ 1.234,56` (punto = miles, coma = decimal).

## Datos del producto

Según la ficha técnica (`Ficha tecnica de producto.txt`):

| Parámetro | Valor |
|---|---|
| Largo | 44 cm |
| Ancho | 33 cm |
| Alto | 11 cm |
| Peso | 1.9 kg |
| Peso volumétrico | 3.19 kg |

## Cómo funciona

### Cotizador

1. **Análisis de zonas** — Lee `zonas_custerboots/37000_cp_mx.csv` y encuentra el CP con mayor distancia al origen por cada zona (A, B, C)
2. **Descubrimiento de servicios** — Consulta `Api/provider_services` para obtener las paqueterías y servicios habilitados en la cuenta
3. **Consulta de CPs** — Obtiene datos geográficos de cada CP vía `Api/get_zip_code`
4. **Cotización** — Llama a `Api/rates_client` con `provider_service_id` específico por cada combinación zona × servicio
5. **Generación CSV** — Escribe los resultados en `output/cotizacion_YYYYMMDD_HHMMSS.csv`

### Exportador Odoo

1. **Lectura de cotización** — Parsea el CSV de cotización y extrae el precio total más barato por zona
2. **Lectura de plantilla** — Lee la plantilla base con los ~32,000 prefijos de CP asignados por zona
3. **Recálculo de precios** — Genera 12 reglas de peso por zona usando el precio más barato como unidad base
4. **Generación CSV** — Escribe la plantilla actualizada preservando el formato exacto de importación de Odoo

### Rate limiting

La API de EnviaTodo permite **120 peticiones por segundo** con un máximo de **500 por sesión**. El cotizador respeta estos límites con:

- **1 segundo** de pausa mínima entre cada petición (`PAUSA_ENTRE_PETICIONES`)
- **2 segundos** de pausa entre zonas (`PAUSA_ENTRE_ZONAS`)
- **Reintentos con backoff progresivo** (3s, 6s) cuando la API responde OK pero sin tarifas — esto ocurre por throttling, no por falta de cobertura
- **Sin reintentos en timeout** — un timeout indica que el servicio no tiene cobertura para esa ruta

Los valores se pueden ajustar en `src/config.py`.

> **Nota:** La cotización se hace servicio por servicio (no todas las paqueterías a la vez) porque el endpoint `rates_client` sin `provider_service_id` causa timeouts.

## Estructura del proyecto

```
├── .venv/                      # Entorno virtual (python3 -m venv .venv)
├── .env.local                  # Token de la API (no commitear)
├── run.sh                      # Wrapper — activa .venv y ejecuta
├── src/
│   ├── __init__.py             # Paquete
│   ├── __main__.py             # CLI entry point (cotizador + exportador Odoo)
│   ├── api.py                  # Cliente API EnviaTodo v2
│   ├── config.py               # Constantes y configuración
│   ├── csv_writer.py           # Generación de CSV de cotización
│   ├── odoo_exporter.py        # Transformador de plantilla Odoo
│   ├── quotation_reader.py     # Parser de CSV de cotización
│   └── zonas.py                # Análisis de zonas (CP más lejano)
├── output/                     # CSVs de cotización generados
│   └── odoo/                   # Plantillas de Odoo generadas
├── zonas_custerboots/
│   ├── 37000_cp_mx.csv         # Datos de zonas y CPs con distancias
│   └── 37000_odoo_delivery_carrier.csv  # Plantilla base de Odoo
├── docs_enviatodo/             # Documentación de la API
└── README.md
```
