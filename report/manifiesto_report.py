from odoo import models

class ManifiestoAmbientalReport(models.AbstractModel):
    _name = 'report.manifiesto_ambiental.manifiesto_pdf'
    _description = 'Reporte PDF del Manifiesto Ambiental'

    def _get_report_values(self, docids, data=None):
        docs = self.env['manifiesto.ambiental'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'manifiesto.ambiental',
            'docs': docs,
        }
