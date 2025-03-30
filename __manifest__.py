{
    "name": "Manifiestos Ambientales",
    "version": "1.0",
    "category": "Custom",
    "depends": ["sale", "residuos_autorizados_partner"],
    "data": [
    "security/ir.model.access.csv",
    "data/sequence.xml",
    "report/manifiesto_pdf.xml",  # Primero plantilla
    "report/report_actions.xml",  # Luego acción del reporte
    "views/manifiesto_views.xml", # Finalmente las vistas
    ],

    "installable": True,
}
