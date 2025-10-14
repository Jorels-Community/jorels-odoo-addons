# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2025)
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

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()

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

        # Calculation of the Edi payment method reported to the DIAN
        positive_payment_ids = self.payment_ids.filtered(lambda payment: payment.amount > 0)
        quantity_positive_payments = len(positive_payment_ids)

        # Report 1 for undefined instrument payment method
        edi_pos_payment_method_id = 1
        if quantity_positive_payments == 1:
            pos_payment_method = positive_payment_ids[0].payment_method_id
            if pos_payment_method.edi_pos_payment_method_id:
                edi_pos_payment_method_id = pos_payment_method.edi_pos_payment_method_id.id

        vals['payment_method_id'] = edi_pos_payment_method_id

        return vals

    def _generate_pos_order_invoice(self):
        """Override to disable automatic email sending if configured"""
        # Check if any order in the recordset has the disable flag enabled
        disable_email = any(order.session_id.config_id.disable_auto_email_invoice for order in self)

        if disable_email:
            # Call the parent method with generate_pdf=False to prevent email sending
            return super(PosOrder, self.with_context(generate_pdf=False))._generate_pos_order_invoice()
        else:
            # Call parent method normally (with automatic email sending)
            return super()._generate_pos_order_invoice()
