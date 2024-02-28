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


class ResCompany(models.Model):
    _inherit = "res.company"

    rndc_insurance_company_id = fields.Many2one(comodel_name='l10n_co_freight_route.insurance_company',
                                                string="Insurance company")
    insurance_number = fields.Char(string="Insurance number")
    insurance_expiration_date = fields.Date(string="Insurance expiration date")

    invoice_product_id = fields.Many2one(comodel_name="product.product", string="Invoice product")
    is_hide_waypoint_values_print = fields.Boolean("Is hide waypoint values on print?", default=False)

    rndc_username = fields.Char("RNDC Username")
    rndc_password = fields.Char("RNDC Password")

    rndc_invoice_username = fields.Char("RNDC Invoice username")
    rndc_invoice_password = fields.Char("RNDC Invoice password")
