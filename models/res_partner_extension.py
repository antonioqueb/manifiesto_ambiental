# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Campos adicionales de dirección
    street_number = fields.Char(
        string='Núm. Exterior',
        help='Número exterior de la dirección'
    )
    
    street_number2 = fields.Char(
        string='Núm. Interior',
        help='Número interior de la dirección'
    )
    
    # Campo específico para registro ambiental
    numero_registro_ambiental = fields.Char(
        string='Número de Registro Ambiental',
        help='Número de registro ambiental del generador de residuos peligrosos'
    )
    
    # Campo para autorización SEMARNAT
    numero_autorizacion_semarnat = fields.Char(
        string='Número de Autorización SEMARNAT',
        help='Número de autorización de la SEMARNAT'
    )
    
    # Campo para permiso SCT (solo para transportistas)
    numero_permiso_sct = fields.Char(
        string='Número de Permiso S.C.T.',
        help='Número de permiso de la Secretaría de Comunicaciones y Transportes'
    )
    
    # Campos para vehículos (transportistas)
    tipo_vehiculo = fields.Char(
        string='Tipo de Vehículo',
        help='Tipo de vehículo utilizado para el transporte'
    )
    
    numero_placa = fields.Char(
        string='Número de Placa',
        help='Número de placa del vehículo'
    )
    
    # Categorización del partner
    es_generador = fields.Boolean(
        string='Es Generador',
        help='Marcar si este contacto es generador de residuos peligrosos'
    )
    
    es_transportista = fields.Boolean(
        string='Es Transportista',
        help='Marcar si este contacto es transportista de residuos peligrosos'
    )
    
    es_destinatario = fields.Boolean(
        string='Es Destinatario',
        help='Marcar si este contacto es destinatario final de residuos peligrosos'
    )