from odoo import _, models, api, fields
from odoo.exceptions import ValidationError

TZ = 'UTC-5'

class WizardAccountClean(models.TransientModel):
    _name = 'wizard.account.clean'

    date_from = fields.Date()
    date_to = fields.Date()

    message = fields.Text()
    is_done = fields.Boolean()

    percentage = fields.Float('Percentage %')

    pos_order_ids = fields.Many2many('pos.order', 'wizard_account_clean_pos_order', 'clean_id', 'order_id', compute='_compute_values')

    pos_session_ids = fields.Many2many('pos.session', compute='_compute_values')

    total_amount = fields.Float(compute='_compute_values')

    total_amount_after = fields.Float(compute='_compute_values')

    pos_ids = fields.Many2many('pos.config',
                              'wizard_account_clean_pos_config', 'clean_id', 'pos_id', string='Point of Sale')



    @api.depends('date_from', 'date_to', 'percentage', 'pos_ids')
    def _compute_values(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                sql = '''
select po.id as po_id, ps.id as ps_id, amount_total from pos_order po
left join pos_session ps on po.session_id = ps.id
left join pos_config pc on ps.config_id = pc.id
where (ps.create_date at time zone '{tz}')::date >= '{date_from}' 
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
    and po.partner_id is null
{where_pos_id}
                '''.format(
                    date_from=rec.date_from, date_to=rec.date_to, tz=TZ,
                    where_pos_id='and pc.id in (%s)' % ','.join([str(n) for n in rec.pos_ids.ids]) if rec.pos_ids.ids else '')
                self.env.cr.execute(sql)
                data = self.env.cr.dictfetchall()
                if data:
                    rec.pos_order_ids = isinstance(data, (list, tuple)) and self.env['pos.order'].browse([d.get('po_id') for d in data])
                    rec.pos_session_ids = isinstance(data, (list, tuple)) and self.env['pos.session'].browse(list(set([d.get('ps_id') for d in data])))
                    totals = isinstance(data, (list, tuple)) and [r.get('amount_total') for r in data]
                    rec.total_amount = totals and sum(totals)
                    if not rec.is_done:
                        rec.total_amount_after = rec.total_amount and rec.total_amount * (1 - (rec.percentage / 100))
                else:
                    rec.pos_order_ids = False
                    rec.pos_session_ids = False
                    rec.total_amount = 0
            else:
                rec.pos_order_ids = False
                rec.pos_session_ids = False
                rec.total_amount = 0
    @api.onchange('percentage')
    def _onchange_form(self):
        for rec in self:
            rec._check_values()

    def compute_preview(self):
        self._compute_values()
        return self.return_form_view()

    @api.constrains('percentage')
    def _check_values(self):
        self.ensure_one()
        if self.percentage < -100 or self.percentage > 100:
            raise ValidationError(_('Incorrect percentage value'))

    def validate(self):
        if not self.percentage:
            raise ValidationError(_('Incorrect percentage value'))
        sql = """
with account_clean_view as (
select pol.id from pos_order_line pol
left join pos_order po on pol.order_id = po.id
left join pos_session ps on po.session_id = ps.id
left join pos_config pc on ps.config_id = pc.id
where (ps.create_date at time zone '{tz}')::date >= '{date_from}' 
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
    and po.partner_id is null
{where_pos_id}
)
update pos_order_line
set price_unit = price_unit * (1 - {percent}),
    price_subtotal = price_subtotal * (1 - {percent}),
    price_subtotal_incl = price_subtotal_incl * (1 - {percent})
from account_clean_view
where 
    pos_order_line.id = account_clean_view.id;

with account_clean_view as (
select po.id from pos_order po
left join pos_session ps on po.session_id = ps.id
left join pos_config pc on ps.config_id = pc.id
where (ps.create_date at time zone '{tz}')::date >= '{date_from}' 
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
    and po.partner_id is null
{where_pos_id}
)
update pos_order
set amount_tax = amount_tax * (1 - {percent}),
    amount_total = amount_total * (1 - {percent}),
    amount_paid = round(amount_paid * (1 - {percent}),0)

from account_clean_view 
where pos_order.id = account_clean_view.id;
    
with account_clean_view as (
select aml.id as aml_id
from pos_session ps
left join pos_config pc on ps.config_id = pc.id
left join pos_order po on ps.id = po.session_id
left join account_move am on am.id = po.account_move
left join account_move_line aml on aml.move_id = am.id
where aml.partner_id is null
and (ps.create_date at time zone '{tz}')::date >= '{date_from}'
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
   {where_pos_id} 
    group by aml.id
union 
select aml.id
from pos_session ps
left join pos_config pc on ps.config_id = pc.id
left join account_bank_statement abs on abs.pos_session_id = ps.id
left join account_move_line aml on aml.statement_id = abs.id
left join account_move am on am.id = aml.move_id
where aml.partner_id is null and aml.id is not null
and (ps.create_date at time zone '{tz}')::date >= '{date_from}'
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
   {where_pos_id} 
group by aml.id
)
update account_move_line
set credit = credit * (1 - {percent}),
    debit = debit * (1 - {percent}),
    balance = balance * (1 - {percent})
from account_clean_view
    where aml_id = id 
;

with account_clean_view as (
    select am.id, sum(aml.debit) as amount_aml
    from account_move am
             left join account_move_line aml on am.id = aml.move_id
    group by am.id, am.amount
    having sum(aml.debit) != am.amount
)
update account_move
set  amount = acv.amount_aml
from account_clean_view acv
where acv.id = account_move.id;

with account_clean_view as (
select ap.id as ap_id
from pos_order po
    left join pos_session ps on po.session_id = ps.id
    left join pos_config pc on ps.config_id = pc.id
    left join account_payment ap on ap.name = ps.name
where (ap.partner_id is null or po.partner_id is null)
and (ps.create_date at time zone '{tz}')::date >= '{date_from}'
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
   {where_pos_id} 
    group by ap.id
)
update account_payment
set amount = amount  * (1 - {percent})
from account_clean_view 
where ap_id = id;

with account_clean_view as (
select absl.id as absl_id
from pos_order po
    left join pos_session ps on po.session_id = ps.id
    left join pos_config pc on ps.config_id = pc.id
    left join account_bank_statement abs on ps.id = abs.pos_session_id
    left join account_bank_statement_line absl on abs.id = absl.statement_id and absl.partner_id is null
where absl.id is not null and po.partner_id is null
and (ps.create_date at time zone '{tz}')::date >= '{date_from}'
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
       {where_pos_id} 
    group by absl.id
)
update account_bank_statement_line
set amount = amount  * (1 - {percent})
from account_clean_view
where id = absl_id;

with cte as (
select abs.id as abs_id, sum(absl.amount) as amount
from pos_order po
    left join pos_session ps on po.session_id = ps.id
    left join pos_config pc on ps.config_id = pc.id
    left join account_bank_statement abs on ps.id = abs.pos_session_id  
    left join account_bank_statement_line absl on abs.id = absl.statement_id and po.id = absl.pos_statement_id 
where abs.id is not null 
and (ps.create_date at time zone '{tz}')::date >= '{date_from}'
    and (ps.create_date at time zone '{tz}')::date <= '{date_to}'
    {where_pos_id} 
    group by abs.id
)
update account_bank_statement
set total_entry_encoding = cte.amount,
    balance_end_real = balance_start + cte.amount,
    balance_end = balance_start + cte.amount
from cte
where id = cte.abs_id;
    """.format(date_from=self.date_from, date_to=self.date_to, percent=self.percentage/100,
               tz=TZ, where_pos_id='and pc.id in (%s)' % ','.join([str(n) for n in self.pos_ids.ids]) if self.pos_ids.ids else '')
        self.env.cr.execute(sql)
        self.is_done = True
        self.message = 'Completed'
        return self.return_form_view()

    def return_form_view(self):
        view_id = self.env.ref(
            'account_clean.wizard_account_clean_form_view').id
        return {
            'name': _('Account Clean'),
            'res_model': 'wizard.account.clean',
            'type': 'ir.actions.act_window',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id
        }





