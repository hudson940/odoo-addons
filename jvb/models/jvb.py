from odoo import api, fields, models

class AccountInvoiceInherit(models.Model):
    _inherit = "account.invoice"
    vehiculo_id = fields.Many2one("fleet.vehicle", ondelete="restrict")

    @api.onchange('vehiculo_id')
    def _change_vehiculo_id(self):
        '''
        partner_id will be updated.
        ----------------------------------------
        @param self: object pointer
        '''
        self.partner_id = self.vehiculo_id.driver_id

