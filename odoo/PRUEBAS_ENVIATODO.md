# Pruebas: Scripts EnviaTodo en Odoo 19

Guía paso a paso para verificar que los scripts funcionan **antes** de conectar con la API real.

---

## Fase 0 — Preparar datos de prueba (5 min)

### 0.1 Crear el transportista

1. **Inventario → Configuración → Métodos de envío → Nuevo**
2. Nombre: `EnviaTodo Pruebas`
3. Guardar

### 0.2 Crear los campos con Studio

1. Abre el transportista que acabas de crear
2. Activa Studio (ícono de lápiz arriba a la derecha)
3. Crea los 9 campos exactamente como dice la tabla de la guía (sección A.2)
4. Llena los valores:

| Campo | Valor de prueba |
|---|---|
| API Key EnviaTodo | `test_key_123` |
| Usuario EnviaTodo | `test_user_456` |
| Tipo de servicio | `express` |
| CP de origen | `37000` |
| URL base API | `https://apiqav2.enviatodo.mx/index.php/` |
| Largo (cm) | `44` |
| Ancho (cm) | `11` |
| Alto (cm) | `33` |
| Peso (kg) | `1.9` |

5. Guardar

### 0.3 Crear un cliente de prueba

1. **Contactos → Nuevo**
2. Nombre: `Cliente Prueba EnviaTodo`
3. Dirección:
   - Calle: `Av. Insurgentes Sur 456`
   - Ciudad: `Ciudad de México`
   - Estado: `Ciudad de México`
   - **CP: `06600`** ← importante, 5 dígitos
   - País: México
4. Teléfono: `5512345678`
5. Email: `prueba@ejemplo.com`
6. Guardar

### 0.4 Crear un producto de prueba

1. **Inventario → Productos → Nuevo**
2. Nombre: `Bota Custer Test`
3. Pestaña Inventario → Peso: `1.9` kg
4. Guardar

---

## Fase 1 — Probar el script mínimo (10 min)

Antes de pegar el script completo, prueba uno mínimo para confirmar que el sandbox funciona.

### 1.1 Crear la regla automatizada de prueba

1. Activa **modo desarrollador**: Configuración → Activar modo desarrollador
2. Ve a **Configuración → Técnico → Automatización → Reglas Automatizadas**
3. Clic en **Nuevo**

| Campo | Valor |
|---|---|
| Nombre | `TEST: Sandbox EnviaTodo` |
| Modelo | `Transferencia (stock.picking)` |
| Disparador | `Al crear y editar` |
| Antes de actualizar dominio | `[("state", "!=", "done")]` |
| Aplicar en | `[("state", "=", "done")]` |

4. En Acciones, agrega una acción → **Ejecutar código Python**

### 1.2 Script mínimo de prueba

Pega este código y guarda:

```python
# TEST 1: ¿El sandbox ejecuta código?
log("TEST EnviaTodo: El sandbox funciona correctamente")

# TEST 2: ¿json está disponible sin import?
test_dict = {"prueba": True, "numero": 42}
test_json = json.dumps(test_dict)
log("TEST EnviaTodo: json.dumps funciona — resultado: %s" % test_json)

# TEST 3: ¿Puedo leer el record?
for picking in records:
    log("TEST EnviaTodo: Picking detectado — %s (estado: %s)" % (picking.name, picking.state))
    if picking.partner_id:
        log("TEST EnviaTodo: Cliente — %s (CP: %s)" % (picking.partner_id.name, picking.partner_id.zip or 'SIN CP'))
    else:
        log("TEST EnviaTodo: Sin cliente asignado")

# TEST 4: ¿Puedo buscar el carrier?
carrier = env['delivery.carrier'].search([
    ('name', 'ilike', 'EnviaTodo'),
], limit=1)
if carrier:
    log("TEST EnviaTodo: Carrier encontrado — %s (id: %s)" % (carrier.name, carrier.id))
    log("TEST EnviaTodo: API Key configurada — %s" % ('SÍ' if carrier.x_studio_api_key_enviatodo else 'NO'))
    log("TEST EnviaTodo: CP origen — %s" % (carrier.x_studio_cp_de_origen or 'NO CONFIGURADO'))
else:
    log("TEST EnviaTodo: No se encontró carrier con nombre 'EnviaTodo'", level="warning")

# TEST 5: ¿Puedo publicar una nota?
for picking in records:
    picking.message_post(
        body="<b>🧪 TEST EnviaTodo:</b> Si ves este mensaje, el script funciona correctamente.",
        message_type='comment',
        subtype_xmlid='mail.mt_note',
    )
    log("TEST EnviaTodo: Nota publicada en %s" % picking.name)
```

### 1.3 Disparar la prueba

1. **Inventario → Operaciones → Recepciones** (o crea una transferencia de salida)
2. Crea una orden de venta con el cliente de prueba y confírmala
3. Ve al picking de salida generado
4. Valida el picking (botón **Validar**)
5. Esto cambia `state` a `done` y dispara la regla

### 1.4 Verificar resultados

**Lugar 1 — Notas del picking:**
- Abre el picking que acabas de validar
- En el chatter (abajo), busca el mensaje:
  > 🧪 TEST EnviaTodo: Si ves este mensaje, el script funciona correctamente.
- ✅ Si lo ves → el script se ejecutó
- ❌ Si no lo ves → revisa los logs

**Lugar 2 — Logs del servidor:**
- Ve a **Configuración → Técnico → Logging** (o **Configuración → Técnico → Registros del servidor**)
- Filtra por `TEST EnviaTodo`
- Deberías ver algo como:

```
INFO  TEST EnviaTodo: El sandbox funciona correctamente
INFO  TEST EnviaTodo: json.dumps funciona — resultado: {"prueba": true, "numero": 42}
INFO  TEST EnviaTodo: Picking detectado — WH/OUT/00001 (estado: done)
INFO  TEST EnviaTodo: Cliente — Cliente Prueba EnviaTodo (CP: 06600)
INFO  TEST EnviaTodo: Carrier encontrado — EnviaTodo Pruebas (id: 5)
INFO  TEST EnviaTodo: API Key configurada — SÍ
INFO  TEST EnviaTodo: CP origen — 37000
INFO  TEST EnviaTodo: Nota publicada en WH/OUT/00001
```

### 1.5 Solución de errores comunes

| Error | Causa | Solución |
|---|---|---|
| `ValueError: forbidden opcode(s) ... IMPORT_NAME` | Hay un `import` en el código | Eliminar toda línea `import` |
| `SyntaxError: 'return' outside function` | Hay un `return` suelto | Usar `if/else` en vez de `return` |
| `ValueError: forbidden opcode(s) ... STORE_ATTR` | Hay `record.campo = valor` | Usar `record.write({'campo': valor})` |
| No aparece nada en logs ni en notas | La regla no se disparó | Verificar disparador y dominios |
| `KeyError: 'x_studio_api_key_enviatodo'` | El campo no existe en el carrier | Crearlo con Studio primero |

---

## Fase 2 — Probar el script completo de generación (10 min)

### 2.1 Reemplazar el código de prueba

1. Abre la regla `TEST: Sandbox EnviaTodo`
2. Reemplaza el código por el script completo de la sección **A.4** de la guía
3. Guardar

### 2.2 Crear un nuevo picking de prueba

1. Crea una nueva orden de venta:
   - Cliente: `Cliente Prueba EnviaTodo` (el que tiene CP 06600)
   - Producto: `Bota Custer Test`
   - Cantidad: 2
2. Confirma la orden
3. Ve al picking de salida generado
4. Valida el picking

### 2.3 Verificar el payload generado

Abre el picking y busca en el chatter una nota como esta:

```
📦 EnviaTodo — Guía solicitada
Destino: Cliente Prueba EnviaTodo (CP 06600)
Peso: 3.800 kg
Referencia: WH/OUT/00002
URL: https://apiqav2.enviatodo.mx/index.php/generar

📋 Payload JSON (clic para expandir)
▼
{
  "api_key": "test_key_123",
  "user_id": "test_user_456",
  "referencia": "WH/OUT/00002",
  "origen": {
    "cp": "37000",
    "nombre": "Custer Boots",
    ...
  },
  "destino": {
    "cp": "06600",
    "nombre": "Cliente Prueba EnviaTodo",
    "telefono": "5512345678",
    ...
  },
  "paquete": {
    "largo": 44,
    "ancho": 11,
    "alto": 33,
    "peso": 3.8,
    ...
  },
  "servicio": "express"
}
```

### 2.4 Qué verificar en el payload

| Verificación | Esperado | Si falla |
|---|---|---|
| `api_key` | `test_key_123` | El campo del carrier no se leyó |
| `origen.cp` | `37000` | Revisar `x_studio_cp_de_origen` |
| `destino.cp` | `06600` | El cliente no tiene CP |
| `destino.nombre` | `Cliente Prueba EnviaTodo` | El picking no tiene partner |
| `destino.telefono` | `5512345678` | El contacto no tiene teléfono |
| `paquete.peso` | `3.800` (2 × 1.9) | El producto no tiene peso configurado |
| `paquete.largo` | `44` | Revisar `x_studio_largo_cm_1` |
| `servicio` | `express` | Revisar `x_studio_tipo_de_servicio` |

---

## Fase 3 — Probar con la API real (10 min)

Una vez que el payload se genera correctamente, pruébalo contra la API real.

### 3.1 Copiar el payload del chatter

1. Abre el picking
2. En la nota del chatter, expande "Payload JSON"
3. Copia todo el JSON

### 3.2 Probar con cURL

Abre una terminal y ejecuta:

```bash
curl -X POST "https://apiqav2.enviatodo.mx/index.php/cotizar" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_API_KEY_REAL" \
  -d 'PEGA_EL_JSON_AQUÍ'
```

> **Importante:** Reemplaza `test_key_123` por tu API Key real de EnviaTodo.

### 3.3 Interpretar la respuesta

**Si funciona (HTTP 200):**
```json
{
  "status": "success",
  "precio": 185.50,
  "moneda": "MXN"
}
```
→ ✅ El payload es correcto. La integración funciona.

**Si falla (HTTP 401):**
```json
{
  "status": "error",
  "message": "Credenciales inválidas"
}
```
→ Verifica tu API Key y User ID con EnviaTodo.

**Si falla (HTTP 422):**
```json
{
  "status": "error",
  "message": "CP de destino inválido"
}
```
→ El formato del payload no es el que espera la API. Ajusta los nombres de los campos.

---

## Fase 4 — Probar casos límite (10 min)

### 4.1 Cliente sin CP

1. Crea un contacto **sin código postal**
2. Crea una orden de venta con ese contacto
3. Confirma y valida el picking
4. **Esperado:** Nota de advertencia en el chatter:
   > ⚠️ EnviaTodo: El cliente **Nombre** no tiene CP válido (5 dígitos). CP actual: ''.

### 4.2 Cliente con CP inválido

1. Edita un contacto y pon CP: `123` (solo 3 dígitos)
2. Repite el flujo
3. **Esperado:** Misma advertencia con CP actual: '123'

### 4.3 Picking que ya tiene guía

1. Abre un picking validado
2. Manualmente escribe algo en el campo `carrier_tracking_ref` (número de rastreo)
3. Vuelve a disparar la regla (edita y guarda el picking)
4. **Esperado:** Log que dice "ya tiene guía: XXX — omitido"

### 4.4 Sin transportista EnviaTodo

1. Archiva (desactiva) el transportista `EnviaTodo Pruebas`
2. Valida un nuevo picking
3. **Esperado:** Log warning "No se encontró transportista activo"
4. Reactiva el transportista después de la prueba

### 4.5 Sin credenciales

1. Borra el valor de `API Key EnviaTodo` en el transportista
2. Valida un nuevo picking
3. **Esperado:** Log warning "Faltan credenciales"
4. Restaura la API Key después de la prueba

---

## Fase 5 — Probar el webhook de entrada (15 min)

Esta prueba verifica que Odoo puede **recibir** la respuesta de EnviaTodo.

### 5.1 Crear la regla de webhook

1. Crea la regla de la sección **A.5** de la guía (disparador: On webhook)
2. Guarda y copia la **URL del webhook** que Odoo genera
   - Se ve en el campo URL de la regla, algo como:
   - `https://tu-odoo.com/web/hook/abc123-def456-...`

### 5.2 Simular la respuesta de EnviaTodo con cURL

Desde tu terminal, simula que EnviaTodo responde:

```bash
# Reemplaza la URL por la de tu webhook de Odoo
# Reemplaza picking_id por el ID real de un picking

curl -X POST "https://tu-odoo.com/web/hook/TU-UUID-AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "picking_id": 42,
    "tracking": "ET9999TEST001MX",
    "numero_guia": "ET9999TEST001MX",
    "precio": 185.50,
    "etiqueta_base64": ""
  }'
```

> **Nota:** Cambia `42` por el ID real de un picking. Para encontrarlo, abre el picking en Odoo y mira la URL: `.../stock.picking/42`

### 5.3 Verificar resultados

Abre el picking con ese ID y busca en el chatter:

```
✅ EnviaTodo — Guía generada
Tracking: ET9999TEST001MX
🔗 Rastrear envío
```

También verifica:
- El campo **Número de rastreo** del picking tiene `ET9999TEST001MX`
- Si enviaste `etiqueta_base64` con datos reales, hay un PDF adjunto

### 5.4 Simular respuesta sin tracking

```bash
curl -X POST "https://tu-odoo.com/web/hook/TU-UUID-AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "picking_id": 42,
    "status": "error",
    "message": "Saldo insuficiente"
  }'
```

**Esperado:** Nota de advertencia en el chatter:
> ⚠️ EnviaTodo: La API no devolvió número de rastreo.

---

## Resumen de Fases

| Fase | Qué prueba | Tiempo | Resultado esperado |
|---|---|---|---|
| 0 | Datos de prueba | 5 min | Carrier, cliente, producto creados |
| 1 | Script mínimo | 10 min | Logs y nota en chatter |
| 2 | Script completo | 10 min | Payload JSON correcto en nota |
| 3 | API real | 10 min | Respuesta exitosa de EnviaTodo |
| 4 | Casos límite | 10 min | Advertencias correctas |
| 5 | Webhook entrada | 15 min | Tracking guardado, PDF adjunto |

**Tiempo total estimado: ~1 hora**

---

## Checklist de Pruebas

- [ ] Fase 1: Script mínimo se ejecuta sin errores
- [ ] Fase 1: `json.dumps` funciona sin `import`
- [ ] Fase 1: Carrier encontrado con credenciales
- [ ] Fase 1: Nota publicada en el chatter
- [ ] Fase 2: Payload JSON completo y correcto
- [ ] Fase 2: Peso calculado desde productos (2 × 1.9 = 3.8)
- [ ] Fase 2: Datos del destinatario correctos
- [ ] Fase 3: cURL a la API real devuelve precio
- [ ] Fase 4: Cliente sin CP → advertencia
- [ ] Fase 4: CP inválido → advertencia
- [ ] Fase 4: Picking con guía → omitido
- [ ] Fase 4: Sin carrier → warning en log
- [ ] Fase 4: Sin credenciales → warning en log
- [ ] Fase 5: Webhook recibe tracking → guardado
- [ ] Fase 5: Webhook sin tracking → advertencia
