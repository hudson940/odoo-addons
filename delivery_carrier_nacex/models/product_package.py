# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductPackage(models.Model):
    _inherit = 'product.packaging'

    package_carrier_type = fields.Selection(selection_add=[('nacex', 'Nacex')])