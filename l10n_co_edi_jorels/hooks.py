# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of freight_trasnport.
#
# freight_trasnport is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# freight_trasnport is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with freight_trasnport.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

from odoo import api, SUPERUSER_ID


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})

    ir_model_data_records = env['ir.model.data'].search(
        [('module', '=', 'l10n_co_edi_jorels'), ('name', 'like', '%customer_software%')])
    ir_model_data_records.unlink()

    model_record = env['ir.model'].search([('model', '=', 'l10n_co_edi_jorels.customer_software')])
    model_record.unlink()
