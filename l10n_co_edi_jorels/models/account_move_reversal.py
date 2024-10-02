# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
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

from odoo import models, fields, api


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    # Required field for credit and debit notes in DIAN
    ei_correction_concept_credit_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.correction_concepts',
                                                      string="Correction concept",
                                                      domain=[('type_document_id', 'in', (5, 13))])
    ei_type_document_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_documents', string="Document type",
                                          compute='_compute_ei_type_document_id')

    @api.depends('date')
    def _compute_ei_type_document_id(self):
        for rec in self:
            move_ids = rec.move_ids._origin
            if len(move_ids) == 1:
                if move_ids.move_type == 'out_invoice':
                    rec.ei_type_document_id = 5
                elif move_ids.move_type == 'in_invoice':
                    rec.ei_type_document_id = 13
                else:
                    rec.ei_type_document_id = None
            else:
                if move_ids[0].move_type == 'out_invoice':
                    rec.ei_type_document_id = 5
                elif move_ids[0].move_type == 'in_invoice':
                    rec.ei_type_document_id = 13
                else:
                    rec.ei_type_document_id = None

    @api.onchange('ei_correction_concept_credit_id')
    def _onchange_ei_correction_concept_credit_id(self):
        if self.ei_correction_concept_credit_id:
            self.reason = self.ei_correction_concept_credit_id.name

    def _prepare_default_reversal(self, move):
        values = super(AccountMoveReversal, self)._prepare_default_reversal(move)

        if self.ei_correction_concept_credit_id:
            values['ei_correction_concept_credit_id'] = self.ei_correction_concept_credit_id.id

        values['is_out_country'] = move.is_out_country

        return values
