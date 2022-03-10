# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2022)
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

{
    'name': 'Facturación electrónica POS para Colombia por Jorels',
    'summary': 'Facturación electrónica POS para Colombia por Jorels',
    'description': "Free POS electronic invoice for Colombia by Jorels",
    'author': 'Jorels SAS',
    'license': 'LGPL-3',
    'category': 'Point of Sale',
    'version': '14.0.22.03.07.11.36',
    'website': 'https://www.jorels.com',
    'images': ['static/images/main_screenshot.png'],
    'support': 'info@jorels.com',
    
    # Odoo and Jorels dependencies
    'depends': [
        'point_of_sale',
        'l10n_co_edi_jorels',
    ],
    'data': [
        'views/pos_view.xml',
        'views/pos_config_view.xml',
    ],
    'qweb': [
        'static/src/xml/ClientDetailsEdit.xml',
        'static/src/xml/OrderReceipt.xml',
        'static/src/xml/PaymentScreen.xml',
    ],
    'installable': True,
    'auto_install': True,
}
