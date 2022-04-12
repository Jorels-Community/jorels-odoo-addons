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

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class TypeOperationEvents(models.Model):
    _name = "l10n_co_edi_jorels.type_operation_events"
    _inherit = "l10n_co_edi_jorels.languages"
    _description = "Type operation events"
    _order = "name"

    event_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.events', string="Event", required=True,
                               readonly=True, index=True, ondelete='RESTRICT')
