# -*- coding: utf-8 -*-
#################################################################################
# Author      : Techmayoreo (<https://techmayoreo.com/>)
# License     : MIT
#
#################################################################################
{
    "name": "Nacex Shipping Api Integration",
    "summary": "Nacex Shipping Api Integration",
    "category": "Delivery",
    "version": "1.0.0",
    "author": "Techmayoreo",
    "maintainer": "Anderson Martinez",
    "email": "anderson.martinez@techmayoreo.com",
    "website": "https://techmayoreo.com",
    "description": """Nacex Shipping Api Integration""",
    "depends": [
        'product',
        'sale',
        'delivery',
    ],
    "data": [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/delivery_carrier.xml',
        'views/menus.xml',
        'views/nacex_odoo_configuration.xml',
        'views/stock_picking.xml',
    ],
    "images": ['static/description/logo.png'],
    "application": True,
    "installable": True,
    "auto_install": False,
}
