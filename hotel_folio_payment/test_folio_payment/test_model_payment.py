from odoo.tests import common

class TestModelAccountPayment(common.TransactionCase):

    def testPaymentPrint(self):
        records = self.env['account.payment'].search([('state', '!=', 'draft')])
        records[0].payment_print()
