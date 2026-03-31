# -*- coding: utf-8 -*-
{
    "name": "EnviaTodo Shipping - Custer Boots",
    "version": "19.0.1.0.0",
    "category": "Inventory/Delivery",
    "summary": "Integración con EnviaTodo.com para cotización y generación de guías de envío",
    "description": """
EnviaTodo Shipping - Custer Boots
==================================

Módulo de integración con la plataforma EnviaTodo.com para la empresa Custer Boots.

Funcionalidades:
- Cotización automática de envíos vía API de EnviaTodo
- Generación de guías de envío al validar transferencias
- Seguimiento de paquetes con enlace directo
- Cancelación de guías desde Odoo
- Configuración de dimensiones predeterminadas del producto (44×11×33 cm, 1.9 kg)
- Validación de códigos postales mexicanos

Datos de origen:
- Empresa: Custer Boots
- Ciudad: León, Guanajuato
- CP Origen: 37000
    """,
    "author": "Custer Boots",
    "website": "",
    "license": "LGPL-3",
    "depends": [
        "delivery",
        "stock",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/delivery_carrier_views.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
