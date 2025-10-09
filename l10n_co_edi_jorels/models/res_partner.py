# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2022)
#
# This file is part of l10n_co_edi_jorels.
#
# l10n_co_edi_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import json
import logging
import re

import requests
from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    type_regime_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_regimes', string="Regime type",
                                     ondelete='RESTRICT')
    type_liability_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_liabilities',
                                        string="Liability type", ondelete='RESTRICT')
    merchant_registration = fields.Char(string="Merchant registration")
    municipality_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.municipalities', string="Municipality",
                                      ondelete='RESTRICT')
    tax_resident_co = fields.Boolean(string="Tax resident in Colombia?", default=True)
    email_edi = fields.Char("Email for invoicing")

    trade_name = fields.Char(string="Trade name", copy=False)

    type_document_identification_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_document_identifications",
                                                      string="Type document identification", readonly=True,
                                                      compute='_compute_type_document_identification_id', store=True,
                                                      copy=False, ondelete='RESTRICT')
    # surname, second_surname, first_name, other_names
    surname = fields.Char("Surname", compute="_compute_names", store=True)
    second_surname = fields.Char("Second surname", compute="_compute_names", store=True)
    first_name = fields.Char("First name", compute="_compute_names", store=True)
    other_names = fields.Char("Other names", compute="_compute_names", store=True)

    # Postal fields
    postal_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.postal', copy=True, string="Postal",
                                compute="_compute_postal_id", store=True)
    postal_department_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.departments', copy=True,
                                           string="Postal department", compute="_compute_postal_id", store=True)
    postal_municipality_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.municipalities', copy=True,
                                             string="Postal municipality", compute="_compute_postal_id", store=True)

    edi_sanitize_vat = fields.Char('Sanitized vat', compute='_compute_edi_sanitize_vat', store=True, readonly=True)

    # DIAN Contact information
    edi_dian_acquirer_email = fields.Char("Dian adquirer email", readonly=True)
    edi_dian_acquirer_name = fields.Char("Dian adquirer name", readonly=True)

    @classmethod
    def _edi_sanitize_vat(cls, vat, type_document_identification_id):
        sanitize_vat = vat and re.sub(r'\W+', '', vat).upper() or False
        if sanitize_vat:
            if type_document_identification_id in (1, 2, 3, 4, 5, 6, 10, 24, 38):
                id_number = ''.join([i for i in sanitize_vat if i.isdigit()])
            else:
                id_number = sanitize_vat

            # If it is Nit remove the check digit
            if type_document_identification_id == 6:
                return id_number[:-1]
            else:
                return id_number
        else:
            return None

    @api.depends('vat', 'type_document_identification_id')
    def _compute_edi_sanitize_vat(self):
        """Sanitize vat in colombia for document type"""
        for rec in self:
            rec.edi_sanitize_vat = rec._edi_sanitize_vat(rec.vat, rec.type_document_identification_id.id)

    @api.depends('l10n_latam_identification_type_id')
    def _compute_type_document_identification_id(self):
        if not self.env['l10n_co_edi_jorels.type_document_identifications'].search_count([]):
            self.env['res.company'].init_csv_data('l10n_co_edi_jorels.l10n_co_edi_jorels.type_document_identifications')

        document_type_mapping = {
            'rut': 6,
            'national_citizen_id': 3,
            'civil_registration': 1,
            'id_card': 2,
            'foreign_colombian_card': 4,
            'foreign_resident_card': 5,
            'passport': 7,
            'PEP': 24,
            'foreign_id_card': 8,
            'external_id': 9,
            'niup_id': 10,
            'id_document': 3,
            'PPT': 38,
        }

        for partner in self:
            document_code = partner.l10n_latam_identification_type_id.l10n_co_document_code
            partner.type_document_identification_id = document_type_mapping.get(document_code, None)

    @api.depends('zip', 'country_id')
    def _compute_postal_id(self):
        for rec in self:
            if rec.zip and rec.country_id and rec.country_id.code == 'CO':
                postal_obj = rec.env['l10n_co_edi_jorels.postal']
                postal_search = postal_obj.sudo().search([('name', '=', rec.zip)])
                if postal_search:
                    rec.postal_id = postal_search[0].id
                    rec.postal_department_id = rec.env['l10n_co_edi_jorels.departments'].sudo().search(
                        [('code', '=', rec.postal_id.department_id.code)]
                    )[0].id
                    rec.postal_municipality_id = rec.env['l10n_co_edi_jorels.municipalities'].sudo().search(
                        [('code', '=', rec.postal_id.municipality_id.code)]
                    )[0].id
            else:
                rec.postal_id = None
                rec.postal_department_id = None
                rec.postal_municipality_id = None

    @api.depends('name', 'is_company')
    def _compute_names(self):
        for rec in self:
            if rec.name:
                rec.first_name = None
                rec.other_names = None
                rec.surname = None
                rec.second_surname = None

                if rec.is_company:
                    rec.first_name = rec.name
                else:
                    split_name = rec.name.split(',')
                    if len(split_name) > 1:
                        # Surnames
                        split_surname = split_name[0].split()
                        if len(split_surname) == 0 or len(split_surname) == 1:
                            rec.surname = split_surname[0]
                        elif len(split_surname) == 2:
                            rec.surname = split_surname[0]
                            rec.second_surname = split_surname[1]
                        else:
                            rec.surname = ' '.join(split_surname[0:-1])
                            rec.second_surname = ' '.join(split_surname[-1:])

                        # Names
                        split_names = split_name[1].split()
                        rec.first_name = split_names[0]
                        if len(split_names) > 1:
                            rec.other_names = ' '.join(split_names[1:])
                    else:
                        split_name = rec.name.split()
                        if len(split_name) == 0 or len(split_name) == 1:
                            rec.first_name = rec.name
                        elif len(split_name) == 2:
                            rec.first_name = split_name[0]
                            rec.surname = split_name[1]
                        elif len(split_name) == 3:
                            rec.first_name = split_name[0]
                            rec.surname = split_name[1]
                            rec.second_surname = split_name[2]
                        elif len(split_name) == 4:
                            rec.first_name = split_name[0]
                            rec.other_names = split_name[1]
                            rec.surname = split_name[2]
                            rec.second_surname = split_name[3]
                        else:
                            rec.first_name = split_name[0]
                            rec.other_names = split_name[1]
                            rec.surname = ' '.join(split_name[2:-1])
                            rec.second_surname = ' '.join(split_name[-1:])

    def get_dian_acquirer(self):
        for rec in self:
            company = rec.company_id or self.env.company
            if not company.ei_enable:
                continue

            if not rec.type_document_identification_id:
                _logger.debug(_("An identification type is needed to query the contact in the DIAN"))
                rec.message_post(body=_("An identification type is needed to query the contact in the DIAN"))
                continue

            if not rec.edi_sanitize_vat:
                _logger.debug(_("An identification number is needed to query the contact in the DIAN"))
                rec.message_post(body=_("An identification number is needed to query the contact in the DIAN"))
                continue

            if rec.edi_sanitize_vat == '222222222222':
                continue
            try:
                id_code = str(rec.type_document_identification_id.id)
                id_number = rec.edi_sanitize_vat

                if company.api_key:
                    token = company.api_key
                else:
                    raise UserError(_("You must configure a token"))

                api_url = self.env['ir.config_parameter'].sudo().get_param('jorels.edipo.api_url',
                                                                           'https://edipo.jorels.com')
                api_url = api_url + "/acquirer/" + id_code + "/" + id_number

                params = {'token': token}
                header = {
                    "accept": "application/json",
                    "Content-Type": "application/json"
                }

                requests_data = {}
                response = requests.post(api_url,
                                         json.dumps(requests_data),
                                         headers=header,
                                         params=params).json()

                _logger.debug('API Response: %s', response)

                if 'detail' in response:
                    raise UserError(response['detail'])
                if 'message' in response and response['message'] is not None:
                    if response['message'] == 'Unauthenticated.' or response['message'] == '':
                        raise UserError(_("Authentication error with the API"))
                    else:
                        if 'errors' in response:
                            raise UserError(response['message'] + '/ errors: ' + str(response['errors']))
                        else:
                            raise UserError(response['message'])
                else:
                    if response['email'] != 'sininformacion@correo.com':
                        rec.edi_dian_acquirer_email = response['email']
                    rec.edi_dian_acquirer_name = response['name'].title()
            except Exception as e:
                _logger.debug("Failed to process the DIAN request: %s", e)
                rec.message_post(body=_("Failed to process the DIAN request: %s") % e)

    @api.model
    def format_colombian_name(self, name):
        """
        Formats a Colombian name assuming the first two words are last names
        and the remaining words are first names.

        Args:
            name (str): Full name with last names first

        Returns:
            str: Formatted name as "Last Names, First Names"
        """
        words = name.strip().split()

        if len(words) < 2:
            return name

        if len(words) == 2:
            return "{}, {}".format(words[0], words[1])

        last_names = " ".join(words[:2])
        first_names = " ".join(words[2:])

        return "{}, {}".format(last_names, first_names)

    def acquirer_replace(self):
        for rec in self:
            company = rec.company_id or self.env.company
            if not company.ei_enable:
                continue

            if rec.edi_dian_acquirer_name:
                if rec.is_company:
                    rec.name = rec.edi_dian_acquirer_name
                else:
                    rec.name = self.format_colombian_name(rec.edi_dian_acquirer_name)

            if rec.edi_dian_acquirer_email:
                rec.email_edi = rec.edi_dian_acquirer_email

    @api.model
    def default_get(self, fields_list):
        defaults = super(ResPartner, self).default_get(fields_list)

        company = self.env.company
        country_co = self.env['res.country'].search([('code', '=', 'CO')], limit=1)

        if company.ei_enable and company.ei_set_default_partner_data and company.country_id == country_co:
            if 'name' in fields_list:
                defaults['name'] = 'Consumidor Final'

            if 'vat' in fields_list:
                defaults['vat'] = '222222222222'

            if 'l10n_latam_identification_type_id' in fields_list:
                national_citizen_rec = self.env['l10n_latam.identification.type'].search(
                    [('l10n_co_document_code', '=', 'national_citizen_id')], limit=1)
                defaults['l10n_latam_identification_type_id'] = national_citizen_rec.id

            if 'type_regime_id' in fields_list:
                defaults['type_regime_id'] = 2

            if 'type_liability_id' in fields_list:
                defaults['type_liability_id'] = 29

            if 'country_id' in fields_list and company.country_id:
                defaults['country_id'] = company.country_id.id

            if 'state_id' in fields_list and company.state_id:
                defaults['state_id'] = company.state_id.id

            if 'city' in fields_list and company.city:
                defaults['city'] = company.city

            if 'municipality_id' in fields_list and company.municipality_id:
                defaults['municipality_id'] = company.municipality_id.id

        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        for rec in partners:
            company = rec.company_id or self.env.company
            if not company.ei_enable:
                continue

            if rec.country_id and rec.country_id.code == 'CO' and rec.name.upper() == 'CONSUMIDOR FINAL':
                rec.get_dian_acquirer()
                rec.acquirer_replace()

        return partners
