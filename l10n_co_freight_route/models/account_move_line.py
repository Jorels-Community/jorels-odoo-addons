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
#
# Jorels S.A.S. - Copyright (2019-2020)
#
# This file is part of l10n_co_freight_route.
#
# email: info@jorels.com
#

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    _sql_constraints = [
        ('waypoint_unique', 'unique(waypoint_id, company_id, move_id)',
         'Delivery must be unique per Invoice and Company!'),
    ]

    waypoint_id = fields.Many2one(comodel_name='freight_route.waypoint', string="Delivery",
                                  domain=[('type', '=', 'delivery')], ondelete='RESTRICT')

    @api.onchange('waypoint_id', 'product_id', 'name', 'quantity', 'company_id')
    def onchange_delivery(self):
        for rec in self:
            if rec.company_id.invoice_product_id:
                if rec.product_id != rec.company_id.invoice_product_id:
                    rec.waypoint_id = None
                else:
                    rec.quantity = 1

                    if rec.waypoint_id:
                        if rec.price_unit != rec.waypoint_id.total_value:
                            rec.price_unit = rec.waypoint_id.total_value

                        if rec.waypoint_id.content:
                            rec.name = _('%s - Freight Transport for %s, %s of: %s') % (
                                rec.waypoint_id.number,
                                rec.waypoint_id.recipient_id.postal_municipality_id.name,
                                rec.waypoint_id.recipient_id.postal_department_id.name,
                                rec.waypoint_id.content
                            )
                        else:
                            rec.name = _('%s - Freight Transport for %s, %s') % (
                                rec.waypoint_id.number,
                                rec.waypoint_id.recipient_id.postal_municipality_id.name,
                                rec.waypoint_id.recipient_id.postal_department_id.name
                            )
