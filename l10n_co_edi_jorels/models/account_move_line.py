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

import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ei_notes = fields.Char(string="Notes")
    ei_provider_party_id = fields.Many2one(comodel_name='res.partner', string="Mandator", copy=True,
                                           help="Principal third party information. Mandatory for mandate invoices.")

    @api.constrains('ei_provider_party_id', 'move_id')
    def _check_mandate_consistency(self):
        """Validate that mandate field is only used when operation type is 'mandates'"""
        for line in self:
            if line.ei_provider_party_id and line.move_id and line.move_id.ei_operation != 'mandates':
                raise ValidationError(
                    _("The 'Principal (Mandante)' field can only be used when the Operation Type is 'Mandates'. "
                      "Please remove the mandate or change the operation type to 'Mandates'.")
                )
