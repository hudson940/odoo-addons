# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import Warning
from .api import nacex_api, CHARGE_TYPES, INSURANCE_TYPES, ALERT_MODES, ALERT_TYPES, REFUND_TYPES



class DeliveryCarrierNacex(models.Model):
    _name = 'nacex.odoo.configuration'

    name = fields.Char()
    url_ws = fields.Char('URL WS', default='http://pda.nacex.com/nacex_ws')
    url_print = fields.Char('URL Print', default='http://www.nacex.es/applets')
    url_tracking = fields.Char('URL seguimiento/rastreo', default='http://pda.nacex.com/nacex_ws')
    printer_model = fields.Selection([('IMAGEN_B', 'IMAGEN')], default='IMAGEN_B')
    user = fields.Char('Usuario Web Service')
    password = fields.Char('Password Web Service')

    delivery_method_ids = fields.One2many('delivery.carrier', 'nacex_config_id', 'Metodos de envío configurados')

    # configuración del abonado
    agency = fields.Char('Agencia', help="Código de agencia")
    client = fields.Char('Cliente', help="Código de cliente")

    packaging_type_id = fields.Many2one('product.packaging', 'Tipo de envío por defecto')
    nacex_default_weight = fields.Float('Peso por defecto en KG',
                                        help='si los productos no tienen peso configurado se usara este valor')
    nacex_defaulf_charge_type = fields.Selection(CHARGE_TYPES, 'Tipo de cobro por defecto')
    nacex_default_refund_type = fields.Selection(REFUND_TYPES, 'Tipo de reembolso por defecto')
    nacex_default_insurance_type = fields.Selection(INSURANCE_TYPES, 'Tipo de seguro por defecto')
    nacex_isurance_from_order_total = fields.Boolean('Asegurar el valor total del pedido')
    nacex_default_insurance_value = fields.Float('Importe asegurado')
    nacex_default_alert_type = fields.Selection(ALERT_TYPES, 'Tipo de prealerta por defecto')
    nacex_default_alert_mode = fields.Selection(ALERT_MODES, 'Modo de prealerta por defecto')

    def test_connection(self):
        conn = nacex_api(self)
        try:
            assert self.delivery_method_ids, 'Configure al menos un método de envío'
            params = conn.prepare_common_params(self.delivery_method_ids[0], partner_shipping_id=self.env.user.partner_id,
                                                partner_origin_id=self.env.user.company_id, lines=[])
            params['kil']=1
            data = conn.params_to_data(params)
            response = conn.get('method=getValoracion&%s' % data).split('|')
        except Exception as e:
            raise Warning('Error %s' % repr(e))
        raise Warning('Conexión existosa: servicio consultado: %s, tarifa estimada: %s ' % tuple(response))

