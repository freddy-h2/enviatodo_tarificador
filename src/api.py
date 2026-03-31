# -*- coding: utf-8 -*-
"""Cliente de la API de EnviaTodo v2."""

import time

import requests

from src.config import (
    ALTO,
    ANCHO,
    API_HEADERS,
    BASE_URL,
    CATALOG_TIMEOUT,
    LARGO,
    PESO,
    PESO_FACTURADO,
    PESO_VOLUMETRICO,
    REQUEST_TIMEOUT,
)


class EnviaTodoClient:
    """Wrapper para la API de EnviaTodo v2."""

    def __init__(self, token):
        self.token = token
        self.headers = {
            **API_HEADERS,
            "Authorization": "Bearer %s" % token,
        }

    # ── Catálogos ─────────────────────────────────────────────

    def obtener_datos_cp(self, cp):
        """Consulta datos de un código postal.

        Returns:
            dict con suburb, municipality, state, city, state_code o None.
        """
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

    def cotizar(self, cp_origen, cp_destino, datos_origen, datos_destino,
                provider_service_id):
        """Cotiza un envío con un servicio específico.

        Args:
            cp_origen: CP de origen (5 dígitos).
            cp_destino: CP de destino (5 dígitos).
            datos_origen: dict con suburb, municipality, state, etc.
            datos_destino: dict con suburb, municipality, state, etc.
            provider_service_id: ID del servicio de paquetería.

        Returns:
            dict con la respuesta de la API, o None si falló.
        """
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
                return resp.json()
        except requests.exceptions.Timeout:
            return None
        except Exception:
            return None
        return None

    def cotizar_zona(self, cp_origen, cp_destino, datos_origen, datos_destino,
                     servicios, pausa=0.5):
        """Cotiza un destino con todos los servicios disponibles.

        Args:
            cp_origen: CP de origen.
            cp_destino: CP de destino.
            datos_origen: dict con datos del CP origen.
            datos_destino: dict con datos del CP destino.
            servicios: list de dicts con id, label, provider.
            pausa: segundos entre peticiones.

        Returns:
            list[dict]: Resultados por servicio.
        """
        resultados = []

        for svc in servicios:
            resp = self.cotizar(
                cp_origen, cp_destino, datos_origen, datos_destino, svc["id"],
            )

            rates = []
            if resp and resp.get("success"):
                rates = resp.get("data", {}).get("rates", [])

            if rates:
                for rate in rates:
                    # Extraer cargo base (sin seguro)
                    cargo_base = next(
                        (c for c in rate.get("charges", []) if c["type"] == "base"),
                        {},
                    )
                    # Extraer cargos detallados
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

                    resultados.append({
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
                    })
            else:
                resultados.append({
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
                })

            if pausa > 0:
                time.sleep(pausa)

        return resultados
