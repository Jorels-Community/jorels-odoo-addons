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

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    _sql_constraints = [('license_plate_unique', 'unique (license_plate)', 'The license plate already exists!')]

    # Required fields
    rndc_configuration_id = fields.Many2one('l10n_co_freight_route.configuration', 'Configuration', required=True)
    empty_weight = fields.Integer(string="Empty weight", required=True)
    holder_id = fields.Many2one('res.partner', 'Holder', required=True, tracking=True, help="Vehicle Holder")
    rndc_measure_unit_id = fields.Many2one('l10n_co_freight_route.measure_unit', 'Measure unit', required=True)
    owner_id = fields.Many2one('res.partner', 'Owner', required=True, tracking=True, help="Vehicle Owner")

    # Optional fields
    rndc_bodywork_id = fields.Many2one('l10n_co_freight_route.bodywork', 'Bodywork')
    capacity = fields.Integer(string="Capacity")
    rndc_color_id = fields.Many2one('l10n_co_freight_route.color', 'Rndc Color')
    rndc_fuel_type_id = fields.Many2one('l10n_co_freight_route.fuel_type', 'Fuel type', copy=False,
                                        compute='_compute_rndc_fuel_type', store=True)
    insurance_expiration_date = fields.Date(string="Insurance expiration date", tracking=True, copy=False)
    rndc_insurance_company_id = fields.Many2one(comodel_name='l10n_co_freight_route.insurance_company',
                                                string="Insurance company", tracking=True)
    insurance_number = fields.Char(string="Insurance number", tracking=True, copy=False)
    number_axes = fields.Integer(string="Number axes")
    repower_model_year = fields.Integer(string="Repower model year", copy=False)

    rndc_entry_code = fields.Char("Entry code", copy=False, tracking=True)

    # Other fields
    satellite_url = fields.Char(string="Satellite URL", tracking=True)
    satellite_company = fields.Char(string="Satellite company", tracking=True)
    satellite_user = fields.Char(string="Satellite user", copy=False, tracking=True)
    satellite_password = fields.Char(string="Satellite password", copy=False, tracking=True)

    technical_mechanical_date = fields.Date(string="Technical-mechanical Date", copy=False, tracking=True)

    @api.depends('fuel_type')
    def _compute_rndc_fuel_type(self):
        for rec in self:
            rndc_fuel_type = {
                'diesel': 1,
                'gasoline': 2,
                'full_hybrid': 4,
                'plug_in_hybrid_diesel': 1,
                'plug_in_hybrid_gasoline': 2,
                'cng': 3,
                'lpg': 0,
                'hydrogen': 0,
                'electric': 5,
            }
            if rec.fuel_type and rec.fuel_type != 0:
                rec.rndc_fuel_type_id = rndc_fuel_type[rec.fuel_type]
            else:
                rec.rndc_fuel_type_id = None
