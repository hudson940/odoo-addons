# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Odoo WooCommerce Connector Ext Lico Express',
    'version': '12.0.0.0.1',
    'category': 'connector',
    'author': 'Lico Express',
    'license': 'AGPL-3',
    'summary': 'Allows modifying the woo commerce connector to add point of sale order synchronization',

    'description': """
        Allows modifying the woo commerce connector to add point of sale order synchronization
    """,
    # any module necessary for this one to work correctly
    'depends': ['woo_commerce_ept'],

    # always loaded
    'data': [
        'views/woo_instance_ept.xml',
        'views/pos_order.xml',
    ]
    ,
}