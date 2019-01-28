# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import misc
from odoo.exceptions import except_orm


class HotelFolioInherit(models.Model):
    _inherit = 'hotel.folio'

    @api.multi
    def _compute_amount_payments(self):
        '''
        amount_payment will display on change of payment_lines
        ----------------------------------------------------
        @param self: object pointer
        '''
        for sale in self:
            sale.amount_payments = sum(line.amount for line
                                       in sale.payment_lines)

    @api.depends('amount_untaxed', 'amount_tax')
    def _compute_balance(self):
        '''
        amount_total will display on change of amount_subtotal
        -------------------------------------------------------
        @param self: object pointer
        '''
        for line in self:
            line.amount_balance = (line.amount_untaxed +
                                   line.amount_tax) - line.amount_payments

    @api.onchange('room_lines', 'service_lines', 'payment_lines')
    def onchage_amounts(self):
        self.button_dummy()

    @api.multi
    def button_dummy(self):
        '''
        @param self: object pointer
        '''
        self.order_id.button_dummy()
        for folio in self:
            folio.amount_balance = (folio.amount_untaxed +
                                    folio.amount_tax) - folio.amount_payments
        return True

    @api.multi
    def action_payment(self):
        '''
                when payment button is clicked then this method is called.
               -------------------------------------------------------------------
               @param self: object pointer
        '''
        ctx = dict(self._context)
        view_payment = self.env.ref(
            'hotel_folio_payment.view_account_payment_folio_form')

        if self.partner_id.id != 0:
            ctx.update({'folio_id': self.id, 'guest': self.partner_id.id})
            self.env.args = misc.frozendict(ctx)
        else:
            raise except_orm(_('Warning'), _('Please Reserve Any Room.'))
        return {'name': _('Register Payment'),
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'views': [(view_payment.id, 'form')],
                'view_id': view_payment.id,
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_folio_id': ctx.get('folio_id'),
                            'default_partner_id': ctx.get('guest'),
                            'default_payment_type': 'inbound',
                            },
                'target': 'new'
                }

    @api.multi
    def action_invoice_create(self):
        invoice_id = super(HotelFolio, self).action_invoice_create()
        for payment in self.payment_lines:
            payment.write({'invoice_ids': [(4, invoice_id.id, None)]})

    payment_lines = fields.One2many('account.payment', 'folio_id',
                                    readonly=True,
                                    states={'draft': [('readonly', False)],
                                            'sent': [('readonly', False)]},
                                    help="Payments for this folio", copy=False
                                    )
    amount_payments = fields.Monetary(
        compute='_compute_amount_payments', readonly=True, string='Total Payments', copy=False)

    amount_balance = fields.Monetary(string='Balance', store=False, readonly=True, compute='_compute_balance',
                                     track_visibility='always', copy=False)


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def payment_print(self):
        """ Print and validate the payment 
        """
        if self.state == 'draft':
            self.post()
        return self.env['report'].get_action(self, 'hotel_folio_payment.report_receipt')

    folio_id = fields.Many2one('hotel.folio', 'Folio', ondelete='restrict')
