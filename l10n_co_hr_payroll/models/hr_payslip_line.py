# -*- coding: utf-8 -*-
#
#   l10n_co_hr_payroll
#   Copyright (C) 2022  Jorels SAS
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
from odoo.addons import decimal_precision as dp


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _default_edi_rate(self):
        for rec in self:
            return rec.rate

    edi_rate = fields.Float(string='Edi Rate (%)', digits=dp.get_precision('Payroll Rate'),
                            default=_default_edi_rate, compute="_compute_edi_rate", store=True)

    @api.depends('rate')
    def _compute_edi_rate(self):
        for rec in self:
            if rec.salary_rule_id.edi_percent_select == 'default':
                rec.edi_rate = rec.rate
            else:
                rec.edi_rate = rec.salary_rule_id._compute_edi_percent(rec.slip_id)
