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

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rndc_insurance_company_id = fields.Many2one(related="company_id.rndc_insurance_company_id",
                                                string="Insurance company", readonly=False)
    insurance_number = fields.Char(related="company_id.insurance_number", string="Insurance number", readonly=False)
    insurance_expiration_date = fields.Date(related="company_id.insurance_expiration_date",
                                            string="Insurance expiration date", readonly=False)

    invoice_product_id = fields.Many2one(related="company_id.invoice_product_id", readonly=False,
                                         string="Invoice product")
    is_hide_waypoint_values_print = fields.Boolean(related="company_id.is_hide_waypoint_values_print", readonly=False,
                                                   string="Is hide waypoint values on print?")

    rndc_username = fields.Char(related="company_id.rndc_username", readonly=False, string="RNDC Username")
    rndc_password = fields.Char(related="company_id.rndc_password", readonly=False, string="RNDC Password")

    rndc_invoice_username = fields.Char(related="company_id.rndc_invoice_username", readonly=False,
                                        string="RNDC Invoice username")
    rndc_invoice_password = fields.Char(related="company_id.rndc_invoice_password", readonly=False,
                                        string="RNDC Invoice password")
