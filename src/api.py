# -*- coding: utf-8 -*-
"""Cliente de la API de EnviaTodo v2.

Rate limiting: la API permite 120 peticiones por segundo, máximo 500
por sesión. Usamos pausas entre peticiones y backoff progresivo en
reintentos para evitar respuestas vacías por throttling.
"""

import time

import requests

from src.config import (
    ALTO,
    ANCHO,
    API_HEADERS,
    BASE_URL,
    CATALOG_TIMEOUT,
    LARGO,
    MAX_REINTENTOS,
    PAUSA_ENTRE_PETICIONES,
    PAUSA_REINTENTO_BASE,
    PESO,
    PESO_FACTURADO,
    PESO_VOLUMETRICO,
    REQUEST_TIMEOUT,
)


class EnviaTodoClient:
    """Wrapper para la API de EnviaTodo v2.

    Respeta el rate limit de la API (120 req/s, máx 500) usando pausas
    entre peticiones y backoff progresivo en reintentos.
    """

    def __init__(self, token):
        self.token = token
        self.headers = {
            **API_HEADERS,
            "Authorization": "Bearer %s" % token,
        }
        self._ultima_peticion = 0.0

    def _esperar_rate_limit(self):
        """Espera el tiempo necesario para respetar el rate limit."""
        ahora = time.monotonic()
        transcurrido = ahora - self._ultima_peticion
        if transcurrido < PAUSA_ENTRE_PETICIONES:
            time.sleep(PAUSA_ENTRE_PETICIONES - transcurrido)
        self._ultima_peticion = time.monotonic()

    # ── Catálogos ─────────────────────────────────────────────

    def obtener_datos_cp(self, cp):
        """Consulta datos de un código postal.

        Returns:
            dict con suburb, municipality, state, city, state_code o None.
        """
        self._esperar_rate_limit()
        url = BASE_URL + "Api/get_zip_code/" + cp
        try:
            resp = requests.get(url, headers=self.headers, timeout=CATALOG_TIMEOUT)
            data = resp.json()
            if data.get("success") and data.get("data", {}).get("items"):
                item = data["data"]["items"][0]
                return {
                    "suburb": item.get("suburb_name", ""),
                    "municipality": item.get("municipality", ""),
                    "state": item.get("state", ""),
                    "city": item.get("city", ""),
                    "state_code": item.get("state_code", ""),
                }
        except Exception:
            pass
        return None

    def obtener_servicios(self):
        """Obtiene la lista de paqueterías y servicios disponibles.

        Returns:
            list[dict]: [{provider, provider_id, services: [{id, label, via}]}]
        """
        self._esperar_rate_limit()
        url = BASE_URL + "Api/provider_services"
        try:
            resp = requests.get(url, headers=self.headers, timeout=CATALOG_TIMEOUT)
            data = resp.json()
            if data.get("success"):
                resultado = []
                for p in data.get("data", []):
                    servicios = []
                    for s in p.get("services", []):
                        servicios.append({
                            "id": int(s["provider_service_id"]),
                            "label": s.get("label") or "%s - %s" % (
                                p["parcel"], s.get("via_transport", "")
                            ),
                            "via": s.get("via_transport", ""),
                        })
                    resultado.append({
                        "provider": p["parcel"],
                        "provider_id": p["provider_id"],
                        "services": servicios,
                    })
                return resultado
        except Exception:
            pass
        return []

    # ── Cotización ────────────────────────────────────────────

    def _cotizar_una_vez(self, cp_origen, cp_destino, datos_origen, datos_destino,
                         provider_service_id):
        """Hace una sola petición de cotización.

        Returns:
            tuple: (respuesta_dict_o_None, fue_timeout_bool)
        """
        self._esperar_rate_limit()
        url = BASE_URL + "Api/rates_client"

        payload = {
            "type": "order",
            "quotes": {
                "shipping_type": "1",
                "quantity": 1,
                "provider_service_id": provider_service_id,
                "origin": {
                    "address_type_id": "1",
                    "full_name": "Custer Boots",
                    "email": "contacto@custerboots.com",
                    "telephone": "4771234567",
                    "street": datos_origen.get("suburb", "Centro"),
                    "ext_number": "1",
                    "int_number": "",
                    "zip_code": cp_origen,
                    "suburb": datos_origen.get("suburb", "Centro"),
                    "municipality": datos_origen.get("municipality", ""),
                    "town": (
                        datos_origen.get("city", "")
                        or datos_origen.get("municipality", "")
                    ),
                    "state": datos_origen.get("state", ""),
                    "state_code": datos_origen.get("state_code", ""),
                    "country_code": "MX",
                    "reference": "-",
                    "company": "Custer Boots",
                },
                "destination": {
                    "address_type_id": "2",
                    "full_name": "Destinatario",
                    "email": "test@test.com",
                    "telephone": "0000000000",
                    "street": datos_destino.get("suburb", ""),
                    "ext_number": "1",
                    "int_number": "",
                    "zip_code": cp_destino,
                    "suburb": datos_destino.get("suburb", ""),
                    "municipality": datos_destino.get("municipality", ""),
                    "town": (
                        datos_destino.get("city", "")
                        or datos_destino.get("municipality", "")
                    ),
                    "state": datos_destino.get("state", ""),
                    "state_code": datos_destino.get("state_code", ""),
                    "country_code": "MX",
                    "reference": "-",
                    "company": "",
                },
                "package": {
                    "name": "Caja Botas Custer",
                    "product_type": "53111600",
                    "unit_type": "XBX",
                    "package_content": "Calzado",
                    "amount_pkg": "1500",
                    "height": ALTO,
                    "width": ANCHO,
                    "length": LARGO,
                    "weight": PESO,
                    "real_weight": str(PESO),
                    "volumetric_weight": str(PESO_VOLUMETRICO),
                    "bill_weight": str(PESO_FACTURADO),
                    "default_pkg": "0",
                    "product_quantity": "1",
                },
            },
        }

        try:
            resp = requests.post(
                url, json=payload, headers=self.headers, timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json(), False
            return None, False
        except requests.exceptions.Timeout:
            return None, True
        except Exception:
            return None, False

    def _extraer_resultado(self, rate, svc):
        """Extrae un dict de resultado a partir de un rate de la API."""
        cargo_base = next(
            (c for c in rate.get("charges", []) if c["type"] == "base"),
            {},
        )
        detalles = rate.get("detail_charges", [])
        zona_ext = next(
            (d["amount"] for d in detalles
             if "zona extendida" in d.get("charge_type", "").lower()
             and d.get("active")),
            0,
        )
        guia = next(
            (d["amount"] for d in detalles
             if "guía unitaria" in d.get("charge_type", "").lower()
             and d.get("active")),
            0,
        )

        return {
            "carrier": svc["provider"],
            "servicio": rate.get("service_name", svc["label"]),
            "via": rate.get("via_transport", svc.get("via", "")),
            "subtotal": cargo_base.get("sub_total", 0),
            "iva": cargo_base.get("tax", 0),
            "total": cargo_base.get("total", 0),
            "zona_ext": zona_ext,
            "guia": guia,
            "entrega": rate.get("estimated_date", "—"),
            "modo": rate.get("delivery_mode", "—"),
            "disponible": True,
        }

    def cotizar_zona(self, cp_origen, cp_destino, datos_origen, datos_destino,
                     servicios, on_progress=None):
        """Cotiza un destino con todos los servicios disponibles.

        Incluye reintentos con backoff progresivo cuando la API devuelve
        rates vacíos (posible throttling). NO reintenta en caso de timeout
        (el servicio probablemente no tiene cobertura).

        Args:
            cp_origen: CP de origen.
            cp_destino: CP de destino.
            datos_origen: dict con datos del CP origen.
            datos_destino: dict con datos del CP destino.
            servicios: list de dicts con id, label, provider.
            on_progress: callback(carrier, servicio, resultado_o_None) para log.

        Returns:
            list[dict]: Resultados por servicio.
        """
        resultados = []

        for svc in servicios:
            rates = []
            fue_timeout = False

            # Primer intento
            resp, fue_timeout = self._cotizar_una_vez(
                cp_origen, cp_destino, datos_origen, datos_destino, svc["id"],
            )

            if resp and resp.get("success"):
                rates = resp.get("data", {}).get("rates", [])

            # Reintentar SOLO si la API respondió OK pero con rates vacíos
            # (posible throttling). Backoff progresivo: 3s, 6s.
            if not rates and not fue_timeout and resp is not None:
                for intento in range(1, MAX_REINTENTOS + 1):
                    pausa = PAUSA_REINTENTO_BASE * intento
                    if on_progress:
                        on_progress(
                            svc["provider"], svc["label"],
                            "reintento %d/%d (espera %.0fs)" % (
                                intento, MAX_REINTENTOS, pausa,
                            ),
                        )
                    time.sleep(pausa)
                    resp, fue_timeout = self._cotizar_una_vez(
                        cp_origen, cp_destino, datos_origen, datos_destino,
                        svc["id"],
                    )
                    if resp and resp.get("success"):
                        rates = resp.get("data", {}).get("rates", [])
                    if rates or fue_timeout:
                        break

            if rates:
                for rate in rates:
                    resultado = self._extraer_resultado(rate, svc)
                    resultados.append(resultado)
                    if on_progress:
                        on_progress(svc["provider"], resultado["servicio"], resultado)
            else:
                sin_cobertura = {
                    "carrier": svc["provider"],
                    "servicio": svc["label"],
                    "via": svc.get("via", ""),
                    "subtotal": 0,
                    "iva": 0,
                    "total": 0,
                    "zona_ext": 0,
                    "guia": 0,
                    "entrega": "—",
                    "modo": "Sin cobertura",
                    "disponible": False,
                }
                resultados.append(sin_cobertura)
                if on_progress:
                    on_progress(svc["provider"], svc["label"], None)

        return resultados
