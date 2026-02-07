# -*- coding: utf-8 -*-
from odoo import models, fields

class ResiduoRecepcion(models.Model):
    _inherit = 'residuo.recepcion'

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto de Origen',
        readonly=True,
        tracking=True,
        help="Manifiesto desde el cual se generó esta recepción."
    )