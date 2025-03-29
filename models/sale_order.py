from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manifiesto_ids = fields.One2many('manifiesto.ambiental', 'sale_order_id', string='Manifiestos Ambientales')
