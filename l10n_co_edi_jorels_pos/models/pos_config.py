# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2022)
#
# This file is part of l10n_co_edi_jorels_pos.
#
# l10n_co_edi_jorels_pos is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels_pos is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels_pos.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_electronic_invoice_journal(self):
        return self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.user.company_id.id)], limit=1)

    electronic_invoice_journal_id = fields.Many2one(
        'account.journal', string='Electronic Invoice Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to create electronic invoices.",
        default=_default_electronic_invoice_journal)
