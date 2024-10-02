# -*- coding: utf-8 -*-
#
#   Jorels S.A.S. - Copyright (C) (2024)
#
#   This file is part of l10n_co_hr_payroll_enterprise.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#   along with this program. If not, see <https://www.gnu.org/licenses/>.
#
#   email: info@jorels.com
#

from odoo import api, fields, models, _


class Employee(models.Model):
    _inherit = "hr.employee"

    private_postal_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.postal', copy=True, string="Postal",
                                        compute="_compute_private_postal", store=True, groups="hr.group_hr_user")
    private_postal_department_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.departments', copy=True,
                                                   string="Postal department", compute="_compute_private_postal",
                                                   store=True, groups="hr.group_hr_user")
    private_postal_municipality_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.municipalities', copy=True,
                                                     string="Postal municipality", compute="_compute_private_postal",
                                                     store=True, groups="hr.group_hr_user")

    private_first_name = fields.Char("First name", compute="_compute_names", store=True, inverse="_inverse_names",
                                     groups="hr.group_hr_user")
    private_other_names = fields.Char("Other names", compute="_compute_names", store=True, inverse="_inverse_names",
                                      groups="hr.group_hr_user")
    private_surname = fields.Char("Surname", compute="_compute_names", store=True, inverse="_inverse_names",
                                  groups="hr.group_hr_user")
    private_second_surname = fields.Char("Second surname", compute="_compute_names", store=True,
                                         inverse="_inverse_names", groups="hr.group_hr_user")

    private_vat = fields.Char(string='Identification Number', groups="hr.group_hr_user")
    private_type_document_identification_id = fields.Many2one(
        comodel_name="l10n_co_edi_jorels.type_document_identifications", string="Type document identification",
        copy=False, domain=[('scope', '=', False)], groups="hr.group_hr_user", default=3)

    @api.onchange('private_surname', 'private_second_surname', 'private_first_name', 'private_other_names')
    def _inverse_names(self):
        for rec in self:
            rec.name = self.calculate_name(
                rec.private_surname,
                rec.private_second_surname,
                rec.private_first_name,
                rec.private_other_names
            )

    @api.model
    def calculate_name(self, private_surname, private_second_surname, private_first_name, private_other_names):
        name = ''
        if private_surname and not private_second_surname:
            name = private_surname + ', '
        if private_surname and private_second_surname:
            name = private_surname + ' ' + private_second_surname + ', '
        if private_first_name and not private_other_names:
            name = name + private_first_name
        if private_first_name and private_other_names:
            name = name + private_first_name + ' ' + private_other_names
        return name

    @api.depends('private_zip', 'private_country_id')
    def _compute_private_postal(self):
        for rec in self:
            rec.private_postal_id = None
            rec.private_postal_department_id = None
            rec.private_postal_municipality_id = None

            if rec.private_zip and rec.private_country_id and rec.private_country_id.code == 'CO':
                postal_obj = rec.env['l10n_co_edi_jorels.postal']
                postal_search = postal_obj.sudo().search([('name', '=', rec.private_zip)])
                if postal_search:
                    rec.private_postal_id = postal_search[0].id
                    rec.private_postal_department_id = rec.env['l10n_co_edi_jorels.departments'].sudo().search(
                        [('code', '=', rec.private_postal_id.department_id.code)]
                    )[0].id
                    rec.private_postal_municipality_id = rec.env['l10n_co_edi_jorels.municipalities'].sudo().search(
                        [('code', '=', rec.private_postal_id.municipality_id.code)]
                    )[0].id

    @api.depends('name')
    def _compute_names(self):
        for rec in self:
            name = self.calculate_name(
                rec.private_surname,
                rec.private_second_surname,
                rec.private_first_name,
                rec.private_other_names
            )

            private_first_name = None
            private_other_names = None
            private_surname = None
            private_second_surname = None

            if rec.name and rec.name != name:
                split_name = rec.name.split(',')
                if len(split_name) > 1:
                    # Surnames
                    split_surname = split_name[0].split()
                    if len(split_surname) == 0 or len(split_surname) == 1:
                        private_surname = split_surname[0]
                    elif len(split_surname) == 2:
                        private_surname = split_surname[0]
                        private_second_surname = split_surname[1]
                    else:
                        private_surname = ' '.join(split_surname[0:-1])
                        private_second_surname = ' '.join(split_surname[-1:])

                    # Names
                    split_names = split_name[1].split()
                    private_first_name = split_names[0]
                    if len(split_names) > 1:
                        private_other_names = ' '.join(split_names[1:])
                else:
                    split_name = rec.name.split()
                    if len(split_name) == 0 or len(split_name) == 1:
                        private_first_name = rec.name
                    elif len(split_name) == 2:
                        private_first_name = split_name[0]
                        private_surname = split_name[1]
                    elif len(split_name) == 3:
                        private_first_name = split_name[0]
                        private_surname = split_name[1]
                        private_second_surname = split_name[2]
                    elif len(split_name) == 4:
                        private_first_name = split_name[0]
                        private_other_names = split_name[1]
                        private_surname = split_name[2]
                        private_second_surname = split_name[3]
                    else:
                        private_first_name = split_name[0]
                        private_other_names = split_name[1]
                        private_surname = ' '.join(split_name[2:-1])
                        private_second_surname = ' '.join(split_name[-1:])

                rec.write({
                    'private_first_name': private_first_name,
                    'private_other_names': private_other_names,
                    'private_surname': private_surname,
                    'private_second_surname': private_second_surname,
                })
