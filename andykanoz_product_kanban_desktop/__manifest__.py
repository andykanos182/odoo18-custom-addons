{
    'name': 'Andykanoz Product Kanban Desktop',
    'version': '18.0.4.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Responsive Product Kanban with Pricelist, Inline Toggles & Category Edits',
    'description': """
        Custom responsive Kanban view for product.template.
        Features:
        - Full responsive: desktop grid, tablet compact, phone horizontal cards.
        - Large product image (1:1 desktop, 3:2 tablet, thumbnail phone).
        - Pricelist dropdown in control panel (recomputes prices live).
        - Inline boolean toggles (Sales, Purchase, POS, Published).
        - Inline category dropdown (Internal Category).
        - Expandable chips for Many2many (eCommerce, POS categories).
        - Cost / Pricelist Price / Profit display per card.
        - 20 products per page limit (server memory safe).
    """,
    'author': 'Andyka Noz',
    'depends': ['product', 'stock', 'sale_management', 'purchase', 'point_of_sale', 'website_sale'],
    'data': [
        'views/product_kanban_views.xml',
        'views/kanban_desktop_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'andykanoz_product_kanban_desktop/static/src/css/kanban_desktop.css',
            'andykanoz_product_kanban_desktop/static/src/js/kanban_boolean_toggle.js',
            'andykanoz_product_kanban_desktop/static/src/xml/kanban_boolean_toggle.xml',
            'andykanoz_product_kanban_desktop/static/src/js/kanban_category_select.js',
            'andykanoz_product_kanban_desktop/static/src/xml/kanban_category_select.xml',
            'andykanoz_product_kanban_desktop/static/src/js/product_kanban_controller.js',
            'andykanoz_product_kanban_desktop/static/src/js/product_kanban_view.js',
            'andykanoz_product_kanban_desktop/static/src/xml/product_kanban_buttons.xml',
            'andykanoz_product_kanban_desktop/static/src/js/view_switcher_patch.js',
            'andykanoz_product_kanban_desktop/static/src/xml/view_switcher_patch.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
