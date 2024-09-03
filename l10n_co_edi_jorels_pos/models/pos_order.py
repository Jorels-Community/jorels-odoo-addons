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


import logging

import psycopg2
import pytz

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    ei_is_dian_document = fields.Boolean("Is it a DIAN electronic document?", default=False)
    to_electronic_invoice = fields.Boolean('To electronic invoice', copy=False)

    def get_invoice(self):
        self.ensure_one()
        return {
            "number": self.account_move.name,
            "ei_uuid": self.account_move.ei_uuid,
            "ei_qr_data": self.account_move.ei_qr_data,
            "ei_is_valid": self.account_move.ei_is_valid,
            "resolution_resolution": self.account_move.resolution_id.resolution_resolution,
            "resolution_resolution_date": self.account_move.resolution_id.resolution_resolution_date,
            "resolution_prefix": self.account_move.resolution_id.resolution_prefix,
            "resolution_from": self.account_move.resolution_id.resolution_from,
            "resolution_to": self.account_move.resolution_id.resolution_to,
            "resolution_date_from": self.account_move.resolution_id.resolution_date_from,
            "resolution_date_to": self.account_move.resolution_id.resolution_date_to,
        }

    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()

        if self.ei_is_dian_document:
            journal_id = self.session_id.config_id.electronic_invoice_journal_id.id
        else:
            journal_id = self.session_id.config_id.invoice_journal_id.id

        vals['journal_id'] = journal_id

        if vals['move_type'] == 'out_refund':
            if 'reversed_entry_id' in vals:
                invoice_search = self.env['account.move'].search([('id', '=', vals['reversed_entry_id'])])
                if invoice_search[0].amount_total == -self.amount_total:
                    # 2 is to report 'Electronic invoice cancellation' Concept
                    vals['ei_correction_concept_credit_id'] = 2
                    vals['ei_correction_concept_id'] = 2
                else:
                    # 1 is to report 'Partial return of goods and/or partial non-acceptance of service' Concept
                    vals['ei_correction_concept_credit_id'] = 1
                    vals['ei_correction_concept_id'] = 1
            else:
                # Credit note without reference
                # 1 is to report 'Partial return of goods and/or partial non-acceptance of service' Concept
                vals['ei_is_correction_without_reference'] = True
                vals['ei_correction_concept_credit_id'] = 1
                vals['ei_correction_concept_id'] = 1

        return vals

    @api.model
    def _order_fields(self, ui_order):
        result = super(PosOrder, self)._order_fields(ui_order)

        result['to_electronic_invoice'] = ui_order[
            'to_electronic_invoice'] if "to_electronic_invoice" in ui_order else False

        result['ei_is_dian_document'] = False
        if 'to_invoice' in ui_order and ui_order['to_invoice']:
            result['ei_is_dian_document'] = result['to_electronic_invoice']

        return result
