# -*- coding: utf-8 -*-
{
    'name': 'account_clean',
    'version': '12.0.1.0.0',
    'category': 'account',
    "author": "Techmayoreo",
    "website": "https://techmayoreo.com",
    'summary': 'account cleaner',
    'description': '',
    'website': '',
    'depends': [
        'base', 'point_of_sale'
    ],
    'data': [
        #'security/ir.model.access.csv',
        'views/menu.xml',
        'views/wizard_account_clean.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
