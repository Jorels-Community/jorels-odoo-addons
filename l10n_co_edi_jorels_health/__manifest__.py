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

{
    'name': 'Facturación electrónica para el sector salud en Colombia por Jorels',
    'summary': 'Electronic invoice for Colombia for Health Sector by Jorels',
    'description': "Electronic invoice for Colombia for Health Sector by Jorels",
    'author': 'Jorels SAS',
    'license': 'LGPL-3',
    'category': 'Invoicing & Payments',
    'version': '18.0.25.04.151513',
    'website': 'https://www.jorels.com',
    'images': ['static/images/main_screenshot.png'],
    'support': 'info@jorels.com',
    'depends': [
        'l10n_co_edi_jorels',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True
}
