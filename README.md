# Cotizador por Zonas — Custer Boots × EnviaTodo

Cotiza envíos desde un CP de origen hacia el código postal más lejano de cada zona (A, B, C) usando la API de EnviaTodo.

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

## Uso

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

## Salida

Los archivos CSV se generan en la carpeta `output/` con el nombre:

```
output/cotizacion_YYYYMMDD_HHMMSS.csv
```

Cada CSV contiene:

- **Encabezado:** fecha, fuente, datos del paquete (CP origen, dimensiones, peso)
- **Tabla de cotizaciones:** una fila por combinación zona × paquetería × servicio

### Columnas del CSV

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

1. **Análisis de zonas** — Lee `zonas_custerboots/37000_cp_mx.csv` y encuentra el CP con mayor distancia al origen por cada zona (A, B, C)
2. **Descubrimiento de servicios** — Consulta `Api/provider_services` para obtener las paqueterías y servicios habilitados en la cuenta
3. **Consulta de CPs** — Obtiene datos geográficos de cada CP vía `Api/get_zip_code`
4. **Cotización** — Llama a `Api/rates_client` con `provider_service_id` específico por cada combinación zona × servicio
5. **Generación CSV** — Escribe los resultados en `output/cotizacion_YYYYMMDD_HHMMSS.csv`

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
├── .venv/                 # Entorno virtual (python3 -m venv .venv)
├── .env.local             # Token de la API (no commitear)
├── run.sh                 # Wrapper — activa .venv y ejecuta
├── src/
│   ├── __init__.py        # Paquete
│   ├── __main__.py        # CLI entry point
│   ├── api.py             # Cliente API EnviaTodo v2
│   ├── config.py          # Constantes y configuración
│   ├── csv_writer.py      # Generación de CSV
│   └── zonas.py           # Análisis de zonas (CP más lejano)
├── output/                # CSVs generados
├── zonas_custerboots/     # Datos de zonas y CPs
├── docs_enviatodo/        # Documentación de la API
└── README.md
```
