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
from datetime import timedelta

import psycopg2

from odoo import api, fields, models, tools, _
from odoo.http import request
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    ei_is_dian_document = fields.Boolean("¿Es un documento electrónico DIAN?", default=False)

    @api.multi
    def get_invoice(self):
        self.ensure_one()
        return {
            "number": self.invoice_id.number,
            "ei_uuid": self.invoice_id.ei_uuid,
            "ei_qr_data": self.invoice_id.ei_qr_data,
            "ei_is_valid": self.invoice_id.ei_is_valid,
            "resolution_resolution": self.invoice_id.resolution_id.resolution_resolution,
            "resolution_resolution_date": self.invoice_id.resolution_id.resolution_resolution_date,
            "resolution_prefix": self.invoice_id.resolution_id.resolution_prefix,
            "resolution_from": self.invoice_id.resolution_id.resolution_from,
            "resolution_to": self.invoice_id.resolution_id.resolution_to,
            "resolution_date_from": self.invoice_id.resolution_id.resolution_date_from,
            "resolution_date_to": self.invoice_id.resolution_id.resolution_date_to,
        }

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a pos order.
        """
        # raise UserError("_prepare_invoice")
        invoice_type = 'out_invoice' if self.amount_total >= 0 else 'out_refund'
        # for rec in self:
        if self.ei_is_dian_document:
            journal_id = self.session_id.config_id.electronic_invoice_journal_id.id
        else:
            journal_id = self.session_id.config_id.invoice_journal_id.id
        return {
            'name': self.name,
            'origin': self.name,
            'account_id': self.partner_id.property_account_receivable_id.id,
            'journal_id': journal_id,
            'company_id': self.company_id.id,
            'type': invoice_type,
            'reference': self.name,
            'partner_id': self.partner_id.id,
            'comment': self.note or '',
            # considering partner's sale pricelist's currency
            'currency_id': self.pricelist_id.currency_id.id,
            'user_id': self.user_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
        }

    @api.model
    def create_from_ui(self, orders):
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        pos_order = self.search([('pos_reference', 'in', submitted_references)])
        existing_orders = pos_order.read(['pos_reference'])
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]
        order_ids = []

        for tmp_order in orders_to_save:
            to_invoice = tmp_order['to_invoice'] or tmp_order['data'].get('to_invoice')
            to_electronic_invoice = tmp_order['data'].get('to_electronic_invoice')
            order = tmp_order['data']

            if to_invoice:
                self._match_payment_to_invoice(order)
            pos_order = self._process_order(order)
            order_ids.append(pos_order.id)

            if to_invoice and not to_electronic_invoice:
                pos_order.ei_is_dian_document = False
            if to_invoice and to_electronic_invoice:
                pos_order.ei_is_dian_document = True

            try:
                pos_order.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e), exc_info=True)

            if to_invoice:
                pos_order.action_pos_order_invoice()
                pos_order.invoice_id.sudo().with_context(
                    force_company=self.env.user.company_id.id, pos_picking_id=pos_order.picking_id
                ).action_invoice_open()
                pos_order.account_move = pos_order.invoice_id.move_id
        return order_ids
