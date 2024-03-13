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

import requests
import urllib3
from num2words import num2words
from odoo import _
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Manifest(models.Model):
    _name = 'freight_route.manifest'
    _description = 'Manifest'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # 15 min
    DELTA_TIME = 0.25

    # Sequence and main fields
    number = fields.Char(string='Number', required=True, copy=False, index=True, default=lambda self: _('New'))
    name = fields.Char(string='Name', required=False, default=None, readonly=True, compute='_compute_name')
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'freight_route.manifest'))
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency')
    manager_id = fields.Many2one('res.users', string='Manager', tracking=True,
                                 default=lambda self: self.env.user, copy=False)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True, copy=False)
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

    # Vehicle
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle', required=True, default=None,
                                 tracking=True)
    driver_id = fields.Many2one(comodel_name='res.partner', string='Driver', required=True, default=None, tracking=True)

    # Data fields
    color = fields.Integer(string='Color', required=False, default=None, readonly=True, compute='_compute_color')
    partner_start_id = fields.Many2one(comodel_name='res.partner', string='Partner start', required=True, default=None,
                                       tracking=True)
    partner_end_id = fields.Many2one(comodel_name='res.partner', string='Partner end', required=True, default=None,
                                     tracking=True)
    waypoint_ids = fields.Many2many(comodel_name='freight_route.waypoint', string='Waypoints', copy=False,
                                    relation='freight_route_manifest_waypoint_rel')
    note = fields.Text(string='Note', required=False, default=None)

    # Calculate fields
    start_time = fields.Float(string='Start time', required=True, default=8.0, tracking=True, copy=False)
    end_time = fields.Float(string='End time', required=True, default=18.0, tracking=True, copy=False)

    distance = fields.Integer(string="Distance/m", required=True, default=0, readonly=True, copy=False)
    duration = fields.Float(string="Duration/h", required=True, default=0.0, readonly=True, copy=False)

    # value totals
    total_cash_value = fields.Monetary(string='Total immediate', currency_field='currency_id',
                                       compute='_compute_total_cash_value', store=True, copy=False, tracking=True)
    total_credit_value = fields.Monetary(string='Total credit', currency_field='currency_id',
                                         compute='_compute_total_credit_value', store=True, copy=False, tracking=True)
    total_cod_value = fields.Monetary(string='Total delivery', currency_field='currency_id',
                                      compute='_compute_total_cod_value', store=True, copy=False, tracking=True)

    total_freight_value = fields.Monetary(string='Total Freight', currency_field='currency_id',
                                          compute='_compute_total_freight_value', store=True, copy=False,
                                          tracking=True)
    total_insurance_value = fields.Monetary(string='Total insurance', currency_field='currency_id',
                                            compute='_compute_total_insurance_value', store=True, copy=False,
                                            tracking=True)
    total_others_value = fields.Monetary(string='Total others', currency_field='currency_id',
                                         compute='_compute_total_others_value', store=True, copy=False, tracking=True)

    agreed_value = fields.Monetary(string='Agreed value', currency_field='currency_id', copy=False, tracking=True)
    assistant_value = fields.Monetary(string='Assistant value', readonly=True, currency_field='currency_id', copy=False,
                                      tracking=True)

    total_cost_value = fields.Monetary(string='Total cost', currency_field='currency_id',
                                       compute='_compute_total_cost_value', store=True, copy=False, tracking=True)
    total_rate_value = fields.Monetary(string='Total rate', currency_field='currency_id',
                                       compute='_compute_total_rate_value', store=True, copy=False, tracking=True)
    total_utility_value = fields.Monetary(string='Total utility', currency_field='currency_id',
                                          compute='_compute_total_utility_value', store=True, copy=False,
                                          tracking=True)

    quantity_units = fields.Integer('# Units', copy=False, tracking=True)
    quantity_waypoints = fields.Integer('# Waypoints', copy=False, tracking=True)

    @api.depends('agreed_value')
    def _value_letters(self):
        for rec in self:
            rec.value_letters = num2words(round(rec.agreed_value), lang='es_CO').upper() + ' ' + \
                                rec.currency_id.currency_unit_label.upper()

    def compute_totals_fields(self):
        self._compute_total_cash()
        self._compute_total_credit()
        self._compute_total_cod()
        self._compute_total_freight_value()
        self._compute_total_insurance_value()
        self._compute_total_others_value()

    def change_waypoints(self):
        self.compute_totals_fields()
        for rec in self:
            waypoints = rec.waypoint_ids
            quantity_waypoints = 0
            quantity_units = 0

            for waypoint in waypoints:
                quantity_waypoints = quantity_waypoints + 1
                quantity_units = quantity_units + waypoint.units

            rec.quantity_waypoints = quantity_waypoints
            rec.quantity_units = quantity_units

    @api.depends('agreed_value', 'assistant_value')
    def _compute_total_cost_value(self):
        for rec in self:
            rec.total_cost_value = rec.agreed_value + rec.assistant_value

    @api.depends('total_freight_value', 'total_insurance_value', 'total_others_value')
    def _compute_total_rate_value(self):
        for rec in self:
            rec.total_rate_value = rec.total_freight_value + rec.total_insurance_value + rec.total_others_value

    @api.depends('total_cost_value', 'total_rate_value')
    def _compute_total_utility_value(self):
        for rec in self:
            rec.total_utility_value = rec.total_rate_value - rec.total_cost_value

    def _compute_total_freight_value(self):
        for rec in self:
            sum_total_freight_value = 0
            for waypoint in rec.waypoint_ids:
                sum_total_freight_value = sum_total_freight_value + waypoint.freight_value
            rec.total_freight_value = sum_total_freight_value

    def _compute_total_insurance_value(self):
        for rec in self:
            sum_total_insurance_value = 0
            for waypoint in rec.waypoint_ids:
                sum_total_insurance_value = sum_total_insurance_value + waypoint.insurance_value
            rec.total_insurance_value = sum_total_insurance_value

    def _compute_total_others_value(self):
        for rec in self:
            sum_total_others_value = 0
            for waypoint in rec.waypoint_ids:
                sum_total_others_value = sum_total_others_value + waypoint.others_value
            rec.total_others_value = sum_total_others_value

    def _compute_total_cash_value(self):
        for rec in self:
            sum_cash = 0
            for waypoint in rec.waypoint_ids:
                if waypoint.payment_method == 'cash':
                    sum_cash = sum_cash + waypoint.total_value
            rec.total_cash_value = sum_cash

    def _compute_total_credit_value(self):
        for rec in self:
            sum_credit = 0
            for waypoint in rec.waypoint_ids:
                if waypoint.payment_method == 'credit':
                    sum_credit = sum_credit + waypoint.total_value
            rec.total_credit_value = sum_credit

    def _compute_total_cod_value(self):
        for rec in self:
            sum_cod = 0
            for waypoint in rec.waypoint_ids:
                if waypoint.payment_method == 'cod':
                    sum_cod = sum_cod + waypoint.total_value
            rec.total_cod_value = sum_cod

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            rec.driver_id = rec.vehicle_id.driver_id

    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id

    @api.depends('number')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.number

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

    @api.model
    def _get_ody_route(self, partner_start, partner_end, waypoints):
        token = self.env['ir.config_parameter'].sudo().get_param('jorels.ody_api_key')
        if not token:
            raise UserError(_(
                "Jorels Maps Api key for GeoCoding required.\n"
                "Visit https://www.jorels.com for more information."
            ))

        url = 'https://ody.jorels.com/trip/driving'

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        }

        waypoints_data = [{
            "lon": partner_start.partner_longitude,
            "lat": partner_start.partner_latitude
        }]

        enable_waypoints = []
        for waypoint in waypoints:
            enable_waypoints.append(waypoint)
            partner = waypoint.recipient_id
            waypoints_data.append({
                "lon": partner.partner_longitude,
                "lat": partner.partner_latitude
            })

        waypoints_data.append({
            "lon": partner_end.partner_longitude,
            "lat": partner_end.partner_latitude
        })

        data = {"waypoints": waypoints_data}

        try:
            response = requests.post(url, json=data, headers=headers).json()

            if 'code' in response and response['code'] == 'Ok':
                return response, enable_waypoints
            else:
                return False, enable_waypoints
        except Exception as e:
            self._raise_query_error(e)

    def _check_distance_route(self, data):
        return data['trips'][0]['distance']

    def _check_duration_route(self, data):
        duration_divider = float(
            self.env['ir.config_parameter'].sudo().get_param('freight_route.duration_divider', default=2048.0))
        return (data['trips'][0]['duration']) / duration_divider

    def _update_waypoints(self, waypoints, enable_waypoints, data):
        for rec in self:
            try:
                duration_divider = float(self.env['ir.config_parameter'].sudo().get_param(
                    'freight_route.duration_divider', default=2048.0))
                num_enable_waypoints = len(enable_waypoints)
                priority_order = [0] * num_enable_waypoints
                trip_duration = [0] * num_enable_waypoints
                for i in range(num_enable_waypoints):
                    # Priority for index i: data['waypoints'][i + 1]['waypoint_index'] - 1
                    priority_order[data['waypoints'][i + 1]['waypoint_index'] - 1] = i
                    trip_duration[i] = (data['trips'][0]['legs'][i]['duration']) / duration_divider

                scheduled_time = rec.start_time - rec.DELTA_TIME

                for priority in range(num_enable_waypoints):
                    waypoint = enable_waypoints[priority_order[priority]]
                    # Dado que el "for" está ordenado por prioridad, los tiempos de recorridos anteriores
                    # se van sumando al scheduled_time
                    scheduled_time = scheduled_time + rec.DELTA_TIME + trip_duration[priority]
                    waypoint.write({
                        # Se suma 1, dado que se han leido las prioridades arrancando en cero
                        'priority': priority + 1,
                        'scheduled_time': scheduled_time,
                        # 'start_time': rec.start_time
                    })

                for waypoint in waypoints:
                    waypoint.set_date_times(rec.date)

            except IndexError as e:
                _logger.debug("Update waypoints: %s" % e)
                rec.message_post(body=_("Index Error on update waypoints"))

    def _route(self):
        for rec in self:
            if rec.waypoint_ids:
                try:
                    partner_start = rec.partner_start_id
                    partner_end = rec.partner_end_id
                    waypoints = rec.waypoint_ids

                    if not (partner_start.partner_latitude and partner_start.partner_longitude):
                        raise UserError(_("The start partner have not a gps location"))
                    if not (partner_end.partner_latitude and partner_end.partner_longitude):
                        raise UserError(_("The end partner have not a gps location"))

                    for waypoint in waypoints:
                        if not (waypoint.recipient_id.partner_latitude and waypoint.recipient_id.partner_longitude):
                            if waypoint.recipient_id.parent_id:
                                partner_name = (waypoint.recipient_id.parent_id.name + ", "
                                                + waypoint.recipient_id.name or _('Delivery Address'))
                            else:
                                partner_name = waypoint.recipient_id.name
                            raise UserError(_("The partner '%s' have not a gps location") % partner_name)

                    # Calculate json route api response
                    data, enable_waypoints = rec._get_ody_route(partner_start, partner_end, waypoints)

                    if data:
                        rec.distance = rec._check_distance_route(data)
                        rec.duration = rec._check_duration_route(data)

                        rec._update_waypoints(waypoints, enable_waypoints, data)

                        rec.message_post(body=_("Manifest has been created."))
                        _logger.debug("Manifest has been created.")
                    else:
                        rec.message_post(body=_("Could not create a manifest for the waypoints."))
                        _logger.debug("Could not create a manifest for the waypoints.")

                except KeyError as e:
                    _logger.debug("_route()[KeyError]: %s", e)
                    raise UserError(_('At least one of the partners does not have an assigned GPS location.'
                                      '\nAssign it and try again'))
                except urllib3.exceptions.MaxRetryError:
                    raise UserError(_('Max retries exceeded with url'))
                except urllib3.exceptions.NewConnectionError:
                    raise UserError(_('Failed to establish a new connection'))
                except requests.exceptions.ConnectionError:
                    raise UserError(_('Connection Error'))
            else:
                raise UserError(_("You must enter at least one waypoint to be able to validate the manifest"))

    def button_route(self):
        self._route()

    def button_validate(self):
        self._route()
        name_sequence = 'freight_route.manifest.sequence'

        for rec in self:
            if not (rec.partner_start_id.street and
                    rec.partner_start_id.zip and
                    rec.partner_end_id.street and
                    rec.partner_end_id.zip):
                rec.message_post(body=_("Street and zip for start and end partners are required to confirm"))
                continue

            if not (rec.partner_start_id.partner_latitude and
                    rec.partner_start_id.partner_longitude and
                    rec.partner_end_id.partner_latitude and
                    rec.partner_end_id.partner_longitude):
                rec.message_post(body=_("Latitude, longitude for start and end partners are required to confirm"))
                continue

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
                super(Manifest, self).unlink()
            else:
                raise UserError(
                    _("It is not possible to delete a manifest once it has received a number. %s") % rec.number)

    def button_open_form_new(self):
        view = self.env.ref('freight_route.view_form_manifest')
        context = self.env.context
        rec_id = 0
        for rec in self:
            rec_id = rec.id

        return {
            'name': _('Manifest'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'freight_route.manifest',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': rec_id,
            'context': context,
        }

    def button_dir_link(self):
        for rec in self:
            geo = "https://www.google.com/maps/dir"

            # Start point
            geo_lat = str(rec.partner_start_id.partner_latitude)
            geo_lng = str(rec.partner_start_id.partner_longitude)
            geo += "/{},{}".format(geo_lat, geo_lng)

            # Other points
            # TODO: Review order for priority
            for waypoint in rec.waypoint_ids:
                geo_lat = str(waypoint.recipient_id.partner_latitude)
                geo_lng = str(waypoint.recipient_id.partner_longitude)
                geo += "/{},{}".format(geo_lat, geo_lng)

            # End point
            geo_lat = str(rec.partner_end_id.partner_latitude)
            geo_lng = str(rec.partner_end_id.partner_longitude)
            geo += "/{},{}".format(geo_lat, geo_lng)

            return {
                "type": "ir.actions.act_url",
                "url": geo,
                "target": "new",
            }

    @api.model
    def default_get(self, fields):
        res = super(Manifest, self).default_get(fields)
        res['partner_start_id'] = self.env.company.partner_id.id
        res['partner_end_id'] = self.env.company.partner_id.id
        return res
