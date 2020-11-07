import requests
from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    woo_order_id = fields.Char("Woo Order Reference", help="WooCommerce Order Reference")
    woo_order_number = fields.Char("Order Number", help="WooCommerce Order Number")
    auto_workflow_process_id = fields.Many2one("sale.workflow.process.ept", "Auto Workflow")
    woo_instance_id = fields.Many2one("woo.instance.ept", "Woo Instance")
    payment_gateway_id = fields.Many2one("woo.payment.gateway", "Woo Payment Gateway")
    woo_trans_id = fields.Char("Transaction Id", help="WooCommerce Order Transaction Id")
    woo_customer_ip = fields.Char("Customer IP", help="WooCommerce Customer IP Address")
   # visible_trans_id = fields.Boolean("trans_id_avail", compute=visibl_transaction_id, store=False)
    global_channel_id = fields.Many2one('global.channel.ept', string="Global Channel")
    updated_in_woo = fields.Boolean()

    def mark_sent_woo(self):
        pass

    def mark_not_sent_woo(self):
        pass

    def _prepare_done_order_for_pos(self):
        res = super(PosOrder, self)._prepare_done_order_for_pos()
        res['note'] = self.note
        return res

    def update_woo_order_status(self):
        transaction_log_obj = self.env["woo.transaction.log"]
        for rec in self:
            try:
                if rec.updated_in_woo or not rec.woo_instance_id:
                    continue
                instance = rec.woo_instance_id
                wcapi = instance.connect_in_woo()
                info = {"status": "completed"}
                data = info
                if instance.woo_version == 'old':
                    data = {"order": info}
                    response = wcapi.put('orders/%s' % (rec.woo_order_id), data)
                else:
                    data.update({"id": rec.woo_order_id})
                    response = wcapi.post('orders/batch', {'update': [data]})
                if not isinstance(response, requests.models.Response):
                    message = "Update Orders %s Status \nResponse is not in proper format :: %s" % (rec.name, response)
                    log = transaction_log_obj.search([('woo_instance_id', '=', instance.id), ('message', '=', message)])
                    if not log:
                        transaction_log_obj.create({'message': message,
                                                     'mismatch_details':True,
                                                     'type':'sales',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                if response.status_code not in [200, 201]:
                    message = "Error in update order %s status,  %s" % (rec.name, response.content)
                    log = transaction_log_obj.search([('woo_instance_id', '=', instance.id), ('message', '=', message)])
                    if not log:
                        transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'sales',
                                             'woo_instance_id':instance.id
                                            })
                        continue
                try:
                    result = response.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update Orders status for order no. %s to WooCommerce for instance %s. \n%s" % (rec.woo_order_id, instance.name, e),
                                 'mismatch_details':True,
                                 'type':'sales',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if instance.woo_version == 'old':
                    errors = result.get('errors', '')
                    if errors:
                        message = errors[0].get('message')
                        transaction_log_obj.create(
                                                    {'message':"Error in update order status,  %s" % (message),
                                                     'mismatch_details':True,
                                                     'type':'sales',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                    else:
                        rec.write({'updated_in_woo': True})
                elif instance.woo_version == 'new':
                    rec.write({'updated_in_woo': True})
            except Exception as e:
                transaction_log_obj.create(
                    {
                        'message': "Json Error : While update Orders status for order no. %s to WooCommerce for instance %s. \n%s" % (
                            rec.woo_order_id, rec.woo_instance_id.name, e),
                        'mismatch_details': True,
                        'type': 'sales',
                        'woo_instance_id': rec.woo_instance_id.id
                    })
            return True


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        res = super(PosMakePayment, self).check()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        order.update_woo_order_status()
        return res

