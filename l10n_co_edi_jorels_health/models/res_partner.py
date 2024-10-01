# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_edi_jorels_health.
#
# l10n_co_edi_jorels_health is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels_health is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels_health.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    edi_health_type_document_id = fields.Many2one(string="Health type document",
                                                  comodel_name='l10n_co_edi_jorels.type_document_identifications',
                                                  domain=[('scope', '=', 'health')], ondelete='RESTRICT')
