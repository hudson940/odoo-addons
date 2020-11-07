from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    producturl = fields.Char()
    woo_line_id = fields.Char()
    is_delivery = fields.Boolean()


    def create_sale_order_line_ept(self,vals):
        """
            pass Dictionary
            vals = {'order_id':order_id,'product_id':product_id,'company_id':company_id,
            'description':product_name,'order_qty':qty,'price_unit':price,'discount':discount}
            Required Parameter :- order_id,name,product_id
        """
        sale_order_line = self.env['pos.order.line']
        order_line = {
            'order_id':vals.get('order_id'),
            'product_id':vals.get('product_id',''),
            'company_id':vals.get('company_id',''),
            'name':vals.get('description'),
            # 'product_uom':vals.get('product_uom')
        }
        new_order_line = sale_order_line.new(order_line)
        #new_order_line.product_id_change()
        order_line = sale_order_line._convert_to_write({name:new_order_line[name] for name in new_order_line._cache})
        price = float(vals.get('price_unit',0.0))
        quantity = float(vals.get('qty',0.0))
        order_line.update({
            'order_id':vals.get('order_id'),
            'qty': quantity,
            'price_unit': price,
            'discount':vals.get('discount',0.0),
            'price_subtotal': price * quantity,
            'price_subtotal_incl': price * quantity,
            #'state':'draft',
        })
        return order_line