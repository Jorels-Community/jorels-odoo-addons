# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_freight_route.
#
# l10n_co_freight_route is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_freight_route is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_freight_route.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

from odoo import api, SUPERUSER_ID


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.cr.execute("""DELETE FROM fleet_vehicle_model""")
    env.cr.execute("""DELETE FROM fleet_vehicle_model_brand""")


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    env.cr.execute("""DELETE from ir_attachment WHERE res_model='fleet.vehicle.model'""")
    env.cr.execute("""DELETE from fleet_vehicle_model WHERE code IS NULL""")

    env.cr.execute("""DELETE from ir_attachment WHERE res_model='fleet.vehicle.model.brand'""")
    env.cr.execute("""DELETE from fleet_vehicle_model_brand WHERE code IS NULL""")
