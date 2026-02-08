{
    'name': 'Manifiesto Ambiental',
    'version': '19.0.2.1.0',
    'category': 'Environmental',
    'summary': 'Gestión de Manifiestos Ambientales para Residuos Peligrosos con Control de Versiones',
    'description': '...',
    'author': 'Alphaqueb Consulting',
    'website': 'https://alphaqueb.com',
    # AGREGADO: Dependencia a 'residuo_recepcion'
    'depends': ['base', 'contacts', 'service_order', 'stock', 'residuo_recepcion_sai'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/res_partner_views.xml',
        'views/manifiesto_ambiental_views.xml',
        'views/manifiesto_ambiental_menus.xml',
        'views/service_order_manifiesto_button.xml',
        'views/recepcion_extension_views.xml',
        'reports/manifiesto_ambiental_report.xml',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'price': 0.0,
    'currency': 'MXN',
}