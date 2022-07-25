# -*- coding: utf-8 -*-
#
#   l10n_co_edi_jorels
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

from odoo import models, fields, api


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    # Required field for credit and debit notes in DIAN
    ei_correction_concept_credit_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.correction_concepts',
                                                      string="Correction concept",
                                                      domain=[('type_document_id', '=', '5')])

    @api.onchange('ei_correction_concept_credit_id')
    def _onchange_ei_correction_concept_credit_id(self):
        if self.ei_correction_concept_credit_id:
            self.reason = self.ei_correction_concept_credit_id.name

    @api.model
    def _prepare_default_reversal(self, move):
        values = super(AccountMoveReversal, self)._prepare_default_reversal(move)

        if self.reason:
            ei_correction_concept_search = self.env['l10n_co_edi_jorels.correction_concepts'].search([
                ('name', '=', self.reason),
                ('type_document_id', '=', 5)
            ])
            if ei_correction_concept_search:
                values['ei_correction_concept_credit_id'] = ei_correction_concept_search[0].id

        values['is_out_country'] = move.is_out_country

        return values
