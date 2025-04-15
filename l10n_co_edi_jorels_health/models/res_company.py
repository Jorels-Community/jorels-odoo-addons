# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2025)
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

import json
import logging

import requests
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    ei_operation = fields.Selection(selection_add=[
        ('ss_cufe', 'SS-CUFE'),
        ('ss_cude', 'SS-CUDE'),
        ('ss_pos', 'SS-POS'),
        ('ss_snum', 'SS-SNum'),
        ('ss_recaudo', 'SS-Recaudo'),
        ('ss_reporte', 'SS-Reporte'),
        ('ss_sinaporte', 'SS-SinAporte'),
    ], ondelete={
        'ss_cufe': 'set standard',
        'ss_cude': 'set standard',
        'ss_pos': 'set standard',
        'ss_snum': 'set standard',
        'ss_recaudo': 'set standard',
        'ss_reporte': 'set standard',
        'ss_sinaporte': 'set standard',
    })
