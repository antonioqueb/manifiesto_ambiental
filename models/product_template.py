from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    residuo_id = fields.Many2one('residuo.catalogo', string='Residuo Asociado')
    capacidad_envase = fields.Char(string="Capacidad del Envase")  # Ej: "200 Kg"
    tipo_envase = fields.Char(string="Tipo de Envase")  # Ej: "TAMBO", "CUBETA"
    etiqueta = fields.Boolean(string="Cuenta con Etiqueta")
    clasificacion_cretib = fields.Selection([
        ('C', 'Corrosivo'),
        ('R', 'Reactivo'),
        ('E', 'Explosivo'),
        ('T', 'Tóxico'),
        ('I', 'Inflamable'),
        ('B', 'Biológico-Infeccioso'),
        ('M', 'Mutagénico'),
    ], string='Clasificación CRETIB', help="Según normativa ambiental")
