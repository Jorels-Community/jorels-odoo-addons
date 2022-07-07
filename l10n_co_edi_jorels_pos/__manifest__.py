# -*- coding: utf-8 -*-
#
#   l10n_co_edi_jorels_pos
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

{
    'name': 'Facturación electrónica POS para Colombia por Jorels',
    'summary': 'Facturación electrónica POS para Colombia por Jorels',
    'description': "Free POS electronic invoice for Colombia by Jorels",
    'author': 'Jorels SAS',
    'license': 'AGPL-3',
    'category': 'Point of Sale',
    'version': '15.0.22.07.07.01.03',
    'website': 'https://www.jorels.com',
    'images': ['static/images/main_screenshot.png'],
    'support': 'info@jorels.com',
    
    # Odoo and Jorels dependencies
    'depends': [
        'point_of_sale',
        'l10n_co_edi_jorels',
    ],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_co_edi_jorels_pos/static/src/css/**/*',
            'l10n_co_edi_jorels_pos/static/src/js/**/*',
            'l10n_co_edi_jorels_pos/static/lib/js/qrcode/qrcode.js',
        ],
        'web.assets_qweb': [
            'l10n_co_edi_jorels_pos/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
}
