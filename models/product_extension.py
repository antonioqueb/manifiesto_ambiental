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
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobreescritura del método create para manejar la creación masiva (vals_list)
        y evitar el error RPC_ERROR al duplicar.
        """
        # 1. Pre-procesamiento: Modificar los valores antes de crear
        for vals in vals_list:
            if vals.get('es_residuo_peligroso'):
                vals.update({
                    'type': 'product',  # Producto almacenable
                })
        
        # 2. Llamada al método padre con la lista
        templates = super(ProductTemplate, self).create(vals_list)
        
        # 3. Post-procesamiento: Configurar variantes
        for template in templates:
            # Verificamos directamente en el objeto creado si es peligroso
            if template.es_residuo_peligroso:
                for variant in template.product_variant_ids:
                    variant.tracking = 'lot'
        
        return templates
    
    def write(self, vals):
        # Si se marca como residuo peligroso, actualizar configuración
        if vals.get('es_residuo_peligroso'):
            vals.update({
                'type': 'product',
            })
        
        result = super(ProductTemplate, self).write(vals)
        
        # Configurar tracking en las variantes después de escribir
        # Nota: Usamos 'for record in self' para manejar la escritura en múltiples registros
        if vals.get('es_residuo_peligroso'):
            for record in self:
                for product in record.product_variant_ids:
                    product.tracking = 'lot'
        
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def get_clasificaciones_cretib(self):
        """Retorna las clasificaciones CRETIB activas para este producto"""
        self.ensure_one() # Buena práctica para asegurar que se llama sobre un solo registro
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