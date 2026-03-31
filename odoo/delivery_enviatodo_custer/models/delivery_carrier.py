# -*- coding: utf-8 -*-
"""
EnviaTodo Shipping Integration for Custer Boots
================================================
Integración con la API de EnviaTodo.com para cotización,
generación y seguimiento de guías de envío.

Empresa: Custer Boots — León, GTO, CP 37000
Producto: Caja 44×11×33 cm, 1.9 kg
API Base: https://apiqav2.enviatodo.mx/index.php/
"""

import base64
import json
import logging
import re

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes del módulo
# ---------------------------------------------------------------------------

ENVIATODO_TRACKING_URL = "https://app.enviatodo.com/#Tracking"

# Dimensiones predeterminadas de la caja Custer Boots
ENVIATODO_DEFAULT_DIMENSIONS = {
    "length": 44,  # cm — largo
    "width": 11,  # cm — ancho
    "height": 33,  # cm — alto
    "weight": 1.9,  # kg
}

# CP de origen: León, Guanajuato
ENVIATODO_DEFAULT_ORIGIN_ZIP = "37000"

# Tiempo de espera máximo para llamadas a la API (segundos)
ENVIATODO_REQUEST_TIMEOUT = 30

# Patrón de validación para códigos postales mexicanos
MX_ZIP_PATTERN = re.compile(r"^\d{5}$")


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # ------------------------------------------------------------------
    # Campo de selección — agrega 'enviatodo' a los tipos existentes
    # ------------------------------------------------------------------
    delivery_type = fields.Selection(
        selection_add=[("enviatodo", "EnviaTodo")],
        ondelete={"enviatodo": "set default"},
    )

    # ------------------------------------------------------------------
    # Credenciales de la API
    # ------------------------------------------------------------------
    x_studio_api_key_enviatodo = fields.Char(
        string="API Key EnviaTodo",
        help="Clave de API proporcionada por EnviaTodo. "
        "Contactar a soporte@enviatodo.com para obtenerla.",
    )
    x_studio_usuario_enviatodo = fields.Char(
        string="Usuario EnviaTodo",
        help="Identificador de usuario o cuenta en la plataforma EnviaTodo.",
    )

    # ------------------------------------------------------------------
    # Configuración del servicio
    # ------------------------------------------------------------------
    x_studio_tipo_de_servicio = fields.Char(
        string="Tipo de servicio",
        default="express",
        help="Código del tipo de servicio en EnviaTodo (ej. 'express', 'standard', 'economy'). "
        "Consultar con EnviaTodo los códigos disponibles para tu cuenta.",
    )
    x_studio_url_base_api = fields.Char(
        string="URL base API",
        default="https://apiqav2.enviatodo.mx/index.php/",
        help="URL base de la API de EnviaTodo. No modificar salvo indicación expresa.",
    )

    # ------------------------------------------------------------------
    # Dimensiones predeterminadas del paquete
    # ------------------------------------------------------------------
    x_studio_largo_cm_1 = fields.Float(
        string="Largo (cm)",
        default=ENVIATODO_DEFAULT_DIMENSIONS["length"],
        help="Largo de la caja en centímetros. Predeterminado: 44 cm.",
    )
    x_studio_ancho_cm_1 = fields.Float(
        string="Ancho (cm)",
        default=ENVIATODO_DEFAULT_DIMENSIONS["width"],
        help="Ancho de la caja en centímetros. Predeterminado: 11 cm.",
    )
    x_studio_alto_cm_1 = fields.Float(
        string="Alto (cm)",
        default=ENVIATODO_DEFAULT_DIMENSIONS["height"],
        help="Alto de la caja en centímetros. Predeterminado: 33 cm.",
    )
    x_studio_peso_kg = fields.Float(
        string="Peso (kg)",
        default=ENVIATODO_DEFAULT_DIMENSIONS["weight"],
        help="Peso del paquete en kilogramos. Predeterminado: 1.9 kg.",
    )

    # ------------------------------------------------------------------
    # Datos de origen
    # ------------------------------------------------------------------
    x_studio_cp_de_origen = fields.Char(
        string="CP de origen",
        default=ENVIATODO_DEFAULT_ORIGIN_ZIP,
        help="Código postal de origen del envío. Custer Boots: León, GTO — CP 37000.",
    )

    # ==================================================================
    # MÉTODOS PRIVADOS / HELPERS
    # ==================================================================

    def _enviatodo_check_credentials(self):
        """Verifica que las credenciales de la API estén configuradas.

        Raises:
            UserError: Si falta la API Key, el ID de usuario o la URL base.
        """
        self.ensure_one()
        if not self.x_studio_api_key_enviatodo:
            raise UserError(
                _(
                    "EnviaTodo: Falta la API Key. "
                    "Configúrela en el transportista → pestaña EnviaTodo → Credenciales."
                )
            )
        if not self.x_studio_usuario_enviatodo:
            raise UserError(
                _(
                    "EnviaTodo: Falta el ID de usuario/cuenta. "
                    "Configúrelo en el transportista → pestaña EnviaTodo → Credenciales."
                )
            )
        if not self.x_studio_url_base_api:
            raise UserError(_("EnviaTodo: La URL base de la API no está configurada."))

    def _enviatodo_request(self, endpoint, payload):
        """Realiza una petición POST a la API de EnviaTodo.

        Args:
            endpoint (str): Nombre del endpoint relativo a la URL base
                            (ej. 'cotizar', 'generar', 'cancelar', 'rastreo').
            payload (dict): Datos a enviar en el cuerpo de la petición (JSON).

        Returns:
            dict: Respuesta JSON de la API.

        Raises:
            UserError: En caso de error de conexión, timeout o respuesta inválida.
        """
        self.ensure_one()
        self._enviatodo_check_credentials()

        base_url = self.x_studio_url_base_api.rstrip("/")
        url = f"{base_url}/{endpoint.lstrip('/')}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.x_studio_api_key_enviatodo}",
            "X-User-Id": str(self.x_studio_usuario_enviatodo),
        }

        _logger.info(
            "EnviaTodo → %s | Payload: %s",
            url,
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=ENVIATODO_REQUEST_TIMEOUT,
            )
        except Timeout:
            raise UserError(
                _(
                    "EnviaTodo: La petición a %s excedió el tiempo de espera (%s s). "
                    "Verifique su conexión a internet e intente de nuevo."
                )
                % (url, ENVIATODO_REQUEST_TIMEOUT)
            )
        except ConnectionError as exc:
            raise UserError(
                _("EnviaTodo: No se pudo conectar con la API (%s). Detalle: %s")
                % (url, str(exc))
            )
        except RequestException as exc:
            raise UserError(
                _("EnviaTodo: Error inesperado en la petición HTTP. Detalle: %s")
                % str(exc)
            )

        _logger.info(
            "EnviaTodo ← %s | Status: %s | Body: %s",
            url,
            response.status_code,
            response.text[:2000],  # limitar log a 2000 chars
        )

        if response.status_code == 401:
            raise UserError(
                _(
                    "EnviaTodo: Credenciales inválidas (HTTP 401). "
                    "Verifique su API Key y ID de usuario."
                )
            )
        if response.status_code == 403:
            raise UserError(
                _(
                    "EnviaTodo: Acceso denegado (HTTP 403). "
                    "Su cuenta no tiene permisos para este endpoint."
                )
            )
        if response.status_code == 404:
            raise UserError(
                _(
                    "EnviaTodo: Endpoint no encontrado (HTTP 404): %s. "
                    "Verifique la URL base de la API."
                )
                % url
            )
        if response.status_code >= 500:
            raise UserError(
                _(
                    "EnviaTodo: Error interno del servidor (HTTP %s). "
                    "Intente más tarde o contacte a soporte de EnviaTodo."
                )
                % response.status_code
            )

        try:
            result = response.json()
        except ValueError:
            raise UserError(
                _(
                    "EnviaTodo: La respuesta de la API no es JSON válido. "
                    "Respuesta recibida: %s"
                )
                % response.text[:500]
            )

        if response.status_code not in (200, 201):
            error_msg = result.get("message") or result.get("error") or str(result)
            raise UserError(
                _("EnviaTodo: Error en la respuesta (HTTP %s): %s")
                % (response.status_code, error_msg)
            )

        return result

    def _enviatodo_validate_zip(self, zip_code, label="CP"):
        """Valida que un código postal sea de 5 dígitos (formato mexicano).

        Args:
            zip_code (str): Código postal a validar.
            label (str): Etiqueta para el mensaje de error.

        Raises:
            UserError: Si el CP no tiene exactamente 5 dígitos.
        """
        if not zip_code or not MX_ZIP_PATTERN.match(str(zip_code).strip()):
            raise UserError(
                _(
                    "EnviaTodo: El %s '%s' no es válido. "
                    "Debe ser un número de exactamente 5 dígitos (ej. 37000)."
                )
                % (label, zip_code)
            )

    def _enviatodo_get_origin_zip(self):
        """Obtiene y valida el CP de origen configurado en el transportista.

        Returns:
            str: Código postal de origen (5 dígitos).
        """
        self.ensure_one()
        origin_zip = (self.x_studio_cp_de_origen or ENVIATODO_DEFAULT_ORIGIN_ZIP).strip()
        self._enviatodo_validate_zip(origin_zip, "CP de origen")
        return origin_zip

    def _enviatodo_get_destination_zip(self, partner):
        """Obtiene y valida el CP de destino del cliente.

        Args:
            partner (res.partner): Contacto de entrega.

        Returns:
            str: Código postal de destino (5 dígitos).

        Raises:
            UserError: Si el cliente no tiene CP configurado o es inválido.
        """
        if not partner:
            raise UserError(
                _("EnviaTodo: No se encontró la dirección de entrega del cliente.")
            )
        dest_zip = (partner.zip or "").strip()
        if not dest_zip:
            raise UserError(
                _(
                    "EnviaTodo: El cliente '%s' no tiene código postal configurado. "
                    "Agréguelo en el contacto antes de cotizar el envío."
                )
                % partner.name
            )
        self._enviatodo_validate_zip(dest_zip, "CP de destino")
        return dest_zip

    def _enviatodo_get_package_dimensions(self, record):
        """Obtiene las dimensiones del paquete.

        Usa las dimensiones configuradas en el transportista como predeterminadas.
        Si el registro tiene información de peso real (stock.picking), lo usa.

        Args:
            record: sale.order o stock.picking

        Returns:
            dict: Diccionario con keys: length, width, height, weight.
        """
        self.ensure_one()

        length = self.x_studio_largo_cm_1 or ENVIATODO_DEFAULT_DIMENSIONS["length"]
        width = self.x_studio_ancho_cm_1 or ENVIATODO_DEFAULT_DIMENSIONS["width"]
        height = self.x_studio_alto_cm_1 or ENVIATODO_DEFAULT_DIMENSIONS["height"]
        weight = self.x_studio_peso_kg or ENVIATODO_DEFAULT_DIMENSIONS["weight"]

        # Si es un stock.picking, intentar obtener el peso real de los movimientos
        if hasattr(record, "move_ids") and record.move_ids:
            try:
                total_weight = sum(
                    (move.product_id.weight or 0.0) * move.product_qty
                    for move in record.move_ids
                    if move.product_id
                )
                if total_weight > 0:
                    weight = total_weight
                    _logger.info(
                        "EnviaTodo: Peso calculado desde movimientos: %.3f kg", weight
                    )
            except Exception as exc:
                _logger.warning(
                    "EnviaTodo: No se pudo calcular el peso desde movimientos: %s", exc
                )

        dimensions = {
            "length": round(length, 2),
            "width": round(width, 2),
            "height": round(height, 2),
            "weight": round(weight, 3),
        }

        _logger.info("EnviaTodo: Dimensiones del paquete: %s", dimensions)
        return dimensions

    def _enviatodo_build_rate_payload(self, order):
        """Construye el payload para la cotización de envío.

        Args:
            order (sale.order): Orden de venta.

        Returns:
            dict: Payload listo para enviar al endpoint de cotización.
        """
        self.ensure_one()
        partner = order.partner_shipping_id or order.partner_id
        dest_zip = self._enviatodo_get_destination_zip(partner)
        origin_zip = self._enviatodo_get_origin_zip()
        dims = self._enviatodo_get_package_dimensions(order)

        payload = {
            "api_key": self.x_studio_api_key_enviatodo,
            "user_id": self.x_studio_usuario_enviatodo,
            "origen": {
                "cp": origin_zip,
            },
            "destino": {
                "cp": dest_zip,
            },
            "paquete": {
                "largo": dims["length"],
                "ancho": dims["width"],
                "alto": dims["height"],
                "peso": dims["weight"],
            },
            "servicio": self.x_studio_tipo_de_servicio or "express",
        }
        return payload

    def _enviatodo_build_shipment_payload(self, picking):
        """Construye el payload para la generación de guía.

        Args:
            picking (stock.picking): Transferencia de inventario.

        Returns:
            dict: Payload listo para enviar al endpoint de generación.
        """
        self.ensure_one()
        partner = picking.partner_id
        if not partner:
            raise UserError(
                _("EnviaTodo: La transferencia '%s' no tiene destinatario asignado.")
                % picking.name
            )

        dest_zip = self._enviatodo_get_destination_zip(partner)
        origin_zip = self._enviatodo_get_origin_zip()
        dims = self._enviatodo_get_package_dimensions(picking)

        # Datos del destinatario
        recipient_name = partner.name or "Sin nombre"
        recipient_phone = partner.phone or partner.mobile or ""
        recipient_email = partner.email or ""
        recipient_street = (
            " ".join(filter(None, [partner.street, partner.street2])) or "Sin dirección"
        )
        recipient_city = partner.city or ""
        recipient_state = partner.state_id.name if partner.state_id else ""

        payload = {
            "api_key": self.x_studio_api_key_enviatodo,
            "user_id": self.x_studio_usuario_enviatodo,
            "referencia": picking.name,
            "origen": {
                "cp": origin_zip,
                "nombre": "Custer Boots",
                "telefono": "",
                "calle": "León, Guanajuato",
                "ciudad": "León",
                "estado": "Guanajuato",
            },
            "destino": {
                "cp": dest_zip,
                "nombre": recipient_name,
                "telefono": recipient_phone,
                "email": recipient_email,
                "calle": recipient_street,
                "ciudad": recipient_city,
                "estado": recipient_state,
            },
            "paquete": {
                "largo": dims["length"],
                "ancho": dims["width"],
                "alto": dims["height"],
                "peso": dims["weight"],
                "descripcion": "Calzado / Botas",
                "valor_declarado": 0,
            },
            "servicio": self.x_studio_tipo_de_servicio or "express",
        }
        return payload

    # ==================================================================
    # MÉTODOS PÚBLICOS — API de Odoo para transportistas
    # ==================================================================

    def enviatodo_rate_shipment(self, order):
        """Cotiza el costo de envío para una orden de venta.

        Este método es llamado automáticamente por Odoo cuando el usuario
        solicita una cotización de envío en la orden de venta.

        Args:
            order (sale.order): Orden de venta a cotizar.

        Returns:
            dict: Resultado con keys:
                - success (bool)
                - price (float) — costo en MXN
                - error_message (str) — mensaje de error si success=False
                - warning_message (str) — advertencia opcional
        """
        self.ensure_one()
        _logger.info("EnviaTodo: Iniciando cotización para orden %s", order.name)

        try:
            payload = self._enviatodo_build_rate_payload(order)
            result = self._enviatodo_request("cotizar", payload)
        except UserError as exc:
            _logger.warning("EnviaTodo: Error al cotizar: %s", exc.args[0])
            return {
                "success": False,
                "price": 0.0,
                "error_message": exc.args[0],
                "warning_message": False,
            }
        except Exception as exc:
            _logger.exception("EnviaTodo: Error inesperado al cotizar")
            return {
                "success": False,
                "price": 0.0,
                "error_message": _("EnviaTodo: Error inesperado: %s") % str(exc),
                "warning_message": False,
            }

        # Extraer el precio de la respuesta
        # Estructura esperada: {"precio": 150.00, "moneda": "MXN", ...}
        # o {"costo": 150.00, ...} — ajustar según respuesta real de la API
        price = (
            result.get("precio")
            or result.get("costo")
            or result.get("price")
            or result.get("total")
            or 0.0
        )

        try:
            price = float(price)
        except (TypeError, ValueError):
            _logger.warning(
                "EnviaTodo: No se pudo convertir el precio '%s' a float. "
                "Respuesta completa: %s",
                price,
                result,
            )
            return {
                "success": False,
                "price": 0.0,
                "error_message": _(
                    "EnviaTodo: La respuesta de la API no contiene un precio válido. "
                    "Respuesta: %s"
                )
                % str(result),
                "warning_message": False,
            }

        _logger.info(
            "EnviaTodo: Cotización exitosa para %s — Precio: %.2f MXN",
            order.name,
            price,
        )

        return {
            "success": True,
            "price": price,
            "error_message": False,
            "warning_message": False,
        }

    def enviatodo_send_shipping(self, pickings):
        """Genera guías de envío para las transferencias indicadas.

        Este método es llamado automáticamente por Odoo al validar
        una transferencia de salida.

        Args:
            pickings (stock.picking recordset): Transferencias a procesar.

        Returns:
            list[dict]: Lista de resultados, uno por picking, con keys:
                - exact_price (float)
                - tracking_number (str)
        """
        results = []

        for picking in pickings:
            _logger.info(
                "EnviaTodo: Generando guía para transferencia %s", picking.name
            )

            try:
                payload = self._enviatodo_build_shipment_payload(picking)
                result = self._enviatodo_request("generar", payload)
            except UserError as exc:
                raise UserError(
                    _("EnviaTodo: No se pudo generar la guía para '%s'.\n%s")
                    % (picking.name, exc.args[0])
                )

            # Extraer número de rastreo
            # Estructura esperada: {"tracking": "ABC123", "guia": "...", "etiqueta": "..."}
            tracking_number = (
                result.get("tracking")
                or result.get("numero_guia")
                or result.get("guia")
                or result.get("tracking_number")
                or ""
            )

            if not tracking_number:
                _logger.warning(
                    "EnviaTodo: La respuesta no contiene número de rastreo. "
                    "Respuesta: %s",
                    result,
                )
                raise UserError(
                    _(
                        "EnviaTodo: La guía fue generada pero la API no devolvió "
                        "número de rastreo. Respuesta: %s"
                    )
                    % str(result)
                )

            # Extraer precio real del envío
            exact_price = float(
                result.get("precio")
                or result.get("costo")
                or result.get("price")
                or result.get("total")
                or 0.0
            )

            # Adjuntar etiqueta PDF si la API la devuelve
            self._enviatodo_attach_label(picking, result, tracking_number)

            _logger.info(
                "EnviaTodo: Guía generada para %s — Tracking: %s — Precio: %.2f MXN",
                picking.name,
                tracking_number,
                exact_price,
            )

            results.append(
                {
                    "exact_price": exact_price,
                    "tracking_number": tracking_number,
                }
            )

        return results

    def _enviatodo_attach_label(self, picking, api_result, tracking_number):
        """Adjunta la etiqueta de envío al picking como adjunto en Odoo.

        Maneja tanto respuestas con URL de PDF como con PDF en base64.

        Args:
            picking (stock.picking): Transferencia.
            api_result (dict): Respuesta completa de la API.
            tracking_number (str): Número de rastreo.
        """
        label_data = None
        label_name = f"Guia_EnviaTodo_{tracking_number}.pdf"

        # Caso 1: La API devuelve el PDF en base64
        label_b64 = (
            api_result.get("etiqueta_base64")
            or api_result.get("label_base64")
            or api_result.get("pdf_base64")
            or api_result.get("etiqueta")
        )
        if label_b64:
            try:
                # Verificar si ya es base64 o si es bytes
                if isinstance(label_b64, str):
                    label_data = label_b64.encode("utf-8")
                else:
                    label_data = label_b64
                _logger.info(
                    "EnviaTodo: Etiqueta recibida en base64 para %s", picking.name
                )
            except Exception as exc:
                _logger.warning("EnviaTodo: Error al procesar etiqueta base64: %s", exc)

        # Caso 2: La API devuelve una URL para descargar el PDF
        if not label_data:
            label_url = (
                api_result.get("url_etiqueta")
                or api_result.get("label_url")
                or api_result.get("pdf_url")
                or api_result.get("etiqueta_url")
            )
            if label_url:
                try:
                    _logger.info(
                        "EnviaTodo: Descargando etiqueta desde URL: %s", label_url
                    )
                    resp = requests.get(label_url, timeout=ENVIATODO_REQUEST_TIMEOUT)
                    if resp.status_code == 200:
                        label_data = base64.b64encode(resp.content).decode("utf-8")
                        _logger.info(
                            "EnviaTodo: Etiqueta descargada exitosamente para %s",
                            picking.name,
                        )
                    else:
                        _logger.warning(
                            "EnviaTodo: No se pudo descargar la etiqueta (HTTP %s): %s",
                            resp.status_code,
                            label_url,
                        )
                except Exception as exc:
                    _logger.warning(
                        "EnviaTodo: Error al descargar etiqueta desde URL: %s", exc
                    )

        if label_data:
            try:
                self.env["ir.attachment"].create(
                    {
                        "name": label_name,
                        "type": "binary",
                        "datas": label_data,
                        "res_model": "stock.picking",
                        "res_id": picking.id,
                        "mimetype": "application/pdf",
                    }
                )
                _logger.info(
                    "EnviaTodo: Etiqueta adjuntada al picking %s", picking.name
                )
            except Exception as exc:
                _logger.warning(
                    "EnviaTodo: No se pudo adjuntar la etiqueta al picking: %s", exc
                )
        else:
            _logger.info(
                "EnviaTodo: La API no devolvió etiqueta para %s. "
                "Descárguela manualmente desde el portal de EnviaTodo.",
                picking.name,
            )

    def enviatodo_get_tracking_link(self, picking):
        """Devuelve el enlace de rastreo para un picking.

        Args:
            picking (stock.picking): Transferencia con número de rastreo.

        Returns:
            str: URL de rastreo.
        """
        tracking = picking.carrier_tracking_ref or ""
        if tracking:
            return f"{ENVIATODO_TRACKING_URL}?guia={tracking}"
        return ENVIATODO_TRACKING_URL

    def enviatodo_cancel_shipment(self, pickings):
        """Cancela las guías de envío generadas.

        Args:
            pickings (stock.picking recordset): Transferencias a cancelar.

        Raises:
            UserError: Si la API rechaza la cancelación.
        """
        for picking in pickings:
            tracking = picking.carrier_tracking_ref
            if not tracking:
                _logger.warning(
                    "EnviaTodo: El picking %s no tiene número de rastreo, "
                    "no se puede cancelar.",
                    picking.name,
                )
                continue

            _logger.info(
                "EnviaTodo: Cancelando guía %s para picking %s",
                tracking,
                picking.name,
            )

            payload = {
                "api_key": self.x_studio_api_key_enviatodo,
                "user_id": self.x_studio_usuario_enviatodo,
                "tracking": tracking,
                "referencia": picking.name,
            }

            try:
                result = self._enviatodo_request("cancelar", payload)
                _logger.info(
                    "EnviaTodo: Guía %s cancelada exitosamente. Respuesta: %s",
                    tracking,
                    result,
                )
            except UserError as exc:
                raise UserError(
                    _(
                        "EnviaTodo: No se pudo cancelar la guía '%s' del picking '%s'.\n%s"
                    )
                    % (tracking, picking.name, exc.args[0])
                )

    # ==================================================================
    # MÉTODO DE PRUEBA DE CONEXIÓN
    # ==================================================================

    def action_enviatodo_test_connection(self):
        """Prueba la conexión con la API de EnviaTodo.

        Muestra un mensaje de éxito o error al usuario.
        Puede ser llamado desde un botón en la vista del transportista.
        """
        self.ensure_one()
        _logger.info("EnviaTodo: Probando conexión con la API...")

        try:
            self._enviatodo_check_credentials()
        except UserError as exc:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("EnviaTodo — Error de configuración"),
                    "message": exc.args[0],
                    "type": "danger",
                    "sticky": True,
                },
            }

        # Intentar una cotización de prueba con CP ficticios
        test_payload = {
            "api_key": self.x_studio_api_key_enviatodo,
            "user_id": self.x_studio_usuario_enviatodo,
            "origen": {"cp": self.x_studio_cp_de_origen or ENVIATODO_DEFAULT_ORIGIN_ZIP},
            "destino": {"cp": "06600"},  # CP de prueba: CDMX
            "paquete": {
                "largo": ENVIATODO_DEFAULT_DIMENSIONS["length"],
                "ancho": ENVIATODO_DEFAULT_DIMENSIONS["width"],
                "alto": ENVIATODO_DEFAULT_DIMENSIONS["height"],
                "peso": ENVIATODO_DEFAULT_DIMENSIONS["weight"],
            },
            "servicio": self.x_studio_tipo_de_servicio or "express",
        }

        try:
            result = self._enviatodo_request("cotizar", test_payload)
            _logger.info("EnviaTodo: Prueba de conexión exitosa. Respuesta: %s", result)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("EnviaTodo — Conexión exitosa"),
                    "message": _(
                        "La API de EnviaTodo respondió correctamente. Respuesta: %s"
                    )
                    % str(result)[:200],
                    "type": "success",
                    "sticky": False,
                },
            }
        except UserError as exc:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("EnviaTodo — Error de conexión"),
                    "message": exc.args[0],
                    "type": "danger",
                    "sticky": True,
                },
            }
