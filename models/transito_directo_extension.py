# -*- coding: utf-8 -*-
from odoo import fields, models


class TransitoDirecto(models.Model):
    """Único campo que `transito.directo` (definido en `service_order`) necesita
    de `manifiesto.ambiental`: el vínculo hacia el manifiesto que lo originó.
    Se agrega aquí, no en `service_order`, porque `service_order` no depende
    de `manifiesto_ambiental` (la dependencia va en sentido contrario)."""
    _inherit = 'transito.directo'

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental', string='Manifiesto Ambiental', readonly=True, copy=False,
    )
