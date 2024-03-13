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
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/listings/additional_value_reason_views.xml',
        'views/listings/agreement_type_views.xml',
        'views/listings/bodywork_views.xml',
        'views/listings/brand_semitrailer_views.xml',
        'views/listings/cancellation_reason_views.xml',
        'views/listings/chapter_views.xml',
        'views/listings/color_views.xml',
        'views/listings/configuration_semitrailer_views.xml',
        'views/listings/configuration_views.xml',
        'views/listings/discount_value_reason_views.xml',
        'views/listings/fleet_vehicle_model_brand_views.xml',
        'views/listings/fleet_vehicle_model_views.xml',
        'views/listings/fulfilled_type_views.xml',
        'views/listings/fuel_type_views.xml',
        'views/listings/insurance_company_views.xml',
        'views/listings/insurance_holder_type_views.xml',
        'views/listings/license_category_views.xml',
        'views/listings/manifest_type_views.xml',
        'views/listings/measure_unit_views.xml',
        'views/listings/nature_views.xml',
        'views/listings/operation_type_views.xml',
        'views/listings/packing_views.xml',
        'views/listings/payment_responsible_views.xml',
        'views/listings/product_views.xml',
        'views/listings/semitrailer_views.xml',
        'views/listings/setting_type_views.xml',
        'views/listings/suspension_consequence_views.xml',
        'views/listings/suspension_reason_views.xml',
        'views/listings/transshipment_reason_views.xml',
        'views/listings/vat_type_views.xml',
        'views/menu.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/account_move_views.xml',
        'views/waypoint_views.xml',
        'reports/paperformat.xml',
        'reports/carry_report.xml',
        'reports/delivery_report.xml',
        # 'reports/manifest_report.xml',
    ],
    'installable': True,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
}
