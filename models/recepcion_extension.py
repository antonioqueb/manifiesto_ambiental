# -*- coding: utf-8 -*-
from odoo import models, fields


class ResiduoRecepcion(models.Model):
    _inherit = 'residuo.recepcion'

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto de Origen',
        readonly=True,
        tracking=True,
        help="Manifiesto desde el cual se generó esta recepción.",
    )


class ResiduoRecepcionLinea(models.Model):
    _inherit = 'residuo.recepcion.linea'

    residuo_manifiesto_id = fields.Many2one(
        'manifiesto.ambiental.residuo',
        string='Residuo del Manifiesto',
        ondelete='set null',
        help="Vínculo directo al residuo del manifiesto que originó esta línea.",
    )