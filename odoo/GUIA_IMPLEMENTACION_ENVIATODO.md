# Guía de Implementación: EnviaTodo en Odoo para Custer Boots

**Versión:** 3.0.0  
**Fecha:** Marzo 2026  
**Empresa:** Custer Boots — León, Guanajuato, CP 37000  
**API:** EnviaTodo.com — `https://apiqav2.enviatodo.mx/index.php/`  
**Odoo:** 19 Community / SaaS  

---

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [PARTE A — Implementación con Odoo Studio (SaaS)](#parte-a--implementación-con-odoo-studio-saas)
3. [PARTE B — Módulo Custom (Self-hosted / Odoo.sh)](#parte-b--módulo-custom-self-hosted--odoosh)
4. [PARTE C — Configuración de la API de EnviaTodo](#parte-c--configuración-de-la-api-de-enviatodo)
5. [PARTE D — Datos del Producto Custer Boots](#parte-d--datos-del-producto-custer-boots)
6. [PARTE E — Checklist de Implementación](#parte-e--checklist-de-implementación)

---

## Introducción

Esta guía describe cómo integrar la plataforma de envíos **EnviaTodo.com** con **Odoo 19** para automatizar la cotización, generación y seguimiento de guías de envío en **Custer Boots**.

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

> **Para Odoo SaaS / Online** donde no se pueden instalar módulos Python.

### A.1 Realidad Técnica del Sandbox de Odoo 19

El código Python en Reglas Automatizadas se ejecuta dentro de `safe_eval`, que **bloquea a nivel de opcode de bytecode**:

```
BLACKLIST = { IMPORT_NAME, IMPORT_FROM, IMPORT_STAR, STORE_ATTR, DELETE_ATTR }
```

| Prohibido | Error que verás |
|---|---|
| `import requests` | `ValueError: forbidden opcode(s) ... IMPORT_NAME` |
| `import json` | Mismo error — **pero `json` ya está inyectado** |
| `return` (top-level) | `SyntaxError: 'return' outside function` |
| `record.field = x` | `ValueError: forbidden opcode(s) ... STORE_ATTR` |

#### ¿Qué SÍ está disponible sin import?

| Variable | Qué es | Ejemplo de uso |
|---|---|---|
| `env` | ORM completo | `env['delivery.carrier'].search([...])` |
| `record` / `records` | Registro(s) que disparan la acción | `record.partner_id.zip` |
| `model` | Modelo de la regla | `model.search([...])` |
| `log(msg, level)` | Escribe en ir.logging | `log("mensaje", level="warning")` |
| `_logger` | LoggerProxy | `_logger.info("mensaje")` |
| `json` | Módulo wrapped | `json.dumps(dict)` / `json.loads(str)` |
| `datetime` | Módulo wrapped | `datetime.datetime.now()` |
| `time` | Módulo wrapped | `time.time()` |
| `b64encode` / `b64decode` | Funciones directas | `b64encode(bytes)` |
| `UserError` | Excepción | `raise UserError("mensaje")` |
| `Command` | odoo.fields.Command | Para M2M/O2M |

#### ¿Se puede hacer HTTP sin `import requests`?

**No.** Después de analizar exhaustivamente el código fuente de Odoo 19:

- `iap_jsonrpc()` es una función standalone, no un método de modelo — no se puede llamar desde el sandbox
- `env['iap.account']` solo habla con servidores IAP de Odoo, no con URLs arbitrarias
- El tipo de acción `webhook` de Odoo 19 es fire-and-forget (no devuelve respuesta) y no acepta payload personalizado
- No existe ningún modelo en Odoo que exponga un método genérico de HTTP callable desde `safe_eval`

#### Entonces, ¿qué hacemos?

La Parte A se divide en **dos reglas automatizadas** que trabajan juntas:

1. **Regla 1 (código Python):** Prepara el payload, valida datos, y dispara una **Acción de Servidor tipo Webhook** que hace el POST a EnviaTodo
2. **Regla 2 (código Python):** Procesa la respuesta cuando EnviaTodo (o un relay) llama de vuelta al webhook de entrada de Odoo

**Alternativa práctica:** Si no quieres montar un relay, la Regla 1 prepara todo y publica el payload como nota interna. Luego configuras una **Acción de Servidor tipo Webhook** (sin código, desde la UI) que envía los campos relevantes a EnviaTodo.

---

### A.2 Crear Campos Personalizados con Odoo Studio

Ve a **Inventario → Configuración → Métodos de envío**, abre un transportista, activa Studio y crea:

| Nombre técnico | Etiqueta | Tipo | Valor predeterminado |
|---|---|---|---|
| `x_studio_api_key_enviatodo` | API Key EnviaTodo | Texto | — |
| `x_studio_usuario_enviatodo` | Usuario EnviaTodo | Texto | — |
| `x_studio_tipo_de_servicio` | Tipo de servicio | Texto | `express` |
| `x_studio_cp_de_origen` | CP de origen | Texto | `37000` |
| `x_studio_url_base_api` | URL base API | Texto | `https://apiqav2.enviatodo.mx/index.php/` |
| `x_studio_largo_cm_1` | Largo (cm) | Decimal | `44` |
| `x_studio_ancho_cm_1` | Ancho (cm) | Decimal | `11` |
| `x_studio_alto_cm_1` | Alto (cm) | Decimal | `33` |
| `x_studio_peso_kg` | Peso (kg) | Decimal | `1.9` |

Organiza en una pestaña **"EnviaTodo"** con grupos: Credenciales, Servicio, Dimensiones.

---

### A.3 Regla Automatizada: Cotizar Envío (sale.order)

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Cotizar envío` |
| **Modelo** | `Orden de venta (sale.order)` |
| **Disparador** | `Al crear y editar` |
| **Antes de actualizar dominio** | `[("state", "!=", "sale")]` |
| **Aplicar en** | `[("state", "=", "sale")]` |

**Acción 1 — Ejecutar código Python:**

```python
# ==============================================================
# EnviaTodo: Cotizar envío — Odoo 19 sandbox-safe
# Modelo: sale.order
#
# SIN import — SIN return — SIN STORE_ATTR
# json.dumps/loads ya disponible como módulo wrapped
# ==============================================================

carrier = env['delivery.carrier'].search([
    ('name', 'ilike', 'EnviaTodo'),
    ('active', '=', True),
], limit=1)

if not carrier:
    log("EnviaTodo: No se encontró transportista activo con nombre 'EnviaTodo'", level="warning")
else:
    API_KEY = carrier.x_studio_api_key_enviatodo or ''
    USER_ID = carrier.x_studio_usuario_enviatodo or ''
    BASE_URL = (carrier.x_studio_url_base_api or 'https://apiqav2.enviatodo.mx/index.php/').rstrip('/')
    SERVICE = carrier.x_studio_tipo_de_servicio or 'express'
    ORIGIN_ZIP = carrier.x_studio_cp_de_origen or '37000'

    if not API_KEY or not USER_ID:
        log("EnviaTodo: Faltan credenciales (API Key o Usuario) en el transportista", level="warning")
    else:
        for order in records:
            partner = order.partner_shipping_id or order.partner_id
            dest_zip = (partner.zip or '').strip() if partner else ''

            if not dest_zip or len(dest_zip) != 5 or not dest_zip.isdigit():
                log(
                    "EnviaTodo: Orden %s — CP destino inválido: '%s' (cliente: %s)"
                    % (order.name, dest_zip, partner.name if partner else 'N/A'),
                    level="warning"
                )
            else:
                payload = {
                    "api_key": API_KEY,
                    "user_id": USER_ID,
                    "origen": {"cp": ORIGIN_ZIP},
                    "destino": {"cp": dest_zip},
                    "paquete": {
                        "largo": carrier.x_studio_largo_cm_1 or 44,
                        "ancho": carrier.x_studio_ancho_cm_1 or 11,
                        "alto": carrier.x_studio_alto_cm_1 or 33,
                        "peso": carrier.x_studio_peso_kg or 1.9,
                    },
                    "servicio": SERVICE,
                }

                payload_str = json.dumps(payload, ensure_ascii=False, indent=2)

                order.message_post(
                    body=(
                        "<b>📦 EnviaTodo — Cotización solicitada</b><br/>"
                        "<b>CP origen:</b> %s<br/>"
                        "<b>CP destino:</b> %s<br/>"
                        "<b>Servicio:</b> %s<br/>"
                        "<b>URL:</b> <code>%s/cotizar</code><br/>"
                        "<details><summary>📋 Payload JSON (clic para expandir)</summary>"
                        "<pre>%s</pre></details>"
                    ) % (ORIGIN_ZIP, dest_zip, SERVICE, BASE_URL, payload_str),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

                log("EnviaTodo: Payload cotización listo — orden %s → CP %s" % (order.name, dest_zip))
```

**Acción 2 — Enviar notificación Webhook** (agregar como acción hija):

Agrega una segunda acción de tipo **"Enviar notificación Webhook"** en la misma regla:
- **URL del Webhook:** `https://apiqav2.enviatodo.mx/index.php/cotizar`
- **Campos a enviar:** selecciona los campos relevantes de la orden

> ⚠️ **Limitación:** La acción webhook de Odoo envía los campos del registro, no un payload personalizado. Si la API de EnviaTodo requiere un formato específico, necesitarás un relay (n8n/Make) o el módulo custom (Parte B).

---

### A.4 Regla Automatizada: Generar Guía (stock.picking)

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Generar guía de envío` |
| **Modelo** | `Transferencia (stock.picking)` |
| **Disparador** | `Al crear y editar` |
| **Antes de actualizar dominio** | `[("state", "!=", "done")]` |
| **Aplicar en** | `[("state", "=", "done"), ("picking_type_code", "=", "outgoing")]` |

**Código Python:**

```python
# ==============================================================
# EnviaTodo: Generar guía — Odoo 19 sandbox-safe
# Modelo: stock.picking
#
# SIN import — SIN return — SIN STORE_ATTR
# Usa .write() en vez de asignación directa
# Usa if/else anidados en vez de return temprano
# ==============================================================

carrier = env['delivery.carrier'].search([
    ('name', 'ilike', 'EnviaTodo'),
    ('active', '=', True),
], limit=1)

if not carrier:
    log("EnviaTodo: No se encontró transportista activo", level="warning")
else:
    API_KEY = carrier.x_studio_api_key_enviatodo or ''
    USER_ID = carrier.x_studio_usuario_enviatodo or ''
    BASE_URL = (carrier.x_studio_url_base_api or 'https://apiqav2.enviatodo.mx/index.php/').rstrip('/')
    SERVICE = carrier.x_studio_tipo_de_servicio or 'express'
    ORIGIN_ZIP = carrier.x_studio_cp_de_origen or '37000'

    if not API_KEY or not USER_ID:
        log("EnviaTodo: Faltan credenciales", level="warning")
    else:
        for picking in records:
            # --- Filtros de seguridad ---
            if picking.carrier_tracking_ref:
                log("EnviaTodo: %s ya tiene guía: %s — omitido" % (picking.name, picking.carrier_tracking_ref))
            else:
                partner = picking.partner_id
                if not partner:
                    log("EnviaTodo: %s sin destinatario" % picking.name, level="warning")
                else:
                    dest_zip = (partner.zip or '').strip()
                    if not dest_zip or len(dest_zip) != 5 or not dest_zip.isdigit():
                        picking.message_post(
                            body=(
                                "<b>⚠️ EnviaTodo:</b> El cliente <b>%s</b> no tiene "
                                "CP válido (5 dígitos). CP actual: '<b>%s</b>'.<br/>"
                                "Corrija el CP antes de generar la guía."
                            ) % (partner.name, dest_zip),
                            message_type='comment',
                            subtype_xmlid='mail.mt_note',
                        )
                    else:
                        # --- Peso real desde movimientos ---
                        weight = carrier.x_studio_peso_kg or 1.9
                        try:
                            total_w = sum(
                                (m.product_id.weight or 0.0) * m.product_qty
                                for m in picking.move_ids
                                if m.product_id
                            )
                            if total_w > 0:
                                weight = total_w
                        except Exception:
                            pass

                        # --- Dirección ---
                        street_parts = []
                        if partner.street:
                            street_parts.append(partner.street)
                        if partner.street2:
                            street_parts.append(partner.street2)
                        street = ' '.join(street_parts) if street_parts else 'Sin dirección'

                        # --- Payload ---
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
                                "largo": carrier.x_studio_largo_cm_1 or 44,
                                "ancho": carrier.x_studio_ancho_cm_1 or 11,
                                "alto": carrier.x_studio_alto_cm_1 or 33,
                                "peso": round(weight, 3),
                                "descripcion": "Calzado / Botas",
                                "valor_declarado": 0,
                            },
                            "servicio": SERVICE,
                        }

                        payload_str = json.dumps(payload, ensure_ascii=False, indent=2)

                        picking.message_post(
                            body=(
                                "<b>📦 EnviaTodo — Guía solicitada</b><br/>"
                                "<b>Destino:</b> %s (CP %s)<br/>"
                                "<b>Peso:</b> %.3f kg<br/>"
                                "<b>Referencia:</b> %s<br/>"
                                "<b>URL:</b> <code>%s/generar</code><br/>"
                                "<details><summary>📋 Payload JSON (clic para expandir)</summary>"
                                "<pre>%s</pre></details>"
                            ) % (partner.name, dest_zip, weight, picking.name, BASE_URL, payload_str),
                            message_type='comment',
                            subtype_xmlid='mail.mt_note',
                        )

                        log("EnviaTodo: Payload generación listo — %s → %s (CP %s)" % (picking.name, partner.name, dest_zip))
```

---

### A.5 Regla Automatizada: Recibir Respuesta (webhook de entrada)

Cuando EnviaTodo (o tu relay) llame de vuelta a Odoo con el resultado:

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Procesar respuesta de guía` |
| **Modelo** | `Transferencia (stock.picking)` |
| **Disparador** | `On webhook` |
| **Record Getter** | `model.browse(int(payload.get('picking_id', 0)))` |

**Código Python:**

```python
# ==============================================================
# EnviaTodo: Procesar respuesta — webhook de entrada
# 'payload' es inyectado por el disparador webhook
# 'record' viene del Record Getter
# ==============================================================

if not record or not record.exists():
    log("EnviaTodo webhook: picking no encontrado. Payload: %s" % str(payload)[:300], level="error")
else:
    tracking = (
        payload.get('tracking')
        or payload.get('numero_guia')
        or payload.get('guia')
        or payload.get('tracking_number')
        or ''
    )

    if not tracking:
        record.message_post(
            body=(
                "<b>⚠️ EnviaTodo:</b> La API no devolvió número de rastreo.<br/>"
                "<b>Respuesta:</b> %s"
            ) % str(payload)[:500],
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        log("EnviaTodo webhook: sin tracking para %s" % record.name, level="warning")
    else:
        # Guardar tracking (usa .write, no asignación directa)
        record.write({'carrier_tracking_ref': tracking})

        # Nota con enlace de rastreo
        record.message_post(
            body=(
                "<b>✅ EnviaTodo — Guía generada</b><br/>"
                "<b>Tracking:</b> %s<br/>"
                "<a href='https://app.enviatodo.com/#Tracking?guia=%s' target='_blank'>"
                "🔗 Rastrear envío</a>"
            ) % (tracking, tracking),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        log("EnviaTodo webhook: guía %s → picking %s" % (tracking, record.name))

        # Adjuntar etiqueta PDF si viene en base64
        label_b64 = (
            payload.get('etiqueta_base64')
            or payload.get('label_base64')
            or payload.get('pdf_base64')
            or payload.get('etiqueta')
        )
        if label_b64:
            try:
                env['ir.attachment'].create({
                    'name': 'Guia_EnviaTodo_%s.pdf' % tracking,
                    'type': 'binary',
                    'datas': label_b64 if isinstance(label_b64, str) else label_b64.decode(),
                    'res_model': 'stock.picking',
                    'res_id': record.id,
                    'mimetype': 'application/pdf',
                })
                log("EnviaTodo webhook: PDF adjuntado a %s" % record.name)
            except Exception as e:
                log("EnviaTodo webhook: error al adjuntar PDF: %s" % str(e), level="warning")
```

---

### A.6 Configurar Enlace de Rastreo

Crea una Regla Automatizada adicional:

| Campo | Valor |
|---|---|
| **Nombre** | `EnviaTodo: Actualizar URL de rastreo` |
| **Modelo** | `Transferencia (stock.picking)` |
| **Disparador** | `Al crear y editar` |
| **Campos disparadores** | `carrier_tracking_ref` |
| **Acción** | `Actualizar el registro` |

Campo a actualizar: `x_enviatodo_tracking_url`  
Valor: `https://app.enviatodo.com/#Tracking?guia={{ object.carrier_tracking_ref }}`

---

### A.7 Resumen de Arquitectura SaaS

```
                        ODOO 19 SaaS
┌──────────────────────────────────────────────────┐
│                                                  │
│  sale.order confirmada                           │
│       │                                          │
│       ▼                                          │
│  [Regla A.3] Prepara payload cotización          │
│       │       → publica JSON en nota interna     │
│       │       → dispara acción webhook (UI)      │
│       │                                          │
│  stock.picking → state = done                    │
│       │                                          │
│       ▼                                          │
│  [Regla A.4] Prepara payload generación          │
│       │       → publica JSON en nota interna     │
│       │       → dispara acción webhook (UI)      │
│       │                                          │
│       ▼                                          │
│  [Regla A.5] Webhook entrada ← respuesta API    │
│               → escribe carrier_tracking_ref     │
│               → adjunta etiqueta PDF             │
│               → publica nota con link rastreo    │
│                                                  │
└──────────────────────────────────────────────────┘
```

> **Nota práctica:** Si la API de EnviaTodo no soporta callbacks (webhook de vuelta), necesitarás un intermediario (n8n, Make, Zapier, o un simple script en un VPS) que reciba el webhook de Odoo, llame a EnviaTodo, y devuelva la respuesta al webhook de entrada de Odoo. Esto es inherente a la limitación del sandbox, no a esta implementación.

---

## PARTE B — Módulo Custom (Self-hosted / Odoo.sh)

> **Recomendada.** Sin restricciones de sandbox. Llamadas HTTP directas con `requests`.

### B.1 Estructura del Módulo

```
delivery_enviatodo_custer/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── delivery_carrier.py      ← usa import requests libremente
├── views/
│   └── delivery_carrier_views.xml
├── security/
│   └── ir.model.access.csv
└── static/
    └── description/
        └── icon.png
```

### B.2 Instalación

```bash
# Odoo.sh
git add delivery_enviatodo_custer/
git commit -m "feat: agregar módulo EnviaTodo para Custer Boots"
git push origin main

# Self-hosted
cp -r delivery_enviatodo_custer/ /opt/odoo/addons/
sudo systemctl restart odoo
```

### B.3 Configuración

1. **Inventario → Configuración → Métodos de envío → Nuevo**
2. Proveedor: `EnviaTodo`
3. Pestaña EnviaTodo → Credenciales: API Key + Usuario
4. Pestaña EnviaTodo → Dimensiones: 44×11×33 cm, 1.9 kg
5. **Probar conexión** ✅

---

## PARTE C — Configuración de la API de EnviaTodo

### C.1 Endpoints

| Endpoint | URL | Método |
|---|---|---|
| Cotizar | `https://apiqav2.enviatodo.mx/index.php/cotizar` | POST |
| Generar | `https://apiqav2.enviatodo.mx/index.php/generar` | POST |
| Cancelar | `https://apiqav2.enviatodo.mx/index.php/cancelar` | POST |
| Rastreo | `https://app.enviatodo.com/#Tracking?guia={TRACKING}` | Web |

### C.2 Probar con cURL

```bash
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

---

## PARTE D — Datos del Producto Custer Boots

| Parámetro | Valor | Unidad |
|---|---|---|
| Largo | 44 | cm |
| Ancho | 11 | cm |
| Alto | 33 | cm |
| Peso | 1.9 | kg |
| CP origen | 37000 | — |
| Ciudad | León | Guanajuato |

---

## PARTE E — Checklist

### Odoo SaaS (Parte A)

- [ ] 9 campos `x_studio_*` creados en `delivery.carrier`
- [ ] Transportista "EnviaTodo" creado con credenciales
- [ ] Regla cotización (sale.order) — A.3
- [ ] Regla generación (stock.picking) — A.4
- [ ] Regla webhook entrada — A.5
- [ ] Regla enlace rastreo — A.6
- [ ] Prueba end-to-end

### Odoo.sh / Self-hosted (Parte B)

- [ ] Módulo instalado
- [ ] Transportista configurado
- [ ] Prueba de conexión ✅
- [ ] Cotización de prueba ✅
- [ ] Generación de guía de prueba ✅

---

## Apéndice A — Campos

### delivery.carrier (transportista)

| Campo técnico | Etiqueta | Tipo | Default |
|---|---|---|---|
| `x_studio_api_key_enviatodo` | API Key EnviaTodo | Char | — |
| `x_studio_usuario_enviatodo` | Usuario EnviaTodo | Char | — |
| `x_studio_tipo_de_servicio` | Tipo de servicio | Char | `express` |
| `x_studio_cp_de_origen` | CP de origen | Char | `37000` |
| `x_studio_url_base_api` | URL base API | Char | `https://apiqav2.enviatodo.mx/index.php/` |
| `x_studio_largo_cm_1` | Largo (cm) | Float | `44` |
| `x_studio_ancho_cm_1` | Ancho (cm) | Float | `11` |
| `x_studio_alto_cm_1` | Alto (cm) | Float | `33` |
| `x_studio_peso_kg` | Peso (kg) | Float | `1.9` |

### stock.picking (estándar Odoo)

| Campo | Descripción |
|---|---|
| `carrier_tracking_ref` | Número de rastreo |
| `carrier_price` | Costo del envío |

---

## Apéndice B — Historial

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0.0 | Marzo 2026 | Versión inicial |
| 2.0.0 | Marzo 2026 | Reescritura Parte A sandbox-safe, nombres `x_studio_*` |
| 3.0.0 | Marzo 2026 | Eliminado n8n como dependencia. Scripts Python puros. Documentación honesta de limitaciones del sandbox. |

---

*Custer Boots — León, Guanajuato, México*  
*Módulo: `delivery_enviatodo_custer` v19.0.1.0.0*
