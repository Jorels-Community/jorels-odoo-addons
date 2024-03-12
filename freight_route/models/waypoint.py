# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of freight_route.
#
# freight_route is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# freight_route is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with freight_route.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import logging

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Waypoint(models.Model):
    _name = 'freight_route.waypoint'
    _description = 'Waypoint'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority asc'

    # 15 min
    DELTA_TIME = 15
    DELTA_TIME_FLOAT = 0.25

    # Sequence
    number = fields.Char(string='Number', required=True, copy=False, index=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'freight_route.waypoint'))
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency')
    manager_id = fields.Many2one('res.users', string='Manager', tracking=True,
                                 default=lambda self: self.env.user, copy=False)
    type = fields.Selection([
        ('carry', 'Carry'),
        ('delivery', 'Delivery')
    ], index=True, change_default=True,
        default=lambda self: self._context.get('type', 'delivery'),
        tracking=True)

    # Custom fields
    name = fields.Char(string='Name', required=False, default=None, compute='_compute_name', index=True, store=True,
                       copy=False)
    color = fields.Integer(string='Color', required=False, default=None, compute='_compute_color', store=True,
                           copy=False)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True, copy=False)

    # Time fields
    priority = fields.Integer(string='Priority', required=True, default=0, copy=False)
    scheduled_time = fields.Float(string="Scheduled time", required=True, default=0.0, copy=False)
    scheduled_datetime = fields.Datetime(string="Scheduled datetime", required=True, default=fields.Datetime.now,
                                         tracking=True, copy=False)

    # Related models
    customer_id = fields.Many2one(comodel_name='res.partner', string='Customer', required=True, default=None,
                                  index=True, tracking=True)
    carry_id = fields.Many2one(comodel_name='res.partner', string='Carry', required=True, default=None,
                               index=True, tracking=True)
    recipient_id = fields.Many2one(comodel_name='res.partner', string='Recipient', required=True, default=None,
                                   index=True, tracking=True)
    driver_id = fields.Many2one(comodel_name='res.partner', string='Driver', required=True, default=None,
                                tracking=True)
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle', required=True, default=None,
                                 index=True, tracking=True)

    # Other fields
    note = fields.Text(string='Note', required=False, default=None)
    image = fields.Binary(string='Image', attachment=True,
                          help=_("This field holds the image used as signature, limited to 1024x1024px."), copy=False)

    # Signature data
    signature_name = fields.Char(string='Name', required=False, default=None, copy=False, tracking=True)
    signature_vat = fields.Char(string='VAT', required=False, default=None, copy=False, tracking=True)

    # Merchandise data
    units = fields.Integer(string='Units', required=True, default=0, tracking=True)
    weight = fields.Integer(string='Weight/kg', required=True, default=0.0, tracking=True)
    content = fields.Char(string='Content', required=False, default=None, tracking=True)
    value = fields.Monetary(string='Goods value', required=True, default=0.0, currency_field='currency_id',
                            tracking=True)

    # Charges
    freight_value = fields.Monetary(string='Freight value', required=True, default=0.0, currency_field='currency_id', tracking=True)
    insurance_value = fields.Monetary(string='Insurance value', required=True, default=0.0, currency_field='currency_id',
                                tracking=True)
    others_value = fields.Monetary(string='Others value', required=True, default=0.0, currency_field='currency_id', tracking=True)
    total_value = fields.Monetary(string='Total value', compute='_compute_total_value', currency_field='currency_id', store=True,
                            tracking=True)
    payment_method = fields.Selection(string="Payment method",
                                      selection=[
                                          ('cash', 'Cash'),
                                          ('credit', 'Credit'),
                                          ('cod', 'Cash on delivery'),
                                      ], required=True, default='credit', index=True, tracking=True)

    manifest_ids = fields.Many2many(comodel_name='freight_route.manifest', string='Manifests', copy=False,
                                    relation='freight_route_manifest_waypoint_rel')

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('packing', 'Packing'),
            ('sorting', 'Sorting'),
            ('loading', 'Loading'),
            ('shipping', 'Shipping'),
            ('customs', 'Customs'),
            ('handover', 'Handover'),
            ('contingency', 'Contingency'),
            ('cancel', 'Cancelled'),
            ('done', 'Done'),
        ], required=True, default='draft', index=True, tracking=True, copy=False)

    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id

    @api.model
    def default_get(self, fields):
        res = super(Waypoint, self).default_get(fields)
        # res['recipient_id'] = self.env.company.partner_id.id
        # res['carry_id'] = self.env.company.partner_id.id
        return res

    @api.depends('freight_value', 'insurance_value', 'others_value')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = rec.freight_value + rec.insurance_value + rec.others_value

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            rec.driver_id = rec.vehicle_id.driver_id

    @api.depends('number', 'priority')
    def _compute_name(self):
        for rec in self:
            if rec.priority:
                rec.name = str(rec.priority) + '|' + rec.number
            else:
                rec.name = rec.number

    @api.depends('state')
    def _compute_color(self):
        for rec in self:
            switcher = {
                'draft': 11,
                'confirmed': 2,
                'progress': 10,
                'cancel': 1,
                'done': 0
            }
            rec.color = switcher.get(rec.state, 11)

    # Button Functions
    def button_geo_link(self):
        for rec in self:
            res = rec.recipient_id.button_geo_link()
            return res

    def button_validate(self):
        for rec in self:
            if not (rec.carry_id.street and
                    rec.carry_id.zip and
                    rec.recipient_id.street and
                    rec.recipient_id.zip):
                rec.message_post(body=_("Street and zip for carry and recipient partners are required to confirm"))
                continue

            if not (rec.carry_id.partner_latitude and
                    rec.carry_id.partner_longitude and
                    rec.recipient_id.partner_latitude and
                    rec.recipient_id.partner_longitude):
                rec.message_post(body=_("Latitude, longitude for carry and recipient partners are required to confirm"))
                continue

            # Calculate name sequence
            name_sequence = 'freight_route.waypoint'
            if rec.type == 'carry':
                name_sequence = name_sequence + '.carry.sequence'
            elif rec.type == 'delivery' and rec.company_id.is_payment_method_sequence:
                name_sequence = name_sequence + '.delivery.' + rec.payment_method + '.sequence'
            else:
                name_sequence = name_sequence + '.delivery.sequence'

            # Calculate sequence
            if rec.number in ('New', _('New')):
                next_number = self.env['ir.sequence'].with_company(rec.company_id).next_by_code(name_sequence)

                check_number = self.env['freight_route.waypoint'].search([
                    ('number', '=', next_number), ('number', 'not in', ('New', _('New')))
                ])
                if not check_number:
                    rec.number = next_number
                else:
                    rec.message_post(body=_("There is already another waypoint with the same number: %s for %s" % (
                        next_number, name_sequence)))

            if rec.number in ('New', _('New')):
                rec.message_post(body=_("Error to calculate sequence: " + name_sequence))
            else:
                rec.state = 'confirmed'

    def button_draft(self):
        for rec in self:
            rec.state = 'draft'

    def button_done(self):
        for rec in self:
            rec.state = 'done'

    def button_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def unlink(self):
        for rec in self:
            if rec.number in ('New', _('New')):
                super(Waypoint, self).unlink()
            else:
                raise UserError(
                    _("It is not possible to delete a waypoint once it has received a number. %s") % rec.number)

    def button_open_form_new(self):
        view = self.env.ref('freight_route.view_form_waypoint')
        context = self.env.context
        rec_id = 0
        for rec in self:
            rec_id = rec.id

        return {
            'name': _('Waypoint'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'freight_route.waypoint',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': rec_id,
            'context': context,
        }

    def button_open_form_current(self):
        view = self.env.ref('freight_route.view_form_waypoint')
        context = self.env.context
        rec_id = 0
        for rec in self:
            rec_id = rec.id

        return {
            'name': _('Waypoint'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'freight_route.waypoint',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': rec_id,
            'context': context,
        }

    def button_dir_link(self):
        for rec in self:
            geo_lat_start = str(rec.carry_id.partner_latitude)
            geo_lng_start = str(rec.carry_id.partner_longitude)
            geo_lat_end = str(rec.recipient_id.partner_latitude)
            geo_lng_end = str(rec.recipient_id.partner_longitude)
            geo = "https://www.google.com/maps/dir/{},{}/{},{}".format(
                geo_lat_start, geo_lng_start,
                geo_lat_end, geo_lng_end
            )
            return {
                "type": "ir.actions.act_url",
                "url": geo,
                "target": "new",
            }

    def set_date_times(self, date):
        for rec in self:
            scheduled_time = rec.scheduled_time
            scheduled_datetime = fields.Date.to_string(date) + ' 00:00:00'

            today = fields.Datetime.from_string(scheduled_datetime)
            today = today + relativedelta(hours=scheduled_time)
            context_today = fields.Datetime.context_timestamp(self, timestamp=today)

            new_context_today = fields.Datetime.from_string(fields.Datetime.to_string(context_today))
            delta_time = today - new_context_today
            context_datetime = today + delta_time

            rec.scheduled_datetime = context_datetime

    def create_delivery(self):
        new_deliveries_ids = []
        for rec in self:
            if rec.type == 'carry':
                new_delivery = rec.copy({
                    'type': 'delivery',
                    'carry_waypoint_id': rec.id
                })
                new_deliveries_ids.append(new_delivery.id)
        return {
            'name': _('Delivery'),
            'view_mode': 'tree,form',
            'res_model': 'freight_route.waypoint',
            'domain': [('id','in',new_deliveries_ids), ('type', '=', 'delivery')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'default_type': 'delivery', 'type': 'delivery'}
        }
