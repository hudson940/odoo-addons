# -*- coding: utf-8 -*-
from odoo import api, models, fields
from .api import SERVICES, nacex_api, CHARGE_TYPES, INSURANCE_TYPES, ALERT_MODES, ALERT_TYPES, REFUND_TYPES
from odoo.exceptions import ValidationError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('nacex', 'Nacex')])

    nacex_config_id = fields.Many2one('nacex.odoo.configuration', 'Configuración Nacex')
    nacex_service = fields.Selection(SERVICES, 'Servicio Nacex')

    def nacex_get_shipping_price_from_so(self, order):
        conn = nacex_api(self.nacex_config_id)
        return [conn.get_valuation(self, order)]

    def nacex_send_shipping(self, pickings):
        conn = nacex_api(self.nacex_config_id)
        pickings.ensure_one()
        cod_exp, tracking = conn.put_expedition(self, pickings)
        pickings.write({'carrier_expedition_code': cod_exp})
        return [{'exact_price': 0.0, 'tracking_number': tracking}]


    def nacex_cancel_shipment(self, picking):
        conn = nacex_api(self.nacex_config_id)
        picking.ensure_one()

        exp_code = picking.carrier_expedition_code
        if not exp_code:
            raise ValidationError("No se encuetra el Código de expedición")
        agency = picking.carrier_tracking_ref.split('/')[0]
        res = conn.cancel_expedition(exp_code, agency)
        if res:
            picking.message_post(body=('Envío cancelado en nacex %s' % (picking.carrier_tracking_ref)))
        return True

    def nacex_get_tracking_link(self, pickings):
        res = ""
        for picking in pickings:
            link = "%s" % picking.carrier_id.nacex_config_id.url_tracking
            if not link:
                raise ValidationError("Configura la URL de seguimiento en la configuración nacex %s" % picking.carrier_id.nacex_config_id.name)
            res = '%s %s' % (link, picking.carrier_tracking_ref)
        return res
