# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2025)
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
