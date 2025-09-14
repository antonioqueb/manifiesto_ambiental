# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Campo para identificar productos de residuos peligrosos
    es_residuo_peligroso = fields.Boolean(
        string='Es Residuo Peligroso',
        help='Marcar si este producto es un residuo peligroso'
    )
    
    # Clasificaciones CRETIB (permitir múltiples selecciones)
    clasificacion_corrosivo = fields.Boolean(string='Corrosivo (C)')
    clasificacion_reactivo = fields.Boolean(string='Reactivo (R)')
    clasificacion_explosivo = fields.Boolean(string='Explosivo (E)')
    clasificacion_toxico = fields.Boolean(string='Tóxico (T)')
    clasificacion_inflamable = fields.Boolean(string='Inflamable (I)')
    clasificacion_biologico = fields.Boolean(string='Biológico (B)')
    
    # Información adicional del residuo
    envase_tipo_default = fields.Selection([
        ('tambor', 'Tambor'),
        ('contenedor', 'Contenedor'),
        ('tote', 'Tote'),
        ('tarima', 'Tarima'),
        ('saco', 'Saco'),
        ('caja', 'Caja'),
        ('bolsa', 'Bolsa'),
        ('tanque', 'Tanque'),
        ('otro', 'Otro'),
    ], string='Tipo de Envase por Defecto')
    
    envase_capacidad_default = fields.Float(
        string='Capacidad de Envase por Defecto',
        help='Capacidad del envase en litros'
    )
    
    @api.model
    def create(self, vals):
        # Si es residuo peligroso, configurar automáticamente algunos campos
        if vals.get('es_residuo_peligroso'):
            vals.update({
                'type': 'product',  # Producto almacenable
            })
        
        result = super().create(vals)
        
        # Configurar tracking en las variantes después de crear el template
        if vals.get('es_residuo_peligroso'):
            for product in result.product_variant_ids:
                product.tracking = 'lot'
        
        return result
    
    def write(self, vals):
        # Si se marca como residuo peligroso, actualizar configuración
        if vals.get('es_residuo_peligroso'):
            vals.update({
                'type': 'product',
            })
        
        result = super().write(vals)
        
        # Configurar tracking en las variantes después de escribir
        if vals.get('es_residuo_peligroso'):
            for record in self:
                for product in record.product_variant_ids:
                    product.tracking = 'lot'
        
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def get_clasificaciones_cretib(self):
        """Retorna las clasificaciones CRETIB activas para este producto"""
        clasificaciones = []
        if self.clasificacion_corrosivo:
            clasificaciones.append('C')
        if self.clasificacion_reactivo:
            clasificaciones.append('R')
        if self.clasificacion_explosivo:
            clasificaciones.append('E')
        if self.clasificacion_toxico:
            clasificaciones.append('T')
        if self.clasificacion_inflamable:
            clasificaciones.append('I')
        if self.clasificacion_biologico:
            clasificaciones.append('B')
        return ', '.join(clasificaciones)