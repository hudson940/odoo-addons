# -*- coding: utf-8 -*-

import time
import datetime
from odoo import models, fields, api, _
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import except_orm, ValidationError


def _offset_format_timestamp1(src_tstamp_str, src_format, dst_format,
                              ignore_unparsable_time=True, context=None):
    """
    Convert a source timeStamp string into a destination timeStamp string,
    attempting to apply the correct offset if both the server and local
    timeZone are recognized,or no offset at all if they aren't or if
    tz_offset is false (i.e. assuming they are both in the same TZ).

    @param src_tstamp_str: the STR value containing the timeStamp.
    @param src_format: the format to use when parsing the local timeStamp.
    @param dst_format: the format to use when formatting the resulting
     timeStamp.
    @param server_to_client: specify timeZone offset direction (server=src
                             and client=dest if True, or client=src and
                             server=dest if False)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str
                                   cannot be parsed using src_format or
                                   formatted using dst_format.
    @return: destination formatted timestamp, expressed in the destination
             timezone if possible and if tz_offset is true, or src_tstamp_str
             if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False
    res = src_tstamp_str
    if src_format and dst_format:
        try:
            # dt_value needs to be a datetime.datetime object\
            # (so notime.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.datetime.strptime(src_tstamp_str, src_format)
            if context.get('tz', False):
                try:
                    import pytz
                    src_tz = pytz.timezone(context['tz'])
                    dst_tz = pytz.timezone('UTC')
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception:
            # Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
            pass
    return res


class HotelFolioInherit(models.Model):
    _inherit = 'hotel.folio'

    @api.model
    def _get_checkin_date(self):
        if self._context.get('tz'):
            to_zone = self._context.get('tz')
        else:
            to_zone = 'UTC'
        tm_delta = datetime.timedelta(minutes=20)
        return datetime.datetime.strptime(_offset_format_timestamp1
                                          (time.strftime("%Y-%m-%d %H:%M:%S"),
                                           DEFAULT_SERVER_DATETIME_FORMAT,
                                           DEFAULT_SERVER_DATETIME_FORMAT,
                                           ignore_unparsable_time=True,
                                           context={'tz': to_zone}),
                                          '%Y-%m-%d %H:%M:%S') + tm_delta

    @api.model
    def _get_checkout_date(self):
        if self._context.get('tz'):
            to_zone = self._context.get('tz')
        else:
            to_zone = 'UTC'
        tm_delta = datetime.timedelta(days=1)
        return datetime.datetime.strptime(_offset_format_timestamp1
                                          (time.strftime("%Y-%m-%d 13:00:00"),
                                           DEFAULT_SERVER_DATETIME_FORMAT,
                                           DEFAULT_SERVER_DATETIME_FORMAT,
                                           ignore_unparsable_time=True,
                                           context={'tz': to_zone}),
                                          '%Y-%m-%d %H:%M:%S') + tm_delta

    # checkin_date = fields.Date('Check In', required=True, readonly=True,
    #                                states={'draft': [('readonly', False)]},
    #                                default=_get_checkin_date)
    #
    # checkout_date = fields.Date('Check Out', required=True, readonly=True,
    #                                 states={'draft': [('readonly', False)]},
    #                                 default=_get_checkout_date)

    @api.onchange('checkout_date', 'checkin_date')
    def onchange_dates(self):
        '''
        This method gives the duration between check in and checkout
        if customer will leave only for some hour it would be considers
        as a whole day.If customer will check in checkout for more or equal
        hours, which configured in company as additional hours than it would
        be consider as full days
        --------------------------------------------------------------------
        @param self: object pointer
        @return: Duration and checkout_date
        '''
        configured_addition_hours = 0
        wid = self.warehouse_id
        whouse_com_id = wid or wid.company_id
        if whouse_com_id:
            configured_addition_hours = wid.company_id.additional_hours
        myduration = 0
        chckin = self.checkin_date
        chckout = self.checkout_date
        if chckin and chckout:
            server_dt = DEFAULT_SERVER_DATETIME_FORMAT
            chkin_dt = datetime.datetime.strptime(chckin, server_dt)
            chkout_dt = datetime.datetime.strptime(chckout, server_dt)
            dur = chkout_dt - chkin_dt
            sec_dur = dur.seconds
            if (not dur.days and not sec_dur) or (dur.days and not sec_dur):
                myduration = dur.days
            else:
                myduration = dur.days + 1
            #            To calculate additional hours in hotel room as per minutes
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60) / 60)
                if additional_hours >= configured_addition_hours:
                    myduration += 1
        self.duration = myduration
        self.duration_dummy = self.duration

    @api.multi
    def add_room_day(self):
        chckout = self.checkout_date
        if chckout:
            chckout = datetime.datetime.strptime(
                chckout, DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(days=1)
            chckout = chckout.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
            for line in self.room_lines:
                line.write({"checkout_date": chckout})
                line.on_change_checkout()
            for line in self.service_lines:
                line.write({"ser_checkout_date": chckout})
                line.on_change_checkout()
            self.write({"checkout_date": chckout})
            self.onchange_dates()

            return True

    @api.multi
    def action_checkout(self):
        chckout = self.checkout_date
        if chckout:
            if self.invoice_status !='invoiced':
                chckout = datetime.datetime.strptime(
                    chckout, DEFAULT_SERVER_DATETIME_FORMAT)
                chckout = datetime.datetime.now()
                chckout = chckout.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT)
                for line in self.room_lines:
                    line.write({"checkout_date": chckout})
                    line.on_change_checkout()
                for line in self.service_lines:
                    line.write({"ser_checkout_date": chckout})
                    line.on_change_checkout()
                self.write({"checkout_date": chckout})
                self.onchange_dates()

                if self.amount_balance > 0:
                    raise ValidationError(_('El balance debe ser 0 ó haber generado la factura'))

            for room in self.room_lines:
                room.color= 6
                room.status= 'dirty'

            self.write({'hotel_policy': 'picking'})

            return True

    @api.multi
    def action_add_order(self):
        '''
                when add order button is clicked then this method is called.
            -------------------------------------------------------------------
            @param self: object pointer
        '''
        ctx = dict(self._context)
        view_order = self.env.ref(
            'hotel_personalizado.view_hotel_restaurant_order_form2')

        ctx.update({'folio_id': self.id,
                    'partner_id': self.partner_id.id,
                    'room_id': self.room_lines[0].product_id.id}, )
        self.env.args = misc.frozendict(ctx)

        return {'name': _('Nueva Orden'),
                'res_model': 'hotel.restaurant.order',
                'type': 'ir.actions.act_window',
                'views': [(view_order.id, 'form')],
                'view_id': view_order.id,
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_folio_id': ctx.get('folio_id'),
                            'default_is_folio': True,
                            'default_cname': ctx.get('partner_id'),
                            'default_room_no': ctx.get('room_id'),

                            },
                'target': 'new'
                }


# for use without datetimes
# class FolioRoomLineInherit(models.Model):
#
#     _inherit = 'folio.room.line'
#     check_in = fields.Date('Check In Date', required=True)
#     check_out = fields.Date('Check Out Date', required=True)


class HotelFolioLineInherit(models.Model):

    @api.model
    def _get_checkin_date(self):
        if 'checkin' in self._context:
            return self._context['checkin']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.model
    def _get_checkout_date(self):
        if 'checkout' in self._context:
            return self._context['checkout']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.onchange('checkin_date', 'checkout_date')
    def on_change_checkout(self):
        '''
        When you change checkin_date or checkout_date it will checked it
        and update the qty of hotel folio line
        -----------------------------------------------------------------
        @param self: object pointer
        '''
        configured_addition_hours = 0
        fwhouse_id = self.folio_id.warehouse_id
        fwc_id = fwhouse_id or fwhouse_id.company_id
        if fwc_id:
            configured_addition_hours = fwhouse_id.company_id.additional_hours
        myduration = 0
        if not self.checkin_date:
            self.checkin_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if not self.checkout_date:
            self.checkout_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        chckin = self.checkin_date
        chckout = self.checkout_date
        if chckin and chckout:
            server_dt = DEFAULT_SERVER_DATETIME_FORMAT
            chkin_dt = datetime.datetime.strptime(chckin, server_dt)
            chkout_dt = datetime.datetime.strptime(chckout, server_dt)
            dur = chkout_dt - chkin_dt
            sec_dur = dur.seconds
            if (not dur.days and not sec_dur) or (dur.days and not sec_dur):
                myduration = dur.days
            else:
                myduration = dur.days + 1
            # To calculate additional hours in hotel room as per minutes
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60) / 60)
                if additional_hours >= configured_addition_hours:
                    myduration += 1
        self.product_uom_qty = myduration
        hotel_room_obj = self.env['hotel.room']
        hotel_room_ids = hotel_room_obj.search([])
        avail_prod_ids = []
        for room in hotel_room_ids:
            assigned = False
            for rm_line in room.room_line_ids:
                if rm_line.status != 'cancel':
                    if (self.checkin_date <= rm_line.check_in <=
                        self.checkout_date) or (self.checkin_date <=
                                                rm_line.check_out <=
                                                self.checkout_date):
                        assigned = True
                    elif (rm_line.check_in <= self.checkin_date <=
                          rm_line.check_out) or (rm_line.check_in <=
                                                 self.checkout_date <=
                                                 rm_line.check_out):
                        assigned = True
            if not assigned:
                avail_prod_ids.append(room.product_id.id)
        domain = {'product_id': [('id', 'in', avail_prod_ids)]}
        return {'domain': domain}

    _inherit = 'hotel.folio.line'

    # checkin_date = fields.Date('Check In', required=True,
    #                            default=_get_checkin_date)
    # checkout_date = fields.Date('Check Out', required=True,
    #                             default=_get_checkout_date)


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'
    # birthday_date = fields.Date('Birthday date')


class HotelRoomInherit(models.Model):
    _inherit = 'hotel.room'

    status = fields.Selection([('available', 'Available'),
                               ('occupied', 'Occupied'),
                               ('dirty', 'Dirty')],
                              'Status', default='available')
