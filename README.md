# Cotizador por Zonas — Custer Boots × EnviaTodo

Cotiza envíos desde un CP de origen hacia el código postal más lejano de cada zona (A, B, C) usando la API de EnviaTodo.

## Requisitos

- Python 3.10+
- `requests`

```bash
pip install requests
```

## Configuración

El token de la API de EnviaTodo se lee de (en orden de prioridad):

1. Variable de entorno `ENVIATODO_TOKEN`
2. Archivo `.env.local` en la raíz del proyecto (cualquier línea que contenga `TOKEN` o `SANDBOX` en el nombre de la variable)

## Uso

```bash
# Cotizar desde CP 37000 (León, GTO) — valor por defecto
python -m src

# Especificar CP de origen como argumento posicional
python -m src 37000

# Especificar CP de origen con flag --cp
python -m src --cp 37000

# Usar un token diferente
ENVIATODO_TOKEN=tu_token python -m src --cp 37000
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
| Subtotal (MXN) | Precio antes de IVA |
| IVA (MXN) | Impuesto |
| Total (MXN) | Precio final con IVA |
| Cargo zona extendida | Sobrecargo por zona remota |
| Cargo guía | Costo base de la guía |
| Entrega estimada | Fecha estimada de entrega |
| Modo entrega | En domicilio, En sucursal, etc. |

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

> **Nota:** La cotización se hace servicio por servicio (no todas las paqueterías a la vez) porque el endpoint `rates_client` sin `provider_service_id` puede causar timeouts.

## Estructura del proyecto

```
├── src/
│   ├── __init__.py        # Paquete
│   ├── __main__.py        # CLI entry point
│   ├── api.py             # Cliente API EnviaTodo v2
│   ├── config.py          # Constantes y configuración
│   ├── csv_writer.py      # Generación de CSV
│   └── zonas.py           # Análisis de zonas (CP más lejano)
├── output/                # CSVs generados (gitignored excepto .gitkeep)
├── zonas_custerboots/     # Datos de zonas y CPs
├── docs_enviatodo/        # Documentación de la API
├── .env.local             # Token de la API (no commitear)
└── README.md
```
