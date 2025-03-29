from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manifiesto_ids = fields.One2many('manifiesto.ambiental', 'sale_order_id', string='Manifiestos Ambientales')

    def action_open_manifiesto_desde_orden(self):
        self.ensure_one()
        manifiesto = self.env['manifiesto.ambiental'].search([('sale_order_id', '=', self.id)], limit=1)
        if not manifiesto:
            residuos = self.order_line.mapped('product_id.residuo_id.id')
            manifiesto = self.env['manifiesto.ambiental'].create({
                'sale_order_id': self.id,
                'residuos_ids': [(6, 0, residuos)],
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manifiesto Ambiental',
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'form',
            'res_id': manifiesto.id,
            'target': 'current',
        }
