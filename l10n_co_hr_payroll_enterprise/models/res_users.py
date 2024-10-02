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

from odoo import models, fields

HR_READABLE_FIELDS = []

HR_WRITABLE_FIELDS = [
    'private_postal_id',
    'private_postal_department_id',
    'private_postal_municipality_id',
    'private_first_name',
    'private_other_names',
    'private_surname',
    'private_second_surname',
    'private_vat',
    'private_type_document_identification_id',
]


class User(models.Model):
    _inherit = ['res.users']

    private_postal_id = fields.Many2one(related='employee_id.private_postal_id', string="Postal", readonly=False,
                                        related_sudo=False)
    private_postal_department_id = fields.Many2one(related='employee_id.private_postal_department_id',
                                                   string="Postal department",
                                                   readonly=False, related_sudo=False)
    private_postal_municipality_id = fields.Many2one(related='employee_id.private_postal_municipality_id',
                                                     string="Postal municipality", readonly=False, related_sudo=False)

    private_first_name = fields.Char(related='employee_id.private_first_name', string="First name", readonly=False,
                                     related_sudo=False)
    private_other_names = fields.Char(related='employee_id.private_other_names', string="Other names", readonly=False,
                                      related_sudo=False)
    private_surname = fields.Char(related='employee_id.private_surname', string="Surname", readonly=False,
                                  related_sudo=False)
    private_second_surname = fields.Char(related='employee_id.private_second_surname', string="Second surname",
                                         readonly=False, related_sudo=False)

    private_vat = fields.Char(related='employee_id.private_vat', string='Identification Number', readonly=False,
                              related_sudo=False)
    private_type_document_identification_id = fields.Many2one(
        related='employee_id.private_type_document_identification_id', string="Type document identification",
        readonly=False, related_sudo=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + HR_READABLE_FIELDS + HR_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + HR_WRITABLE_FIELDS
