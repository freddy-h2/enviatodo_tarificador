# Guía de Implementación: EnviaTodo en Odoo para Custer Boots

**Versión:** 1.0.0  
**Fecha:** Marzo 2026  
**Empresa:** Custer Boots — León, Guanajuato, CP 37000  
**API:** EnviaTodo.com — `https://apiqav2.enviatodo.mx/index.php/`  
**Odoo:** 19 Community / SaaS  

---

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [PARTE A — Implementación con Odoo Studio (SaaS)](#parte-a--implementación-con-odoo-studio-saas)
3. [PARTE B — Módulo Custom (Self-hosted / Odoo.sh)](#parte-b--módulo-custom-self-hosted--odoo-sh)
4. [PARTE C — Configuración de la API de EnviaTodo](#parte-c--configuración-de-la-api-de-enviatodo)
5. [PARTE D — Datos del Producto Custer Boots](#parte-d--datos-del-producto-custer-boots)
6. [PARTE E — Checklist de Implementación](#parte-e--checklist-de-implementación)

---

## Introducción

Esta guía describe cómo integrar la plataforma de envíos **EnviaTodo.com** con **Odoo 19** para automatizar la cotización, generación y seguimiento de guías de envío en **Custer Boots**.

### ¿Qué hace esta integración?

| Funcionalidad | Descripción |
|---|---|
| **Cotización automática** | Al confirmar una orden de venta, Odoo consulta la API de EnviaTodo para obtener el costo de envío en tiempo real |
| **Generación de guía** | Al validar una transferencia de salida, se genera automáticamente la guía de envío |
| **Etiqueta PDF** | La etiqueta de envío se adjunta al picking en Odoo |
| **Rastreo** | Enlace directo al portal de rastreo de EnviaTodo |
| **Cancelación** | Posibilidad de cancelar guías desde Odoo |

### Datos fijos de Custer Boots

```
Empresa:    Custer Boots
Ciudad:     León, Guanajuato
CP Origen:  37000
Caja:       44 cm × 11 cm × 33 cm
Peso:       1.9 kg
```

---

## PARTE A — Implementación con Odoo Studio (SaaS)

> **Importante:** Esta sección es para instalaciones de **Odoo SaaS** (Odoo Online) donde no es posible instalar módulos Python personalizados. Si tienes Odoo Self-hosted u Odoo.sh, ve directamente a la **Parte B**.

### A.1 Limitaciones de Odoo SaaS

Odoo SaaS (la versión en la nube de Odoo) **no permite**:
- Instalar módulos Python personalizados (`.py`)
- Acceder al sistema de archivos del servidor
- Instalar paquetes pip adicionales

Sin embargo, **sí permite**:
- Crear campos personalizados con **Odoo Studio**
- Ejecutar código Python en **Acciones Automatizadas** (con restricciones)
- Usar `requests` en acciones automatizadas (disponible en el entorno sandbox de Odoo)

> ⚠️ **Advertencia:** El módulo `requests` en acciones automatizadas de Odoo SaaS puede estar restringido o no disponible según la versión y el plan contratado. Si `requests` no funciona, la única opción es el módulo custom (Parte B) en Odoo.sh o Self-hosted.

---

### A.2 Crear Campos Personalizados con Odoo Studio

#### Paso 1: Activar Odoo Studio

1. En el menú principal de Odoo, haz clic en el ícono de **cuadrícula** (apps) en la esquina superior derecha
2. Busca y abre **Studio**
3. Si no aparece, ve a **Configuración → Aplicaciones** y activa Studio

#### Paso 2: Abrir el modelo de Transportistas

1. Ve a **Inventario → Configuración → Métodos de envío**
2. Abre cualquier transportista existente (o crea uno nuevo)
3. Haz clic en el ícono de **lápiz** de Studio (esquina superior derecha)

#### Paso 3: Crear los campos de EnviaTodo

En el panel de Studio, selecciona **Campos** y crea los siguientes:

| Nombre técnico | Etiqueta | Tipo | Valor predeterminado |
|---|---|---|---|
| `x_enviatodo_api_key` | API Key EnviaTodo | Texto | — |
| `x_enviatodo_user_id` | Usuario EnviaTodo | Texto | — |
| `x_enviatodo_service_type` | Tipo de servicio | Texto | `express` |
| `x_enviatodo_origin_zip` | CP de origen | Texto | `37000` |
| `x_enviatodo_api_base_url` | URL base API | Texto | `https://apiqav2.enviatodo.mx/index.php/` |
| `x_enviatodo_default_length` | Largo (cm) | Decimal | `44` |
| `x_enviatodo_default_width` | Ancho (cm) | Decimal | `11` |
| `x_enviatodo_default_height` | Alto (cm) | Decimal | `33` |
| `x_enviatodo_default_weight` | Peso (kg) | Decimal | `1.9` |

**Cómo crear cada campo:**
1. En el panel derecho de Studio, haz clic en **"+ Agregar campo"**
2. Selecciona el tipo (Texto o Decimal)
3. Escribe el nombre técnico exactamente como aparece en la tabla
4. Escribe la etiqueta
5. Establece el valor predeterminado
6. Haz clic en **Guardar**

#### Paso 4: Organizar los campos en la vista

1. En Studio, arrastra los campos nuevos a una nueva pestaña
2. Crea una pestaña llamada **"EnviaTodo"**
3. Organiza los campos en grupos:
   - **Credenciales:** API Key, Usuario
   - **Servicio:** Tipo de servicio, CP de origen, URL base
   - **Dimensiones:** Largo, Ancho, Alto, Peso
4. Haz clic en **Guardar** en Studio

---

### A.3 Crear Acción Automatizada: Cotización de Envío

Las Acciones Automatizadas permiten ejecutar código Python cuando ocurre un evento en Odoo.

#### Paso 1: Ir a Acciones Automatizadas

1. Ve a **Configuración → Técnico → Acciones Automatizadas**
   - Si no ves el menú Técnico, activa el **modo desarrollador**: `Configuración → Activar modo desarrollador`
2. Haz clic en **Nuevo**

#### Paso 2: Configurar la acción de cotización

Llena los campos:

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Cotizar envío` |
| **Modelo** | `Orden de venta (sale.order)` |
| **Cuando ejecutar** | `Basado en etapa` → Al confirmar la orden |
| **Acción** | `Ejecutar código Python` |

#### Paso 3: Código Python para cotización

En el campo **Código Python**, pega el siguiente código:

```python
import requests
import json
import logging

_logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN — Ajustar según tu transportista de EnviaTodo
# ============================================================
# Buscar el transportista de EnviaTodo por nombre
carrier = env['delivery.carrier'].search([
    ('name', 'ilike', 'EnviaTodo'),
    ('active', '=', True),
], limit=1)

if not carrier:
    log.warning("EnviaTodo: No se encontró transportista activo con nombre 'EnviaTodo'")
    return

# Leer credenciales desde los campos personalizados del transportista
API_KEY = carrier.x_enviatodo_api_key or ''
USER_ID = carrier.x_enviatodo_user_id or ''
BASE_URL = carrier.x_enviatodo_api_base_url or 'https://apiqav2.enviatodo.mx/index.php/'
SERVICE = carrier.x_enviatodo_service_type or 'express'
ORIGIN_ZIP = carrier.x_enviatodo_origin_zip or '37000'

if not API_KEY or not USER_ID:
    log.warning("EnviaTodo: Faltan credenciales en el transportista")
    return

# ============================================================
# OBTENER DATOS DE LA ORDEN
# ============================================================
for order in records:
    partner = order.partner_shipping_id or order.partner_id
    dest_zip = partner.zip or ''
    
    if not dest_zip or len(dest_zip.strip()) != 5:
        log.warning(
            "EnviaTodo: El cliente '%s' no tiene CP válido (5 dígitos). "
            "Orden: %s", partner.name, order.name
        )
        continue
    
    # ============================================================
    # CONSTRUIR PAYLOAD
    # ============================================================
    payload = {
        "api_key": API_KEY,
        "user_id": USER_ID,
        "origen": {"cp": ORIGIN_ZIP},
        "destino": {"cp": dest_zip.strip()},
        "paquete": {
            "largo": carrier.x_enviatodo_default_length or 44,
            "ancho": carrier.x_enviatodo_default_width or 11,
            "alto": carrier.x_enviatodo_default_height or 33,
            "peso": carrier.x_enviatodo_default_weight or 1.9,
        },
        "servicio": SERVICE,
    }
    
    log.info(
        "EnviaTodo: Cotizando envío para orden %s → CP %s",
        order.name, dest_zip
    )
    
    # ============================================================
    # LLAMAR A LA API
    # ============================================================
    try:
        url = BASE_URL.rstrip('/') + '/cotizar'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + API_KEY,
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        log.info(
            "EnviaTodo: Respuesta cotización [%s]: %s",
            response.status_code, response.text[:500]
        )
        
        if response.status_code == 200:
            data = response.json()
            price = (
                data.get('precio') or
                data.get('costo') or
                data.get('price') or
                data.get('total') or
                0.0
            )
            # Guardar el precio en una nota interna de la orden
            order.message_post(
                body="<b>EnviaTodo:</b> Cotización de envío: <b>$%.2f MXN</b> "
                     "(CP destino: %s)" % (float(price), dest_zip),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            log.info(
                "EnviaTodo: Cotización exitosa para %s — $%.2f MXN",
                order.name, float(price)
            )
        else:
            log.warning(
                "EnviaTodo: Error al cotizar para %s — HTTP %s: %s",
                order.name, response.status_code, response.text[:200]
            )
    except Exception as e:
        log.error("EnviaTodo: Excepción al cotizar para %s: %s", order.name, str(e))
```

---

### A.4 Crear Acción Automatizada: Generación de Guía

#### Paso 1: Crear nueva acción automatizada

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Generar guía de envío` |
| **Modelo** | `Transferencia (stock.picking)` |
| **Cuando ejecutar** | `Al escribir` → Campo: `state` → Valor: `done` |
| **Acción** | `Ejecutar código Python` |

> **Alternativa:** También puedes configurarlo como **"Basado en etapa"** cuando el estado cambia a `done`.

#### Paso 2: Código Python para generación de guía

```python
import requests
import json
import base64
import logging

_logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================
carrier_record = env['delivery.carrier'].search([
    ('name', 'ilike', 'EnviaTodo'),
    ('active', '=', True),
], limit=1)

if not carrier_record:
    log.warning("EnviaTodo: No se encontró transportista activo")
    return

API_KEY = carrier_record.x_enviatodo_api_key or ''
USER_ID = carrier_record.x_enviatodo_user_id or ''
BASE_URL = carrier_record.x_enviatodo_api_base_url or 'https://apiqav2.enviatodo.mx/index.php/'
SERVICE = carrier_record.x_enviatodo_service_type or 'express'
ORIGIN_ZIP = carrier_record.x_enviatodo_origin_zip or '37000'

if not API_KEY or not USER_ID:
    log.warning("EnviaTodo: Faltan credenciales")
    return

# ============================================================
# PROCESAR CADA TRANSFERENCIA
# ============================================================
for picking in records:
    # Solo procesar transferencias de salida (delivery orders)
    if picking.picking_type_code != 'outgoing':
        continue
    
    # Evitar generar guía si ya tiene número de rastreo
    if picking.carrier_tracking_ref:
        log.info(
            "EnviaTodo: El picking %s ya tiene guía: %s",
            picking.name, picking.carrier_tracking_ref
        )
        continue
    
    partner = picking.partner_id
    if not partner:
        log.warning("EnviaTodo: Picking %s sin destinatario", picking.name)
        continue
    
    dest_zip = (partner.zip or '').strip()
    if not dest_zip or len(dest_zip) != 5:
        log.warning(
            "EnviaTodo: Picking %s — cliente '%s' sin CP válido",
            picking.name, partner.name
        )
        continue
    
    # Calcular peso real si los productos tienen peso configurado
    weight = carrier_record.x_enviatodo_default_weight or 1.9
    try:
        total_weight = sum(
            (m.product_id.weight or 0.0) * m.product_qty
            for m in picking.move_ids
            if m.product_id
        )
        if total_weight > 0:
            weight = total_weight
    except Exception:
        pass
    
    # ============================================================
    # CONSTRUIR PAYLOAD
    # ============================================================
    street = ' '.join(filter(None, [partner.street, partner.street2])) or 'Sin dirección'
    
    payload = {
        "api_key": API_KEY,
        "user_id": USER_ID,
        "referencia": picking.name,
        "origen": {
            "cp": ORIGIN_ZIP,
            "nombre": "Custer Boots",
            "telefono": "",
            "calle": "León, Guanajuato",
            "ciudad": "León",
            "estado": "Guanajuato",
        },
        "destino": {
            "cp": dest_zip,
            "nombre": partner.name or 'Sin nombre',
            "telefono": partner.phone or partner.mobile or '',
            "email": partner.email or '',
            "calle": street,
            "ciudad": partner.city or '',
            "estado": partner.state_id.name if partner.state_id else '',
        },
        "paquete": {
            "largo": carrier_record.x_enviatodo_default_length or 44,
            "ancho": carrier_record.x_enviatodo_default_width or 11,
            "alto": carrier_record.x_enviatodo_default_height or 33,
            "peso": round(weight, 3),
            "descripcion": "Calzado / Botas",
            "valor_declarado": 0,
        },
        "servicio": SERVICE,
    }
    
    log.info(
        "EnviaTodo: Generando guía para picking %s → %s (CP %s)",
        picking.name, partner.name, dest_zip
    )
    
    # ============================================================
    # LLAMAR A LA API
    # ============================================================
    try:
        url = BASE_URL.rstrip('/') + '/generar'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + API_KEY,
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        log.info(
            "EnviaTodo: Respuesta generación [%s]: %s",
            response.status_code, response.text[:500]
        )
        
        if response.status_code in (200, 201):
            data = response.json()
            
            tracking = (
                data.get('tracking') or
                data.get('numero_guia') or
                data.get('guia') or
                data.get('tracking_number') or
                ''
            )
            
            if tracking:
                # Guardar número de rastreo en el picking
                picking.write({'carrier_tracking_ref': tracking})
                
                # Publicar nota interna
                picking.message_post(
                    body="<b>EnviaTodo:</b> Guía generada exitosamente.<br/>"
                         "<b>Número de rastreo:</b> %s<br/>"
                         "<b>Rastrear en:</b> "
                         "<a href='https://app.enviatodo.com/#Tracking?guia=%s' target='_blank'>"
                         "Ver rastreo</a>" % (tracking, tracking),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                
                log.info(
                    "EnviaTodo: Guía generada para %s — Tracking: %s",
                    picking.name, tracking
                )
                
                # Intentar adjuntar etiqueta PDF si la API la devuelve
                label_b64 = (
                    data.get('etiqueta_base64') or
                    data.get('label_base64') or
                    data.get('pdf_base64') or
                    data.get('etiqueta')
                )
                label_url = (
                    data.get('url_etiqueta') or
                    data.get('label_url') or
                    data.get('pdf_url')
                )
                
                if label_b64:
                    try:
                        env['ir.attachment'].create({
                            'name': 'Guia_EnviaTodo_%s.pdf' % tracking,
                            'type': 'binary',
                            'datas': label_b64 if isinstance(label_b64, str) else label_b64.decode(),
                            'res_model': 'stock.picking',
                            'res_id': picking.id,
                            'mimetype': 'application/pdf',
                        })
                        log.info("EnviaTodo: Etiqueta adjuntada al picking %s", picking.name)
                    except Exception as e:
                        log.warning("EnviaTodo: No se pudo adjuntar etiqueta: %s", e)
                
                elif label_url:
                    try:
                        r = requests.get(label_url, timeout=30)
                        if r.status_code == 200:
                            env['ir.attachment'].create({
                                'name': 'Guia_EnviaTodo_%s.pdf' % tracking,
                                'type': 'binary',
                                'datas': base64.b64encode(r.content).decode('utf-8'),
                                'res_model': 'stock.picking',
                                'res_id': picking.id,
                                'mimetype': 'application/pdf',
                            })
                            log.info("EnviaTodo: Etiqueta descargada y adjuntada para %s", picking.name)
                    except Exception as e:
                        log.warning("EnviaTodo: No se pudo descargar etiqueta desde URL: %s", e)
            else:
                log.warning(
                    "EnviaTodo: Guía generada pero sin número de rastreo. "
                    "Respuesta: %s", data
                )
        else:
            log.error(
                "EnviaTodo: Error al generar guía para %s — HTTP %s: %s",
                picking.name, response.status_code, response.text[:300]
            )
    except Exception as e:
        log.error(
            "EnviaTodo: Excepción al generar guía para %s: %s",
            picking.name, str(e)
        )
```

---

### A.5 Configurar el Enlace de Rastreo

Para mostrar el enlace de rastreo en los pickings:

1. Ve a **Studio** → abre un picking de salida
2. Agrega un campo de tipo **URL** llamado `x_enviatodo_tracking_url`
3. Crea una **Acción Automatizada** adicional:

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Actualizar URL de rastreo` |
| **Modelo** | `Transferencia (stock.picking)` |
| **Cuando ejecutar** | `Al escribir` → Campo: `carrier_tracking_ref` |
| **Acción** | `Actualizar el registro` |

En la acción de actualización:
- **Campo:** `x_enviatodo_tracking_url`
- **Valor:** `https://app.enviatodo.com/#Tracking?guia=` + `{{ object.carrier_tracking_ref }}`

---

### A.6 Limitaciones Conocidas de la Implementación con Studio

| Limitación | Impacto | Solución |
|---|---|---|
| `requests` puede no estar disponible | La cotización/generación falla silenciosamente | Usar módulo custom (Parte B) |
| No hay manejo de errores robusto | Los errores solo aparecen en logs | Revisar logs del servidor |
| No se puede agregar `delivery_type` como selección | El transportista no aparece en el selector de tipo | Usar módulo custom |
| Las acciones automatizadas tienen timeout corto | Peticiones lentas pueden fallar | Optimizar o usar módulo custom |
| No se puede validar CP en tiempo real | El usuario puede ingresar CPs inválidos | Agregar validación manual |

---

## PARTE B — Módulo Custom (Self-hosted / Odoo.sh)

> Esta es la implementación **recomendada** para Odoo Self-hosted y Odoo.sh. Ofrece integración completa, robusta y mantenible.

### B.1 Estructura del Módulo

```
delivery_enviatodo_custer/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── delivery_carrier.py
├── views/
│   └── delivery_carrier_views.xml
├── security/
│   └── ir.model.access.csv
└── static/
    └── description/
        └── icon.png
```

### B.2 Requisitos Previos

- Odoo 19 Community o Enterprise (Self-hosted o Odoo.sh)
- Python 3.12+
- Módulo `requests` instalado (incluido en Odoo por defecto)
- Módulos de Odoo: `delivery`, `stock`, `sale`

### B.3 Instalación del Módulo

#### Opción 1: Odoo Self-hosted

```bash
# 1. Copiar el módulo al directorio de addons
cp -r delivery_enviatodo_custer/ /opt/odoo/addons/

# 2. Reiniciar el servidor Odoo
sudo systemctl restart odoo

# 3. Actualizar la lista de módulos
# En Odoo: Configuración → Aplicaciones → Actualizar lista de aplicaciones

# 4. Buscar e instalar el módulo
# Buscar: "EnviaTodo"
# Hacer clic en "Instalar"
```

#### Opción 2: Odoo.sh

```bash
# 1. Agregar el módulo al repositorio del proyecto
git add delivery_enviatodo_custer/
git commit -m "feat: agregar módulo EnviaTodo para Custer Boots"
git push origin main

# Odoo.sh detectará automáticamente el nuevo módulo y lo instalará
# en el siguiente build
```

#### Opción 3: Actualizar módulo existente

```bash
# Si el módulo ya está instalado y se hicieron cambios:
./odoo-bin -u delivery_enviatodo_custer -d nombre_base_datos

# O desde la interfaz:
# Configuración → Aplicaciones → buscar "EnviaTodo" → Actualizar
```

### B.4 Descripción de los Archivos del Módulo

#### `__manifest__.py`
Define los metadatos del módulo: nombre, versión, dependencias y archivos de datos.

#### `models/delivery_carrier.py`
Contiene la clase principal con toda la lógica de integración:

| Método | Descripción |
|---|---|
| `_enviatodo_check_credentials()` | Valida que API Key y User ID estén configurados |
| `_enviatodo_request(endpoint, payload)` | Realiza peticiones HTTP a la API |
| `_enviatodo_validate_zip(zip, label)` | Valida formato de CP mexicano (5 dígitos) |
| `_enviatodo_get_origin_zip()` | Obtiene CP de origen del transportista |
| `_enviatodo_get_destination_zip(partner)` | Obtiene y valida CP del cliente |
| `_enviatodo_get_package_dimensions(record)` | Calcula dimensiones del paquete |
| `_enviatodo_build_rate_payload(order)` | Construye payload para cotización |
| `_enviatodo_build_shipment_payload(picking)` | Construye payload para generación |
| `_enviatodo_attach_label(picking, result, tracking)` | Adjunta etiqueta PDF al picking |
| `enviatodo_rate_shipment(order)` | **API Odoo:** Cotiza el envío |
| `enviatodo_send_shipping(pickings)` | **API Odoo:** Genera guías |
| `enviatodo_get_tracking_link(picking)` | **API Odoo:** Devuelve URL de rastreo |
| `enviatodo_cancel_shipment(pickings)` | **API Odoo:** Cancela guías |
| `action_enviatodo_test_connection()` | Prueba la conexión con la API |

#### `views/delivery_carrier_views.xml`
Vista XML que agrega una pestaña "EnviaTodo" al formulario del transportista con todos los campos de configuración.

#### `security/ir.model.access.csv`
Reglas de acceso: los usuarios normales pueden leer, los gerentes de almacén pueden crear/editar/eliminar.

### B.5 Configuración Post-instalación

1. Ve a **Inventario → Configuración → Métodos de envío**
2. Haz clic en **Nuevo**
3. Configura:
   - **Nombre:** `EnviaTodo Express` (o el nombre que prefieras)
   - **Proveedor:** `EnviaTodo`
   - **Empresa:** Custer Boots
4. Ve a la pestaña **EnviaTodo** y configura las credenciales
5. Haz clic en **Probar conexión** para verificar

### B.6 Convenciones de Código

El módulo sigue las convenciones de Odoo 19:

```python
# ✅ Correcto — Odoo 19
invisible="delivery_type != 'enviatodo'"

# ❌ Incorrecto — Odoo 16 y anteriores
attrs="{'invisible': [('delivery_type', '!=', 'enviatodo')]}"

# ✅ Correcto — selection_add
delivery_type = fields.Selection(
    selection_add=[("enviatodo", "EnviaTodo")],
    ondelete={"enviatodo": "set default"},
)

# ✅ Correcto — mensajes de error en español
raise UserError(_("EnviaTodo: Falta la API Key."))
```

---

## PARTE C — Configuración de la API de EnviaTodo

### C.1 Obtener Credenciales

Para obtener las credenciales de la API de EnviaTodo:

1. **Contactar a EnviaTodo:**
   - Email: soporte@enviatodo.com (o el contacto que te hayan asignado)
   - Solicitar: "Credenciales de API para integración con Odoo"
   - Proporcionar: nombre de empresa, RFC, volumen estimado de envíos

2. **Datos que te proporcionarán:**
   - `API Key` — clave de autenticación (larga cadena alfanumérica)
   - `User ID` — identificador numérico de tu cuenta
   - Documentación de endpoints disponibles para tu plan

3. **Acceder al portal:**
   - URL: `https://app.enviatodo.com`
   - La documentación de la API está en: `https://app.enviatodo.com/#Api` (requiere login)

### C.2 Estructura de Endpoints

> **Nota:** Los nombres de endpoints son estimados basados en la convención REST de EnviaTodo. Confirmar con el equipo técnico de EnviaTodo los nombres exactos.

#### Base URL
```
https://apiqav2.enviatodo.mx/index.php/
```

#### Autenticación
Todas las peticiones deben incluir en los headers:
```http
Authorization: Bearer {API_KEY}
Content-Type: application/json
X-User-Id: {USER_ID}
```

---

#### Endpoint: Cotizar envío

**Método:** `POST`  
**URL:** `https://apiqav2.enviatodo.mx/index.php/cotizar`

**Request:**
```json
{
  "api_key": "tu_api_key_aqui",
  "user_id": "tu_user_id",
  "origen": {
    "cp": "37000"
  },
  "destino": {
    "cp": "06600"
  },
  "paquete": {
    "largo": 44,
    "ancho": 11,
    "alto": 33,
    "peso": 1.9
  },
  "servicio": "express"
}
```

**Response esperada (éxito):**
```json
{
  "status": "success",
  "precio": 185.50,
  "moneda": "MXN",
  "tiempo_entrega": "2-3 días hábiles",
  "servicio": "express",
  "carrier": "FedEx"
}
```

**Response de error:**
```json
{
  "status": "error",
  "message": "CP de destino inválido",
  "code": "INVALID_ZIP"
}
```

---

#### Endpoint: Generar guía

**Método:** `POST`  
**URL:** `https://apiqav2.enviatodo.mx/index.php/generar`

**Request:**
```json
{
  "api_key": "tu_api_key_aqui",
  "user_id": "tu_user_id",
  "referencia": "WH/OUT/00123",
  "origen": {
    "cp": "37000",
    "nombre": "Custer Boots",
    "telefono": "477-000-0000",
    "calle": "Blvd. Torres Landa 1234",
    "ciudad": "León",
    "estado": "Guanajuato"
  },
  "destino": {
    "cp": "06600",
    "nombre": "Juan Pérez García",
    "telefono": "55-1234-5678",
    "email": "juan@ejemplo.com",
    "calle": "Av. Insurgentes Sur 456, Col. Roma Norte",
    "ciudad": "Ciudad de México",
    "estado": "Ciudad de México"
  },
  "paquete": {
    "largo": 44,
    "ancho": 11,
    "alto": 33,
    "peso": 1.9,
    "descripcion": "Calzado / Botas",
    "valor_declarado": 0
  },
  "servicio": "express"
}
```

**Response esperada (éxito):**
```json
{
  "status": "success",
  "tracking": "ET1234567890MX",
  "numero_guia": "ET1234567890MX",
  "precio": 185.50,
  "moneda": "MXN",
  "url_etiqueta": "https://app.enviatodo.com/etiquetas/ET1234567890MX.pdf",
  "etiqueta_base64": "JVBERi0xLjQK...",
  "carrier": "FedEx",
  "servicio": "express"
}
```

---

#### Endpoint: Cancelar guía

**Método:** `POST`  
**URL:** `https://apiqav2.enviatodo.mx/index.php/cancelar`

**Request:**
```json
{
  "api_key": "tu_api_key_aqui",
  "user_id": "tu_user_id",
  "tracking": "ET1234567890MX",
  "referencia": "WH/OUT/00123"
}
```

**Response esperada (éxito):**
```json
{
  "status": "success",
  "message": "Guía cancelada exitosamente",
  "tracking": "ET1234567890MX"
}
```

---

#### Endpoint: Rastreo

**Portal de rastreo (web):**
```
https://app.enviatodo.com/#Tracking?guia={TRACKING_NUMBER}
```

**API de rastreo (si disponible):**  
**Método:** `POST`  
**URL:** `https://apiqav2.enviatodo.mx/index.php/rastreo`

**Request:**
```json
{
  "api_key": "tu_api_key_aqui",
  "user_id": "tu_user_id",
  "tracking": "ET1234567890MX"
}
```

**Response esperada:**
```json
{
  "status": "success",
  "tracking": "ET1234567890MX",
  "estado_actual": "En tránsito",
  "ubicacion": "Guadalajara, Jalisco",
  "fecha_estimada": "2026-04-02",
  "historial": [
    {
      "fecha": "2026-03-30 14:30:00",
      "estado": "Recolectado",
      "ubicacion": "León, Guanajuato"
    },
    {
      "fecha": "2026-03-31 08:15:00",
      "estado": "En tránsito",
      "ubicacion": "Guadalajara, Jalisco"
    }
  ]
}
```

---

### C.3 Manejo de Errores Comunes

| Código HTTP | Causa probable | Solución |
|---|---|---|
| `401 Unauthorized` | API Key incorrecta o expirada | Verificar API Key en el transportista |
| `403 Forbidden` | Sin permisos para el endpoint | Contactar a EnviaTodo para habilitar el servicio |
| `404 Not Found` | URL del endpoint incorrecta | Verificar la URL base de la API |
| `422 Unprocessable` | Datos del payload inválidos | Revisar formato de CP, peso, dimensiones |
| `429 Too Many Requests` | Límite de peticiones excedido | Esperar y reintentar; revisar plan de API |
| `500 Internal Server Error` | Error en el servidor de EnviaTodo | Contactar soporte de EnviaTodo |
| `Timeout` | Conexión lenta o servidor caído | Verificar conectividad; reintentar |

#### Errores de negocio comunes

| Error | Causa | Solución |
|---|---|---|
| `"CP de destino inválido"` | CP no existe o mal formateado | Verificar que el CP del cliente sea de 5 dígitos |
| `"Servicio no disponible"` | El tipo de servicio no cubre esa ruta | Cambiar tipo de servicio o contactar EnviaTodo |
| `"Peso excedido"` | El paquete supera el límite del servicio | Usar servicio diferente o dividir el envío |
| `"Saldo insuficiente"` | Sin crédito en la cuenta EnviaTodo | Recargar saldo en el portal de EnviaTodo |

---

### C.4 Debugging con `_logger`

El módulo registra todas las peticiones y respuestas. Para ver los logs:

#### En Odoo Self-hosted:
```bash
# Ver logs en tiempo real
tail -f /var/log/odoo/odoo.log | grep EnviaTodo

# Filtrar solo errores
grep "EnviaTodo" /var/log/odoo/odoo.log | grep -E "ERROR|WARNING"
```

#### En Odoo (interfaz web):
1. Ve a **Configuración → Técnico → Logging**
2. Agrega un logger: `odoo.addons.delivery_enviatodo_custer`
3. Nivel: `DEBUG` para máximo detalle

#### Ejemplo de log exitoso:
```
INFO odoo.addons.delivery_enviatodo_custer.models.delivery_carrier: 
  EnviaTodo → https://apiqav2.enviatodo.mx/index.php/cotizar | 
  Payload: {"api_key": "***", "origen": {"cp": "37000"}, ...}

INFO odoo.addons.delivery_enviatodo_custer.models.delivery_carrier: 
  EnviaTodo ← https://apiqav2.enviatodo.mx/index.php/cotizar | 
  Status: 200 | Body: {"status": "success", "precio": 185.50, ...}
```

#### Ejemplo de log de error:
```
WARNING odoo.addons.delivery_enviatodo_custer.models.delivery_carrier: 
  EnviaTodo: Error al cotizar: EnviaTodo: Credenciales inválidas (HTTP 401).
```

---

### C.5 Probar la API con cURL

Antes de configurar Odoo, puedes probar la API directamente:

```bash
# Probar cotización
curl -X POST "https://apiqav2.enviatodo.mx/index.php/cotizar" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_API_KEY" \
  -d '{
    "api_key": "TU_API_KEY",
    "user_id": "TU_USER_ID",
    "origen": {"cp": "37000"},
    "destino": {"cp": "06600"},
    "paquete": {"largo": 44, "ancho": 11, "alto": 33, "peso": 1.9},
    "servicio": "express"
  }'
```

```bash
# Probar generación de guía
curl -X POST "https://apiqav2.enviatodo.mx/index.php/generar" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_API_KEY" \
  -d '{
    "api_key": "TU_API_KEY",
    "user_id": "TU_USER_ID",
    "referencia": "TEST-001",
    "origen": {
      "cp": "37000",
      "nombre": "Custer Boots",
      "calle": "León, Guanajuato",
      "ciudad": "León",
      "estado": "Guanajuato"
    },
    "destino": {
      "cp": "06600",
      "nombre": "Cliente Prueba",
      "telefono": "5512345678",
      "calle": "Av. Insurgentes 100",
      "ciudad": "Ciudad de México",
      "estado": "CDMX"
    },
    "paquete": {
      "largo": 44, "ancho": 11, "alto": 33, "peso": 1.9,
      "descripcion": "Calzado / Botas"
    },
    "servicio": "express"
  }'
```

---

### C.6 Ajustar Nombres de Campos de la Respuesta

Si la API de EnviaTodo devuelve campos con nombres diferentes a los esperados, edita el método `enviatodo_rate_shipment` en `delivery_carrier.py`:

```python
# Línea actual — busca múltiples nombres posibles:
price = (
    result.get("precio")
    or result.get("costo")
    or result.get("price")
    or result.get("total")
    or 0.0
)

# Si la API devuelve "monto_total", agregar:
price = (
    result.get("precio")
    or result.get("costo")
    or result.get("price")
    or result.get("total")
    or result.get("monto_total")  # ← agregar aquí
    or 0.0
)
```

Lo mismo aplica para el número de rastreo en `enviatodo_send_shipping`:
```python
tracking_number = (
    result.get("tracking")
    or result.get("numero_guia")
    or result.get("guia")
    or result.get("tracking_number")
    or result.get("folio")  # ← agregar si la API usa "folio"
    or ""
)
```

---

## PARTE D — Datos del Producto Custer Boots

### D.1 Especificaciones del Paquete

| Parámetro | Valor | Unidad |
|---|---|---|
| **Largo** | 44 | cm |
| **Ancho** | 11 | cm |
| **Alto** | 33 | cm |
| **Peso** | 1.9 | kg |
| **CP de origen** | 37000 | — |
| **Ciudad de origen** | León | Guanajuato |

### D.2 Configurar Dimensiones en Odoo

#### Opción A: En el transportista (recomendado)

1. Ve a **Inventario → Configuración → Métodos de envío**
2. Abre el transportista **EnviaTodo**
3. Ve a la pestaña **EnviaTodo → Dimensiones Predeterminadas**
4. Configura:
   - Largo: `44`
   - Ancho: `11`
   - Alto: `33`
   - Peso: `1.9`
5. Guarda

Estas dimensiones se usarán para **todos los envíos** a menos que el producto tenga peso configurado.

#### Opción B: En el producto (peso real)

Si los productos tienen pesos diferentes, configura el peso en cada producto:

1. Ve a **Inventario → Productos → Productos**
2. Abre el producto (ej. "Bota Custer Modelo X")
3. Ve a la pestaña **Inventario**
4. En el campo **Peso**, ingresa el peso en kg (ej. `1.9`)
5. Guarda

El módulo calculará automáticamente el peso total del picking sumando `peso × cantidad` de cada producto.

#### Opción C: Configurar dimensiones en el tipo de paquete

1. Ve a **Inventario → Configuración → Tipos de paquete**
2. Crea un nuevo tipo: **"Caja Custer Boots"**
3. Configura:
   - Largo: `44 cm`
   - Ancho: `11 cm`
   - Alto: `33 cm`
   - Peso máximo: `5 kg`
4. Asigna este tipo de paquete en las operaciones de envío

### D.3 Código Postal de Origen

El CP de origen **37000** corresponde a:
- **Ciudad:** León
- **Estado:** Guanajuato
- **País:** México

Este CP está configurado como valor predeterminado en el módulo. Para cambiarlo:
1. Ve al transportista EnviaTodo
2. Pestaña **EnviaTodo → Configuración del Servicio**
3. Campo **CP de origen**
4. Cambiar el valor y guardar

### D.4 Configurar la Dirección de Origen en Odoo

1. Ve a **Configuración → Empresas**
2. Abre **Custer Boots**
3. Configura:
   - **Dirección:** (dirección completa en León)
   - **Ciudad:** León
   - **Estado:** Guanajuato
   - **CP:** 37000
   - **País:** México
4. Guarda

Esta dirección se usará como remitente en las guías de envío.

---

## PARTE E — Checklist de Implementación

### E.1 Pre-requisitos

Antes de comenzar, verifica que tienes:

- [ ] Acceso de administrador a Odoo
- [ ] Credenciales de la API de EnviaTodo (API Key + User ID)
- [ ] Módulos de Odoo instalados: `delivery`, `stock`, `sale`
- [ ] Para módulo custom: acceso SSH al servidor o repositorio de Odoo.sh
- [ ] Dirección completa de Custer Boots configurada en Odoo (CP 37000)
- [ ] Productos con peso configurado (opcional pero recomendado)

### E.2 Checklist de Instalación (Módulo Custom)

#### Preparación del servidor
- [ ] Verificar versión de Odoo: `./odoo-bin --version` (debe ser 19.x)
- [ ] Verificar Python: `python3 --version` (debe ser 3.12+)
- [ ] Verificar que `requests` está disponible: `python3 -c "import requests; print(requests.__version__)"`

#### Instalación del módulo
- [ ] Copiar `delivery_enviatodo_custer/` al directorio de addons
- [ ] Verificar permisos: `ls -la /opt/odoo/addons/delivery_enviatodo_custer/`
- [ ] Reiniciar servidor Odoo
- [ ] Actualizar lista de aplicaciones en Odoo
- [ ] Instalar el módulo "EnviaTodo Shipping - Custer Boots"
- [ ] Verificar que no hay errores en los logs: `grep -i error /var/log/odoo/odoo.log | tail -20`

#### Configuración del transportista
- [ ] Crear nuevo método de envío: **Inventario → Configuración → Métodos de envío → Nuevo**
- [ ] Nombre: `EnviaTodo Express` (o el nombre deseado)
- [ ] Proveedor: `EnviaTodo`
- [ ] Pestaña EnviaTodo → Credenciales:
  - [ ] API Key: (ingresar la clave proporcionada por EnviaTodo)
  - [ ] Usuario/ID: (ingresar el ID de cuenta)
- [ ] Pestaña EnviaTodo → Servicio:
  - [ ] Tipo de servicio: `express` (o el código correcto)
  - [ ] CP de origen: `37000`
- [ ] Pestaña EnviaTodo → Dimensiones:
  - [ ] Largo: `44`
  - [ ] Ancho: `11`
  - [ ] Alto: `33`
  - [ ] Peso: `1.9`
- [ ] Guardar el transportista
- [ ] Hacer clic en **"Probar conexión"** y verificar éxito

### E.3 Procedimiento de Pruebas

#### Prueba 1: Conexión con la API
1. Abrir el transportista EnviaTodo en Odoo
2. Hacer clic en **"Probar conexión"**
3. ✅ Esperado: Notificación verde "Conexión exitosa"
4. ❌ Si falla: Revisar API Key y User ID

#### Prueba 2: Cotización de envío
1. Crear una orden de venta de prueba
2. Asegurarse de que el cliente tiene CP válido (5 dígitos)
3. En la orden, ir a la pestaña **Otro info → Transportista**
4. Seleccionar **EnviaTodo Express**
5. Hacer clic en **"Obtener tarifa"** (o el botón equivalente)
6. ✅ Esperado: Se muestra el costo de envío en MXN
7. ❌ Si falla: Revisar logs con `grep EnviaTodo /var/log/odoo/odoo.log`

#### Prueba 3: Generación de guía
1. Confirmar la orden de venta de prueba
2. Ir al picking de salida generado
3. Validar el picking (hacer clic en **Validar**)
4. ✅ Esperado:
   - El campo **Número de rastreo** se llena automáticamente
   - Aparece un adjunto PDF con la etiqueta de envío
   - Se publica una nota interna con el número de guía
5. ❌ Si falla: Revisar logs

#### Prueba 4: Enlace de rastreo
1. Abrir el picking validado
2. Hacer clic en el enlace de rastreo (ícono de camión o botón "Rastrear")
3. ✅ Esperado: Se abre `https://app.enviatodo.com/#Tracking?guia=XXXXXXXX`

#### Prueba 5: Cancelación de guía
1. Abrir el picking con guía generada
2. Hacer clic en **"Cancelar guía"** (si el botón está disponible)
3. ✅ Esperado: Mensaje de confirmación de cancelación
4. Verificar en el portal de EnviaTodo que la guía fue cancelada

### E.4 Checklist de Go-Live

Antes de usar en producción:

- [ ] Todas las pruebas del E.3 pasaron exitosamente
- [ ] El equipo de almacén fue capacitado en el nuevo flujo
- [ ] Se documentaron los pasos para generar guías manualmente (en caso de falla de la API)
- [ ] Se configuró monitoreo de logs para detectar errores de la API
- [ ] Se tiene el contacto de soporte de EnviaTodo disponible
- [ ] Se probó con un envío real (no solo de prueba)
- [ ] Se verificó que las etiquetas impresas son legibles y escaneables
- [ ] Se configuró la impresora de etiquetas (si aplica)
- [ ] Se revisó el saldo disponible en la cuenta de EnviaTodo

### E.5 Flujo de Trabajo Diario

Una vez en producción, el flujo típico es:

```
1. Cliente hace pedido en Odoo (o se crea manualmente)
   ↓
2. Se confirma la orden de venta
   → Odoo cotiza automáticamente el envío con EnviaTodo
   → El costo de envío se agrega a la orden
   ↓
3. Almacén prepara el pedido
   → Se crea automáticamente un picking de salida
   ↓
4. Almacén valida el picking (marca como enviado)
   → Odoo genera automáticamente la guía en EnviaTodo
   → Se adjunta la etiqueta PDF al picking
   → El número de rastreo se guarda en Odoo
   ↓
5. Se imprime la etiqueta y se pega en la caja
   ↓
6. El cliente puede rastrear su pedido en:
   https://app.enviatodo.com/#Tracking?guia=XXXXXXXX
```

### E.6 Solución de Problemas Frecuentes

#### "La cotización siempre devuelve $0"
- Verificar que la respuesta de la API contiene el campo correcto (ver C.6)
- Revisar logs para ver la respuesta completa de la API
- Contactar a EnviaTodo para confirmar el nombre del campo de precio

#### "No se genera la guía al validar el picking"
- Verificar que el picking tiene un transportista asignado (debe ser EnviaTodo)
- Verificar que el cliente tiene CP válido
- Revisar logs: `grep "EnviaTodo" /var/log/odoo/odoo.log | tail -50`

#### "La etiqueta PDF no se adjunta"
- La API puede devolver la etiqueta en un campo diferente (ver C.6)
- Verificar si la API devuelve URL o base64
- Revisar logs para ver la estructura completa de la respuesta

#### "Error 401 — Credenciales inválidas"
- Verificar que la API Key no tiene espacios al inicio o al final
- Verificar que el User ID es correcto
- Contactar a EnviaTodo para confirmar que las credenciales están activas

#### "El módulo no aparece en la lista de aplicaciones"
- Verificar que el directorio del módulo está en el path de addons de Odoo
- Verificar que `__manifest__.py` no tiene errores de sintaxis: `python3 -c "import ast; ast.parse(open('__manifest__.py').read())"`
- Reiniciar Odoo y actualizar la lista de aplicaciones

#### "Error al instalar: campo delivery_type ya existe"
- Esto puede ocurrir si hay otro módulo que también agrega `delivery_type`
- Verificar que no hay conflictos con otros módulos de envío instalados
- Revisar el log de instalación para el error específico

---

## Apéndice A — Referencia Rápida de Campos

### Campos del transportista (delivery.carrier)

| Campo técnico | Etiqueta | Tipo | Predeterminado |
|---|---|---|---|
| `enviatodo_api_key` | API Key | Char | — |
| `enviatodo_user_id` | Usuario/ID | Char | — |
| `enviatodo_service_type` | Tipo de servicio | Char | `express` |
| `enviatodo_api_base_url` | URL base API | Char | `https://apiqav2.enviatodo.mx/index.php/` |
| `enviatodo_default_length` | Largo (cm) | Float | `44` |
| `enviatodo_default_width` | Ancho (cm) | Float | `11` |
| `enviatodo_default_height` | Alto (cm) | Float | `33` |
| `enviatodo_default_weight` | Peso (kg) | Float | `1.9` |
| `enviatodo_origin_zip` | CP de origen | Char | `37000` |

### Campos del picking (stock.picking) — estándar de Odoo

| Campo técnico | Descripción |
|---|---|
| `carrier_id` | Transportista asignado |
| `carrier_tracking_ref` | Número de rastreo (guía) |
| `carrier_price` | Costo real del envío |

---

## Apéndice B — Contactos y Recursos

| Recurso | URL / Contacto |
|---|---|
| Portal EnviaTodo | https://app.enviatodo.com |
| Documentación API | https://app.enviatodo.com/#Api (requiere login) |
| Rastreo de paquetes | https://app.enviatodo.com/#Tracking |
| Soporte EnviaTodo | soporte@enviatodo.com |
| Documentación Odoo Delivery | https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/setup_configuration/delivery_method.html |

---

## Apéndice C — Historial de Cambios

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0.0 | Marzo 2026 | Versión inicial — integración básica con EnviaTodo |

---

*Documento generado para Custer Boots — León, Guanajuato, México*  
*Módulo: `delivery_enviatodo_custer` v19.0.1.0.0*
