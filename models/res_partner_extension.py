# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # =========================================================================
    # MÁSCARA PARA DOCUMENTOS OFICIALES / MANIFIESTO
    # =========================================================================
    nombre_en_manifiesto = fields.Char(
        string='Nombre en Manifiesto',
        help=(
            'Nombre o razón social que debe mostrarse/imprimirse en el manifiesto. '
            'Si se deja vacío, el sistema usará el nombre normal del contacto.'
        ),
    )

    # =========================================================================
    # CAMPOS ADICIONALES DE DIRECCIÓN
    # =========================================================================
    street_number = fields.Char(
        string='Núm. Exterior',
        help='Número exterior de la dirección',
    )

    street_number2 = fields.Char(
        string='Núm. Interior',
        help='Número interior de la dirección',
    )

    # =========================================================================
    # DOCUMENTACIÓN AMBIENTAL
    # =========================================================================
    numero_registro_ambiental = fields.Char(
        string='Número de Registro Ambiental',
        help='Número de registro ambiental del generador de residuos peligrosos',
    )

    numero_autorizacion_semarnat = fields.Char(
        string='Número de Autorización SEMARNAT',
        help='Número de autorización de la SEMARNAT',
    )

    numero_permiso_sct = fields.Char(
        string='Número de Permiso S.C.T.',
        help='Número de permiso de la Secretaría de Comunicaciones y Transportes',
    )

    # =========================================================================
    # VEHÍCULOS / TRANSPORTISTAS
    # =========================================================================
    tipo_vehiculo = fields.Char(
        string='Tipo de Vehículo',
        help='Tipo de vehículo utilizado para el transporte',
    )

    numero_placa = fields.Char(
        string='Número de Placa',
        help='Número de placa del vehículo',
    )

    # =========================================================================
    # CLASIFICACIÓN DEL CONTACTO
    # =========================================================================
    es_generador = fields.Boolean(
        string='Es Generador',
        help='Marcar si este contacto es generador de residuos peligrosos',
    )

    es_transportista = fields.Boolean(
        string='Es Transportista',
        help='Marcar si este contacto es transportista de residuos peligrosos',
    )

    es_destinatario = fields.Boolean(
        string='Es Destinatario',
        help='Marcar si este contacto es destinatario final de residuos peligrosos',
    )

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _get_nombre_en_manifiesto(self):
        """
        Devuelve el nombre que debe usarse en el manifiesto.

        Regla:
        - Si el contacto tiene 'Nombre en Manifiesto', se usa ese valor.
        - Si está vacío, se usa el nombre normal del contacto.
        """
        self.ensure_one()
        nombre_mascara = (self.nombre_en_manifiesto or '').strip()
        return nombre_mascara or (self.name or '')