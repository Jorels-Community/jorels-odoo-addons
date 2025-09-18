# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2025)
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
                                         help="Código prestador de servicios de salud (Debe registrarse el código "
                                              "asignado en el Sistema General de Seguridad Social en Salud (SGSSS) a "
                                              "los prestadores de servicios de salud que estén en el Registro Especial "
                                              "de Prestadores de Servicios de Salud (REPS), o el código asignado por "
                                              "el Ministerio de Salud y Protección Social para los para los "
                                              "Proveedores de Tecnologías en Salud y demás casos de excepción.)")
    ei_health_payment_method_id = fields.Many2one(string="Health payment method",
                                                  comodel_name='l10n_co_edi_jorels.payment_methods',
                                                  domain=[('scope', '=', 'health')], ondelete='RESTRICT',
                                                  help="Modalidades de pago (Debe registrarse la modalidad de pago "
                                                       "pactada objeto de facturación)")
    ei_health_type_coverage_id = fields.Many2one(string="Coverage type",
                                                 comodel_name='l10n_co_edi_jorels.type_coverages',
                                                 domain=[('scope', '=', 'health')], ondelete='RESTRICT',
                                                 help="Cobertura o plan de beneficios (Se registra la entidad "
                                                      "responsable de financiar la cobertura o plan de beneficios, y "
                                                      "de pagar la prestación de los servicios y tecnologías de salud "
                                                      "incluidas en la factura de venta.)")
    ei_health_contract = fields.Char(string="Contract number",
                                     help="Número de Contrato (Se debe registrar el número del contrato objeto de "
                                          "facturación)")
    ei_health_policy = fields.Char(string="Policy number",
                                   help="Número de póliza (Se debe registrar el número de póliza SOAT o del número de "
                                        "póliza de planes voluntarios de salud)")

    ei_health_partner_id = fields.Many2one(string="Health service user", comodel_name='res.partner',
                                           ondelete='RESTRICT')

    ei_operation = fields.Selection(selection_add=[
        ('ss_cufe', 'SS-CUFE'),
        ('ss_cude', 'SS-CUDE'),
        ('ss_pos', 'SS-POS'),
        ('ss_snum', 'SS-SNum'),
        ('ss_recaudo', 'SS-Recaudo'),
        ('ss_reporte', 'SS-Reporte'),
        ('ss_sinaporte', 'SS-SinAporte'),
    ], ondelete={
        'ss_cufe': 'set standard',
        'ss_cude': 'set standard',
        'ss_pos': 'set standard',
        'ss_snum': 'set standard',
        'ss_recaudo': 'set standard',
        'ss_reporte': 'set standard',
        'ss_sinaporte': 'set standard',
    })

    def get_operation_code(self):
        self.ensure_one()
        try:
            return super(AccountMove, self).get_operation_code()
        except KeyError:
            operation = {
                'ss_cufe': 19,
                'ss_cude': 20,
                'ss_pos': 21,
                'ss_snum': 22,
                'ss_recaudo': 23,
                'ss_reporte': 24,
                'ss_sinaporte': 25,
            }
            return operation[self.ei_operation]

    def get_json_request(self, check_date=True):
        json_request = super(AccountMove, self).get_json_request(check_date)

        if self.ei_operation[:3] != 'ss_':
            return json_request

        health_data = {}

        if self.ei_operation in ('ss_cufe', 'ss_cude', 'ss_pos', 'ss_snum'):
            if not self.ei_health_provider_ref:
                raise UserError(_("The health service provider code is mandatory."))
            if not self.ei_health_payment_method_id:
                raise UserError(_("The health payment method is mandatory."))
            if not self.ei_health_type_coverage_id:
                raise UserError(_("The health coverage type is mandatory."))
            if self.ei_health_contract and self.ei_health_policy:
                raise UserError(_("Please provide either health contract or police number, not both."))

            # Collect health-related data
            collection = {
                'provider_ref': self.ei_health_provider_ref or None,
                'payment_method_code': self.ei_health_payment_method_id.id or None,
                'type_coverage_code': self.ei_health_type_coverage_id.id or None,
                'contract': self.ei_health_contract or None,
                'policy': self.ei_health_policy or None
            }

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
                'id_number': partner.edi_sanitize_vat or None,
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
