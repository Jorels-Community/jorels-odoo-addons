# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_freight_route.
#
# l10n_co_freight_route is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_freight_route is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_freight_route.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Waypoint(models.Model):
    _inherit = ['freight_route.waypoint']

    # Model field  -> Api values:
    #
    # customer_id  -> owner_vat_type_id, owner_vat
    # carry_id     -> sender_vat_type_id, sender_vat
    # recipient_id -> recipient_vat_type_id, recipient_vat, recipient_site_code

    # rndc_environment_id = fields.Many2one('l10n_co_freight_route.environment', 'Environment')
    rndc_insurance_holder_type_id = fields.Many2one('l10n_co_freight_route.insurance_holder_type',
                                                    'Insurance holder type', required=True)
    rndc_nature_id = fields.Many2one('l10n_co_freight_route.nature',
                                     'Nature', required=True)
    rndc_operation_type_id = fields.Many2one('l10n_co_freight_route.operation_type',
                                             'Operation type', required=True)
    rndc_packing_id = fields.Many2one('l10n_co_freight_route.packing',
                                      'Packing', required=True)
    rndc_short_product_description = fields.Char('Short product description', required=True)
    rndc_product_id = fields.Many2one('l10n_co_freight_route.product',
                                      'Product', required=True)
    unload_appointment_datetime = fields.Datetime("Unload appointment datetime", required=True)
    load_appointment_datetime = fields.Datetime("Load appointment datetime", required=True)
    unload_agreed_time = fields.Float("Unload agreed time", required=True)
    load_agreed_time = fields.Float("Load agreed time")
    is_unload_agreement_time = fields.Boolean("Was the download time agreement met?", required=False)
    is_load_agreement_time = fields.Boolean("Was the load time agreement met?", required=False)

    carry_waypoint_id = fields.Many2one('freight_route.waypoint', string='Carry waypoint', copy=False)
    empty_container_weight = fields.Integer("Empty container weight")
    extra_charge_permit = fields.Char("Extra charge permit")

    gps_partner_id = fields.Many2one('res.partner', string='GPS Company')

    insurance_expiration_date = fields.Date(string="Insurance expiration date", tracking=True, copy=False)
    rndc_insurance_company_id = fields.Many2one(comodel_name='l10n_co_freight_route.insurance_company',
                                                string="Insurance company", tracking=True)
    insurance_number = fields.Char(string="Insurance number", tracking=True, copy=False)

    measure_unit_id = fields.Many2one('l10n_co_freight_route.measure_unit', string='Measure unit')
    quantity = fields.Integer('Quantity', default=0)
    load_arrival_datetime = fields.Datetime("Load arrival datetime")
    load_departure_datetime = fields.Datetime("Load departure datetime")
    load_entry_datetime = fields.Datetime("Load entry datetime")

    rndc_entry_code = fields.Char("Entry code", copy=False, tracking=True)

    invoice_ids = fields.One2many(comodel_name="account.move.line", inverse_name="waypoint_id", string="Invoices",
                                  readonly=True, copy=False)
