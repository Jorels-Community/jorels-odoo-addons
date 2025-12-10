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


import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class Municipalities(models.Model):
    _name = "l10n_co_edi_jorels.municipalities"
    _inherit = ['l10n_co_edi_jorels.municipalities', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name']
