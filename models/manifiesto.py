from odoo import models, fields, api

class ManifiestoAmbiental(models.Model):
    _name = 'manifiesto.ambiental'
    _description = 'Manifiesto de Entrega, Transporte y Recepción de Residuos Peligrosos'
    _order = 'name desc'

    name = fields.Char(string='Número de Manifiesto', required=True, copy=False, default='Nuevo', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True, ondelete='cascade')

    # Datos del generador (cliente)
    partner_id = fields.Many2one(related='sale_order_id.partner_id', string='Generador', store=True)
    registro_ambiental = fields.Char(string='Núm. de registro ambiental')
    calle = fields.Char(related='partner_id.street', readonly=True)
    no_exterior = fields.Char(string='Núm. Ext.')  # campo manual porque no existe en res.partner
    no_interior = fields.Char(string='Núm. Int.')  # campo manual porque no existe en res.partner
    colonia = fields.Char(string='Colonia')        # campo manual porque no existe en res.partner
    municipio = fields.Char(related='partner_id.city', readonly=True)
    estado = fields.Char(related='partner_id.state_id.name', readonly=True)
    codigo_postal = fields.Char(related='partner_id.zip', readonly=True)
    telefono = fields.Char(related='partner_id.phone', readonly=True)
    email = fields.Char(related='partner_id.email', readonly=True)


    # Residuos asociados
    residuos_ids = fields.Many2many('residuo.catalogo', string='Residuos')
    instrucciones = fields.Text(string='Instrucciones Especiales')
    observaciones = fields.Text(string='Observaciones')

    # Firma de declaración
    responsable_nombre = fields.Char(string="Responsable del generador")
    responsable_firma = fields.Binary(string="Firma (generador)")
    fecha_generador = fields.Date(string="Fecha (generador)")

    # Transportista
    transportista_nombre = fields.Char(default="SERVICIOS AMBIENTALES INTERNACIONALES S. DE R.L. DE C.V.")
    transportista_cp = fields.Char(default="65500")
    transportista_calle = fields.Char(default="DE LA INDUSTRIA")
    transportista_num_ext = fields.Char(default="102")
    transportista_colonia = fields.Char(default="SALINAS VICTORIA")
    transportista_municipio = fields.Char(default="SALINAS VICTORIA")
    transportista_estado = fields.Char(default="NUEVO LEON")
    transportista_tel = fields.Char(default="(81) 1344 - 0000")
    transportista_email = fields.Char(default="logistica@serviciosambientales.com.mx")
    semarnat_autorizacion = fields.Char(default="19-I-030D-19")
    permiso_sct = fields.Char(default="27022001020466037")
    tipo_vehiculo = fields.Char()
    placa = fields.Char()
    ruta = fields.Text()

    # Firma transportista
    responsable_transporte_nombre = fields.Char(string="Responsable transporte")
    responsable_transporte_firma = fields.Binary(string="Firma transporte")
    fecha_transporte = fields.Date(string="Fecha transporte")

    # Destinatario
    destinatario_nombre = fields.Char(default="SERVICIOS AMBIENTALES INTERNACIONALES, S. DE R.L. DE C.V.")
    destinatario_cp = fields.Char(default="65515")
    destinatario_calle = fields.Char(default="DE LA INDUSTRIA")
    destinatario_num_ext = fields.Char(default="102")
    destinatario_colonia = fields.Char(default="SALINAS VICTORIA")
    destinatario_municipio = fields.Char(default="SALINAS VICTORIA")
    destinatario_estado = fields.Char(default="NUEVO LEON")
    destinatario_tel = fields.Char(default="(81) 1344 - 0000")
    destinatario_email = fields.Char(default="centroacopio@serviciosambientales.com.mx")
    destinatario_semarnat = fields.Char(default="19-II-004D-2020 PRÓRROGA")
    destinatario_receptor = fields.Char(default="Lic. Rosa A. Padrón Gómez (Supervisor Centro de Acopio)")

    # Firma destinatario
    responsable_recepcion_nombre = fields.Char(string="Responsable recepción")
    responsable_recepcion_firma = fields.Binary(string="Firma recepción")
    fecha_recepcion = fields.Date(string="Fecha recepción")

    estatus = fields.Selection([
        ('borrador', 'Borrador'),
        ('validado', 'Validado'),
        ('cerrado', 'Cerrado'),
    ], default='borrador', string='Estatus')

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('manifiesto.ambiental')
        return super().create(vals)
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.calle = self.partner_id.street or ''
            self.municipio = self.partner_id.city or ''
            self.estado = self.partner_id.state_id.name if self.partner_id.state_id else ''
            self.codigo_postal = self.partner_id.zip or ''
            self.telefono = self.partner_id.phone or ''
            self.email = self.partner_id.email or ''

