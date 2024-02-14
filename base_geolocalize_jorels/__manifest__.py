# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of base_geolocalize_jorels.
#
# base_geolocalize_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# base_geolocalize_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with base_geolocalize_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

{
    'name': 'Partners Geolocation with Jorels SAS',
    'summary': 'Partners Geolocation with Jorels SAS',
    'description': "Partners Geolocation with Jorels SAS",
    'author': "Jorels SAS",
    'license': "LGPL-3",
    'category': 'Customizations',
    'version': '16.0.24.01.261811',
    'website': 'https://www.jorels.com',
    'images': ['static/images/main_screenshot.png'],
    'support': 'info@jorels.com',
    'depends': [
        'base',
        'base_geolocalize',
        # 'partner_external_map'
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'data/data.xml',
    ],
    'installable': True,
}
