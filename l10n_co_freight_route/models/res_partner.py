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


class ResPartner(models.Model):
    _inherit = "res.partner"

    rndc_vat_type_id = fields.Many2one('l10n_co_freight_route.vat_type', "Vat type",
                                       compute="_compute_rndc_vat_type_id")
    rndc_license_category_id = fields.Many2one('l10n_co_freight_route.license_category', "License category",
                                               tracking=True, help="License category")
    license_number = fields.Char("License number", tracking=True, help="License number")
    license_expiration_date = fields.Date("License expiration date", default=fields.Date.context_today, tracking=True,
                                          help="License expiration date")
    rndc_site_code = fields.Char("Site Code")

    rndc_entry_code = fields.Char("Entry code", copy=False, tracking=True)

    @api.depends('l10n_latam_identification_type_id')
    def _compute_rndc_vat_type_id(self):
        for rec in self:
            rndc_vat_type = {
                "national_citizen_id": 1,
                "rut": 2,
                "passport": 3,
                "foreign_resident_card": 4,
                "id_card": 5,
                "niup_id": 6
            }

            if (rec.type == 'contact'
                    and rec.l10n_latam_identification_type_id
                    and rec.l10n_latam_identification_type_id.l10n_co_document_code):
                document_code = rec.l10n_latam_identification_type_id.l10n_co_document_code
            elif (rec.type == 'delivery'
                  and rec.parent_id
                  and rec.parent_id.l10n_latam_identification_type_id
                  and rec.parent_id.l10n_latam_identification_type_id.l10n_co_document_code):
                document_code = rec.parent_id.l10n_latam_identification_type_id.l10n_co_document_code
            else:
                document_code = None

            if document_code and document_code in rndc_vat_type:
                rec.rndc_vat_type_id = rndc_vat_type[document_code]
            else:
                rec.rndc_vat_type_id = None
