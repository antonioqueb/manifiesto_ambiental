{
    'name': 'Manifiesto Ambiental',
    'version': '19.0.2.0.0',
    'category': 'Environmental',
    'summary': 'Gestión de Manifiestos Ambientales para Residuos Peligrosos con Control de Versiones',
    'description': '''
        Manifiesto Ambiental con Control de Versiones
        =============================================
        
        Características principales:
        ---------------------------
        * Gestión completa de manifiestos ambientales para residuos peligrosos
        * Sistema de control de versiones tipo Git
        * Botón "Remanifestar" para crear nuevas versiones
        * Guardado automático de PDFs de cada versión
        * Historial completo de cambios y versiones
        * Mantenimiento del mismo número de folio para todas las versiones
        * Navegación entre versiones (actual, históricas, todas)
        * Bloqueo de edición en versiones históricas
        * Trazabilidad completa de cambios
        
        Funcionalidades de versionado:
        ----------------------------
        * Cada remanifestación genera una nueva versión
        * Se guarda un PDF de la versión anterior automáticamente
        * El número de manifiesto se mantiene igual en todas las versiones
        * Control de versión actual vs versiones históricas
        * Historial detallado con motivos de cambio
        * Descarga y visualización de PDFs históricos
        
        Flujo de trabajo:
        ----------------
        1. Crear manifiesto inicial (versión 1)
        2. Confirmar y procesar manifiesto
        3. Cuando sea necesario hacer cambios, usar "Remanifestar"
        4. Se guarda PDF de versión actual y se crea versión nueva
        5. Editar la nueva versión según necesidades
        6. Repetir proceso según sea necesario
        
        Integración:
        -----------
        * Compatible con órdenes de servicio existentes
        * Gestión de productos y residuos peligrosos
        * Clasificación CRETIB automática
        * Generación automática de lotes
        * Reportes PDF profesionales
    ''',
    'author': 'Alphaqueb Consulting',
    'website': 'https://alphaqueb.com',
    'depends': ['base', 'contacts', 'service_order', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/res_partner_views.xml',
        'views/manifiesto_ambiental_views.xml',  # ← PRIMERO las vistas (con las acciones)
        'views/product_views.xml',
        'views/manifiesto_ambiental_menus.xml',  # ← DESPUÉS los menús
        'views/service_order_manifiesto_button.xml',
        'reports/manifiesto_ambiental_report.xml',
    ],
    'demo': [],
    'qweb': [],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'price': 0.0,
    'currency': 'MXN',
}