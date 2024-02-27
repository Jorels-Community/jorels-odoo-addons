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


class CancellationReason(models.Model):
    _name = 'l10n_co_freight_route.cancellation_reason'
    _description = 'Cancellation reason'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string='Name', required=True)

    cargo = fields.Boolean(string="Cargo", required=True)
    trip = fields.Boolean(string="Trip", required=True)
    shipment = fields.Boolean(string="Shipment", required=True)
    manifest = fields.Boolean(string="Manifest", required=True)
    initial_fulfilled_shipment = fields.Boolean(string="Initial fulfill shipment", required=True)
    fulfilled_shipment = fields.Boolean(string="Fulfill shipment", required=True)
    fulfilled_manifest = fields.Boolean(string="Fulfill manifest", required=True)
