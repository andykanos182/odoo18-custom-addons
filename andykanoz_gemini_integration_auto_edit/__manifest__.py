# -*- coding: utf-8 -*-
{
    'name': 'AndykaNoz - Gemini Auto Edit',
    'version': '18.0.5.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Remove product image background using Gemini AI and apply white background',
    'description': """
        Adds an "Auto White BG" button on the product form, plus a bulk
        "Auto White BG (Bulk)" action in the product list view that processes
        up to 50 selected products in the background with live progress.

        Setup:
            1. Get a free Gemini API key from https://aistudio.google.com/apikey
            2. Go to Settings > General Settings > Integrations
            3. Enter your Gemini API key + daily quota limit
            4. Open any product with an image and click "Auto White BG"
               OR select multiple products in the list view and pick
               Actions > Auto White BG (Bulk).
    """,
    'author': 'AndyKanoz',
    'depends': ['product', 'base_setup', 'bus', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/batch_edit_security.xml',
        'data/ir_cron.xml',
        'data/ir_actions_data.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
        'views/andykanoz_batch_edit_wizard_views.xml',
        'views/andykanoz_batch_edit_job_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_gemini_integration_auto_edit/static/src/scss/batch_edit.scss',
            'andykanoz_gemini_integration_auto_edit/static/src/js/batch_edit_service.js',
            'andykanoz_gemini_integration_auto_edit/static/src/js/batch_edit_progress_dialog.js',
            'andykanoz_gemini_integration_auto_edit/static/src/js/batch_edit_progress_dialog.xml',
            'andykanoz_gemini_integration_auto_edit/static/src/js/batch_edit_systray.js',
            'andykanoz_gemini_integration_auto_edit/static/src/js/batch_edit_systray.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
