# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of freight_route.
#
# freight_route is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# freight_route is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with freight_route.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

{
    'name': "Freight Route",
    'summary': """Freight route with Jorels SAS""",
    'description': "Freight route with Jorels SAS",
    'author': "Jorels SAS",
    'website': "https://www.jorels.com",
    'images': ['static/images/main_screenshot.png'],
    'license': "LGPL-3",
    'category': 'Services',
    'version': '16.0.0.1',
    'depends': [
        'base',
        'contacts',
        'fleet',
        'base_geolocalize_jorels'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/res_config_settings_views.xml',
        'data/ir_sequence_data.xml',
        'views/res_partner_views.xml',
        'views/waypoint_views.xml',
        'views/manifest_views.xml',
    ],
    'application': True,
    'installable': True,
}
