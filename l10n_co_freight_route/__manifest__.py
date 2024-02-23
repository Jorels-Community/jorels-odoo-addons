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
{
    'name': "Freight route Colombia Localization",
    'summary': """Freight route Colombia Localization with Jorels SAS""",
    'description': """
    Freight route Colombia Localization with Jorels SAS.
    Localización de Ruta de transporte de carga para Colombia con Jorels SAS
    """,
    'author': "Jorels SAS",
    'website': "https://www.jorels.com",
    'images': ['static/images/main_screenshot.png'],
    'license': "LGPL-3",
    'category': 'Services',
    'version': '16.0.0.1',
    'depends': [
        'base',
        'update_from_csv',
        'freight_route',
        'l10n_co',
        'l10n_co_edi_jorels',
    ],
    'data': [

    ],
    'installable': True,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
}
