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
        return [{'exact_price': 0.0, 'tracking_number': tracking}]
            # body = self.create_or_update_order(picking)
            # try:
            #     response_data = self.api_calling_function("/orders/createorder", body)
            #     if response_data.status_code == 200:
            #         responses = response_data.json()
            #         _logger.info("Response Data: %s" % (responses))
            #         order_id = responses.get('orderId')
            #         order_key = responses.get('orderKey')
            #         if order_id:
            #             picking.nacex_order_id = order_id
            #             picking.nacex_order_key = order_key
            #         return [{'exact_price': 0.0, 'tracking_number': ''}]
            #     else:
            #         error_code = "%s" % (response_data.status_code)
            #         error_message = response_data.reason
            #         error_detail = {'error': error_code + " - " + error_message + " - "}
            #         if response_data.json():
            #             error_detail = {'error': error_code + " - " + error_message + " - %s" % (response_data.json())}
            #         raise ValidationError(error_detail)
            # except Exception, e:
            #     raise ValidationError(e)

    def nacex_cancel_shipment(self, picking):
        conn = nacex_api(self.nacex_config_id)
        shipment_id = picking.nacex_shipment_id
        if not shipment_id:
            raise ValidationError("nacex Shipment Id Not Available!")
        req_data = {"shipmentId": shipment_id}
        try:
            response_data = self.api_calling_function("/shipments/voidlabel", req_data)
            if response_data.status_code == 200:
                responses = response_data.json()
                _logger.info("Response Data: %s" % (responses))
                approved = responses.get('approved')
                if approved:
                    picking.message_post(body=_('Shipment Cancelled In nacex %s' % (shipment_id)))
            else:
                error_code = "%s" % (response_data.status_code)
                error_message = response_data.reason
                error_detail = {'error': error_code + " - " + error_message + " - "}
                if response_data.json():
                    error_detail = {'error': error_code + " - " + error_message + " - %s" % (response_data.json())}
                raise ValidationError(error_detail)
        except Exception, e:
            raise Warning(e)
        return True

    def nacex_get_tracking_link(self, pickings):
        res = ""
        for picking in pickings:
            link = "%s"%(picking.carrier_id and picking.carrier_id.nacex_carrier_id and picking.carrier_id and picking.carrier_id.nacex_carrier_id.provider_tracking_link)
            if not link:
                raise ValidationError("Provider Link Is not available")
            res = '%s %s' % (link, picking.carrier_tracking_ref)
        return res
