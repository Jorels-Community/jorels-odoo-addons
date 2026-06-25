# -*- coding: utf-8 -*-
#
#   l10n_co_hr_payroll
#   Copyright (C) 2026  Jorels SAS
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published
#   by the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#   email: info@jorels.com
#


from odoo import fields, models, api


class HrVersion(models.Model):
    _inherit = "hr.version"

    type_worker_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_workers", string="Type worker",
                                     tracking=True, groups="hr.group_hr_manager")
    subtype_worker_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.subtype_workers", string="Subtype worker",
                                        tracking=True, groups="hr.group_hr_manager")
    high_risk_pension = fields.Boolean(string="High risk pension", default=False, tracking=True,
                                       groups="hr.group_hr_manager")
    integral_salary = fields.Boolean(string="Integral salary", default=False, tracking=True,
                                     groups="hr.group_hr_manager")
    type_contract_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_contracts", string="Type contract",
                                       tracking=True, groups="hr.group_hr_manager")
    payroll_period_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.payroll_periods", string="Payroll period",
                                        compute="_compute_payroll_period_id", store=True, tracking=True,
                                        groups="hr.group_hr_manager")

    def get_all_structures(self):
        structures = self.mapped('struct_id')
        if structures:
            return list(set(structures._get_parent_structure().ids))
        return super().get_all_structures()

    @api.depends('schedule_pay')
    def _compute_payroll_period_id(self):
        for rec in self:
            values = {
                'monthly': 5,
                'quarterly': 6,
                'semi-annually': 6,
                'annually': 6,
                'weekly': 1,
                'bi-weekly': 4,
                'bi-monthly': 6,
            }
            if rec.schedule_pay:
                rec.payroll_period_id = values[rec.schedule_pay]
            else:
                rec.payroll_period_id = None

    @api.model
    def _get_whitelist_fields_from_template(self):
        res = super()._get_whitelist_fields_from_template()
        new_fields = [
            'struct_id',
            'type_worker_id',
            'subtype_worker_id',
            'high_risk_pension',
            'integral_salary',
            'type_contract_id',
            'payroll_period_id',
        ]
        # Only add those that are not already present
        res.extend([f for f in new_fields if f not in res])
        return res