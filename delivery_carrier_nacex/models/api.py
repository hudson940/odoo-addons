# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import requests
import json
import logging
from datetime import datetime

_log = logging.getLogger(__name__)

SERVICES = [
    ('01', 'NACEX 10:00H'),
    ('02', 'NACEX 12:00H'),
    ('03', 'INTERDIA'),
    ('04', 'PLUS BAG 1'),
    ('05', 'PLUS BAG 2'),
    ('06', 'VALIJA	'),
    ('07', 'VALIJA IDA Y VUELTA'),
    ('08', 'NACEX 19:00H'),
    ('09', 'PUENTE URBANO'),
    ('10', 'DEVOLUCION ALBARAN CLIENTE'),
    ('11', 'NACEX 08:30H'),
    ('12', 'DEVOLUCION TALON'),
    ('14', 'DEVOLUCION PLUS BAG 1'),
    ('15', 'DEVOLUCION PLUS BAG 2'),
    ('17', 'DEVOLUCION E-NACEX'),
    ('21', 'NACEX SABADO'),
    ('22', 'CANARIAS MARITIMO'),
    ('24', 'CANARIAS 24H'),
    ('26', 'PLUS PACK'),
    ('27', 'E-NACEX'),
    ('28', 'PREMIUM'),
    ('29', 'NX-SHOP VERDE'),
    ('30', 'NX-SHOP NARANJA'),
    ('31', 'E-NACEX SHOP'),
    ('33', 'C@MBIO'),
    ('48', 'CANARIAS 48H'),
    ('88', 'INMEDIATO'),
    ('90', 'NACEX.SHOP'),
    ('91', 'SWAP'),
    ('95', 'RETORNO SWAP'),
    ('96', 'DEV. ORIGEN')]

CHARGE_TYPES = [('O', 'Origen'), ('D', 'Destino'), ('T', 'Tercera')]

INSURANCE_TYPES = [('N', 'No asegurado, valor por defecto. (Seguro básico hasta 3.000 €)',),
                   ('A', 'Mercancía general superior a 3.000 €'),
                   ('B', 'Joyería'),
                   ('C', 'Telefonía'),
                   ('D', 'Mercancía especial/exclusiva'),
                   ('E', 'Armas munición, accesorios y repuestos'),
                   ('F', 'Loteria, cheques gourmet, entradas espectáculos, Smartbox')]

ALERT_TYPES = [('N', 'No se avisa'),
               ('S', 'Envío de prealerta mediante un SMS'),
               ('E', 'Envío de prealerta mediante un EMAIL'),
               ('Z',
                'Envío de prealerta mediante un SMS sin compromiso de entrega.'),
               ('M',
                'Envío de prealerta mediante un EMAIL sin compromiso de entrega.')]

ALERT_MODES = [('S', 'Standard'), ('P', 'Plus'), ('R', 'Reparto'), ('E', 'Reparto Plus')]
REFUND_TYPES = [('N', 'No'), ('O', 'Origen'), ('D', 'Destino'), ('A', 'Adelanto')]
class nacex_api():

    def __init__(self, config_id):
        self.base_url = config_id.url_ws
        self.url_print = config_id.url_print
        self.user = config_id.user
        self.password = config_id.password
        self._requests = requests
        self.session = requests.Session()
        self.config_id = config_id

    def prepare_url(self, path):
        if self.base_url in path:
            return path
        return '{base_url}/ws?user={user}&pass={password}&{path}'.format(
            base_url=self.base_url, user=self.user, password=self.password, path=path)

    def get(self, path, params=None, extra_headers=None):
        params = params or {}
        if extra_headers:
            self.session.headers.update(extra_headers)
        url = self.prepare_url(path)
        try:
            response = self.session.get(url, params=params,
                                    headers=self.session.headers)
        except Exception as e:
            raise ValidationError(repr(e))
        return self.validate_response(response, params)

    def post(self, path, data=None, extra_headers=None):
        if extra_headers:
            self.session.headers.update(extra_headers)
        url = self.prepare_url(path)
        if isinstance(data, (dict, list, tuple)):
            data = json.dumps(data)
        response = self.session.post(url, data=data,
                                     headers=self.session.headers)
        return self.validate_response(response, data=data)

    def put(self, path, data=None, params={}, extra_headers=None):
        if extra_headers:
            self.session.headers.update(extra_headers)
        if isinstance(data, (dict, list, tuple)):
            data = json.dumps(data)
        url = self.prepare_url(path)

        response = self.session.put(url, data=data, params=params,
                                    headers=self.session.headers)
        return self.validate_response(response, data=data, params=params)

    def validate_response(self, res, params=None, data=None):
        if 300 > res.status_code >= 200:
            if 'ERROR' in res.content:
                return self.manage_errors(res, params, data)
            return res.content or ''
        else:
            return self.manage_errors(res, params, data)

    def manage_errors(self, res, params=None, data=None):
        """
        :param res:
        :param params:
        :param data:
        :return:
        """
        # url = res.request.url
        # hidden_credentials_url = '&'.join([p for p in url.split('&') if 'pass' not in p])
        error = 'There\'s an error in your request:\n Response: \n\n%s' % (
            res.text)
        raise ValidationError(error)

    def prepare_common_params(self, carrier_id, partner_shipping_id, partner_origin_id, lines):
        """

        :param carrier_id:
        :param partner_shipping_id:
        :param partner_origin_id:
        :param lines:
        :return: dict: del_cli, num_cli, cp_rec, cp_ent, tip_ser, tip_env, kil
        """
        params = {}
        del_cli = self.config_id.agency
        if del_cli:
            # raise ValidationError('Debe configurar el código de agencia en %s' % self.config_id.name)
            params['del_cli'] = del_cli
        num_cli = self.config_id.client
        if num_cli:
            # raise ValidationError('Debe configurar el código de cliente en %s' % self.config_id.name)
            params['num_cli'] = num_cli
        cp_rec = partner_origin_id.zip
        if not cp_rec:
            raise ValidationError('Debe configurar el código zip en la compañía %s' % partner_origin_id)
        params['cp_rec'] = cp_rec
        cp_ent = partner_shipping_id.zip
        if not cp_ent:
            raise ValidationError('Debe diligenciar el código zip para el cliente %s' % partner_shipping_id)
        params['cp_ent'] = cp_ent
        tip_ser = carrier_id.nacex_service
        params['tip_ser'] = tip_ser
        tip_env = self.config_id.packaging_type_id.shipper_package_code
        if not tip_env:
            raise ValidationError(
                'Falta el código del empaque para %s' % self.config_id.packaging_type_id.name or 'tipo de empaque no encontrado')
        params['tip_env'] = tip_env
        kil = sum(l.product_id.weight or self.config_id.nacex_default_weight for l in lines if
                  l.product_id.type == 'product')
        # todo: validate system measure unit
        params['kil'] = kil

        return params

    @staticmethod
    def params_to_data(params):
        return 'data=%s' % '|'.join('%s=%s' % p for p in params.items() if p[1])

    def get_valuation(self, carrier_id, order):
        """
        :param order: sale.order
        :param carrier_id: delivery.carrier
        this method calls api to get valuation of delivery using this params

        - cp_rec	Código postal de recogida (origen)	8
        - cp_ent	Código postal de entrega (destino)	8
        - tip_ser	Tipo de Servicio nacional [01 (Nacex 10H), 02 (Nacex 13H), etc)	2
        - tip_env	Tipo de envío nacional (0 = Docs / 1 = Bag / 2 = Paq)	1
        - kil	Peso en kilos. Necesario cuando se indica el tipo de envío como PAQ o muestra (formateado como 5.3)	5.3
        - tarifa	Tarifa a aplicar. Si se omite éste parámetro y los dos siguientes (del_cli y num_cli) se aplicará la tarifa por defecto	20
        - del_cli	Agencia. Si se omite el parámetro "tarifa" y se informa de este parámetro y de "num_cli" se intentará recuperar la tarifa para este abonado registrada en el sistema.	4
        - num_cli	Cliente. Si se omite el parámetro "tarifa" y se informa de este parámetro y de "del_cli" se intentará recuperar la tarifa para este abonado registrada en el sistema.	5
        - alto	Alto del bulto en cm.	4
        - ancho	Ancho del bulto en cm.	4
        - largo	Largo del bulto en cm.	4
        """

        params = self.prepare_common_params(carrier_id, partner_shipping_id=order.partner_shipping_id,
                                            partner_origin_id=order.warehouse_id.partner_id, lines=order.order_line)
        data = self.params_to_data(params)
        response = self.get('method=getValoracion&%s' % data).split('|')
        try:
            if len(response) > 1:
                if ',' in response[1]:
                    response[1] = response[1].replace(',', '.')
                return float(response[1])
        except Exception as e:
            raise ValidationError('Error al estimar el costo del envio %s' % repr(e))
        raise ValidationError('Error al estimar el costo del envio')

    def put_expedition(self, carrier_id, picking):
        """

        :param carrier_id:
        :param picking:
        :return:
        request params
        clave	Descripción	Máx. Long.
        del_cli	Delegación del cliente	4
        num_cli	Código del cliente (Nº abonado Nacex)	5
        dep_cli	Departamento del cliente	10
        fec	Fecha de la expedición (dd/mm/yyyy)	10
        tip_ser	Código de Servicio Nacex(ver servicios)	2
        tip_cob	Código de Cobro Nacex (ver cobros)	1
        exc	Número de Excesos	3
        ref_cli	Referencia del cliente (Para multiples referencias separarlas por ; )	20
        tip_env	Código de envase Nacex (ver envases)	1
        bul	Número de bultos (Ej. Para 5 bultos, 005)	3
        kil	Peso del paquete en Kilos	5.3
        nom_rec	Nombre de recogida	35
        dir_rec	Dirección de recogida	45
        cp_rec	Código postal recogida (Ej. 08902)	8
        pais_rec	País de recogida	2
        pob_rec	Población de recogida	30
        tel_rec	Teléfono de recogida	15
        nom_ent	Nombre de entrega	50
        per_ent	Persona de entrega	35
        dir_ent	Dirección de entrega	45
        pais_ent	País de entrega	2
        cp_ent	Código postal entrega (Ej. 08902)	15
        pob_ent	Población de entrega	40
        tel_ent	Teléfono de entrega	20
        ree	Importe de reembolso	5.3
        tip_ree	Código de reembolso o adelanto Nacex (ver reembolsos/adelanto)	1
        obs"n"	Observaciones, hasta 4 observaciones	38 x4
        ret	Envío con retorno (S / N)	1
        ges	Código de gestión ó Trámite, (ver gestión/trámite)	1
        ok15	Confirmación Ok. 15 minutos (S / N)	1
        pre	Prepagado (S / N)	1
        tip_seg	Código del tipo de Seguro, (ver seguros)	1
        seg	Importe valor a asegurar en Euros sin decimales	5.3
        tip_ea	Tipo de Ealerta, (ver tipos)	1
        ealerta	Ealerta (al móvil o dirección de e-mail indicados)	60
        alto	Alto del paquete en CM.	3
        ancho	Ancho del paquete en CM.	3
        largo	Largo del paquete en CM.	3
        con	Contenido (Obligatorio si se trata de un envío internacional)	80
        val_dec	Valor declarado (Obligatorio si se trata de un envío internacional)	5.3
        dig	Código para digitalización o almacenaje de albaranes de cliente, (ver códigos)	1
        num_dig	Número de copias a escanear, si el número de copia es cero, se indica como 00	2
        ins_adi"n"	Línea de instrucciones adicionales de entrega, hasta 15 líneas. Requiere ins_adi informado	40 x15
        tip_pre"n"	Tipo de prealertas, hasta 5 prealertas, (ver tipos)	1 x5
        mod_pre"n"	Modos de prealerta, hasta 5 prealertas, (ver modos)	1 x5
        pre"n"	Prealerta SMS ó Email de destino, hasta 5 prealertas	50 x5
        msg"n"	Texto para mensaje prealerta plus, hasta 5 prealertas	195 x5
        ins_adi	Para añadir o no las instrucciones adicionales será necesario informar este parámetro con los posibles valores S ó N	1
        cam_serv	Para permitir un cambio de servicio para forzar la validez de la expedición será necesario informar este parámetro con los posibles valores S ó N	1
        shop_codigo	Código del punto de entrega NacexShop	6
        frec_codigo	Código de frecuencia para servicios Interdía y Puente Urbano, (ver frecuencias)	1
            """
        params = self.prepare_common_params(carrier_id, partner_shipping_id=picking.partner_id,
                                            partner_origin_id=picking.picking_type_id.warehouse_id.partner_id,
                                            lines=picking.pack_operation_ids)
        # required
        params['fec'] = datetime.now().strftime('%d/%m/%Y')
        params['tip_cob'] = self.config_id.nacex_defaulf_charge_type
        params['bul'] = len(picking.pack_operation_ids.mapped('result_package_id') or picking.pack_operation_ids)

        params['nom_ent'] = picking.partner_id.name
        params['dir_ent'] = picking.partner_id.street
        params['pais_ent'] = picking.partner_id.country_id.code
        params['pob_ent'] = picking.partner_id.state_id.name
        params['tel_ent'] = picking.partner_id.mobile or picking.partner_id.phone

        # optional
        params['tip_rec'] = self.config_id.nacex_default_refund_type
        params['tip_seg'] = self.config_id.nacex_default_insurance_type
        params['seg'] = picking.sale_id.amount_total if \
                (self.config_id.nacex_isurance_from_order_total and picking.sale_id.amount_total) \
                else self.config_id.nacex_default_insurance_value
        params['tip_ea'] = self.config_id.nacex_default_alert_type
        if self.config_id.nacex_default_alert_type in ('E', 'M'):
            params['ealerta'] = picking.partner_id.email
        elif self.config_id.nacex_default_alert_type in ('S', 'Z'):
            params['ealerta'] = picking.partner_id.mobile or picking.partner_id.phone
        params['con'] = ','.join(picking.pack_operation_ids.mapped('product_id.name'))[:80]
        params['val_dec'] = picking.sale_id.amount_total
        params['tip_pre1'] = self.config_id.nacex_default_alert_type
        params['mod_pre1'] = self.config_id.nacex_default_alert_mode
        params['pre1'] = picking.partner_id.email

        data = self.params_to_data(params)
        response = self.get('method=putExpedicion&%s' % data).split('|')
        try:
            if len(response) > 1:
                cod_exp = response[0]
                tracking = response[1]
                return cod_exp, tracking
        except Exception as e:
            raise ValidationError('Error al estimar el costo del envio %s' % repr(e))
        raise ValidationError('Error al estimar el costo del envio')

    def cancel_expedition(self, exp_code, agency):
        data = 'data=%s|%s' % (exp_code, agency)
        return self.get('method=cancelExpedicion&%s' % data).split('|')

    def get_label(self, cod_exp, tracking, model):
        data = 'data=codExp={cod_exp}|modelo={modelo}'.format(cod_exp=cod_exp, modelo=model)
        res = self.get('method=getEtiqueta&%s' % data)
        return res
