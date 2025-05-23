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
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/debug_ai_views.xml',
        'views/module_analysis_views.xml',
        'views/menu_items.xml',
        'views/res_config_settings_views.xml',
        'views/ir_ui_view_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/debug_ai/static/src/scss/claude_response.scss',
        ],
    },
    'external_dependencies': {
        'python': [
            'markdown',
            'pygments',  # Para el resaltado de sintaxis
            'anthropic',  # Librería oficial de Anthropic
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}