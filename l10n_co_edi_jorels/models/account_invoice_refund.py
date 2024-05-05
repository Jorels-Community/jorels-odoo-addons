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

from odoo import api, fields, models


class AccountInvoiceRefund(models.TransientModel):
    _inherit = 'account.invoice.refund'

    # Required field for credit notes in DIAN
    ei_correction_concept_credit_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.correction_concepts',
                                                      string="Correction concept",
                                                      domain=[('type_document_id', 'in', (5, 13))])
    ei_type_document_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_documents', string="Document type",
                                          compute='_compute_ei_type_document_id', store=True)

    @api.depends('date_invoice')
    @api.one
    def _compute_ei_type_document_id(self):
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id', False))
        if invoice_id.type == 'out_invoice':
            self.ei_type_document_id = 5
        elif invoice_id.type == 'in_invoice':
            self.ei_type_document_id = 13
        else:
            self.ei_type_document_id = None

    @api.onchange('ei_correction_concept_credit_id')
    def _onchange_ei_correction_concept_credit_id(self):
        if self.ei_correction_concept_credit_id:
            self.description = self.ei_correction_concept_credit_id.name
