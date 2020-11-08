# -*- coding: utf-8 -*-
import binascii
from odoo import models, fields
from .api import nacex_api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    carrier_expedition_code = fields.Char()

    def action_get_label(self):
        self.ensure_one()
        if self.carrier_expedition_code and self.carrier_id:
            conn = nacex_api(self.carrier_id.nacex_config_id)
            label = conn.get_label(cod_exp=self.carrier_expedition_code, tracking=self.carrier_tracking_ref,
                                        model=self.carrier_id.nacex_config_id.printer_model)
            data = binascii.a2b_base64(str(label))
            body = ("Etiqueta Nacex: </b>%s" % (self.carrier_tracking_ref))
            self.message_post(body=body, attachments=[
                ('%s_nacex_label_%s.pdf' % (self.name, self.carrier_expedition_code), data)])



