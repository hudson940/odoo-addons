from odoo import models, api, _
from odoo.exceptions import Warning
import requests
from datetime import datetime
from dateutil import parser
import pytz
utc = pytz.utc


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.model
    def get_woo_order_vals(self, result, workflow, invoice_address, instance, partner, shipping_address, pricelist_id,
                           fiscal_position, payment_term, payment_gateway):
        vals = super(SaleOrder, self).get_woo_order_vals(result, workflow, invoice_address, instance, partner, shipping_address, pricelist_id,
                           fiscal_position, payment_term, payment_gateway)
        vals['amount_tax'] = result.get('total_tax')
        vals['amount_total'] = result.get('total')
        vals['amount_paid'] = 0
        vals['amount_return'] = 0
        vals['pos_reference'] = result.get('id')
        session_id = self.env['pos.session'].search(
            [('config_id', '=', instance.pos_config_id.id), ('state', '=', 'opened')], limit=1)
        vals['session_id'] = session_id.id
        meta_data = result.get('meta_data') or []
        neighborhood, payment = '', ''
        for data in meta_data:
            if data.get('key') == 'billing_barrio':
                neighborhood = data.get('value')
            elif data.get('key') == 'billing_pago':
                payment = data.get('value')
            if neighborhood and payment:
                break
        address = '%s%s' % (shipping_address.street,'\n' + shipping_address.street2 if shipping_address.street2 else '')
        vals['note'] = 'Nombre: {name},\nDirección: {address},\nbarrio: {neighborhood},\nTel: {phone},\nPago: {payment}'.format(
            name=shipping_address.name, address=address, neighborhood=neighborhood,
            phone=shipping_address.phone or partner.phone, payment=payment
        )
        try:
            vals['config_id'] = instance.pos_config_id.id
            del vals['partner_id']
            del vals['partner_invoice_id']
            del vals['warehouse_id']
            del vals['partner_shipping_id']
            del vals['payment_term_id']
            if vals.get('picking_policy'):
                del vals['picking_policy']
            if vals.get('invoice_policy'):
                del vals['invoice_policy']
            del vals['team_id']
        except Exception as e:
            pass
        return vals

    @api.model
    def import_woo_orders(self, instance=False, before_date=False, after_date=False, is_cron=False):
        instances = []
        pos_order = self.env['pos.order']
        transaction_log_obj = self.env["woo.transaction.log"]
        if not instance:
            instances = self.env['woo.instance.ept'].search(
                [('order_auto_import', '=', True), ('state', '=', 'confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            wcapi = instance.connect_in_woo()
            order_ids = []
            try:
                tax_included = instance.tax_included
            except Exception as e:
                transaction_log_obj.create({
                                               'message': "Json Error : While import Product Tax from WooCommerce for instance %s. \n%s" % (
                                               instance.name, e),
                                               'mismatch_details': True,
                                               'type': 'sales',
                                               'woo_instance_id': instance.id
                                               })
            for order_status in instance.import_order_status_ids:
                instance.last_synced_order_date = before_date
                if before_date and after_date:
                    response = wcapi.get('orders?after=%s&before=%s&status=%s&per_page=100' % (
                    after_date, before_date, order_status.status))
                else:
                    response = wcapi.get('orders?status=%s&filter[limit]=1000' % (order_status.status))
                if not isinstance(response, requests.models.Response):
                    transaction_log_obj.create(
                        {'message': "Import Orders \nResponse is not in proper format :: %s" % (response),
                         'mismatch_details': True,
                         'type': 'sales',
                         'woo_instance_id': instance.id
                         })
                    continue
                if response.status_code not in [200, 201]:
                    message = "Error in Import Orders %s" % (response.content)
                    transaction_log_obj.create(
                        {'message': message,
                         'mismatch_details': True,
                         'type': 'sales',
                         'woo_instance_id': instance.id
                         })
                    continue
                try:
                    order_response = response.json()
                except Exception as e:
                    transaction_log_obj.create({
                                                   'message': "Json Error : While import Orders from WooCommerce for instance %s. \n%s" % (
                                                   instance.name, e),
                                                   'mismatch_details': True,
                                                   'type': 'sales',
                                                   'woo_instance_id': instance.id
                                                   })
                    continue
                order_ids = order_ids + order_response.get('orders')
                total_pages = response.headers.get('X-WC-TotalPages')
                if int(total_pages) >= 2:
                    for page in range(2, int(total_pages) + 1):
                        order_ids = order_ids + self.import_all_woo_orders(wcapi, instance, transaction_log_obj,
                                                                           order_status, page, after_date, before_date,
                                                                           is_cron)

            import_order_ids = []

            for order in order_ids:
                if pos_order.search_count([('woo_instance_id', '=', instance.id), ('woo_order_id', '=', order.get('id')),
                                ('woo_order_number', '=', order.get('order_number'))]):
                    continue
                lines = order.get('line_items')
                if self.check_woo_mismatch_details(lines, instance, order.get('order_number')):
                    continue
                financial_status = 'paid'
                if order.get('payment_details').get('paid'):
                    financial_status = 'paid'
                else:
                    financial_status = 'not_paid'

                no_payment_gateway = False
                payment_gateway = self.create_or_update_payment_gateway(instance, order)

                if not payment_gateway:
                    no_payment_gateway = self.verify_order(instance, order)
                    if not no_payment_gateway:
                        message = "Payment Gateway is not found for this order %s and financial status is %s" % (
                        order.get('order_number'), financial_status)
                        log = transaction_log_obj.search(
                            [('woo_instance_id', '=', instance.id), ('message', '=', message)])
                        if not log:
                            transaction_log_obj.create(
                                {'message': message,
                                 'mismatch_details': True,
                                 'type': 'sales',
                                 'woo_instance_id': instance.id
                                 })
                        continue

                workflow = False
                if not no_payment_gateway and payment_gateway:
                    workflow_config = self.env['woo.sale.auto.workflow.configuration'].search(
                        [('woo_instance_id', '=', instance.id), ('financial_status', '=', financial_status),
                         ('payment_gateway_id', '=', payment_gateway.id)], limit=1)
                    workflow = workflow_config and workflow_config.auto_workflow_id or False

                if not workflow and not no_payment_gateway:
                    message = "Workflow Configuration not found for this order %s, financial status is %s and Payment Gateway is %s" % (
                    order.get('order_number'), financial_status, order.get('payment_details').get('method_id'))
                    log = transaction_log_obj.search([('woo_instance_id', '=', instance.id), ('message', '=', message)])
                    if not log:
                        transaction_log_obj.create(
                            {'message': message,
                             'mismatch_details': True,
                             'type': 'sales',
                             'woo_instance_id': instance.id
                             })
                    continue
                woo_customer_id = order.get('customer', {}).get('id', False)
                partner = order.get('billing_address', False) and self.create_or_update_woo_customer(woo_customer_id,
                                                                                                     order.get(
                                                                                                         'billing_address'),
                                                                                                     False, False,
                                                                                                     False, instance)
                if not partner:
                    message = "Customer Not Available In %s Order" % (order.get('order_number'))
                    log = transaction_log_obj.search([('woo_instance_id', '=', instance.id), ('message', '=', message)])
                    if not log:
                        transaction_log_obj.create(
                            {'message': message,
                             'mismatch_details': True,
                             'type': 'sales',
                             'woo_instance_id': instance.id
                             })
                    continue
                shipping_address = order.get('shipping_address', False) and self.create_or_update_woo_customer(False,
                                                                                                               order.get(
                                                                                                                   'shipping_address'),
                                                                                                               False,
                                                                                                               partner.id,
                                                                                                               'delivery',
                                                                                                               instance) or partner
                new_record = self.new({'partner_id': partner.id})
                new_record.onchange_partner_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                new_record = self.new(retval)
                new_record.onchange_partner_shipping_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                fiscal_position = partner.property_account_position_id
                pricelist_id = retval.get('pricelist_id', False)
                payment_term = retval.get('payment_term_id')

                woo_order_vals = self.get_woo_order_vals(order, workflow, partner, instance, partner, shipping_address,
                                                         pricelist_id, fiscal_position, payment_term, payment_gateway)
                sale_order = pos_order.create(woo_order_vals) if woo_order_vals else False

                if not sale_order:
                    continue

                def calclulate_line_discount(line):
                    return (float(line.get('subtotal')) - float(line.get('total'))) + (
                                float(line.get('subtotal_tax')) - float(line.get('total_tax')))

                order_discount = False
                discount_value = 0.0
                total_discount = float(order.get('total_discount', 0.0))
                if float(total_discount) > 0.0:
                    order_discount = True
                    if not tax_included:
                        discount_value = float(total_discount)

                import_order_ids.append(sale_order.id)
                shipping_taxable = False
                tax_datas = []
                tax_ids = []
                for tax_line in order.get('tax_lines'):
                    tax_data = {}
                    rate_id = tax_line.get('rate_id')
                    if rate_id:
                        res_rate = wcapi.get('taxes/%s' % (rate_id))
                        try:
                            rate = res_rate.json()
                        except Exception as e:
                            transaction_log_obj.create({
                                                           'message': "Json Error : While retrive Product tax id %s from WooCommerce for instance %s. \n%s" % (
                                                           rate_id, instance.name, e),
                                                           'mismatch_details': True,
                                                           'type': 'sales',
                                                           'woo_instance_id': instance.id
                                                           })
                            continue
                        tax_data = rate.get('tax', {})
                        tax_datas.append(tax_data)
                        shipping_taxable = tax_data.get('shipping')
                tax_ids = self.get_woo_tax_id_ept(instance, tax_datas, tax_included)
                for line in lines:
                    woo_product = self.create_or_update_woo_product(line, instance, wcapi)
                    if not woo_product:
                        continue
                    product = woo_product.product_id
                    actual_unit_price = 0.0
                    if tax_included:
                        actual_unit_price = (float(line.get('subtotal_tax')) + float(line.get('subtotal'))) / float(
                            line.get('quantity'))
                    else:
                        actual_unit_price = float(line.get('subtotal')) / float(line.get('quantity'))
                    if tax_included and float(total_discount) > 0.0:
                        discount_value += calclulate_line_discount(line) if order_discount else 0.0
                    self.create_woo_sale_order_line(line, tax_ids, product, line.get('quantity'), fiscal_position,
                                                    partner, pricelist_id, product.name, sale_order, actual_unit_price,
                                                    False)

                shipping_tax_ids = []
                for line in order.get('shipping_lines', []):
                    if shipping_taxable and float(order.get('shipping_tax')) > 0.0:
                        shipping_tax_ids = self.get_woo_tax_id_ept(instance, tax_datas, False)
                    else:
                        shipping_tax_ids = []

                    delivery_method = line.get('method_title')
                    if delivery_method:
                        carrier = self.env['delivery.carrier'].search([('woo_code', '=', delivery_method)], limit=1)
                        if not carrier:
                            carrier = self.env['delivery.carrier'].search([('name', '=', delivery_method)], limit=1)
                        if not carrier:
                            carrier = self.env['delivery.carrier'].search(
                                ['|', ('name', 'ilike', delivery_method), ('woo_code', 'ilike', delivery_method)],
                                limit=1)
                        if not carrier:
                            carrier = self.env['delivery.carrier'].create(
                                {'name': delivery_method, 'woo_code': delivery_method,
                                 'fixed_price': line.get('total')})
                        sale_order.write({'carrier_id': carrier.id})
                        if carrier.product_id:
                            shipping_product = carrier.product_id
                    line = self.create_woo_sale_order_line(line, shipping_tax_ids, shipping_product, 1, fiscal_position,
                                                           partner, pricelist_id,
                                                           shipping_product and shipping_product.name or line.get(
                                                               'method_title'), sale_order, line.get('total'), True)
                if order_discount and discount_value:
                    self.create_woo_sale_order_line({}, tax_ids, instance.discount_product_id, 1, fiscal_position,
                                                    partner, pricelist_id, instance.discount_product_id.name,
                                                    sale_order, discount_value * -1, False)
                fee_lines = order.get("fee_lines", [])
                for fee_line in fee_lines:
                    fee_value = fee_line.get("total")
                    fee = fee_line.get("title")
                    fee_line_tax_ids = []
                    fee_line_tax_ids = self.get_woo_tax_id_ept(instance, tax_datas, False)
                    if fee_value:
                        self.create_woo_sale_order_line({}, fee_line_tax_ids, instance.fee_line_id, 1, fiscal_position,
                                                        partner, pricelist_id, fee, sale_order, fee_value, False)
            if import_order_ids:
                self.env['sale.workflow.process.ept'].auto_workflow_process(ids=import_order_ids)
                odoo_orders = self.browse(import_order_ids)
                for order in odoo_orders:
                    order.invoice_shipping_on_delivery = False
        return True

    @api.model
    def import_new_woo_orders(self, instance=False, before_date=False, after_date=False, is_cron=True):
        """
        @Modify by :Haresh Mori on date 22/04/2019
        Add new functionality to import order base on date wise.
        """
        instances = []
        pos_order = self.env['pos.order']
        transaction_log_obj = self.env["woo.transaction.log"]
        product_product = self.env['product.product']
        if not instance:
            instances = self.env['woo.instance.ept'].search(
                [('order_auto_import', '=', True), ('state', '=', 'confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            instance.last_synced_order_date = before_date
            wcapi = instance.connect_in_woo()
            order_ids = []
            # Converting the after_date and before_date according to timezone. @author:Priya Pal 8th Jan 2020
            if instance.store_timezone:
                after_date = datetime.strptime(pytz.utc.localize(after_date).astimezone(
                    pytz.timezone(instance.store_timezone[:19] or 'UTC')).strftime('%Y-%m-%d %H:%M:%S'),
                                               "%Y-%m-%d %H:%M:%S")
                before_date = datetime.strptime(pytz.utc.localize(before_date).astimezone(
                            pytz.timezone(instance.store_timezone[:19] or 'UTC')).strftime(
                            '%Y-%m-%d %H:%M:%S'), "%Y-%m-%d %H:%M:%S")

            for order_status in instance.import_order_status_ids:
                # instance.last_synced_order_date = before_date
                if before_date and after_date:
                    response = wcapi.get('orders?after=%s&before=%s&status=%s&per_page=100' % (
                    after_date, before_date, order_status.status))
                else:
                    response = wcapi.get('orders?status=%s&per_page=100' % (order_status.status))
                if not isinstance(response, requests.models.Response):
                    transaction_log_obj.create(
                        {'message': "Import Orders \nResponse is not in proper format :: %s" % (response),
                         'mismatch_details': True,
                         'type': 'sales',
                         'woo_instance_id': instance.id
                         })
                    continue
                if response.status_code not in [200, 201]:
                    message = "Error in Import Orders %s" % (response.content)
                    transaction_log_obj.create(
                        {'message': message,
                         'mismatch_details': True,
                         'type': 'sales',
                         'woo_instance_id': instance.id
                         })
                    continue
                try:
                    order_ids = order_ids + response.json()
                except Exception as e:
                    transaction_log_obj.create({
                                                   'message': "Json Error : While import Orders from WooCommerce for instance %s. \n%s" % (
                                                   instance.name, e),
                                                   'mismatch_details': True,
                                                   'type': 'sales',
                                                   'woo_instance_id': instance.id
                                                   })
                    continue
                total_pages = response.headers.get('x-wp-totalpages')
                if int(total_pages) >= 2:
                    for page in range(2, int(total_pages) + 1):
                        order_ids = order_ids + self.import_all_woo_orders(wcapi, instance, transaction_log_obj,
                                                                           order_status, page, after_date, before_date,
                                                                           is_cron)

            import_order_ids = []

            for order in order_ids:
                tax_included = instance.tax_included
                if pos_order.search([('woo_instance_id', '=', instance.id), ('woo_order_id', '=', order.get('id')),
                                ('woo_order_number', '=', order.get('number'))]):
                    continue
                lines = order.get('line_items')
                if self.check_woo_mismatch_details(lines, instance, order.get('number')):
                    continue
                financial_status = 'paid'
                if order.get('transaction_id'):
                    financial_status = 'paid'
                elif order.get('date_paid') and order.get('payment_method') != 'cod' and order.get(
                        'status') == 'processing':
                    financial_status = 'paid'
                else:
                    financial_status = 'not_paid'

                no_payment_gateway = False
                payment_gateway = self.create_or_update_payment_gateway(instance, order)

                if not payment_gateway:
                    no_payment_gateway = self.verify_order(instance, order)
                    if not no_payment_gateway:
                        message = "Payment Gateway not found for this order %s and financial status is %s" % (
                        order.get('number'), financial_status)
                        log = transaction_log_obj.search(
                            [('woo_instance_id', '=', instance.id), ('message', '=', message)])
                        if not log:
                            transaction_log_obj.create(
                                {'message': message,
                                 'mismatch_details': True,
                                 'type': 'sales',
                                 'woo_instance_id': instance.id
                                 })
                        continue

                workflow = False
                if not no_payment_gateway and payment_gateway:
                    workflow_config = self.env['woo.sale.auto.workflow.configuration'].search(
                        [('woo_instance_id', '=', instance.id), ('financial_status', '=', financial_status),
                         ('payment_gateway_id', '=', payment_gateway.id)], limit=1)
                    workflow = workflow_config and workflow_config.auto_workflow_id or False

                if no_payment_gateway and not payment_gateway:
                    payment_gateway = self.env['woo.payment.gateway'].search([
                        ("code", "=", "no_payment_method"), ("woo_instance_id", "=", instance.id)])
                    workflow_config = self.env['woo.sale.auto.workflow.configuration'].search(
                        [('woo_instance_id', '=', instance.id), ('financial_status', '=', financial_status),
                         ('payment_gateway_id', '=', payment_gateway.id)], limit=1)
                    workflow = workflow_config and workflow_config.auto_workflow_id or False

                if not workflow:
                    message = "Workflow Configuration not found for this order %s, financial status is %s and Payment Gateway is %s" % (
                    order.get('number'), financial_status, order.get('payment_method'))
                    log = transaction_log_obj.search([('woo_instance_id', '=', instance.id), ('message', '=', message)])
                    if not log:
                        transaction_log_obj.create(
                            {'message': message,
                             'mismatch_details': True,
                             'type': 'sales', 'woo_instance_id': instance.id
                             })
                    continue
                woo_customer_id = order.get('customer_id', False)
                partner = order.get('billing', False) and self.create_or_update_woo_customer(woo_customer_id,
                                                                                             order.get('billing'),
                                                                                             False, False, False,
                                                                                             instance)
                if not partner:
                    message = "Customer Not Available In %s Order" % (order.get('number'))
                    log = transaction_log_obj.search([('woo_instance_id', '=', instance.id), ('message', '=', message)])
                    if not log:
                        transaction_log_obj.create(
                            {'message': message,
                             'mismatch_details': True,
                             'type': 'sales',
                             'woo_instance_id': instance.id
                             })
                    continue
                shipping_address = order.get('shipping', False) and self.create_or_update_woo_customer(False, order.get(
                    'shipping'), False, partner.id, 'delivery', instance) or partner
                new_record = self.new({'partner_id': partner.id})
                #new_record.onchange_partner_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                new_record = pos_order.new(retval)
                #new_record.onchange_partner_shipping_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})

                fiscal_position = partner.property_account_position_id
                pricelist_id = retval.get('pricelist_id', False)
                payment_term = retval.get('payment_term_id', False)
                woo_order_vals = self.get_woo_order_vals(order, workflow, partner, instance, partner, shipping_address,
                                                         pricelist_id, fiscal_position, payment_term, payment_gateway)
                sale_order = pos_order.create(woo_order_vals) if woo_order_vals else False

                if not sale_order:
                    continue
                #                 sale_order.onchange_partner_id()
                #                 sale_order.onchange_partner_shipping_id()
                #                 if not fiscal_position:
                #                     sale_order.write({'fiscal_position_id':False})
                if tax_included:
                    total_discount = float(order.get('discount_total', 0.0)) + float(order.get('discount_tax', 0.0))
                if not tax_included:
                    total_discount = float(order.get('discount_total', 0.0))

                import_order_ids.append(sale_order.id)
                shipping_taxable = False
                tax_datas = []
                tax_ids = []
                for tax_line in order.get('tax_lines'):
                    rate_id = tax_line.get('rate_id')
                    if rate_id:
                        res_rate = wcapi.get('taxes/%s' % (rate_id))
                        try:
                            rate = res_rate.json()
                        except Exception as e:
                            transaction_log_obj.create({
                                                           'message': "Json Error : While retrive Product tax id %s from WooCommerce for instance %s. \n%s" % (
                                                           rate_id, instance.name, e),
                                                           'mismatch_details': True,
                                                           'type': 'sales',
                                                           'woo_instance_id': instance.id
                                                           })
                            continue
                        tax_datas.append(rate)
                        shipping_taxable = rate.get('shipping')
                tax_ids = self.get_woo_tax_id_ept(instance, tax_datas, tax_included)
                product = False
                for line in lines:
                    woo_product = self.create_or_update_woo_product(line, instance, wcapi)
                    if not woo_product:
                        continue
                    product_url = woo_product and woo_product.producturl or False
                    if product_url:
                        line.update({'product_url': product_url})
                    product = woo_product.product_id
                    actual_unit_price = 0.0
                    if tax_included:
                        actual_unit_price = (float(line.get('subtotal_tax')) + float(line.get('subtotal'))) / float(
                            line.get('quantity'))
                    else:
                        actual_unit_price = float(line.get('subtotal')) / float(line.get('quantity'))
                    taxes = product.taxes_id.ids
                    self.create_woo_sale_order_line(line, [(6, 0, taxes)], product, line.get('quantity'),
                                                    fiscal_position, partner, sale_order.pricelist_id.id, product.name,
                                                    sale_order, actual_unit_price, False)

                shipping_tax_ids = []
                product_template_obj = self.env['product.template']
                for line in order.get('shipping_lines', []):
                    product = False
                    delivery_method = line.get('method_title')
                    shipping_product = product_product
                    if delivery_method:
                        carrier = self.env['delivery.carrier'].search([('woo_code', '=', delivery_method)], limit=1)
                        if not carrier:
                            carrier = self.env['delivery.carrier'].search([('name', '=', delivery_method)], limit=1)
                        if not carrier:
                            carrier = self.env['delivery.carrier'].search(
                                ['|', ('name', 'ilike', delivery_method), ('woo_code', 'ilike', delivery_method)],
                                limit=1)
                        if not carrier:
                            product_template = product_template_obj.search(
                                [('name', '=', delivery_method), ('type', '=', 'service')], limit=1)
                            if not product_template:
                                product_template = product_template_obj.create(
                                    {'name': delivery_method, 'type': 'service'})
                            carrier = self.env['delivery.carrier'].create(
                                {'name': delivery_method, 'woo_code': delivery_method, 'fixed_price': line.get('total'),
                                 'product_id': product_template.product_variant_ids[0].id})
                        sale_order.write({'carrier_id': carrier.id})
                        if carrier.product_id:
                            shipping_product = carrier.product_id
                    shipping_tax_ids = [(6, 0, shipping_product.taxes_id.ids)]
                    line = self.create_woo_sale_order_line(line, shipping_tax_ids, shipping_product, 1, fiscal_position,
                                                           partner, sale_order.pricelist_id.id,
                                                           shipping_product and shipping_product.name or line.get(
                                                               'method_title'), sale_order, line.get('total'), True)
                if total_discount > 0.0:
                    self.create_woo_sale_order_line({}, tax_ids, instance.discount_product_id, 1, fiscal_position,
                                                    partner, sale_order.pricelist_id.id,
                                                    instance.discount_product_id.name, sale_order, total_discount * -1,
                                                    False)

                fee_lines = order.get("fee_lines", [])
                for fee_line in fee_lines:
                    fee_value = fee_line.get("total")
                    fee = fee_line.get("name")
                    fee_line_tax_ids = []
                    fee_line_tax_ids = self.get_woo_tax_id_ept(instance, tax_datas, False)
                    if fee_value:
                        self.create_woo_sale_order_line({}, fee_line_tax_ids, instance.fee_line_id, 1, fiscal_position,
                                                        partner, pricelist_id, fee, sale_order, fee_value, False)
            # if import_order_ids:
                # for pos orders we do not need this
                # self.env['sale.workflow.process.ept'].auto_workflow_process(ids=import_order_ids)
                # odoo_orders = self.browse(import_order_ids)
                # for order in odoo_orders:
                #     order.invoice_shipping_on_delivery = False
        return True

    @api.model
    def create_woo_sale_order_line(self, line, tax_ids, product, quantity, fiscal_position, partner, pricelist_id, name, order, price, is_shipping=False):
        sale_order_line_obj = self.env['pos.order.line']
       # uom_id = product and product.uom_id and product.uom_id.id or False
        product_data = {
                      'product_id':product and product.ids[0] or False,
                      'order_id':order.id,
                      'company_id':order.company_id.id,
                      'name':name,
                      'producturl':line.get('product_url') or False
                    }
        tmp_rec = sale_order_line_obj.new(product_data)
        #tmp_rec.product_id_change()
        so_line_vals = sale_order_line_obj._convert_to_write({name: tmp_rec[name] for name in tmp_rec._cache})
        if tax_ids:
            tax_ids = tax_ids and self.env['account.tax'].search([('id', 'in', tax_ids[0][2])])
        if fiscal_position:
            tax_ids = fiscal_position.map_tax(tax_ids, product[0], order.partner_id) if fiscal_position else tax_ids
        tax_amount = sum([t.amount for t in tax_ids]) / 100.0
        so_line_vals.update(
                            {
                            'order_id':order.id,
                            'qty':quantity,
                            'price_unit':price,
                            'woo_line_id':line.get('id'),
                            'is_delivery':is_shipping,
                            'tax_ids':tax_ids and [(6, 0, tax_ids.ids)] or [(6, 0, [])],
                            'price_subtotal': float(price) * float(quantity),
                            'price_subtotal_incl':(1 + tax_amount) * (float(price) * float(quantity)),

                            }
                            )
        woo_so_line_vals = sale_order_line_obj.create_sale_order_line_ept(so_line_vals)
        woo_so_line_vals.update({'woo_line_id':line.get('id')})
        woo_so_line_vals.update({'tax_ids': tax_ids and [(6, 0, tax_ids.ids)] or [(6, 0, [])]})
        line = sale_order_line_obj.create(woo_so_line_vals)
        return line

