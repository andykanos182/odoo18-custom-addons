{
    'name': 'Andykanoz POS Auto Manufacturing Order',
    'version': '18.0.1.0.0',
    'category': 'MyCustom/Modules',
    'summary': 'Auto-create Manufacturing Orders from POS orders (multi-level BoM support)',
    'description': """
Andykanoz POS Auto MO
=====================
Automatically creates Manufacturing Orders when a POS order is paid.

Features:
- Triggers on POS order state change to 'paid'
- Supports multi-level BoM (recursive sub-MO creation)
- Skips products without active BoM (sold as-is from stock)
- Skips sub-MO creation for components with sufficient stock (pre-cooked items)
- Auto-confirms MO so they appear in kitchen queue immediately
- Links each MO back to the originating POS order for later reporting
    """,
    'author': 'Andyka',
    'depends': ['point_of_sale', 'mrp', 'stock'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
