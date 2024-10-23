# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of debug_ai.
#
# debug_ai is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# debug_ai is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with debug_ai.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

{
    'name': 'Debug AI by Jorels SAS',
    'summary': 'Edit XML views using AI',
    'sequence': -100,
    'description': """This module allows editing XML views using artificial intelligence.""",
    'author': 'Jorels SAS',
    'license': 'LGPL-3',
    'category': 'Productivity',
    'version': '15.0.1.0.0',
    'website': 'https://www.jorels.com',
    'images': ['static/images/main_screenshot.png'],
    'support': 'info@jorels.com',

    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/debug_ai_views.xml',
        'views/menu_items.xml',
        'views/res_config_settings_views.xml',
        'views/ir_ui_view_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
