{
    'name': 'Purchase WhatsApp Sender',
    'version': '18.0.1.0.0',
    'summary': 'Add button to send RFQ/PO product list to WhatsApp',
    'description': 'Adds buttons on RFQ and PO to open WhatsApp with a prefilled message containing the product list.',
    'author': 'andykanoz / Copilot',
    'category': 'Purchases',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
