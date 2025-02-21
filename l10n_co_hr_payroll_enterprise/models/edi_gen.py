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

import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class EdiGen(models.TransientModel):
    _name = 'l10n_co_hr_payroll.edi_gen'
    _description = 'Generate Edi Payslips'

    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], string='Month', required=True, default=lambda self: str(fields.Date.context_today(self).month))
    year = fields.Integer(string='Year', required=True, default=lambda self: fields.Date.context_today(self).year)

    # It only works for one contract per employee.
    # If an employee's payroll has multiple contracts, then the generated payroll will grab the last contract it finds.
    def generate(self):
        payslip_env = self.env['hr.payslip']
        edi_payslip_env = self.env['hr.payslip.edi']

        # Existing Payslips
        payslip_recs = payslip_env.search([
            ('year', '=', int(self.year)),
            ('month', '=', self.month),
            ('credit_note', '=', False),
            ('origin_payslip_id', '=', False),
            ('state', 'in', ('done', 'paid'))
        ])

        # Existing Credit notes
        credit_note_recs = payslip_env.search([
            ('year', '=', int(self.year)),
            ('month', '=', self.month),
            ('credit_note', '=', True),
            ('origin_payslip_id', '!=', False),
            ('state', 'in', ('done', 'paid'))
        ])

        # Filtered valid Payslips
        origin_payslip_list = []
        for credit_note_rec in credit_note_recs:
            origin_payslip_list.append(credit_note_rec.origin_payslip_id.id)
        valid_payslips = payslip_recs.filtered(lambda payslip: payslip.id not in origin_payslip_list)

        # Delete existing Edi Payslips in draft state
        for_delete_edi_payslip_recs = edi_payslip_env.search([
            ('year', '=', int(self.year)),
            ('month', '=', self.month),
            ('state', '=', 'draft')
        ])
        for_delete_edi_payslip_recs.unlink()

        # Creating new Edi Payslips in draft state without payslips
        for valid_payslip in valid_payslips:
            existing_edi_payslip_recs = edi_payslip_env.search([
                ('year', '=', int(self.year)),
                ('month', '=', self.month),
                ('employee_id', '=', valid_payslip.employee_id.id)
            ])
            if not existing_edi_payslip_recs:
                edi_payslip_env.create({
                    'year': int(self.year),
                    'month': self.month,
                    'employee_id': valid_payslip.employee_id.id,
                })

        # Adding Payslips to Edi Payslips

        # Search for existing Edi Payslips in draft state
        existing_edi_payslip_recs = edi_payslip_env.search([
            ('year', '=', int(self.year)),
            ('month', '=', self.month),
            ('state', '=', 'draft')
        ])
        for existing_edi_payslip_rec in existing_edi_payslip_recs:
            # First remove existing Payslips in Edi Payslip
            existing_edi_payslip_rec.write({'payslip_ids': [(5,)]})

            # Filtered new Edi Payslips for an employee
            valid_payslips_employee = valid_payslips.filtered(
                lambda payslip: payslip.employee_id.id == existing_edi_payslip_rec.employee_id.id
            )

            # Then add Payslips to Edi Payslip
            for valid_payslip_employee in valid_payslips_employee:
                existing_edi_payslip_rec.write({
                    'payslip_ids': [(4, valid_payslip_employee.id)],
                    'contract_id': valid_payslip_employee.contract_id.id
                })

        # To update or redirect to the Edi Payslip view
        return {
            "name": "Edi Payslips",
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.edi",
            "views": [[False, "list"], [False, "form"]],
        }
