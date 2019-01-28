# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Folio Payment',
    'version': '10.0.1.0.1',
    'author': 'Anderson Martinez',
    'category': 'Generic Modules/Hotel',
    'website': '',
    'depends': ['hotel'],
    'license': 'AGPL-3',
    'demo': [

    ],
    'data': [
        'security/ir.model.access.csv',
        'views/folio_payment.xml',
        'views/report_payment.xml',
        'views/report_receipt.xml',

    ],
    'js': [],
    'qweb': ['static/src/xml/hotel_room_summary.xml'],
    'css': [],
    'images': [],
    'installable': True,
    'auto_install': False,
}
