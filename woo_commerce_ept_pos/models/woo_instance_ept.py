from odoo import models, fields


class WooInstance(models.Model):
    _inherit = 'woo.instance.ept'

    pos_config_id = fields.Many2one('pos.config', srting='Point Of Sale')
    tax_included = fields.Boolean('Impuesto Incluido')