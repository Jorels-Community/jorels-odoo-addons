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


from odoo import fields, models, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    type_worker_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_workers", string="Type worker")
    subtype_worker_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.subtype_workers", string="Subtype worker")
    high_risk_pension = fields.Boolean(string="High risk pension", default=False)
    integral_salary = fields.Boolean(string="Integral salary", default=False)
    type_contract_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_contracts", string="Type contract")
    payroll_period_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.payroll_periods", string="Payroll period",
                                        compute="_compute_payroll_period_id", store=True)

    @api.depends('schedule_pay')
    def _compute_payroll_period_id(self):
        for rec in self:
            values = {
                'weekly': 1,      # Weekly
                'bi-weekly': 3,   # Bi-weekly
                'semi-monthly': 4,  # Semi-monthly
                'monthly': 5,     # Monthly
            }
            # Default to 'Other' (6) if not found in the mapping
            rec.payroll_period_id = values.get(rec.schedule_pay, 6)
