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

    ei_is_dian_document = fields.Boolean("¿Es un documento electrónico DIAN?", default=False)
    to_electronic_invoice = fields.Boolean('To electronic invoice')

    def get_invoice(self):
        self.ensure_one()
        return {
            "number": self.account_move.name,
            "ei_uuid": self.account_move.ei_uuid,
            "ei_qr_data": self.account_move.ei_qr_data,
            "ei_is_valid": self.account_move.ei_is_valid,
            "resolution_resolution": self.account_move.journal_id.sequence_id.resolution_id.resolution_resolution,
            "resolution_resolution_date": self.account_move.journal_id.sequence_id.resolution_id.resolution_resolution_date,
            "resolution_prefix": self.account_move.journal_id.sequence_id.resolution_id.resolution_prefix,
            "resolution_from": self.account_move.journal_id.sequence_id.resolution_id.resolution_from,
            "resolution_to": self.account_move.journal_id.sequence_id.resolution_id.resolution_to,
            "resolution_date_from": self.account_move.journal_id.sequence_id.resolution_id.resolution_date_from,
            "resolution_date_to": self.account_move.journal_id.sequence_id.resolution_id.resolution_date_to,
        }

    def _prepare_invoice_vals(self):
        self.ensure_one()
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')

        if self.ei_is_dian_document:
            journal_id = self.session_id.config_id.electronic_invoice_journal_id.id
        else:
            journal_id = self.session_id.config_id.invoice_journal_id.id

        vals = {
            'invoice_payment_ref': self.name,
            'invoice_origin': self.name,
            'journal_id': journal_id,
            'type': 'out_invoice' if self.amount_total >= 0 else 'out_refund',
            'ref': self.name,
            'partner_id': self.partner_id.id,
            'narration': self.note or '',
            # considering partner's sale pricelist's currency
            'currency_id': self.pricelist_id.currency_id.id,
            'invoice_user_id': self.user_id.id,
            'invoice_date': self.date_order.astimezone(timezone).date(),
            'fiscal_position_id': self.fiscal_position_id.id,
            'invoice_line_ids': [(0, None, self._prepare_invoice_line(line)) for line in self.lines],
        }
        return vals

    @api.model
    def _process_order(self, order, draft, existing_order):
        """Create or update an pos.order from a given dictionary.

        :param pos_order: dictionary representing the order.
        :type pos_order: dict.
        :param draft: Indicate that the pos_order is not validated yet.
        :type draft: bool.
        :param existing_order: order to be updated or False.
        :type existing_order: pos.order.
        :returns number pos_order id
        """
        order = order['data']
        pos_session = self.env['pos.session'].browse(order['pos_session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            order['pos_session_id'] = self._get_valid_session(order).id

        pos_order = False
        if not existing_order:
            pos_order = self.create(self._order_fields(order))
        else:
            pos_order = existing_order
            pos_order.lines.unlink()
            order['user_id'] = pos_order.user_id.id
            pos_order.write(self._order_fields(order))

        self._process_payment_lines(order, pos_order, pos_session, draft)

        if pos_order.to_invoice and not pos_order.to_electronic_invoice:
            pos_order.ei_is_dian_document = False
        if pos_order.to_invoice and pos_order.to_electronic_invoice:
            pos_order.ei_is_dian_document = True

        if not draft:
            try:
                pos_order.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

        if pos_order.to_invoice and pos_order.state == 'paid':
            pos_order.action_pos_order_invoice()

        return pos_order.id

    @api.model
    def _order_fields(self, ui_order):
        result = super(PosOrder, self)._order_fields(ui_order)
        result['to_electronic_invoice'] = ui_order[
            'to_electronic_invoice'] if "to_electronic_invoice" in ui_order else False
        return result
