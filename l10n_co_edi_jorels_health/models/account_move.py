# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_edi_jorels_health.
#
# l10n_co_edi_jorels_health is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels_health is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels_health.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#


import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"
    _description = "Electronic invoicing"

    ei_health_provider_ref = fields.Char(string="Service provider code",
                                         readonly=True, states={'draft': [('readonly', False)]})
    ei_health_payment_method_id = fields.Many2one(string="Payment method",
                                                  comodel_name='l10n_co_edi_jorels.payment_methods',
                                                  readonly=True, states={'draft': [('readonly', False)]},
                                                  domain=[('scope', '=', 'health')], ondelete='RESTRICT')
    ei_health_type_coverage_id = fields.Many2one(string="Coverage type",
                                                 comodel_name='l10n_co_edi_jorels.type_coverages',
                                                 readonly=True, states={'draft': [('readonly', False)]},
                                                 domain=[('scope', '=', 'health')], ondelete='RESTRICT')
    ei_health_contract = fields.Char(string="Contract number", readonly=True, states={'draft': [('readonly', False)]})
    ei_health_policy = fields.Char(string="Policy number", readonly=True, states={'draft': [('readonly', False)]})

    ei_health_partner_id = fields.Many2one(string="Health service user",
                                           comodel_name='res.partner',
                                           readonly=True, states={'draft': [('readonly', False)]},
                                           ondelete='RESTRICT')

    def get_json_request(self):
        json_request = super(AccountMove, self).get_json_request()
        health_data = {}

        # Collect health-related data
        collection = {
            'provider_ref': self.ei_health_provider_ref or None,
            'payment_method_code': self.ei_health_payment_method_id.id or None,
            'type_coverage_code': self.ei_health_type_coverage_id.id or None,
            'contract': self.ei_health_contract or None,
            'policy': self.ei_health_policy or None
        }
        collection = {k: v for k, v in collection.items() if v is not None}
        if collection:
            health_data['collections'] = [collection]

        # Process partner data if available
        if self.ei_health_partner_id:
            partner = self.ei_health_partner_id

            # Validate country
            if not partner.country_id:
                raise UserError(_("You must assign a country to the health service user"))

            country = self.env['l10n_co_edi_jorels.countries'].search([('code', '=', partner.country_id.code)], limit=1)
            if not country:
                raise UserError(_("Invalid country assigned to the health service user"))

            # Process municipality for Colombian addresses
            municipality_code = None
            if partner.country_id.code == 'CO':
                municipality_code = (partner.municipality_id and partner.municipality_id.id) or \
                                    (partner.postal_municipality_id and self.env[
                                        'l10n_co_edi_jorels.municipalities'
                                    ].search([('code', '=', partner.postal_municipality_id.code)], limit=1).id)
                if not municipality_code:
                    raise UserError(_("You must assign a valid municipality to the Colombian health service user"))

            # Prepare person data
            person = {
                'id_code': partner.edi_health_type_document_id.id or None,
                'id_number': partner.vat or None,
                'name': partner.name or None,
                'country_code': country.id or None,
                'municipality_code': municipality_code or None,
                'address': partner.street or None
            }
            health_data['person'] = {k: v for k, v in person.items() if v is not None}

        # Add health data to json_request if not empty
        if health_data:
            json_request['health'] = health_data

        return json_request
