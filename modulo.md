## ./__init__.py
```py
from . import models```

## ./__manifest__.py
```py
{
    'name': 'Manifiesto Ambiental',
    'version': '19.0.2.1.0',
    'category': 'Environmental',
    'summary': 'Gestión de Manifiestos Ambientales para Residuos Peligrosos con Control de Versiones',
    'description': '...',
    'author': 'Alphaqueb Consulting',
    'website': 'https://alphaqueb.com',
    'depends': [ 'mail','base', 'contacts', 'service_order', 'stock', 'residuo_recepcion_sai','fleet'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/manifiesto_ambiental_assets.xml',
        'views/res_partner_views.xml',
        'views/manifiesto_ambiental_views.xml',
        'views/manifiesto_ambiental_menus.xml',
        'views/service_order_manifiesto_button.xml',
        'views/recepcion_extension_views.xml',
        'views/views_discrepancia.xml',
        'reports/manifiesto_ambiental_report.xml',
        'reports/report_discrepancia.xml',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'price': 0.0,
    'currency': 'MXN',
}```

## ./data/sequences.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="seq_manifiesto_ambiental" model="ir.sequence">
        <field name="name">Manifiesto Ambiental</field>
        <field name="code">manifiesto.ambiental</field>
        <field name="prefix"></field>
        <field name="padding">0</field>
        <field name="company_id" eval="False"/>
        <field name="use_date_range" eval="False"/>
        <field name="implementation">no_gap</field>
    </record>
</odoo>```

## ./models/__init__.py
```py
from . import manifiesto_ambiental
from . import service_order_extension
from . import res_partner_extension
from . import product_extension
from . import recepcion_extension 
from . import manifiesto_discrepancia```

## ./models/manifiesto_ambiental.py
```py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import base64
import logging
import json
import re

_logger = logging.getLogger(__name__)


class ManifiestoAmbiental(models.Model):
    _name = 'manifiesto.ambiental'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manifiesto Ambiental'
    _rec_name = 'numero_manifiesto'
    _order = 'numero_manifiesto desc, version desc'

    # =========================================================================
    # VERSIONADO
    # =========================================================================
    version = fields.Integer(string='Versión', default=1, readonly=True, tracking=True)
    is_current_version = fields.Boolean(string='Versión Actual', default=True, tracking=True)
    original_manifiesto_id = fields.Many2one('manifiesto.ambiental', string='Manifiesto Original')
    version_history_ids = fields.One2many('manifiesto.ambiental.version', 'manifiesto_id', string='Historial de Versiones')
    change_reason = fields.Text(string='Motivo del Cambio', tracking=True)
    created_by_remanifest = fields.Boolean(string='Creado por Remanifestación', default=False)

    sequence_number = fields.Integer(string='Número de Secuencia', readonly=True, copy=False)

    documento_fisico = fields.Binary(string='Documento Físico Escaneado')
    documento_fisico_filename = fields.Char(string='Nombre del Archivo Físico')
    tiene_documento_fisico = fields.Boolean(
        string='Tiene Documento Físico',
        compute='_compute_tiene_documento_fisico',
        store=True,
    )

    # =========================================================================
    # INTEGRACIONES
    # =========================================================================
    recepcion_ids = fields.One2many('residuo.recepcion', 'manifiesto_id', string='Recepciones Generadas')
    recepcion_count = fields.Integer(string='No. Recepciones', compute='_compute_recepcion_count')

    discrepancia_ids = fields.One2many('manifiesto.discrepancia', 'manifiesto_id', string='Reportes de Discrepancias')
    discrepancia_count = fields.Integer(string='No. Discrepancias', compute='_compute_discrepancia_count')

    # =========================================================================
    # CAMPOS PRINCIPALES
    # =========================================================================
    tipo_manifiesto = fields.Selection([
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ], string='Tipo de Manifiesto', default='entrada', required=True, tracking=True,
       help='Entrada: SAI recibe residuos (generador externo). Salida: SAI envía residuos (SAI es generador).')

    numero_registro_ambiental = fields.Char(string='1. Núm. de registro ambiental', required=True, tracking=True)
    numero_manifiesto = fields.Char(string='2. Núm. de manifiesto', required=True, copy=False, tracking=True)
    numero_manifiesto_display = fields.Char(
        string='Número de Manifiesto',
        compute='_compute_numero_manifiesto_display',
        store=True,
    )
    pagina = fields.Integer(string='3. Página', default=1)

    # =========================================================================
    # 4. GENERADOR
    # =========================================================================
    generador_id = fields.Many2one(
        'res.partner',
        string='Generador',
        domain=[('es_generador', '=', True), ('parent_id', '=', False)],
        tracking=True,
    )
    generador_nombre = fields.Char(
        string='4. Nombre o razón social del generador',
        required=True,
        compute='_compute_generador_nombre',
        store=True,
        readonly=False,
        tracking=True,
    )
    generador_codigo_postal = fields.Char(string='Código postal')
    generador_calle = fields.Char(string='Calle')
    generador_num_ext = fields.Char(string='Núm. Ext.')
    generador_num_int = fields.Char(string='Núm. Int.')
    generador_colonia = fields.Char(string='Colonia')
    generador_municipio = fields.Char(string='Municipio o Delegación')
    generador_estado = fields.Char(string='Estado')
    generador_telefono = fields.Char(string='Teléfono')
    generador_email = fields.Char(string='Correo electrónico')

    generador_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Generador',
        domain="['|', ('parent_id', '=', generador_id), ('id', '=', generador_id)]",
        help='Contacto responsable del generador.',
        tracking=True,
    )
    generador_responsable_nombre = fields.Char(
        string='Nombre responsable generador',
        compute='_compute_generador_responsable_nombre',
        store=True,
        readonly=False,
        tracking=True,
    )
    generador_fecha = fields.Date(string='Fecha generador', default=fields.Date.context_today, tracking=True)
    generador_sello = fields.Char(string='Sello generador')

    # =========================================================================
    # 5. RESIDUOS
    # =========================================================================
    residuo_ids = fields.One2many('manifiesto.ambiental.residuo', 'manifiesto_id', string='5. Identificación de los residuos')
    instrucciones_especiales = fields.Text(string='6. Instrucciones especiales', tracking=True)

    # =========================================================================
    # 7. DECLARACIÓN GENERADOR
    # =========================================================================
    declaracion_generador = fields.Text(
        string='7. Declaración del generador',
        default='Declaro bajo protesta de decir verdad que el contenido de este lote está total y correctamente descrito mediante el número de manifiesto, nombre del residuo, características cretib, debidamente envasado y etiquetado y que se han previsto las condiciones de seguridad para su transporte por vía terrestre de acuerdo con la legislación vigente.',
        readonly=True,
    )

    # =========================================================================
    # 8. TRANSPORTISTA
    # =========================================================================
    transportista_id = fields.Many2one(
        'res.partner', string='Transportista',
        domain=[('es_transportista', '=', True)],
        tracking=True,
    )
    transportista_nombre = fields.Char(string='8. Nombre o razón social del transportista', required=True, tracking=True)
    transportista_codigo_postal = fields.Char(string='Código postal')
    transportista_calle = fields.Char(string='Calle')
    transportista_num_ext = fields.Char(string='Núm. Ext.')
    transportista_num_int = fields.Char(string='Núm. Int.')
    transportista_colonia = fields.Char(string='Colonia')
    transportista_municipio = fields.Char(string='Municipio o Delegación')
    transportista_estado = fields.Char(string='Estado')
    transportista_telefono = fields.Char(string='Teléfono')
    transportista_email = fields.Char(string='Correo electrónico')

    numero_autorizacion_semarnat = fields.Char(string='9. Núm. de autorización de la SEMARNAT', tracking=True)
    numero_permiso_sct = fields.Char(string='10. Núm. de permiso S.C.T.', tracking=True)

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        help='Unidad de transporte. Rellena automáticamente tipo y placa.',
        tracking=True,
    )
    tipo_vehiculo = fields.Char(
        string='11. Tipo de vehículo',
        compute='_compute_vehicle_fields',
        store=True,
        readonly=False,
        tracking=True,
    )
    numero_placa = fields.Char(
        string='12. Núm. de placa',
        help='Editable manualmente.',
        tracking=True,
    )

    chofer_id = fields.Many2one(
        'res.partner',
        string='Chofer',
        domain="[('is_driver', '=', True)]",
        tracking=True,
    )

    transportista_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Transportista',
        domain="['|', ('parent_id', '=', transportista_id), ('id', '=', transportista_id)]",
        tracking=True,
    )
    transportista_responsable_nombre = fields.Char(
        string='Nombre responsable transportista',
        compute='_compute_transportista_responsable_nombre',
        store=True,
        readonly=False,
        tracking=True,
    )
    transportista_fecha = fields.Date(string='Fecha transportista', default=fields.Date.context_today, tracking=True)
    transportista_sello = fields.Char(string='Sello transportista')

    ruta_empresa = fields.Text(string='13. Ruta de la empresa generadora hasta su entrega', tracking=True)
    declaracion_transportista = fields.Text(
        string='14. Declaración del transportista',
        default='Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto para su transporte a la empresa destinataria señalada por el generador.',
        readonly=True,
    )

    # =========================================================================
    # 15. DESTINATARIO
    # =========================================================================
    destinatario_id = fields.Many2one(
        'res.partner', string='Destinatario',
        domain=[('es_destinatario', '=', True)],
        tracking=True,
    )
    destinatario_nombre = fields.Char(string='15. Nombre o razón social del destinatario', required=True, tracking=True)
    destinatario_codigo_postal = fields.Char(string='Código postal')
    destinatario_calle = fields.Char(string='Calle')
    destinatario_num_ext = fields.Char(string='Núm. Ext.')
    destinatario_num_int = fields.Char(string='Núm. Int.')
    destinatario_colonia = fields.Char(string='Colonia')
    destinatario_municipio = fields.Char(string='Municipio o Delegación')
    destinatario_estado = fields.Char(string='Estado')
    destinatario_telefono = fields.Char(string='Teléfono')
    destinatario_email = fields.Char(string='Correo electrónico')
    numero_autorizacion_semarnat_destinatario = fields.Char(string='16. Núm. autorización de la SEMARNAT', tracking=True)
    nombre_persona_recibe = fields.Char(string='17. Nombre y cargo de la persona que recibe los residuos', tracking=True)
    observaciones_destinatario = fields.Text(string='18. Observaciones', tracking=True)
    declaracion_destinatario = fields.Text(
        string='19. Declaración del destinatario',
        default='Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto.',
        readonly=True,
    )
    destinatario_responsable_nombre = fields.Char(string='Nombre y firma del responsable', tracking=True)
    destinatario_fecha = fields.Date(string='Fecha', default=fields.Date.context_today, tracking=True)
    destinatario_sello = fields.Char(string='Sello')

    # =========================================================================
    # CONTROL
    # =========================================================================
    service_order_id = fields.Many2one('service.order', string='Orden de Servicio', tracking=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('in_transit', 'En Tránsito'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    # =========================================================================
    # COMPUTES
    # =========================================================================
    @api.depends('numero_manifiesto', 'version')
    def _compute_numero_manifiesto_display(self):
        for record in self:
            if record.version > 1:
                record.numero_manifiesto_display = f"{record.numero_manifiesto} (v{record.version})"
            else:
                record.numero_manifiesto_display = record.numero_manifiesto or ''

    @api.depends('documento_fisico')
    def _compute_tiene_documento_fisico(self):
        for record in self:
            record.tiene_documento_fisico = bool(record.documento_fisico)

    @api.depends('recepcion_ids')
    def _compute_recepcion_count(self):
        for rec in self:
            rec.recepcion_count = len(rec.recepcion_ids)

    @api.depends('discrepancia_ids')
    def _compute_discrepancia_count(self):
        for rec in self:
            rec.discrepancia_count = len(rec.discrepancia_ids)

    @api.depends('generador_id', 'generador_id.name')
    def _compute_generador_nombre(self):
        for rec in self:
            if rec.generador_id:
                if not rec.service_order_id:
                    rec.generador_nombre = rec.generador_id.name or ''

    @api.depends('generador_responsable_id', 'generador_responsable_id.name')
    def _compute_generador_responsable_nombre(self):
        for rec in self:
            if rec.generador_responsable_id:
                rec.generador_responsable_nombre = rec.generador_responsable_id.name or ''

    @api.depends('transportista_responsable_id', 'transportista_responsable_id.name')
    def _compute_transportista_responsable_nombre(self):
        for rec in self:
            if rec.transportista_responsable_id:
                rec.transportista_responsable_nombre = rec.transportista_responsable_id.name or ''

    @api.depends('vehicle_id', 'vehicle_id.model_id', 'vehicle_id.model_id.brand_id')
    def _compute_vehicle_fields(self):
        for rec in self:
            if rec.vehicle_id:
                brand = rec.vehicle_id.model_id.brand_id.name if rec.vehicle_id.model_id and rec.vehicle_id.model_id.brand_id else ''
                model = rec.vehicle_id.model_id.name if rec.vehicle_id.model_id else ''
                rec.tipo_vehiculo = f"{brand} {model}".strip() or rec.vehicle_id.name or ''

    # =========================================================================
    # ONCHANGES
    # =========================================================================
    @api.onchange('generador_id')
    def _onchange_generador_id(self):
        if self.generador_id:
            p = self.generador_id
            self.numero_registro_ambiental = p.numero_registro_ambiental or ''
            if not self.service_order_id:
                self.generador_nombre = p.name or ''
            self.generador_codigo_postal = p.zip or ''
            self.generador_calle = p.street or ''
            self.generador_num_ext = p.street_number or ''
            self.generador_num_int = p.street_number2 or ''
            self.generador_colonia = p.street2 or ''
            self.generador_municipio = p.city or ''
            self.generador_estado = p.state_id.name if p.state_id else ''
            self.generador_telefono = p.phone or ''
            self.generador_email = p.email or ''
            if self.generador_responsable_id:
                ok = (self.generador_responsable_id.id == p.id or
                      self.generador_responsable_id.parent_id.id == p.id)
                if not ok:
                    self.generador_responsable_id = False

    @api.onchange('generador_responsable_id')
    def _onchange_generador_responsable_id(self):
        if self.generador_responsable_id:
            self.generador_responsable_nombre = self.generador_responsable_id.name or ''

    @api.onchange('transportista_id')
    def _onchange_transportista_id(self):
        if self.transportista_id:
            p = self.transportista_id
            self.transportista_nombre = p.name or ''
            self.transportista_codigo_postal = p.zip or ''
            self.transportista_calle = p.street or ''
            self.transportista_num_ext = p.street_number or ''
            self.transportista_num_int = p.street_number2 or ''
            self.transportista_colonia = p.street2 or ''
            self.transportista_municipio = p.city or ''
            self.transportista_estado = p.state_id.name if p.state_id else ''
            self.transportista_telefono = p.phone or ''
            self.transportista_email = p.email or ''
            self.numero_autorizacion_semarnat = p.numero_autorizacion_semarnat or ''
            self.numero_permiso_sct = p.numero_permiso_sct or ''
            if self.transportista_responsable_id:
                ok = (self.transportista_responsable_id.id == p.id or
                      self.transportista_responsable_id.parent_id.id == p.id)
                if not ok:
                    self.transportista_responsable_id = False

    @api.onchange('transportista_responsable_id')
    def _onchange_transportista_responsable_id(self):
        if self.transportista_responsable_id:
            self.transportista_responsable_nombre = self.transportista_responsable_id.name or ''

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            v = self.vehicle_id
            brand = v.model_id.brand_id.name if v.model_id and v.model_id.brand_id else ''
            model = v.model_id.name if v.model_id else ''
            self.tipo_vehiculo = f"{brand} {model}".strip() or v.name or ''
            if not self.numero_placa:
                self.numero_placa = v.license_plate or ''

    @api.onchange('destinatario_id')
    def _onchange_destinatario_id(self):
        if self.destinatario_id:
            p = self.destinatario_id
            self.destinatario_nombre = p.name or ''
            self.destinatario_codigo_postal = p.zip or ''
            self.destinatario_calle = p.street or ''
            self.destinatario_num_ext = p.street_number or ''
            self.destinatario_num_int = p.street_number2 or ''
            self.destinatario_colonia = p.street2 or ''
            self.destinatario_municipio = p.city or ''
            self.destinatario_estado = p.state_id.name if p.state_id else ''
            self.destinatario_telefono = p.phone or ''
            self.destinatario_email = p.email or ''
            self.numero_autorizacion_semarnat_destinatario = p.numero_autorizacion_semarnat or ''

    # =========================================================================
    # NUMERACIÓN
    # =========================================================================
    def _get_next_sequence_number(self):
        self.env.cr.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM manifiesto_ambiental"
        )
        return self.env.cr.fetchone()[0]

    def _generate_manifiesto_number(self, generador_partner, fecha_servicio=None, sequence_num=None):
        if not generador_partner:
            raise UserError("Se requiere un generador para crear el número de manifiesto.")

        razon_social = generador_partner.name.upper()
        palabras_excluir = [
            'S.A.', 'SA', 'S.A', 'DE', 'C.V.', 'CV', 'C.V', 'S.A.P.I.', 'SAPI',
            'S. DE R.L.', 'S.R.L.', 'SRL', 'SOCIEDAD', 'ANONIMA', 'CIVIL',
            'RESPONSABILIDAD', 'LIMITADA', 'CAPITAL', 'VARIABLE', 'Y', 'E',
            'LA', 'EL', 'LOS', 'LAS', 'DEL', 'CON', 'SIN', 'PARA', 'POR'
        ]
        razon_limpia = re.sub(r'[^\w\s]', ' ', razon_social)
        palabras = razon_limpia.split()
        palabras_significativas = [p for p in palabras if p not in palabras_excluir and len(p) > 1]

        if len(palabras_significativas) >= 2:
            iniciales = palabras_significativas[0][0] + palabras_significativas[1][0]
        elif len(palabras_significativas) == 1:
            iniciales = palabras_significativas[0][:2]
        else:
            iniciales = razon_social[:2]

        if fecha_servicio:
            if isinstance(fecha_servicio, str):
                from datetime import datetime
                fecha = datetime.strptime(fecha_servicio, '%Y-%m-%d').date()
            else:
                fecha = fecha_servicio
        else:
            fecha = fields.Date.context_today(self)

        fecha_str = fecha.strftime('%d%m%Y')
        numero_base = f"{iniciales}-{fecha_str}"

        existing_count = self.env['manifiesto.ambiental'].search_count([
            ('numero_manifiesto', 'like', f'{numero_base}%')
        ])

        if existing_count > 0:
            sufijo = sequence_num if sequence_num else (existing_count + 1)
            numero_final = f"{numero_base}-{sufijo:02d}"
        else:
            numero_final = numero_base

        return numero_final

    # =========================================================================
    # CREATE
    # =========================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('created_by_remanifest'):
                next_seq = self._get_next_sequence_number()
                vals['sequence_number'] = next_seq

                if not vals.get('numero_manifiesto'):
                    generador_id = vals.get('generador_id')
                    if generador_id:
                        generador_partner = self.env['res.partner'].browse(generador_id)
                        vals['numero_manifiesto'] = self._generate_manifiesto_number(
                            generador_partner,
                            vals.get('generador_fecha'),
                            next_seq,
                        )
                    else:
                        vals['numero_manifiesto'] = str(next_seq)

            if vals.get('generador_id') and not vals.get('generador_nombre'):
                p = self.env['res.partner'].browse(vals['generador_id'])
                vals.update({
                    'numero_registro_ambiental': vals.get('numero_registro_ambiental') or p.numero_registro_ambiental or '',
                    'generador_nombre': p.name or '',
                    'generador_codigo_postal': vals.get('generador_codigo_postal') or p.zip or '',
                    'generador_calle': vals.get('generador_calle') or p.street or '',
                    'generador_num_ext': vals.get('generador_num_ext') or p.street_number or '',
                    'generador_num_int': vals.get('generador_num_int') or p.street_number2 or '',
                    'generador_colonia': vals.get('generador_colonia') or p.street2 or '',
                    'generador_municipio': vals.get('generador_municipio') or p.city or '',
                    'generador_estado': vals.get('generador_estado') or (p.state_id.name if p.state_id else ''),
                    'generador_telefono': vals.get('generador_telefono') or p.phone or '',
                    'generador_email': vals.get('generador_email') or p.email or '',
                })

            if vals.get('generador_responsable_id') and not vals.get('generador_responsable_nombre'):
                r = self.env['res.partner'].browse(vals['generador_responsable_id'])
                vals['generador_responsable_nombre'] = r.name or ''

            if vals.get('transportista_responsable_id') and not vals.get('transportista_responsable_nombre'):
                r = self.env['res.partner'].browse(vals['transportista_responsable_id'])
                vals['transportista_responsable_nombre'] = r.name or ''

            if vals.get('vehicle_id') and not vals.get('tipo_vehiculo'):
                v = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
                brand = v.model_id.brand_id.name if v.model_id and v.model_id.brand_id else ''
                model = v.model_id.name if v.model_id else ''
                vals['tipo_vehiculo'] = f"{brand} {model}".strip() or v.name or ''

        records = super().create(vals_list)

        for record in records:
            if not record.original_manifiesto_id:
                record.original_manifiesto_id = record.id

        return records

    # =========================================================================
    # IMPRESIÓN INTELIGENTE
    # =========================================================================
    def action_print_manifiesto(self):
        """Imprime el reporte correcto según el tipo de manifiesto (entrada o salida)."""
        self.ensure_one()
        if self.tipo_manifiesto == 'salida':
            report = self.env.ref(
                'salida_acopio_manifiesto.action_report_manifiesto_salida',
                raise_if_not_found=False,
            )
        else:
            report = self.env.ref(
                'manifiesto_ambiental.action_report_manifiesto_ambiental',
                raise_if_not_found=False,
            )
        if not report:
            raise UserError(_("No se encontró el reporte correspondiente."))
        return report.report_action(self)

    # =========================================================================
    # ACCIONES DE ESTADO
    # =========================================================================
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_in_transit(self):
        for rec in self:
            rec.state = 'in_transit'

    def action_delivered(self):
        for rec in self:
            rec.state = 'delivered'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    # =========================================================================
    # INTEGRACIÓN CON RECEPCIÓN
    # =========================================================================
    def action_recibir_residuos(self):
        self.ensure_one()
        if self.state not in ['in_transit', 'delivered']:
            raise UserError(_("El manifiesto debe estar 'En Tránsito' o 'Entregado' para recibir residuos."))
        if not self.residuo_ids:
            raise UserError(_("No hay residuos en el manifiesto para recibir."))

        lineas_recepcion = []
        for residuo in self.residuo_ids:
            lineas_recepcion.append((0, 0, {
                'descripcion_origen': residuo.nombre_residuo or (
                    residuo.product_id.name if residuo.product_id else 'Sin descripción'),
                'product_id': False,
                'cantidad': residuo.cantidad,
                'lote_asignado': self.numero_manifiesto,
                'clasificacion_corrosivo': residuo.clasificacion_corrosivo,
                'clasificacion_reactivo': residuo.clasificacion_reactivo,
                'clasificacion_explosivo': residuo.clasificacion_explosivo,
                'clasificacion_toxico': residuo.clasificacion_toxico,
                'clasificacion_inflamable': residuo.clasificacion_inflamable,
                'clasificacion_biologico': residuo.clasificacion_biologico,
            }))

        if not lineas_recepcion:
            raise UserError(_("No se pudieron generar líneas para la recepción."))

        vals = {
            'manifiesto_id': self.id,
            'partner_id': self.generador_id.id,
            'company_id': self.company_id.id,
            'fecha_recepcion': fields.Date.context_today(self),
            'linea_ids': lineas_recepcion,
            'notas': "<p>Generado desde Manifiesto: <strong>%s</strong> (Versión %s)</p>" % (
                self.numero_manifiesto, self.version),
        }
        try:
            recepcion = self.env['residuo.recepcion'].create(vals)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'residuo.recepcion',
                'view_mode': 'form',
                'res_id': recepcion.id,
                'target': 'current',
            }
        except Exception as e:
            raise UserError(_("Error al crear la recepción: %s") % str(e))

    def action_view_recepciones(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recepciones de Residuos'),
            'res_model': 'residuo.recepcion',
            'view_mode': 'list,form',
            'domain': [('manifiesto_id', '=', self.id)],
            'context': {'default_manifiesto_id': self.id},
        }

    # =========================================================================
    # DISCREPANCIAS
    # =========================================================================
    def action_crear_discrepancia(self):
        self.ensure_one()
        lineas = []
        for residuo in self.residuo_ids:
            nombre = residuo.nombre_residuo or (residuo.product_id.name if residuo.product_id else '')
            if residuo.packaging_id:
                contenedor = residuo.packaging_id.name
            elif residuo.envase_tipo:
                contenedor = dict(residuo._fields['envase_tipo'].selection).get(residuo.envase_tipo, residuo.envase_tipo)
            else:
                contenedor = ''
            lineas.append((0, 0, {
                'residuo_manifiesto_id': residuo.id,
                'nombre_residuo': nombre,
                'cantidad_manifestada': residuo.cantidad,
                'contenedor_manifestado': contenedor,
                'cantidad_real': residuo.cantidad,
                'contenedor_real': contenedor,
                'tipo_discrepancia': 'ok',
            }))
        discrepancia = self.env['manifiesto.discrepancia'].create({
            'manifiesto_id': self.id,
            'fecha_inspeccion': fields.Date.context_today(self),
            'linea_ids': lineas,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de Discrepancias',
            'res_model': 'manifiesto.discrepancia',
            'view_mode': 'form',
            'res_id': discrepancia.id,
            'target': 'current',
        }

    def action_view_discrepancias(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reportes de Discrepancias',
            'res_model': 'manifiesto.discrepancia',
            'view_mode': 'list,form',
            'domain': [('manifiesto_id', '=', self.id)],
            'context': {'default_manifiesto_id': self.id},
        }

    # =========================================================================
    # REMANIFESTACIÓN
    # =========================================================================
    def action_remanifestar(self):
        self.ensure_one()
        if not self.is_current_version:
            raise UserError("Solo se puede remanifestar la versión actual del manifiesto.")
        if self.state == 'draft':
            raise UserError("No se puede remanifestar un manifiesto en estado borrador.")
        try:
            pdf_data = self._generate_current_pdf_corregido()
            self._save_version_to_history(pdf_data)
            new_version = self._create_new_version()
            self._deactivate_current_version()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manifiesto.ambiental',
                'view_mode': 'form',
                'res_id': new_version.id,
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error en remanifestación: {str(e)}")
            raise UserError(f"Error durante la remanifestación: {str(e)}")

    def action_remanifestar_sin_pdf(self):
        self.ensure_one()
        if not self.is_current_version:
            raise UserError("Solo se puede remanifestar la versión actual del manifiesto.")
        if self.state == 'draft':
            raise UserError("No se puede remanifestar un manifiesto en estado borrador.")
        try:
            data_estructurados = self._generate_structured_data()
            self._save_version_to_history_with_data(data_estructurados)
            new_version = self._create_new_version()
            self._deactivate_current_version()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manifiesto.ambiental',
                'view_mode': 'form',
                'res_id': new_version.id,
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error en remanifestación: {str(e)}")
            raise UserError(f"Error durante la remanifestación: {str(e)}")

    def _generate_current_pdf_corregido(self):
        try:
            self._validate_required_data()
            self.env.cr.commit()
            current_record = self.sudo().browse(self.id)

            # Usar el reporte correcto según tipo de manifiesto
            report = None
            if current_record.tipo_manifiesto == 'salida':
                try:
                    report = self.env.ref('salida_acopio_manifiesto.action_report_manifiesto_salida')
                except Exception:
                    pass
            if not report:
                try:
                    report = self.env.ref('manifiesto_ambiental.action_report_manifiesto_ambiental')
                except Exception:
                    report = self.env['ir.actions.report'].search([
                        ('model', '=', 'manifiesto.ambiental'),
                        ('report_type', '=', 'qweb-pdf'),
                    ], limit=1)
            if not report:
                raise UserError("No se encontró el reporte PDF del manifiesto.")
            clean_context = {
                'lang': self.env.user.lang or 'es_ES',
                'tz': self.env.user.tz or 'UTC',
            }
            pdf_content, _ = report.sudo().with_context(clean_context)._render_qweb_pdf(
                report.report_name,
                res_ids=[current_record.id],
                data=None,
            )
            if not pdf_content:
                raise UserError("El contenido del PDF generado está vacío.")
            return base64.b64encode(pdf_content)
        except Exception as e:
            _logger.error(f"Error generando PDF: {str(e)}")
            raise UserError(f"Error al generar el PDF: {str(e)}")

    def _validate_required_data(self):
        errors = []
        if not self.numero_manifiesto:
            errors.append("Número de manifiesto")
        if not self.generador_nombre:
            errors.append("Nombre del generador")
        if not self.transportista_nombre:
            errors.append("Nombre del transportista")
        if not self.destinatario_nombre:
            errors.append("Nombre del destinatario")
        if not self.residuo_ids:
            errors.append("Debe tener al menos un residuo")
        if errors:
            raise UserError(f"Faltan datos requeridos: {', '.join(errors)}")

    def _generate_structured_data(self):
        return {
            'numero_manifiesto': self.numero_manifiesto or '',
            'version': self.version,
            'tipo_manifiesto': self.tipo_manifiesto,
            'fecha_generacion': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'estado': self.state,
            'tiene_documento_fisico': self.tiene_documento_fisico,
            'documento_fisico_filename': self.documento_fisico_filename or '',
            'generador': {
                'numero_registro': self.numero_registro_ambiental or '',
                'nombre': self.generador_nombre or '',
                'responsable': self.generador_responsable_nombre or '',
                'fecha': str(self.generador_fecha) if self.generador_fecha else '',
            },
            'transportista': {
                'nombre': self.transportista_nombre or '',
                'autorizacion_semarnat': self.numero_autorizacion_semarnat or '',
                'permiso_sct': self.numero_permiso_sct or '',
                'vehiculo': {
                    'tipo': self.tipo_vehiculo or '',
                    'placa': self.numero_placa or '',
                },
                'responsable': self.transportista_responsable_nombre or '',
                'fecha': str(self.transportista_fecha) if self.transportista_fecha else '',
            },
            'destinatario': {
                'nombre': self.destinatario_nombre or '',
                'autorizacion_semarnat': self.numero_autorizacion_semarnat_destinatario or '',
                'persona_recibe': self.nombre_persona_recibe or '',
                'responsable': self.destinatario_responsable_nombre or '',
                'fecha': str(self.destinatario_fecha) if self.destinatario_fecha else '',
            },
            'residuos': [{
                'nombre': r.nombre_residuo or '',
                'cantidad': r.cantidad,
                'clasificaciones': r.clasificaciones_display or '',
                'envase': {'tipo': r.envase_tipo or '', 'capacidad': r.envase_capacidad or ''},
                'etiquetado': 'Sí' if r.etiqueta_si else 'No',
            } for r in self.residuo_ids],
        }

    def _save_version_to_history_with_data(self, data_estructurados):
        try:
            data_text = self._format_data_as_text(data_estructurados)
            data_encoded = base64.b64encode(data_text.encode('utf-8'))
            self.env['manifiesto.ambiental.version'].create({
                'manifiesto_id': self.original_manifiesto_id.id,
                'version_number': self.version,
                'data_file': data_encoded,
                'data_filename': f"Manifiesto_{self.numero_manifiesto}_v{self.version}_datos.txt",
                'creation_date': fields.Datetime.now(),
                'created_by': self.env.user.id,
                'state_at_creation': self.state,
                'change_reason': self.change_reason or f"Versión {self.version} guardada antes de remanifestación",
                'documento_fisico_original': self.documento_fisico,
                'documento_fisico_filename_original': self.documento_fisico_filename,
                'tenia_documento_fisico': self.tiene_documento_fisico,
                'generador_nombre': self.generador_nombre or '',
                'transportista_nombre': self.transportista_nombre or '',
                'destinatario_nombre': self.destinatario_nombre or '',
                'total_residuos': len(self.residuo_ids),
            })
        except Exception as e:
            raise UserError(f"Error al guardar la versión: {str(e)}")

    def _format_data_as_text(self, data):
        tipo = data.get('tipo_manifiesto', 'entrada')
        tipo_label = 'SALIDA' if tipo == 'salida' else 'ENTRADA'
        texto = f"""
MANIFIESTO AMBIENTAL ({tipo_label}) - VERSIÓN {data['version']}
{'='*50}
Número de Manifiesto: {data['numero_manifiesto']}
Tipo: {tipo_label}
Fecha de Generación: {data['fecha_generacion']}
Estado: {data['estado']}

GENERADOR
{'-'*20}
Número de Registro: {data['generador']['numero_registro']}
Nombre: {data['generador']['nombre']}
Responsable: {data['generador']['responsable']}
Fecha: {data['generador']['fecha']}

TRANSPORTISTA
{'-'*20}
Nombre: {data['transportista']['nombre']}
Autorización SEMARNAT: {data['transportista']['autorizacion_semarnat']}
Permiso SCT: {data['transportista']['permiso_sct']}
Tipo de Vehículo: {data['transportista']['vehiculo']['tipo']}
Placa: {data['transportista']['vehiculo']['placa']}
Responsable: {data['transportista']['responsable']}
Fecha: {data['transportista']['fecha']}

DESTINATARIO
{'-'*20}
Nombre: {data['destinatario']['nombre']}
Autorización SEMARNAT: {data['destinatario']['autorizacion_semarnat']}
Persona que Recibe: {data['destinatario']['persona_recibe']}
Responsable: {data['destinatario']['responsable']}
Fecha: {data['destinatario']['fecha']}

RESIDUOS
{'-'*20}
"""
        for i, r in enumerate(data['residuos'], 1):
            texto += f"\n{i}. {r['nombre']}\n   Cantidad: {r['cantidad']} kg\n   Clasificaciones CRETIB: {r['clasificaciones']}\n   Envase: {r['envase']['tipo']} - {r['envase']['capacidad']}\n   Etiquetado: {r['etiquetado']}\n"
        return texto

    def _save_version_to_history(self, pdf_data):
        try:
            self.env['manifiesto.ambiental.version'].create({
                'manifiesto_id': self.original_manifiesto_id.id,
                'version_number': self.version,
                'pdf_file': pdf_data,
                'pdf_filename': f"Manifiesto_{self.numero_manifiesto}_v{self.version}.pdf",
                'creation_date': fields.Datetime.now(),
                'created_by': self.env.user.id,
                'state_at_creation': self.state,
                'change_reason': self.change_reason or f"Versión {self.version} guardada antes de remanifestación",
                'documento_fisico_original': self.documento_fisico,
                'documento_fisico_filename_original': self.documento_fisico_filename,
                'tenia_documento_fisico': self.tiene_documento_fisico,
                'generador_nombre': self.generador_nombre or '',
                'transportista_nombre': self.transportista_nombre or '',
                'destinatario_nombre': self.destinatario_nombre or '',
                'total_residuos': len(self.residuo_ids),
            })
        except Exception as e:
            raise UserError(f"Error al guardar la versión en el historial: {str(e)}")

    def _create_new_version(self):
        next_version = self.version + 1
        new_vals = self._prepare_version_data(next_version)
        new_version = self.create(new_vals)
        self._copy_residuos_to_version(new_version)
        return new_version

    def _prepare_version_data(self, next_version):
        exclude_fields = {
            'id', 'create_date', 'create_uid', 'write_date', 'write_uid',
            'version_history_ids', 'residuo_ids', '__last_update', 'display_name',
        }
        new_vals = {}
        for field_name, field in self._fields.items():
            if field_name in exclude_fields:
                continue
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if field.type == 'many2one' and value:
                    new_vals[field_name] = value.id
                elif field.type not in ['one2many', 'many2many']:
                    if isinstance(value, (list, tuple)) and value:
                        new_vals[field_name] = str(value[0]) if value[0] else ''
                    else:
                        new_vals[field_name] = value
        new_vals.update({
            'version': next_version,
            'is_current_version': True,
            'created_by_remanifest': True,
            'change_reason': '',
            'state': 'draft',
            'documento_fisico': False,
            'documento_fisico_filename': False,
            'numero_manifiesto': self.numero_manifiesto,
            'sequence_number': self.sequence_number,
        })
        return new_vals

    def _copy_residuos_to_version(self, new_version):
        for residuo in self.residuo_ids:
            self.env['manifiesto.ambiental.residuo'].create({
                'manifiesto_id': new_version.id,
                'product_id': residuo.product_id.id if residuo.product_id else False,
                'nombre_residuo': residuo.nombre_residuo or '',
                'clasificacion_corrosivo': residuo.clasificacion_corrosivo,
                'clasificacion_reactivo': residuo.clasificacion_reactivo,
                'clasificacion_explosivo': residuo.clasificacion_explosivo,
                'clasificacion_toxico': residuo.clasificacion_toxico,
                'clasificacion_inflamable': residuo.clasificacion_inflamable,
                'clasificacion_biologico': residuo.clasificacion_biologico,
                'envase_tipo': residuo.envase_tipo,
                'envase_capacidad': residuo.envase_capacidad,
                'cantidad': residuo.cantidad,
                'etiqueta_si': residuo.etiqueta_si,
                'etiqueta_no': residuo.etiqueta_no,
            })

    def _deactivate_current_version(self):
        self.write({'is_current_version': False, 'state': 'delivered'})

    # =========================================================================
    # NAVEGACIÓN DE VERSIONES
    # =========================================================================
    def action_view_version_history(self):
        return {
            'name': f'Historial de Versiones - {self.numero_manifiesto}',
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.ambiental.version',
            'view_mode': 'list,form',
            'domain': [('manifiesto_id', '=', self.original_manifiesto_id.id)],
            'context': {'default_manifiesto_id': self.original_manifiesto_id.id},
        }

    def action_view_current_version(self):
        current_version = self.search([
            ('original_manifiesto_id', '=', self.original_manifiesto_id.id),
            ('is_current_version', '=', True),
        ], limit=1)
        if current_version:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manifiesto.ambiental',
                'view_mode': 'form',
                'res_id': current_version.id,
                'target': 'current',
            }

    def action_view_all_versions(self):
        return {
            'name': f'Todas las Versiones - {self.numero_manifiesto}',
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'list,form',
            'domain': [('original_manifiesto_id', '=', self.original_manifiesto_id.id)],
            'context': {'default_original_manifiesto_id': self.original_manifiesto_id.id},
        }


# =============================================================================
# RESIDUO
# =============================================================================
class ManifiestoAmbientalResiduo(models.Model):
    _name = 'manifiesto.ambiental.residuo'
    _description = 'Residuo del Manifiesto Ambiental'

    TRACKED_FIELDS = {
        'nombre_residuo': 'Nombre del residuo',
        'cantidad': 'Cantidad (kg)',
        'clasificacion_corrosivo': 'Corrosivo (C)',
        'clasificacion_reactivo': 'Reactivo (R)',
        'clasificacion_explosivo': 'Explosivo (E)',
        'clasificacion_toxico': 'Tóxico (T)',
        'clasificacion_inflamable': 'Inflamable (I)',
        'clasificacion_biologico': 'Biológico (B)',
        'envase_tipo': 'Tipo de Envase',
        'envase_capacidad': 'Capacidad',
        'etiqueta_si': 'Etiqueta Sí',
        'etiqueta_no': 'Etiqueta No',
        'residue_type': 'Tipo de Residuo',
        'product_id': 'Producto/Residuo',
    }

    manifiesto_id = fields.Many2one('manifiesto.ambiental', string='Manifiesto', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto/Residuo')
    nombre_residuo = fields.Char(string='Nombre del residuo', required=True)
    residue_type = fields.Selection([('rsu', 'RSU'), ('rme', 'RME'), ('rp', 'RP')], string='Tipo de Residuo')

    clasificacion_corrosivo = fields.Boolean(string='Corrosivo (C)')
    clasificacion_reactivo = fields.Boolean(string='Reactivo (R)')
    clasificacion_explosivo = fields.Boolean(string='Explosivo (E)')
    clasificacion_toxico = fields.Boolean(string='Tóxico (T)')
    clasificacion_inflamable = fields.Boolean(string='Inflamable (I)')
    clasificacion_biologico = fields.Boolean(string='Biológico (B)')

    clasificaciones_display = fields.Char(
        string='Clasificaciones CRETIB',
        compute='_compute_clasificaciones_display',
        store=True,
    )

    envase_tipo = fields.Selection([
        ('tambor', 'Tambor'), ('contenedor', 'Contenedor'), ('tote', 'Tote'),
        ('tarima', 'Tarima'), ('saco', 'Saco'), ('caja', 'Caja'),
        ('bolsa', 'Bolsa'), ('tanque', 'Tanque'), ('otro', 'Otro'),
    ], string='Tipo de Envase')

    packaging_id = fields.Many2one('uom.uom', string='Unidad de Embalaje')
    envase_capacidad = fields.Char(string='Capacidad')
    cantidad = fields.Float(string='Cantidad (kg)', required=True)
    unidad = fields.Char(string='Unidad', default='kg', readonly=True)
    etiqueta_si = fields.Boolean(string='Etiqueta - Sí', default=True)
    etiqueta_no = fields.Boolean(string='Etiqueta - No', default=False)
    lot_id = fields.Many2one('stock.lot', string='Número de Lote', readonly=True)

    @api.depends('clasificacion_corrosivo', 'clasificacion_reactivo', 'clasificacion_explosivo',
                 'clasificacion_toxico', 'clasificacion_inflamable', 'clasificacion_biologico')
    def _compute_clasificaciones_display(self):
        for record in self:
            clasificaciones = []
            if record.clasificacion_corrosivo: clasificaciones.append('C')
            if record.clasificacion_reactivo: clasificaciones.append('R')
            if record.clasificacion_explosivo: clasificaciones.append('E')
            if record.clasificacion_toxico: clasificaciones.append('T')
            if record.clasificacion_inflamable: clasificaciones.append('I')
            if record.clasificacion_biologico: clasificaciones.append('B')
            record.clasificaciones_display = ', '.join(clasificaciones)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            prod = self.product_id
            if hasattr(prod, 'es_residuo_peligroso') and prod.es_residuo_peligroso:
                self.nombre_residuo = prod.name
                self.clasificacion_corrosivo = getattr(prod, 'clasificacion_corrosivo', False)
                self.clasificacion_reactivo = getattr(prod, 'clasificacion_reactivo', False)
                self.clasificacion_explosivo = getattr(prod, 'clasificacion_explosivo', False)
                self.clasificacion_toxico = getattr(prod, 'clasificacion_toxico', False)
                self.clasificacion_inflamable = getattr(prod, 'clasificacion_inflamable', False)
                self.clasificacion_biologico = getattr(prod, 'clasificacion_biologico', False)
                self.envase_tipo = getattr(prod, 'envase_tipo_default', False)
                val = getattr(prod, 'envase_capacidad_default', False)
                self.envase_capacidad = str(val) if val else ''
            else:
                self.nombre_residuo = prod.name

    @api.onchange('etiqueta_si')
    def _onchange_etiqueta_si(self):
        if self.etiqueta_si:
            self.etiqueta_no = False

    @api.onchange('etiqueta_no')
    def _onchange_etiqueta_no(self):
        if self.etiqueta_no:
            self.etiqueta_si = False

    def _get_field_display_value(self, field_name, value):
        """Retorna el valor legible de un campo para mostrar en el chatter."""
        if value is False or value is None:
            return 'Vacío'
        field = self._fields.get(field_name)
        if not field:
            return str(value)
        if field.type == 'boolean':
            return 'Sí' if value else 'No'
        if field.type == 'selection' and value:
            sel_dict = dict(field.selection)
            return sel_dict.get(value, value)
        if field.type == 'many2one':
            if hasattr(value, 'display_name'):
                return value.display_name or 'Vacío'
            return str(value) if value else 'Vacío'
        if value == '':
            return 'Vacío'
        return str(value)

    def write(self, vals):
        # Capturar valores anteriores para tracking
        changes_by_manifiesto = {}
        tracked_keys = [k for k in vals if k in self.TRACKED_FIELDS]

        if tracked_keys:
            for rec in self:
                if not rec.manifiesto_id:
                    continue
                mid = rec.manifiesto_id.id
                if mid not in changes_by_manifiesto:
                    changes_by_manifiesto[mid] = {'manifiesto': rec.manifiesto_id, 'lines': []}

                line_changes = []
                residuo_label = rec.nombre_residuo or f'Residuo #{rec.id}'
                for field_key in tracked_keys:
                    old_val = getattr(rec, field_key)
                    new_val = vals[field_key]

                    # Comparar correctamente many2one
                    if self._fields[field_key].type == 'many2one':
                        old_comparable = old_val.id if old_val else False
                        new_comparable = new_val
                    else:
                        old_comparable = old_val
                        new_comparable = new_val

                    if old_comparable != new_comparable:
                        label = self.TRACKED_FIELDS[field_key]
                        old_display = self._get_field_display_value(field_key, old_val)
                        # Para many2one, resolver el nuevo valor
                        if self._fields[field_key].type == 'many2one' and new_val:
                            new_record = self.env[self._fields[field_key].comodel_name].browse(new_val)
                            new_display = new_record.display_name or 'Vacío'
                        else:
                            new_display = self._get_field_display_value(field_key, new_val)
                        line_changes.append(f"<li><b>{label}</b>: {old_display} → {new_display}</li>")

                if line_changes:
                    changes_by_manifiesto[mid]['lines'].append(
                        f"<b>📦 {residuo_label}</b><ul>{''.join(line_changes)}</ul>"
                    )

        res = super().write(vals)

        # Postear en el chatter del manifiesto padre
        for _mid, data in changes_by_manifiesto.items():
            if data['lines']:
                body = "<p><b>Cambios en Residuos:</b></p>" + "".join(data['lines'])
                data['manifiesto'].message_post(
                    body=body,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._create_lot_for_residuo()

        # Notificar creación en el chatter del manifiesto padre
        for rec in records:
            if rec.manifiesto_id:
                nombre = rec.nombre_residuo or (rec.product_id.name if rec.product_id else 'Sin nombre')
                cretib = rec.clasificaciones_display or 'Ninguna'
                body = (
                    f"<p>📦 <b>Residuo agregado:</b> {nombre}"
                    f" — {rec.cantidad} kg"
                    f" — CRETIB: {cretib}</p>"
                )
                rec.manifiesto_id.message_post(
                    body=body,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

        return records

    def unlink(self):
        # Notificar eliminación en el chatter del manifiesto padre
        for rec in self:
            if rec.manifiesto_id:
                nombre = rec.nombre_residuo or f'Residuo #{rec.id}'
                body = (
                    f"<p>🗑️ <b>Residuo eliminado:</b> {nombre}"
                    f" — {rec.cantidad} kg</p>"
                )
                rec.manifiesto_id.message_post(
                    body=body,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
        return super().unlink()

    def _create_lot_for_residuo(self):
        for record in self:
            if record.product_id and record.manifiesto_id.numero_manifiesto:
                existing_lot = self.env['stock.lot'].search([
                    ('name', '=', record.manifiesto_id.numero_manifiesto),
                    ('product_id', '=', record.product_id.id),
                    ('company_id', '=', record.manifiesto_id.company_id.id),
                ], limit=1)
                if not existing_lot:
                    lot = self.env['stock.lot'].create({
                        'name': record.manifiesto_id.numero_manifiesto,
                        'product_id': record.product_id.id,
                        'company_id': record.manifiesto_id.company_id.id,
                    })
                    record.lot_id = lot.id
                else:
                    record.lot_id = existing_lot.id


# =============================================================================
# HISTORIAL DE VERSIONES
# =============================================================================
class ManifiestoAmbientalVersion(models.Model):
    _name = 'manifiesto.ambiental.version'
    _description = 'Historial de Versiones del Manifiesto Ambiental'
    _order = 'creation_date desc, version_number desc'
    _rec_name = 'display_name'

    manifiesto_id = fields.Many2one('manifiesto.ambiental', string='Manifiesto Original', required=True, ondelete='cascade')
    version_number = fields.Integer(string='Número de Versión', required=True)
    display_name = fields.Char(string='Nombre', compute='_compute_display_name', store=True)

    pdf_file = fields.Binary(string='Archivo PDF')
    pdf_filename = fields.Char(string='Nombre del PDF')
    data_file = fields.Binary(string='Archivo de Datos')
    data_filename = fields.Char(string='Nombre de Datos')
    documento_fisico_original = fields.Binary(string='Documento Físico Original')
    documento_fisico_filename_original = fields.Char(string='Nombre del Documento Físico Original')
    tenia_documento_fisico = fields.Boolean(string='Tenía Documento Físico')

    creation_date = fields.Datetime(string='Fecha de Creación', required=True, default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string='Creado por', required=True, default=lambda self: self.env.user)
    state_at_creation = fields.Selection([
        ('draft', 'Borrador'), ('confirmed', 'Confirmado'),
        ('in_transit', 'En Tránsito'), ('delivered', 'Entregado'), ('cancel', 'Cancelado'),
    ], string='Estado al Guardar')
    change_reason = fields.Text(string='Motivo del Cambio')
    generador_nombre = fields.Char(string='Generador')
    transportista_nombre = fields.Char(string='Transportista')
    destinatario_nombre = fields.Char(string='Destinatario')
    total_residuos = fields.Integer(string='Total de Residuos')

    @api.depends('manifiesto_id.numero_manifiesto', 'version_number', 'creation_date')
    def _compute_display_name(self):
        for record in self:
            if record.manifiesto_id and record.version_number:
                date_str = record.creation_date.strftime('%d/%m/%Y %H:%M') if record.creation_date else ''
                doc_indicator = " 📄" if record.tenia_documento_fisico else ""
                record.display_name = f"{record.manifiesto_id.numero_manifiesto} - Versión {record.version_number}{doc_indicator} ({date_str})"
            else:
                record.display_name = 'Nueva Versión'

    def get_available_file_info(self):
        if self.pdf_file and self.pdf_filename:
            return {'has_file': True, 'file_type': 'pdf', 'field_name': 'pdf_file', 'filename_field': 'pdf_filename', 'filename': self.pdf_filename, 'display_name': 'PDF'}
        elif self.data_file and self.data_filename:
            return {'has_file': True, 'file_type': 'data', 'field_name': 'data_file', 'filename_field': 'data_filename', 'filename': self.data_filename, 'display_name': 'Datos'}
        return {'has_file': False, 'file_type': None, 'field_name': None, 'filename_field': None, 'filename': None, 'display_name': 'Sin archivo'}

    def action_download_file(self):
        file_info = self.get_available_file_info()
        if not file_info['has_file']:
            raise UserError("No hay archivo disponible para esta versión.")
        return {'type': 'ir.actions.act_url', 'url': f'/web/content/{self._name}/{self.id}/{file_info["field_name"]}/{file_info["filename"]}?download=true', 'target': 'self'}

    def action_view_file(self):
        file_info = self.get_available_file_info()
        if not file_info['has_file']:
            raise UserError("No hay archivo disponible para esta versión.")
        return {'type': 'ir.actions.act_url', 'url': f'/web/content/{self._name}/{self.id}/{file_info["field_name"]}/{file_info["filename"]}', 'target': 'new'}

    def action_download_documento_fisico(self):
        if not self.documento_fisico_original:
            raise UserError("Esta versión no tiene documento físico disponible.")
        return {'type': 'ir.actions.act_url', 'url': f'/web/content/{self._name}/{self.id}/documento_fisico_original/{self.documento_fisico_filename_original}?download=true', 'target': 'self'}

    def action_view_documento_fisico(self):
        if not self.documento_fisico_original:
            raise UserError("Esta versión no tiene documento físico disponible.")
        return {'type': 'ir.actions.act_url', 'url': f'/web/content/{self._name}/{self.id}/documento_fisico_original/{self.documento_fisico_filename_original}', 'target': 'new'}

    def unlink(self):
        if any(v.version_number == 1 for v in self):
            raise UserError("No se puede eliminar la versión 1 (original) del manifiesto.")
        return super().unlink()

    def action_open_documento_fisico(self):
        return False

    def action_open_secuencia(self):
        return False```

## ./models/manifiesto_discrepancia.py
```py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ManifiestoDiscrepancia(models.Model):
    _name = 'manifiesto.discrepancia'
    _description = 'Reporte de Discrepancias del Manifiesto'
    _rec_name = 'name'
    _order = 'fecha_inspeccion desc'

    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True
    )

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto',
        required=True,
        ondelete='cascade'
    )

    # Datos del encabezado (se autocompletan del manifiesto)
    numero_manifiesto = fields.Char(
        string='Número de Manifiesto',
        related='manifiesto_id.numero_manifiesto',
        store=True
    )

    fecha_manifiesto = fields.Date(
        string='Fecha del Manifiesto',
        related='manifiesto_id.generador_fecha',
        store=True
    )

    transportista_nombre = fields.Char(
        string='Transportista',
        related='manifiesto_id.transportista_nombre',
        store=True
    )

    numero_placa = fields.Char(
        string='Placa',
        related='manifiesto_id.numero_placa',
        store=True
    )

    generador_nombre = fields.Char(
        string='Generador',
        related='manifiesto_id.generador_nombre',
        store=True
    )

    # Campos editables del encabezado
    operador_nombre = fields.Char(
        string='Nombre del Operador',
        help='Nombre del operador/chofer del vehículo'
    )

    fecha_inspeccion = fields.Date(
        string='Fecha de Inspección',
        default=fields.Date.context_today,
        required=True
    )

    revisado_por = fields.Char(
        string='Revisó',
        help='Nombre y cargo de quien revisó'
    )

    observaciones_generales = fields.Text(
        string='Observaciones Generales'
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Finalizado'),
    ], string='Estado', default='draft')

    linea_ids = fields.One2many(
        'manifiesto.discrepancia.linea',
        'discrepancia_id',
        string='Líneas de Discrepancia'
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    tiene_discrepancias = fields.Boolean(
        string='Tiene Discrepancias',
        compute='_compute_tiene_discrepancias',
        store=True
    )

    @api.depends('numero_manifiesto', 'fecha_inspeccion')
    def _compute_name(self):
        for rec in self:
            if rec.numero_manifiesto and rec.fecha_inspeccion:
                rec.name = f"DISC-{rec.numero_manifiesto}-{rec.fecha_inspeccion.strftime('%d%m%Y')}"
            elif rec.numero_manifiesto:
                rec.name = f"DISC-{rec.numero_manifiesto}"
            else:
                rec.name = 'Nueva Discrepancia'

    @api.depends('linea_ids.tiene_diferencia')
    def _compute_tiene_discrepancias(self):
        for rec in self:
            rec.tiene_discrepancias = any(l.tiene_diferencia for l in rec.linea_ids)

    def action_finalizar(self):
        self.state = 'done'

    def action_borrador(self):
        self.state = 'draft'

    def action_print_discrepancia(self):
        return self.env.ref('manifiesto_ambiental.action_report_discrepancia').report_action(self)


class ManifiestoDiscrepanciaLinea(models.Model):
    _name = 'manifiesto.discrepancia.linea'
    _description = 'Línea de Discrepancia'
    _order = 'sequence, id'

    discrepancia_id = fields.Many2one(
        'manifiesto.discrepancia',
        string='Discrepancia',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(default=10)

    # Referencia al residuo del manifiesto (opcional, para autocompletar)
    residuo_manifiesto_id = fields.Many2one(
        'manifiesto.ambiental.residuo',
        string='Residuo del Manifiesto',
        domain="[('manifiesto_id', '=', parent.manifiesto_id)]",
        help='Seleccionar el residuo del manifiesto para autocompletar'
    )

    # --- LO QUE DECÍA EL MANIFIESTO ---
    nombre_residuo = fields.Char(
        string='Nombre del Residuo',
        required=True
    )

    cantidad_manifestada = fields.Float(
        string='Cantidad Manifestada',
        digits=(16, 2)
    )

    contenedor_manifestado = fields.Char(
        string='Contenedor Manifestado',
        help='Tipo de contenedor según el manifiesto'
    )

    # --- LO QUE SE RECIBIÓ REALMENTE ---
    cantidad_real = fields.Float(
        string='Cantidad Real',
        digits=(16, 2)
    )

    contenedor_real = fields.Char(
        string='Contenedor Real',
        help='Tipo de contenedor realmente recibido'
    )

    observacion = fields.Text(
        string='Observación'
    )

    tiene_diferencia = fields.Boolean(
        string='Hay Diferencia',
        compute='_compute_tiene_diferencia',
        store=True
    )

    tipo_discrepancia = fields.Selection([
        ('ok', 'OK - Sin Diferencia'),
        ('cantidad', 'Diferencia en Cantidad'),
        ('contenedor', 'Diferencia en Contenedor'),
        ('no_manifestado', 'Material No Manifestado'),
        ('faltante', 'Material Faltante'),
        ('ambos', 'Diferencia en Cantidad y Contenedor'),
        ('otro', 'Otro'),
    ], string='Tipo de Discrepancia', default='ok')

    @api.depends('cantidad_manifestada', 'cantidad_real', 'contenedor_manifestado', 'contenedor_real')
    def _compute_tiene_diferencia(self):
        for rec in self:
            diff_cantidad = abs((rec.cantidad_real or 0) - (rec.cantidad_manifestada or 0)) > 0.001
            diff_contenedor = (rec.contenedor_real or '').strip().lower() != (rec.contenedor_manifestado or '').strip().lower()
            rec.tiene_diferencia = diff_cantidad or diff_contenedor

    @api.onchange('residuo_manifiesto_id')
    def _onchange_residuo_manifiesto_id(self):
        if self.residuo_manifiesto_id:
            r = self.residuo_manifiesto_id
            self.nombre_residuo = r.nombre_residuo or (r.product_id.name if r.product_id else '')
            self.cantidad_manifestada = r.cantidad
            # Determinar contenedor manifestado
            if r.packaging_id:
                self.contenedor_manifestado = r.packaging_id.name
            elif r.envase_tipo:
                self.contenedor_manifestado = dict(r._fields['envase_tipo'].selection).get(r.envase_tipo, r.envase_tipo)
            else:
                self.contenedor_manifestado = ''
            # Pre-llenar real igual al manifestado
            self.cantidad_real = r.cantidad
            self.contenedor_real = self.contenedor_manifestado```

## ./models/product_extension.py
```py
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
        return ', '.join(clasificaciones)```

## ./models/recepcion_extension.py
```py
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
    )```

## ./models/res_partner_extension.py
```py
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
    )```

## ./models/service_order_extension.py
```py
# models/service_order_extension.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    manifiesto_ids = fields.One2many(
        'manifiesto.ambiental',
        'service_order_id',
        string='Manifiestos Generados',
    )
    manifiesto_count = fields.Integer(
        string='No. Manifiestos',
        compute='_compute_manifiesto_count',
    )

    @api.depends('manifiesto_ids')
    def _compute_manifiesto_count(self):
        for rec in self:
            rec.manifiesto_count = len(rec.manifiesto_ids)

    def action_view_manifiestos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Manifiestos Ambientales'),
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'list,form',
            'domain': [('service_order_id', '=', self.id)],
            'context': {'default_service_order_id': self.id},
        }

    def action_create_manifiesto(self):
        self.ensure_one()

        # 1. Generador (para datos de dirección)
        generador = self.generador_id if self.generador_id else self.partner_id

        # El nombre/razón social en el campo 4 siempre es el cliente de la OS
        # La dirección y demás datos vienen del generador seleccionado
        nombre_razon_social = self.partner_id.name or generador.name or ''

        # 2. Fecha del servicio
        fecha_servicio = (
            getattr(self, 'date_start', None) or
            getattr(self, 'scheduled_date', None) or
            getattr(self, 'service_date', None) or
            getattr(self, 'date_order', None) or
            fields.Date.context_today(self)
        )

        # 3. Ruta
        ruta = ''
        if self.pickup_location_id:
            ruta = self.pickup_location_id.contact_address_complete or self.pickup_location_id.name or ''
            ruta = ruta.replace('\n', ', ')
        elif self.pickup_location:
            ruta = self.pickup_location

        # 4. Líneas de residuos
        residuo_lines = []
        for line in self.line_ids:
            if not line.product_id:
                continue
            prod_name = line.product_id.name or ''
            if prod_name.strip().upper().startswith('SERVICIO DE'):
                continue

            cantidad_final = line.weight_kg if line.weight_kg > 0.0 else line.product_uom_qty
            prod = line.product_id

            capacidad_final = line.capacity if line.capacity else ''
            if not capacidad_final and hasattr(prod, 'envase_capacidad_default') and prod.envase_capacidad_default:
                capacidad_final = str(prod.envase_capacidad_default)

            residuo_lines.append((0, 0, {
                'product_id': prod.id,
                'nombre_residuo': line.description or prod.name,
                'cantidad': cantidad_final,
                'residue_type': line.residue_type,
                'packaging_id': line.packaging_id.id if line.packaging_id else False,
                'clasificacion_corrosivo': prod.clasificacion_corrosivo,
                'clasificacion_reactivo': prod.clasificacion_reactivo,
                'clasificacion_explosivo': prod.clasificacion_explosivo,
                'clasificacion_toxico': prod.clasificacion_toxico,
                'clasificacion_inflamable': prod.clasificacion_inflamable,
                'clasificacion_biologico': prod.clasificacion_biologico,
                'envase_tipo': prod.envase_tipo_default,
                'envase_capacidad': capacidad_final,
                'etiqueta_si': True,
                'etiqueta_no': False,
            }))

        # 5. Destinatario
        dest = self.destinatario_id if self.destinatario_id else self.partner_id

        # 6. Vehículo y placa
        vehicle = self.vehicle_id
        vehicle_id = vehicle.id if vehicle else False
        # Placa: prioridad al campo de la OS, luego la del vehículo
        numero_placa = self.numero_placa or (vehicle.license_plate if vehicle else '') or ''

        # 7. Tipo de vehículo: construir desde el fleet.vehicle, fallback al transportista
        tipo_vehiculo = ''
        if vehicle:
            brand = vehicle.model_id.brand_id.name if vehicle.model_id and vehicle.model_id.brand_id else ''
            model = vehicle.model_id.name if vehicle.model_id else ''
            tipo_vehiculo = f"{brand} {model}".strip() or vehicle.name or ''
        if not tipo_vehiculo and self.transportista_id:
            tipo_vehiculo = self.transportista_id.tipo_vehiculo or ''

        # 8. Chofer
        chofer_id = self.chofer_id.id if self.chofer_id else False

        manifiesto_vals = {
            'service_order_id': self.id,

            # --- GENERADOR ---
            'generador_id': generador.id,
            'numero_registro_ambiental': generador.numero_registro_ambiental or '',
            'generador_nombre': nombre_razon_social,
            'generador_codigo_postal': generador.zip or '',
            'generador_calle': generador.street or '',
            'generador_num_ext': generador.street_number or '',
            'generador_num_int': generador.street_number2 or '',
            'generador_colonia': generador.street2 or '',
            'generador_municipio': generador.city or '',
            'generador_estado': generador.state_id.name if generador.state_id else '',
            'generador_telefono': generador.phone or '',
            'generador_email': generador.email or '',
            'generador_responsable_id': self.generador_responsable_id.id if self.generador_responsable_id else False,
            'generador_responsable_nombre': self.generador_responsable_id.name if self.generador_responsable_id else '',
            'generador_fecha': fecha_servicio,

            # --- TRANSPORTISTA ---
            'transportista_id': self.transportista_id.id if self.transportista_id else False,
            'transportista_nombre': self.transportista_id.name if self.transportista_id else '',
            'transportista_codigo_postal': self.transportista_id.zip if self.transportista_id else '',
            'transportista_calle': self.transportista_id.street if self.transportista_id else '',
            'transportista_num_ext': self.transportista_id.street_number if self.transportista_id else '',
            'transportista_num_int': self.transportista_id.street_number2 if self.transportista_id else '',
            'transportista_colonia': self.transportista_id.street2 if self.transportista_id else '',
            'transportista_municipio': self.transportista_id.city if self.transportista_id else '',
            'transportista_estado': self.transportista_id.state_id.name if (self.transportista_id and self.transportista_id.state_id) else '',
            'transportista_telefono': self.transportista_id.phone if self.transportista_id else '',
            'transportista_email': self.transportista_id.email if self.transportista_id else '',
            'numero_autorizacion_semarnat': self.transportista_id.numero_autorizacion_semarnat if self.transportista_id else '',
            'numero_permiso_sct': self.transportista_id.numero_permiso_sct if self.transportista_id else '',

            # --- VEHÍCULO, PLACA, CHOFER (propagación explícita) ---
            'vehicle_id': vehicle_id,
            'tipo_vehiculo': tipo_vehiculo,
            'numero_placa': numero_placa,
            'chofer_id': chofer_id,

            # --- RESPONSABLE TRANSPORTISTA ---
            'transportista_responsable_id': self.transportista_responsable_id.id if self.transportista_responsable_id else False,
            'transportista_responsable_nombre': self.transportista_responsable_id.name if self.transportista_responsable_id else '',
            'transportista_fecha': fecha_servicio,

            # --- DESTINATARIO ---
            'destinatario_id': dest.id,
            'destinatario_nombre': dest.name or '',
            'destinatario_codigo_postal': dest.zip or '',
            'destinatario_calle': dest.street or '',
            'destinatario_num_ext': dest.street_number or '',
            'destinatario_num_int': dest.street_number2 or '',
            'destinatario_colonia': dest.street2 or '',
            'destinatario_municipio': dest.city or '',
            'destinatario_estado': dest.state_id.name if dest.state_id else '',
            'destinatario_telefono': dest.phone or '',
            'destinatario_email': dest.email or '',
            'numero_autorizacion_semarnat_destinatario': dest.numero_autorizacion_semarnat or '',
            'destinatario_fecha': fecha_servicio,

            # --- OTROS ---
            'nombre_persona_recibe': self.contact_name or '',
            'ruta_empresa': ruta,
            'instrucciones_especiales': self.observaciones or '',

            # --- RESIDUOS ---
            'residuo_ids': residuo_lines,
        }

        manifiesto = self.env['manifiesto.ambiental'].create(manifiesto_vals)

        return {
            'name': 'Manifiesto Ambiental',
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'form',
            'res_id': manifiesto.id,
            'target': 'current',
        }```

## ./reports/manifiesto_ambiental_report.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- FORMATO DE PÁGINA A4 SIN MÁRGENES -->
    <record id="paperformat_manifiesto_ambiental_sin_margen" model="report.paperformat">
        <field name="name">Manifiesto Ambiental Sin Margen</field>
        <field name="default" eval="False"/>
        <field name="format">A4</field>
        <field name="orientation">Portrait</field>
        <field name="margin_top">2</field>
        <field name="margin_bottom">10</field>
        <field name="margin_left">5</field>
        <field name="margin_right">5</field>
        <field name="header_line" eval="False"/>
        <field name="header_spacing">35</field>
        <field name="dpi">90</field>
    </record>

    <!-- ACCIÓN DEL REPORTE (Entrada) - SIN binding para que NO aparezca en el engrane -->
    <record id="action_report_manifiesto_ambiental" model="ir.actions.report">
        <field name="name">Manifiesto Ambiental (Entrada)</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">manifiesto_ambiental.manifiesto_ambiental_document</field>
        <field name="report_file">manifiesto_ambiental.manifiesto_ambiental_document</field>
        <!-- NO binding_model_id - el botón action_print_manifiesto decide qué reporte usar -->
        <field name="paperformat_id" ref="manifiesto_ambiental.paperformat_manifiesto_ambiental_sin_margen"/>
    </record>

    <!-- PLANTILLA QWEB DEL REPORTE -->
    <template id="manifiesto_ambiental_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">
                        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
                        <style>
                            @page { margin: 5mm; size: A4; }

                            /* Tipografía y densidad para caber en 1 hoja */
                            body, td, th, strong, .labelcell, .subcell {
                                font-family: "DejaVu Sans", Arial, "Liberation Sans", sans-serif !important;
                                font-size: 10.5px;
                                line-height: 1.15;
                            }
                            .page { margin-top: 2px !important; padding-top: 2px !important; }

                            /* Encabezado externo compacto */
                            .header, .o_company_document_layout .header, .company_address, .o_company_address,
                            .external_layout .header, .address, .o_report_layout_standard .header,
                            .o_report_layout_boxed .header, .o_report_layout_clean .header {
                                margin-bottom: 8px !important;
                                padding-bottom: 4px !important;
                                border-bottom: none !important;
                            }

                            .footer, .o_company_document_layout .footer {
                                display: none !important;
                                height: 0px !important;
                                padding: 0px !important;
                                margin: 0px !important;
                            }

                            .page-title {
                                text-align: center;
                                font-size: 12px;
                                font-weight: 700;
                                margin: 2px 0 4px;
                                font-family: "DejaVu Sans", Arial, sans-serif !important;
                            }

                            table { width: 100%; border-collapse: collapse; margin-bottom: 2px; page-break-inside: avoid; }
                            td, th { border: 1px solid #666; padding: 2px 4px; font-size: 10px; vertical-align: top; }

                            /* Sin sombreados */
                            th, .header-table, .labelcell, .subcell { background: none !important; }
                            th, .header-table { font-weight: 700; text-align: center; }
                            .labelcell { font-weight: 700; font-size: 10.5px; }
                            .subcell { font-weight: 700; font-size: 9.8px; }

                            .no-border { border: none !important; }
                            .center-text { text-align: center; }

                            table.section-4 { width: 100%; border-collapse: collapse; table-layout: fixed; }

                            table.signature-section { width: 100%; border-collapse: separate; border-spacing: 0; margin-bottom: 2px; }
                            table.signature-section > tbody > tr > td { border: none !important; padding: 0; }
                            .signature-container { border: 1px solid #666; padding: 4px; }
                            .signature-text { margin: 0 0 4px 0; }
                            .signature-fields { display: table; width: 100%; margin-top: 2px; }
                            .signature-fields .cell { display: table-cell; vertical-align: top; padding-right: 8px; }
                            .signature-fields .cell:last-child { padding-right: 0; }

                            tr, td { page-break-inside: avoid; }
                        </style>

                        <!-- TÍTULO PRINCIPAL -->
                        <div class="page-title">
                            MANIFIESTO DE ENTREGA, TRANSPORTE Y RECEPCIÓN DE RESIDUOS PELIGROSOS (GENERADOR)
                        </div>

                        <!-- ENCABEZADO 1-3 -->
                        <table>
                            <tr>
                                <td class="labelcell" style="width:45%">
                                    1. Núm. de registro ambiental: <span t-field="doc.numero_registro_ambiental"/>
                                </td>
                                <td class="labelcell" style="width:40%">
                                    2. Núm. de manifiesto: <span t-field="doc.numero_manifiesto"/>
                                </td>
                                <td class="labelcell" style="width:15%">
                                    3. Página: <span t-field="doc.pagina"/>
                                </td>
                            </tr>
                        </table>

                        <!-- 4. GENERADOR -->
                        <table class="section-4">
                            <colgroup>
                                <col style="width:15%"/>
                                <col style="width:25%"/>
                                <col style="width:40%"/>
                                <col style="width:10%"/>
                                <col style="width:10%"/>
                            </colgroup>

                            <tr>
                                <td class="labelcell" colspan="5">
                                    4. Nombre o razón social del generador: <span t-field="doc.generador_nombre"/>
                                </td>
                            </tr>

                            <tr>
                                <td class="subcell">Domicilio</td>
                                <td class="subcell">Código postal: <span t-field="doc.generador_codigo_postal"/></td>
                                <td class="subcell">Calle: <span t-field="doc.generador_calle"/></td>
                                <td class="subcell">Núm. Ext.: <span t-field="doc.generador_num_ext"/></td>
                                <td class="subcell">Núm. Int.: <span t-field="doc.generador_num_int"/></td>
                            </tr>

                            <tr>
                                <td class="subcell" colspan="2">
                                    Colonia: <span t-field="doc.generador_colonia"/>
                                </td>
                                <td class="subcell" colspan="1">
                                    Municipio o Delegación: <span t-field="doc.generador_municipio"/>
                                </td>
                                <td class="subcell" colspan="2">
                                    Estado: <span t-field="doc.generador_estado"/>
                                </td>
                            </tr>

                            <tr>
                                <td class="subcell" colspan="2">
                                    Teléfono: <span t-field="doc.generador_telefono"/>
                                </td>
                                <td class="subcell" colspan="3">
                                    Correo electrónico: <span t-field="doc.generador_email"/>
                                </td>
                            </tr>
                        </table>

                        <!-- 5. IDENTIFICACIÓN DE LOS RESIDUOS -->
                        <table>
                            <colgroup>
                                <col style="width:25%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                                <col style="width:12%"/>
                                <col style="width:10%"/>
                                <col style="width:10%"/>
                                <col style="width:3%"/>
                                <col style="width:3%"/>
                            </colgroup>

                            <tr>
                                <th colspan="13" class="header-table">5. Identificación de los residuos</th>
                            </tr>
                            <tr>
                                <th class="header-table">Nombre del residuo</th>
                                <th class="header-table" colspan="7">Clasificación</th>
                                <th class="header-table" colspan="2">Envase</th>
                                <th class="header-table">Cantidad (kg)</th>
                                <th class="header-table" colspan="2">Etiqueta</th>
                            </tr>
                            <tr>
                                <th class="header-table"></th>
                                <th class="header-table">C</th>
                                <th class="header-table">R</th>
                                <th class="header-table">E</th>
                                <th class="header-table">T</th>
                                <th class="header-table">I</th>
                                <th class="header-table">B</th>
                                <th class="header-table">M</th>
                                <th class="header-table">Embalaje</th>
                                <th class="header-table">Capacidad</th>
                                <th class="header-table"></th>
                                <th class="header-table">Sí</th>
                                <th class="header-table">No</th>
                            </tr>

                            <t t-foreach="doc.residuo_ids" t-as="residuo">
                                <tr>
                                    <td><span t-field="residuo.nombre_residuo"/></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_corrosivo">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_reactivo">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_explosivo">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_toxico">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_inflamable">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_biologico">X</span></td>
                                    <td class="center-text"></td>
                                    <td class="center-text">
                                        <span t-if="residuo.packaging_id" t-field="residuo.packaging_id.name"/>
                                        <span t-elif="residuo.envase_tipo" t-field="residuo.envase_tipo"/>
                                    </td>
                                    <td class="center-text"><span t-field="residuo.envase_capacidad"/></td>
                                    <td class="center-text"><span t-field="residuo.cantidad"/> kg</td>
                                    <td class="center-text"><span t-if="residuo.etiqueta_si">X</span></td>
                                    <td class="center-text"><span t-if="residuo.etiqueta_no">X</span></td>
                                </tr>
                            </t>

                            <t t-set="residuos_count" t-value="len(doc.residuo_ids)"/>
                            <t t-set="min_rows" t-value="18"/>
                            <t t-set="empty_rows" t-value="max(0, min_rows - residuos_count)"/>
                            <t t-foreach="range(empty_rows)" t-as="empty_row">
                                <tr style="height: 22px;">
                                    <td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td>
                                    <td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td>
                                    <td>&#160;</td><td>&#160;</td><td>&#160;</td>
                                </tr>
                            </t>
                        </table>

                        <!-- 6. INSTRUCCIONES ESPECIALES -->
                        <table>
                            <tr>
                                <td class="labelcell">6. Instrucciones especiales e información adicional para el manejo seguro:</td>
                            </tr>
                            <tr>
                                <td style="height: 28px; vertical-align: top;">
                                    <span t-field="doc.instrucciones_especiales"/>
                                </td>
                            </tr>
                        </table>

                        <!-- 7. DECLARACIÓN DEL GENERADOR -->
                        <table class="signature-section">
                            <tr>
                                <td>
                                    <div class="signature-container">
                                        <div class="signature-text">
                                            7. Declaración del generador: Declaro bajo protesta de decir verdad que el contenido de este lote está total y correctamente descrito mediante el número de manifiesto, nombre del residuo, características CRETIB, debidamente envasado y etiquetado y que se han previsto las condiciones de seguridad para su transporte por vía terrestre de acuerdo con la legislación vigente.
                                        </div>
                                        <div class="signature-fields">
                                            <div class="cell" style="width:40%;">
                                                <strong>Nombre y firma del responsable:</strong><br/>
                                                <span t-field="doc.generador_responsable_nombre"/>
                                            </div>
                                            <div class="cell" style="width:30%;">
                                                <strong>Fecha:</strong><br/>
                                                <span t-field="doc.generador_fecha"/>
                                            </div>
                                            <div class="cell" style="width:30%;">
                                                <strong>Sello:</strong><br/>
                                                <span t-field="doc.generador_sello"/>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </table>

                        <!-- 8. TRANSPORTISTA -->
                        <table>
                            <tr>
                                <td colspan="4" class="labelcell">8. Nombre o razón social del transportista: <span t-field="doc.transportista_nombre"/></td>
                            </tr>
                            <tr>
                                <td class="subcell" style="width:25%;">Código postal: <span t-field="doc.transportista_codigo_postal"/></td>
                                <td class="subcell" style="width:25%;">Calle: <span t-field="doc.transportista_calle"/></td>
                                <td class="subcell" style="width:25%;">Núm. Ext.: <span t-field="doc.transportista_num_ext"/></td>
                                <td class="subcell" style="width:25%;">Núm. Int.: <span t-field="doc.transportista_num_int"/></td>
                            </tr>
                            <tr>
                                <td><strong>Colonia:</strong> <span t-field="doc.transportista_colonia"/></td>
                                <td><strong>Municipio o Delegación:</strong> <span t-field="doc.transportista_municipio"/></td>
                                <td colspan="2"><strong>Estado:</strong> <span t-field="doc.transportista_estado"/></td>
                            </tr>
                            <tr>
                                <td><strong>Teléfono:</strong> <span t-field="doc.transportista_telefono"/></td>
                                <td colspan="3"><strong>Correo electrónico:</strong> <span t-field="doc.transportista_email"/></td>
                            </tr>
                        </table>

                        <!-- 9-12. INFORMACIÓN DEL TRANSPORTE -->
                        <table>
                            <tr>
                                <td style="width:25%;"><strong>9. Núm. de autorización de la SEMARNAT:</strong><br/><span t-field="doc.numero_autorizacion_semarnat"/></td>
                                <td style="width:25%;"><strong>10. Núm. de permiso S.C.T.:</strong><br/><span t-field="doc.numero_permiso_sct"/></td>
                                <td style="width:25%;"><strong>11. Tipo de vehículo:</strong><br/><span t-field="doc.tipo_vehiculo"/></td>
                                <td style="width:25%;"><strong>12. Núm. de placa:</strong><br/><span t-field="doc.numero_placa"/></td>
                            </tr>
                        </table>

                        <!-- 13. RUTA -->
                        <table>
                            <tr>
                                <td class="labelcell">13. Ruta de la empresa generadora hasta su entrega:</td>
                            </tr>
                            <tr>
                                <td style="height: 28px; vertical-align: top;">
                                    <span t-field="doc.ruta_empresa"/>
                                </td>
                            </tr>
                        </table>

                        <!-- 14. DECLARACIÓN DEL TRANSPORTISTA -->
                        <table class="signature-section">
                            <tr>
                                <td>
                                    <div class="signature-container">
                                        <div class="signature-text">
                                            14. Declaración del transportista: Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto para su transporte a la empresa destinataria señalada por el generador.
                                        </div>
                                        <div class="signature-fields">
                                            <div class="cell" style="width:40%;">
                                                <strong>Nombre y firma del responsable:</strong><br/>
                                                <span t-field="doc.transportista_responsable_nombre"/>
                                            </div>
                                            <div class="cell" style="width:30%;">
                                                <strong>Fecha:</strong><br/>
                                                <span t-field="doc.transportista_fecha"/>
                                            </div>
                                            <div class="cell" style="width:30%;">
                                                <strong>Sello:</strong><br/>
                                                <span t-field="doc.transportista_sello"/>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </table>

                        <!-- 15. DESTINATARIO -->
                        <table>
                            <tr>
                                <td colspan="4" class="labelcell">15. Nombre o razón social del destinatario: <span t-field="doc.destinatario_nombre"/></td>
                            </tr>
                            <tr>
                                <td class="subcell" style="width:25%;">Código postal: <span t-field="doc.destinatario_codigo_postal"/></td>
                                <td class="subcell" style="width:25%;">Calle: <span t-field="doc.destinatario_calle"/></td>
                                <td class="subcell" style="width:25%;">Núm. Ext.: <span t-field="doc.destinatario_num_ext"/></td>
                                <td class="subcell" style="width:25%;">Núm. Int.: <span t-field="doc.destinatario_num_int"/></td>
                            </tr>
                            <tr>
                                <td><strong>Colonia:</strong> <span t-field="doc.destinatario_colonia"/></td>
                                <td><strong>Municipio o Delegación:</strong> <span t-field="doc.destinatario_municipio"/></td>
                                <td colspan="2"><strong>Estado:</strong> <span t-field="doc.destinatario_estado"/></td>
                            </tr>
                            <tr>
                                <td><strong>Teléfono:</strong> <span t-field="doc.destinatario_telefono"/></td>
                                <td colspan="3"><strong>Correo electrónico:</strong> <span t-field="doc.destinatario_email"/></td>
                            </tr>
                        </table>

                        <!-- 16-18. INFORMACIÓN ADICIONAL DEL DESTINATARIO -->
                        <table>
                            <tr>
                                <td style="width:50%;"><strong>16. Núm. autorización de la SEMARNAT:</strong><br/><span t-field="doc.numero_autorizacion_semarnat_destinatario"/></td>
                                <td style="width:50%;"><strong>17. Nombre y cargo de la persona que recibe los residuos:</strong><br/><span t-field="doc.nombre_persona_recibe"/></td>
                            </tr>
                            <tr>
                                <td colspan="2" class="labelcell">18. Observaciones:</td>
                            </tr>
                            <tr>
                                <td colspan="2" style="height: 28px; vertical-align: top;">
                                    <span t-field="doc.observaciones_destinatario"/>
                                </td>
                            </tr>
                        </table>

                        <!-- 19. DECLARACIÓN DEL DESTINATARIO -->
                        <table class="signature-section">
                            <tr>
                                <td>
                                    <div class="signature-container">
                                        <div class="signature-text">
                                            19. Declaración del destinatario: Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto.
                                        </div>
                                        <div class="signature-fields">
                                            <div class="cell" style="width:40%;">
                                                <strong>Nombre y firma del responsable:</strong><br/>
                                                <span t-field="doc.destinatario_responsable_nombre"/>
                                            </div>
                                            <div class="cell" style="width:30%;">
                                                <strong>Fecha:</strong><br/>
                                                <span t-field="doc.destinatario_fecha"/>
                                            </div>
                                            <div class="cell" style="width:30%;">
                                                <strong>Sello:</strong><br/>
                                                <span t-field="doc.destinatario_sello"/>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>```

## ./reports/report_discrepancia.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- FORMATO HOJA -->
    <record id="paperformat_discrepancia" model="report.paperformat">
        <field name="name">Reporte Discrepancias</field>
        <field name="default" eval="False"/>
        <field name="format">A4</field>
        <field name="orientation">Portrait</field>
        <field name="margin_top">65</field>
        <field name="margin_bottom">10</field>
        <field name="margin_left">10</field>
        <field name="margin_right">10</field>
        <field name="header_line" eval="False"/>
        <field name="header_spacing">55</field>
        <field name="dpi">90</field>
    </record>

    <!-- ACCIÓN DEL REPORTE -->
    <record id="action_report_discrepancia" model="ir.actions.report">
        <field name="name">Reporte de Discrepancias</field>
        <field name="model">manifiesto.discrepancia</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">manifiesto_ambiental.report_discrepancia_document</field>
        <field name="report_file">manifiesto_ambiental.report_discrepancia_document</field>
        <field name="binding_model_id" ref="model_manifiesto_discrepancia"/>
        <field name="binding_type">report</field>
        <field name="paperformat_id" ref="manifiesto_ambiental.paperformat_discrepancia"/>
    </record>

    <!-- PLANTILLA QWEB -->
    <template id="report_discrepancia_document">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page" style="margin-top: 0px;">
                        <style>
                            .formal-table {
                                width: 100%;
                                border-collapse: collapse;
                                font-size: 10px;
                                margin-bottom: 15px;
                                color: #000;
                            }
                            .formal-table th,
                            .formal-table td {
                                border: 1px solid #000;
                                padding: 4px 6px;
                                vertical-align: middle;
                            }
                            .bg-header {
                                background-color: #f0f0f0;
                                font-weight: bold;
                                text-transform: uppercase;
                                width: 15%;
                            }
                            .section-title {
                                background-color: #2c5f2e;
                                color: #fff;
                                padding: 3px 10px;
                                font-size: 11px;
                                font-weight: bold;
                                text-transform: uppercase;
                                margin-bottom: 0;
                            }
                            .text-right  { text-align: right; }
                            .text-center { text-align: center; }

                            .disc-table {
                                width: 100%;
                                border-collapse: collapse;
                                font-size: 9.5px;
                                margin-bottom: 15px;
                                color: #000;
                            }
                            .disc-table th,
                            .disc-table td {
                                border: 1px solid #000;
                                padding: 4px 6px;
                                vertical-align: middle;
                                text-align: center;
                            }
                            .disc-table th {
                                background-color: #2c5f2e !important;
                                color: #fff !important;
                                font-weight: bold;
                                font-size: 9px;
                                -webkit-print-color-adjust: exact;
                                print-color-adjust: exact;
                            }
                            .disc-table th.th-manifesto {
                                background-color: #1a3e1c !important;
                            }
                            .disc-table th.th-real {
                                background-color: #4a7c4e !important;
                            }
                            .disc-table td.td-left { text-align: left; }
                            .disc-table tr.row-discrepancia td {
                                background-color: #fff3cd !important;
                                -webkit-print-color-adjust: exact;
                                print-color-adjust: exact;
                            }
                            .disc-table tr.row-ok td {
                                background-color: #d4edda !important;
                                -webkit-print-color-adjust: exact;
                                print-color-adjust: exact;
                            }
                            .badge-diff { font-weight: bold; color: #856404; }
                            .badge-ok   { font-weight: bold; color: #155724; }
                        </style>

                        <div class="oe_structure"/>

                        <!-- ENCABEZADO -->
                        <div class="row mb16 align-items-center">
                            <div class="col-8">
                                <h4 class="m-0" style="font-weight: bold; text-transform: uppercase;">
                                    Reporte de Discrepancias – Recepción de Residuos Peligrosos
                                </h4>
                            </div>
                            <div class="col-4 text-right">
                                <div style="border: 2px solid #000; padding: 5px; text-align: center;">
                                    <strong style="font-size: 13px;">
                                        MANIFIESTO: <t t-esc="doc.numero_manifiesto or '—'"/>
                                    </strong>
                                </div>
                            </div>
                        </div>

                        <!-- 1. INFORMACIÓN GENERAL -->
                        <div class="section-title">Información General</div>
                        <table class="formal-table">
                            <tr>
                                <td class="bg-header">No. Manifiesto</td>
                                <td style="width: 35%;"><strong><t t-esc="doc.numero_manifiesto or '—'"/></strong></td>
                                <td class="bg-header">Fecha Manifiesto</td>
                                <td style="width: 35%;">
                                    <t t-if="doc.fecha_manifiesto">
                                        <t t-esc="doc.fecha_manifiesto.strftime('%d/%m/%Y')"/>
                                    </t>
                                    <t t-else="">—</t>
                                </td>
                            </tr>
                            <tr>
                                <td class="bg-header">Generador</td>
                                <td><t t-esc="doc.generador_nombre or '—'"/></td>
                                <td class="bg-header">Fecha Inspección</td>
                                <td>
                                    <t t-if="doc.fecha_inspeccion">
                                        <t t-esc="doc.fecha_inspeccion.strftime('%d/%m/%Y')"/>
                                    </t>
                                    <t t-else="">—</t>
                                </td>
                            </tr>
                            <tr>
                                <td class="bg-header">Transportista</td>
                                <td><t t-esc="doc.transportista_nombre or '—'"/></td>
                                <td class="bg-header">No. Placa</td>
                                <td><t t-esc="doc.numero_placa or '—'"/></td>
                            </tr>
                            <tr>
                                <td class="bg-header">Operador</td>
                                <td><t t-esc="doc.operador_nombre or '—'"/></td>
                                <td class="bg-header">Revisó</td>
                                <td><t t-esc="doc.revisado_por or '—'"/></td>
                            </tr>
                        </table>

                        <!-- 2. TABLA DE DISCREPANCIAS -->
                        <div class="section-title">Detalle de Discrepancias</div>
                        <table class="disc-table">
                            <thead>
                                <tr>
                                    <th rowspan="2" style="width: 24%;">Nombre del Residuo</th>
                                    <th colspan="2" class="th-manifesto" style="width: 26%;">LO QUE DECÍA EL MANIFIESTO</th>
                                    <th colspan="2" class="th-real" style="width: 26%;">LO QUE SE RECIBIÓ</th>
                                    <th rowspan="2" style="width: 10%;">Resultado</th>
                                    <th rowspan="2" style="width: 14%;">Observación</th>
                                </tr>
                                <tr>
                                    <th class="th-manifesto">Cantidad</th>
                                    <th class="th-manifesto">Contenedor</th>
                                    <th class="th-real">Cantidad</th>
                                    <th class="th-real">Contenedor</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="doc.linea_ids" t-as="linea">
                                    <tr t-attf-class="{{ 'row-discrepancia' if linea.tiene_diferencia else 'row-ok' }}">
                                        <td class="td-left"><t t-esc="linea.nombre_residuo or ''"/></td>
                                        <td>
                                            <t t-if="linea.cantidad_manifestada">
                                                <t t-esc="int(linea.cantidad_manifestada) if linea.cantidad_manifestada == int(linea.cantidad_manifestada) else linea.cantidad_manifestada"/>
                                            </t>
                                            <t t-else="">—</t>
                                        </td>
                                        <td><t t-esc="linea.contenedor_manifestado or '—'"/></td>
                                        <td>
                                            <t t-if="linea.cantidad_real">
                                                <t t-esc="int(linea.cantidad_real) if linea.cantidad_real == int(linea.cantidad_real) else linea.cantidad_real"/>
                                            </t>
                                            <t t-else="">—</t>
                                        </td>
                                        <td><t t-esc="linea.contenedor_real or '—'"/></td>
                                        <td>
                                            <t t-if="linea.tiene_diferencia">
                                                <span class="badge-diff">
                                                    <t t-esc="dict([
                                                        ('ok','OK'),
                                                        ('cantidad','Dif. Cantidad'),
                                                        ('contenedor','Dif. Contenedor'),
                                                        ('no_manifestado','No Manifestado'),
                                                        ('faltante','Faltante'),
                                                        ('ambos','Dif. Ambos'),
                                                        ('otro','Otro')
                                                    ]).get(linea.tipo_discrepancia, linea.tipo_discrepancia or '')"/>
                                                </span>
                                            </t>
                                            <t t-else="">
                                                <span class="badge-ok">OK</span>
                                            </t>
                                        </td>
                                        <td class="td-left"><t t-esc="linea.observacion or ''"/></td>
                                    </tr>
                                </t>
                                <t t-if="not doc.linea_ids">
                                    <tr>
                                        <td colspan="7" class="text-center" style="padding: 12px; font-style: italic; color: #666;">
                                            Sin líneas de discrepancia registradas
                                        </td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>

                        <!-- 3. OBSERVACIONES Y FIRMA -->
                        <div class="row mt16">
                            <div class="col-7">
                                <div class="section-title">Observaciones Generales</div>
                                <div style="border: 1px solid #000; min-height: 80px; padding: 5px; font-size: 10px; background-color: #fff;">
                                    <t t-if="doc.observaciones_generales">
                                        <t t-esc="doc.observaciones_generales"/>
                                    </t>
                                    <span t-else="" style="color: #ccc; font-style: italic;">Sin observaciones adicionales.</span>
                                </div>
                            </div>

                            <div class="col-5">
                                <div class="section-title text-center">Autorización</div>
                                <div style="border: 1px solid #000; padding: 0;">
                                    <div style="height: 60px; border-bottom: 1px dotted #ccc;"></div>
                                    <div style="text-align: center; font-size: 9px; font-weight: bold; background-color: #f0f0f0; border-bottom: 1px solid #000; padding: 3px;">
                                        FIRMA DE CONFORMIDAD
                                    </div>
                                    <div style="height: 40px; display: flex; align-items: center; justify-content: center; font-size: 9px; color: #555; padding: 4px;">
                                        <t t-esc="doc.revisado_por or ''"/>
                                    </div>
                                    <div style="text-align: center; font-size: 9px; font-weight: bold; background-color: #f0f0f0; padding: 3px;">
                                        NOMBRE Y SELLO
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="row mt16">
                            <div class="col-12 text-center" style="font-size: 8px; color: #666;">
                                Este documento es un comprobante interno de inspección de residuos peligrosos.
                            </div>
                        </div>

                        <div class="oe_structure"/>
                    </div>
                </t>
            </t>
        </t>
    </template>

</odoo>```

## ./static/src/scss/manifiesto_ambiental.scss
```scss
// ============================================================================
// MANIFIESTO AMBIENTAL — Clean Theme v2 (Fixed Layout)
// Module: manifiesto_ambiental | Odoo 19 Enterprise
// Scope: .o_manifiesto_ambiental_form_v2
// ============================================================================

// ---------------------------------------------------------------------------
// TOKENS
// ---------------------------------------------------------------------------
$ma-navy:         #0F172A;
$ma-slate:        #334155;
$ma-slate-light:  #64748B;
$ma-slate-muted:  #94A3B8;
$ma-teal:         #0F766E;
$ma-teal-soft:    rgba(15, 118, 110, 0.08);
$ma-teal-glow:    rgba(15, 118, 110, 0.12);
$ma-amber:        #D97706;
$ma-red:          #DC2626;
$ma-green:        #059669;

$ma-surface:      #FFFFFF;
$ma-surface-alt:  #F8FAFC;
$ma-bg:           #F1F5F9;
$ma-border:       #E2E8F0;
$ma-border-soft:  #EEF2F7;
$ma-text:         #1E293B;
$ma-text-soft:    #475569;
$ma-text-muted:   #64748B;

$ma-radius-sm:    6px;
$ma-radius:       10px;
$ma-radius-lg:    16px;

$ma-shadow-sm:    0 1px 2px rgba(15, 23, 42, 0.05);
$ma-shadow:       0 6px 18px rgba(15, 23, 42, 0.06);
$ma-shadow-lg:    0 16px 40px rgba(15, 23, 42, 0.08);

$ma-transition:   all 0.18s ease;

// ============================================================================
// FORM
// ============================================================================
.o_manifiesto_ambiental_form_v2 {

  // -------------------------------------------------------------------------
  // CORE LAYOUT
  // -------------------------------------------------------------------------
  &.o_form_view {
    background: $ma-bg;
    width: 100% !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;

    .o_form_sheet_bg {
      background: transparent !important;
      width: 100% !important;
      max-width: 100% !important;
      overflow: visible !important;
    }

    .o_form_sheet {
      width: 100% !important;
      max-width: 100% !important;
      margin: 18px 0;
      background: $ma-surface;
      border: 1px solid $ma-border;
      border-radius: $ma-radius-lg;
      box-shadow: $ma-shadow;
      padding: 0 !important;
      overflow: visible;
      box-sizing: border-box;
    }
  }

  // -------------------------------------------------------------------------
  // STATUSBAR — proper wrapping, no cramming
  // -------------------------------------------------------------------------
  .o_form_statusbar {
    border-radius: $ma-radius-lg $ma-radius-lg 0 0;
    border-bottom: 1px solid $ma-border;
    width: 100% !important;
    min-height: auto !important;
    padding: 10px 16px !important;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;

    .o_statusbar_buttons {
      display: flex !important;
      flex-wrap: wrap !important;
      gap: 6px 8px !important;
      align-items: center;
      padding: 0;
      margin: 0;

      > .btn,
      > button {
        white-space: nowrap;
        font-size: 12.5px;
        padding: 7px 16px;
        border-radius: $ma-radius-sm;
        line-height: 1.4;
        flex-shrink: 0;
      }
    }

    .o_statusbar_status {
      flex-shrink: 0;
      margin-left: auto;
    }
  }

  // -------------------------------------------------------------------------
  // SMART BUTTONS
  // -------------------------------------------------------------------------
  .oe_button_box {
    padding: 10px 22px;
    border-bottom: 1px solid $ma-border-soft;
    gap: 8px;
    width: 100% !important;
    box-sizing: border-box;

    .oe_stat_button {
      border: 1px solid $ma-border;
      border-radius: $ma-radius;
      background: $ma-surface;
      min-width: 104px;
      padding: 10px 14px;
      box-shadow: $ma-shadow-sm;
      transition: $ma-transition;

      &:hover {
        border-color: $ma-teal;
        background: $ma-surface-alt;
        transform: translateY(-1px);
      }

      .o_stat_info {
        .o_stat_value {
          color: $ma-navy;
          font-weight: 800;
          font-size: 15px;
        }

        .o_stat_text {
          color: $ma-text-muted;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: .06em;
        }
      }
    }
  }

  // -------------------------------------------------------------------------
  // ALERTS
  // -------------------------------------------------------------------------
  .ma_alert_strip {
    margin: 0 !important;
    border: none !important;
    border-radius: 0 !important;
    background: #FFF7ED !important;
    color: #9A3412 !important;
    border-bottom: 1px solid #FED7AA !important;
    padding: 10px 22px !important;
    width: 100% !important;
    box-sizing: border-box;
  }

  .ma_inline_info {
    border-radius: $ma-radius;
    border: 1px solid #BFDBFE;
    background: #EFF6FF;
    color: #1D4ED8;
    padding: 10px 14px;
    margin-bottom: 16px;
    font-size: 12.5px;
    width: 100% !important;
    box-sizing: border-box;
  }

  // -------------------------------------------------------------------------
  // HERO
  // -------------------------------------------------------------------------
  .ma_hero {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
    padding: 28px 32px 24px;
    border-bottom: 1px solid $ma-border-soft;
    background:
      linear-gradient(180deg, rgba(248,250,252,0.95) 0%, rgba(255,255,255,1) 100%);
    width: 100% !important;
    box-sizing: border-box;
  }

  .ma_hero_main {
    flex: 1 1 0%;
    min-width: 0;
    overflow: hidden;
  }

  .ma_eyebrow {
    color: $ma-text-muted;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .14em;
    margin-bottom: 6px;
  }

  .ma_title {
    margin: 0 0 20px 0;

    .o_field_widget {
      font-size: 30px !important;
      font-weight: 900 !important;
      color: $ma-navy !important;
      letter-spacing: -0.03em;
      line-height: 1.1;

      input {
        font-size: 30px !important;
        font-weight: 900 !important;
        color: $ma-navy !important;
      }
    }
  }

  // =========================================================================
  // META CHIPS — segmented control bar
  // =========================================================================
  .ma_hero_meta {
    display: inline-flex;
    flex-wrap: wrap;
    border: 1px solid $ma-border;
    border-radius: $ma-radius;
    overflow: hidden;
    background: $ma-surface-alt;
    box-shadow: $ma-shadow-sm;
  }

  .ma_chip_block {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    padding: 10px 22px;
    background: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    min-height: 48px;
    min-width: 0;
    position: relative;

    // Vertical dividers between chips
    & + .ma_chip_block::before {
      content: "";
      position: absolute;
      left: 0;
      top: 20%;
      bottom: 20%;
      width: 1px;
      background: $ma-border;
    }

    .ma_chip_label {
      color: $ma-text-muted;
      font-size: 9.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .1em;
      line-height: 1;
      margin: 0;
    }

    // Value styling — override Odoo's widget sizes
    .o_field_widget {
      font-size: 13.5px !important;
      font-weight: 700 !important;
      color: $ma-navy !important;
      line-height: 1.3;
      overflow: visible !important;
    }

    .o_field_badge .badge {
      font-size: 11px;
      padding: 3px 10px;
    }

    a {
      font-size: 13px;
      font-weight: 700;
      color: $ma-teal !important;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  // =========================================================================
  // HERO SIDE KPIs
  // =========================================================================
  .ma_hero_side {
    width: 200px;
    flex: 0 0 200px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .ma_kpi {
    border: 1px solid $ma-border;
    border-radius: $ma-radius;
    background: $ma-surface-alt;
    padding: 12px 14px;
    box-shadow: $ma-shadow-sm;
  }

  .ma_kpi_label {
    display: block;
    font-size: 9.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: $ma-text-muted;
    margin-bottom: 4px;
    line-height: 1;
  }

  .ma_kpi_value {
    display: block;
    color: $ma-navy;
    font-size: 18px;
    font-weight: 800;
  }

  // -------------------------------------------------------------------------
  // TOP GROUP
  // -------------------------------------------------------------------------
  .ma_top_group {
    padding: 18px 28px 6px;
    width: 100% !important;
    box-sizing: border-box;

    > table,
    table.o_group {
      width: 100% !important;
      table-layout: fixed !important;
    }
  }

  // -------------------------------------------------------------------------
  // GLOBAL TABLE/GROUP WIDTH FIX
  // -------------------------------------------------------------------------
  .o_group {
    width: 100% !important;
    table-layout: fixed !important;

    > tbody > tr > td {
      vertical-align: top;
      padding: 0 8px;
      box-sizing: border-box;
    }

    &[col="2"] > tbody > tr > td,
    &.o_group_col_2 > tbody > tr > td {
      width: 50% !important;
    }

    &[col="4"] > tbody > tr > td,
    &.o_group_col_4 > tbody > tr > td {
      width: 25% !important;
    }
  }

  .o_inner_group {
    width: 100% !important;
    background: $ma-surface;
    border: 1px solid $ma-border-soft;
    border-radius: $ma-radius;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-sizing: border-box;
    overflow: hidden;

    > table,
    table.o_group,
    > tbody {
      width: 100% !important;
      table-layout: fixed !important;
    }

    td {
      overflow: hidden;
      text-overflow: ellipsis;
      vertical-align: middle;
      box-sizing: border-box;
    }

    .o_cell.o_wrap_label {
      width: 34% !important;
      max-width: 34% !important;
    }

    .o_cell:not(.o_wrap_label) {
      width: 66% !important;
      max-width: 66% !important;
    }
  }

  .ma_summary_grid {
    width: 100% !important;

    > tbody > tr > td {
      width: 50% !important;
    }
  }

  .o_notebook .tab-pane > .o_group:first-child .o_inner_group {
    background: $ma-surface-alt;
  }

  .o_horizontal_separator,
  .o_group > tbody > tr > td.o_group_col > div > .o_group_header {
    color: $ma-navy !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin: 2px 0 14px;
    padding: 0 0 10px;
    border-bottom: 1px solid $ma-border;
    position: relative;

    &::after {
      content: "";
      position: absolute;
      left: 0;
      bottom: -1px;
      width: 34px;
      height: 2px;
      background: $ma-teal;
      border-radius: 2px;
    }
  }

  .o_field_widget {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box;
    overflow: hidden;

    .o_input,
    input,
    select,
    textarea {
      width: 100% !important;
      max-width: 100% !important;
      box-sizing: border-box;
    }
  }

  // -------------------------------------------------------------------------
  // LABELS
  // -------------------------------------------------------------------------
  .o_form_label,
  label.o_form_label {
    color: $ma-text-soft;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.35;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  // -------------------------------------------------------------------------
  // FIELDS
  // -------------------------------------------------------------------------
  .o_field_widget .o_input {
    border: 1px solid $ma-border;
    border-radius: $ma-radius-sm;
    background: $ma-surface;
    color: $ma-text;
    padding: 7px 10px;
    font-size: 13px;
    transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;

    &:focus {
      border-color: $ma-teal;
      box-shadow: 0 0 0 3px $ma-teal-glow;
      outline: none;
    }

    &[readonly],
    &.o_readonly {
      background: $ma-surface-alt;
      border-color: $ma-border-soft;
      color: $ma-slate;
    }
  }

  textarea.o_input {
    min-height: 76px;
    border-radius: $ma-radius;
    line-height: 1.55;
  }

  .o_field_many2one {
    .o_input {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .o_external_button {
      color: $ma-slate-muted;

      &:hover {
        color: $ma-teal;
      }
    }
  }

  .o_field_badge .badge {
    border-radius: 999px;
    padding: 4px 10px;
    font-weight: 800;
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: .05em;
  }

  .o_field_widget[name="declaracion_generador"],
  .o_field_widget[name="declaracion_transportista"],
  .o_field_widget[name="declaracion_destinatario"] {
    span,
    textarea[readonly],
    .o_field_text_value {
      display: block;
      background: $ma-surface-alt;
      border: 1px solid $ma-border;
      border-left: 4px solid $ma-teal;
      border-radius: 0 $ma-radius-sm $ma-radius-sm 0;
      padding: 12px 14px;
      font-size: 12.5px;
      line-height: 1.7;
      color: $ma-slate;
      font-style: italic;
    }
  }

  // -------------------------------------------------------------------------
  // NOTEBOOK
  // -------------------------------------------------------------------------
  .o_notebook {
    margin: 0;
    border: none;
    width: 100% !important;

    > .o_notebook_headers {
      background: $ma-surface;
      border-bottom: 1px solid $ma-border;
      padding: 0 24px;
      width: 100% !important;
      box-sizing: border-box;

      .nav-tabs {
        border: none;
        gap: 4px;
        flex-wrap: wrap;

        .nav-item .nav-link {
          border: none;
          border-radius: 0;
          background: transparent;
          color: $ma-slate-light;
          font-size: 13px;
          font-weight: 700;
          padding: 14px 16px;
          position: relative;
          transition: $ma-transition;

          &:hover {
            color: $ma-text;
          }

          &::after {
            content: "";
            position: absolute;
            left: 8px;
            right: 8px;
            bottom: 0;
            height: 2px;
            background: $ma-teal;
            transform: scaleX(0);
            transition: transform .18s ease;
          }

          &.active {
            color: $ma-teal;
            font-weight: 800;

            &::after {
              transform: scaleX(1);
            }
          }
        }
      }
    }

    .tab-content {
      background: $ma-surface;
      padding: 22px 24px 20px;
      width: 100% !important;
      box-sizing: border-box;
      overflow: visible !important;

      .tab-pane {
        width: 100% !important;
        overflow: visible !important;
      }
    }
  }

  // -------------------------------------------------------------------------
  // ONE2MANY / MANY2MANY TABLES — ensure rows are visible
  // -------------------------------------------------------------------------
  .o_field_one2many,
  .o_field_many2many {
    overflow: visible !important;

    .o_list_view {
      overflow: visible !important;
      min-height: 120px;
      margin-top: 12px;
    }

    .o_list_table {
      th {
        padding-top: 12px !important;
        padding-bottom: 10px !important;
        line-height: 1.5 !important;
        vertical-align: middle !important;
      }

      td {
        padding-top: 8px !important;
        padding-bottom: 8px !important;
        line-height: 1.5 !important;
        vertical-align: middle !important;
      }
    }
  }

  // CRETIB booleans → traditional round checkboxes instead of toggles
  .o_field_widget[name="clasificacion_corrosivo"],
  .o_field_widget[name="clasificacion_reactivo"],
  .o_field_widget[name="clasificacion_explosivo"],
  .o_field_widget[name="clasificacion_toxico"],
  .o_field_widget[name="clasificacion_inflamable"],
  .o_field_widget[name="clasificacion_biologico"] {
    .o_boolean_toggle {
      .form-check {
        padding-left: 0;
        min-height: auto;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .form-check-input {
        appearance: auto !important;
        -webkit-appearance: checkbox !important;
        width: 16px !important;
        height: 16px !important;
        border-radius: 50% !important;
        border: 2px solid $ma-border !important;
        background: $ma-surface !important;
        background-image: none !important;
        margin: 0 !important;
        cursor: pointer;
        transition: $ma-transition;
        float: none !important;

        &:checked {
          background-color: $ma-teal !important;
          border-color: $ma-teal !important;
        }
      }

      .form-check-input::before,
      .form-check-input::after {
        display: none !important;
      }
    }
  }

  // -------------------------------------------------------------------------
  // PDF VIEWER
  // -------------------------------------------------------------------------
  .ma_pdf_viewer_wrap {
    width: 100% !important;
    min-height: 640px;
    border: 1px solid $ma-border;
    border-radius: $ma-radius;
    overflow: hidden;
    background: $ma-surface-alt;
    box-sizing: border-box;

    .o_field_pdf_viewer,
    .o_field_binary_file {
      min-height: 640px;
      background: $ma-surface-alt;
      width: 100% !important;
    }

    &:hover {
      border-color: $ma-teal;
    }
  }

  // -------------------------------------------------------------------------
  // CHATTER
  // -------------------------------------------------------------------------
  .o_FormRenderer_chatterContainer .o_ChatterContainer {
    border-top: 1px solid $ma-border;
    background: $ma-surface-alt;
  }

  // -------------------------------------------------------------------------
  // RESPONSIVE
  // -------------------------------------------------------------------------
  @media (max-width: 992px) {
    .ma_hero {
      flex-direction: column;
    }

    .ma_hero_side {
      width: 100%;
      flex: 1 1 auto;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
    }

    .ma_hero_meta {
      flex-direction: column;
      width: 100%;
      display: flex;

      .ma_chip_block {
        width: 100%;

        & + .ma_chip_block::before {
          top: 0;
          bottom: auto;
          left: 10%;
          right: 10%;
          width: auto;
          height: 1px;
        }
      }
    }
  }

  @media (max-width: 768px) {
    &.o_form_view .o_form_sheet {
      margin: 8px 0;
      border-radius: $ma-radius;
    }

    .ma_hero {
      padding: 18px 16px 16px;
    }

    .ma_title .o_field_widget,
    .ma_title .o_field_widget input {
      font-size: 24px !important;
    }

    .ma_top_group {
      padding: 14px 16px 4px;
    }

    .o_notebook > .o_notebook_headers {
      padding: 0 12px;
    }

    .o_notebook .tab-content {
      padding: 16px 12px;
    }

    .ma_hero_side {
      grid-template-columns: 1fr;
    }
  }

  // -------------------------------------------------------------------------
  // PRINT
  // -------------------------------------------------------------------------
  @media print {
    .o_form_statusbar,
    .oe_button_box,
    .o_FormRenderer_chatterContainer {
      display: none !important;
    }

    &.o_form_view {
      width: 100% !important;
      background: white !important;

      .o_form_sheet_bg,
      .o_form_sheet {
        width: 100% !important;
        max-width: 100% !important;
        box-shadow: none;
        border: none;
        margin: 0;
        border-radius: 0;
      }
    }

    .ma_hero {
      page-break-inside: avoid;
    }

    .o_notebook .tab-content {
      width: 100% !important;
    }

    .o_group,
    .o_inner_group,
    .o_inner_group > table,
    .o_field_one2many .o_list_view,
    .o_field_one2many .o_list_view table {
      width: 100% !important;
    }

    .o_inner_group,
    .ma_kpi {
      page-break-inside: avoid;
    }
  }
}```

## ./views/manifiesto_ambiental_assets.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- Register SCSS asset for web backend -->
    <record id="manifiesto_ambiental_scss_asset" model="ir.asset">
        <field name="name">Manifiesto Ambiental SCSS</field>
        <field name="bundle">web.assets_backend</field>
        <field name="path">manifiesto_ambiental/static/src/scss/manifiesto_ambiental.scss</field>
    </record>
</odoo>```

## ./views/manifiesto_ambiental_menus.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>

    <menuitem id="menu_manifiesto_ambiental_root"
              name="Manifiestos"
              sequence="50"
              web_icon="manifiesto_ambiental,static/description/icon.png"/>

    <menuitem id="menu_manifiesto_ambiental_manifiestos"
              name="Manifiestos Actuales"
              parent="menu_manifiesto_ambiental_root"
              action="action_manifiesto_ambiental"
              sequence="10"/>

    <menuitem id="menu_manifiesto_ambiental_versions"
              name="Historial de Versiones"
              parent="menu_manifiesto_ambiental_root"
              action="action_manifiesto_ambiental_version"
              sequence="20"/>

    <menuitem id="menu_manifiesto_ambiental_all_versions"
              name="Todas las Versiones"
              parent="menu_manifiesto_ambiental_root"
              action="action_manifiesto_ambiental_all_versions"
              sequence="30"/>

    <menuitem id="menu_manifiesto_ambiental_config"
              name="Configuración"
              parent="menu_manifiesto_ambiental_root"
              sequence="90"/>

    <!-- 🔥 CORREGIDO -->
    <menuitem id="menu_manifiesto_discrepancia"
              name="Discrepancias"
              parent="menu_manifiesto_ambiental_root"
              action="gestion_discrepancias.action_discrepancy_log"
              sequence="40"/>

</odoo>```

## ./views/manifiesto_ambiental_views.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>

    <!-- ================================================================== -->
    <!-- ACCIONES -->
    <!-- ================================================================== -->

    <record id="action_manifiesto_ambiental" model="ir.actions.act_window">
        <field name="name">Manifiestos Ambientales</field>
        <field name="res_model">manifiesto.ambiental</field>
        <field name="view_mode">list,form</field>
        <field name="domain">[('is_current_version', '=', True)]</field>
        <field name="context">{'search_default_current_versions': 1}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">Crear su primer Manifiesto Ambiental</p>
            <p>Documentos oficiales para el control y trazabilidad de residuos peligrosos.</p>
        </field>
    </record>

    <record id="action_manifiesto_ambiental_version" model="ir.actions.act_window">
        <field name="name">Historial de Versiones</field>
        <field name="res_model">manifiesto.ambiental.version</field>
        <field name="view_mode">list,form</field>
    </record>

    <record id="action_manifiesto_ambiental_all_versions" model="ir.actions.act_window">
        <field name="name">Todas las Versiones de Manifiestos</field>
        <field name="res_model">manifiesto.ambiental</field>
        <field name="view_mode">list,form</field>
        <field name="domain">[]</field>
    </record>

    <!-- ================================================================== -->
    <!-- LISTA PRINCIPAL -->
    <!-- ================================================================== -->

    <record id="view_manifiesto_ambiental_list" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.list</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="type">list</field>
        <field name="arch" type="xml">
            <list string="Manifiestos Ambientales"
                  default_order="sequence_number desc, version desc"
                  decoration-muted="not is_current_version"
                  decoration-bf="is_current_version">

                <field name="sequence_number" string="Sec." optional="show" width="60px"/>
                <field name="tipo_manifiesto" string="Tipo" widget="badge"
                       decoration-info="tipo_manifiesto == 'entrada'"
                       decoration-success="tipo_manifiesto == 'salida'"/>
                <field name="numero_manifiesto_display" string="Nº Manifiesto"/>
                <field name="numero_registro_ambiental" string="Reg. Ambiental" optional="show"/>

                <field name="generador_nombre" string="Generador"/>
                <field name="transportista_nombre" string="Transportista" optional="show"/>
                <field name="destinatario_nombre" string="Destinatario" optional="show"/>

                <field name="generador_fecha" string="Fecha"/>
                <field name="version" string="Ver." width="50px"/>
                <field name="is_current_version" string="Actual" widget="boolean_toggle" width="60px"/>
                <field name="tiene_documento_fisico" string="Doc." widget="boolean_toggle"
                       optional="show" width="50px"/>

                <field name="state" widget="badge"
                       decoration-success="state == 'delivered'"
                       decoration-info="state == 'confirmed'"
                       decoration-warning="state == 'in_transit'"
                       decoration-muted="state == 'cancelled'"/>
            </list>
        </field>
    </record>

    <!-- ================================================================== -->
    <!-- FORMULARIO PRINCIPAL V2 -->
    <!-- ================================================================== -->

    <record id="view_manifiesto_ambiental_form" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.form.v2</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="type">form</field>
        <field name="arch" type="xml">
            <form string="Manifiesto Ambiental" class="o_manifiesto_ambiental_form_v2">

                <header>
                    <!-- Acciones primarias -->
                    <button name="action_confirm" string="Confirmar" type="object"
                            class="btn-primary"
                            invisible="state != 'draft'"/>

                    <button name="action_in_transit" string="Marcar En Tránsito" type="object"
                            class="btn-primary"
                            invisible="state != 'confirmed'"/>

                    <button name="action_delivered" string="Marcar Entregado" type="object"
                            class="btn-primary"
                            invisible="state != 'in_transit'"/>

                    <!-- Operativas -->
                    <button name="action_recibir_residuos" string="Recibir Residuos" type="object"
                            class="btn-success" icon="fa-download"
                            invisible="state not in ['in_transit', 'delivered'] or not is_current_version or tipo_manifiesto == 'salida'"
                            confirm="¿Desea generar la recepción de inventario para estos residuos?"/>

                    <button name="action_print_manifiesto" string="Imprimir PDF" type="object"
                            class="btn-secondary" icon="fa-print"/>

                    <!-- Secundarias -->
                    <button name="action_crear_discrepancia" string="Reportar Discrepancia" type="object"
                            class="btn-warning" icon="fa-exclamation-triangle"
                            invisible="state not in ['in_transit', 'delivered'] or not is_current_version or tipo_manifiesto == 'salida'"/>

                    <button name="action_remanifestar" string="Remanifestar (PDF)" type="object"
                            class="btn-secondary" icon="fa-refresh"
                            invisible="not is_current_version or state == 'draft'"
                            confirm="Se creará una nueva versión y se guardará un PDF de la actual. ¿Continuar?"/>

                    <button name="action_remanifestar_sin_pdf" string="Remanifestar (Datos)" type="object"
                            class="btn-secondary"
                            invisible="not is_current_version or state == 'draft'"
                            confirm="Se creará una nueva versión sin respaldo PDF. ¿Continuar?"/>

                    <button name="action_cancel" string="Cancelar" type="object"
                            class="btn-danger"
                            invisible="state not in ['draft','confirmed','in_transit']"
                            confirm="¿Está seguro de cancelar este manifiesto?"/>

                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,confirmed,in_transit,delivered"/>
                </header>

                <sheet>

                    <!-- Smart buttons -->
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_version_history" type="object"
                                class="oe_stat_button" icon="fa-history">
                            <field name="version" widget="statinfo" string="Versión"/>
                        </button>

                        <button name="action_view_discrepancias" type="object"
                                class="oe_stat_button" icon="fa-exclamation-triangle"
                                invisible="discrepancia_count == 0">
                            <field name="discrepancia_count" widget="statinfo" string="Discrepancias"/>
                        </button>

                        <button name="action_view_recepciones" type="object"
                                class="oe_stat_button" icon="fa-truck"
                                invisible="recepcion_count == 0">
                            <field name="recepcion_count" widget="statinfo" string="Recepciones"/>
                        </button>

                        <button type="object" name="action_view_version_history"
                                class="oe_stat_button" icon="fa-file-pdf-o">
                            <div class="o_field_widget o_stat_info">
                                <span class="o_stat_value" invisible="not tiene_documento_fisico">Sí</span>
                                <span class="o_stat_value" invisible="tiene_documento_fisico">No</span>
                                <span class="o_stat_text">Doc. físico</span>
                            </div>
                        </button>
                    </div>

                    <!-- Aviso versión histórica -->
                    <div class="alert alert-warning ma_alert_strip" invisible="is_current_version">
                        <strong>Versión histórica.</strong>
                        Este registro no es la versión actual del manifiesto.
                        <button name="action_view_current_version" type="object"
                                class="btn btn-sm btn-warning ms-2">
                            Ir a versión actual
                        </button>
                    </div>

                    <!-- HERO -->
                    <div class="ma_hero">
                        <div class="ma_hero_main">
                            <div class="ma_eyebrow">Número de manifiesto</div>
                            <h1 class="ma_title">
                                <field name="numero_manifiesto"
                                       readonly="not is_current_version"
                                       placeholder="Ej: MA-2026-001"/>
                            </h1>

                            <div class="ma_hero_meta">
                                <div class="ma_chip_block">
                                    <span class="ma_chip_label">Tipo</span>
                                    <field name="tipo_manifiesto" readonly="1" widget="badge"/>
                                </div>

                                <div class="ma_chip_block">
                                    <span class="ma_chip_label">Fecha</span>
                                    <field name="generador_fecha" readonly="not is_current_version"/>
                                </div>

                                <div class="ma_chip_block" invisible="not service_order_id">
                                    <span class="ma_chip_label">Orden de servicio</span>
                                    <field name="service_order_id" readonly="1"/>
                                </div>
                            </div>
                        </div>

                        <div class="ma_hero_side">
                            <div class="ma_kpi">
                                <span class="ma_kpi_label">Versión</span>
                                <span class="ma_kpi_value">
                                    <field name="version" readonly="1"/>
                                </span>
                            </div>

                            <div class="ma_kpi">
                                <span class="ma_kpi_label">Documento físico</span>
                                <span class="ma_kpi_value">
                                    <span invisible="not tiene_documento_fisico">Sí</span>
                                    <span invisible="tiene_documento_fisico">No</span>
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Metadata compacta -->
                    <group class="ma_top_group" col="4">
                        <field name="numero_registro_ambiental" readonly="not is_current_version"/>
                        <field name="pagina" readonly="not is_current_version"/>
                        <field name="company_id" groups="base.group_multi_company"/>
                        <field name="service_order_id" invisible="1"/>
                    </group>

                    <notebook>

                        <!-- ====================================================== -->
                        <!-- RESUMEN -->
                        <!-- ====================================================== -->
                        <page string="Resumen" name="resumen">
                            <group col="2" class="ma_summary_grid">
                                <group string="Generador">
                                    <field name="generador_id"
                                           string="Empresa"
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                    <field name="generador_nombre" string="Razón Social"
                                           readonly="not is_current_version"/>
                                    <field name="generador_estado" readonly="not is_current_version"/>
                                    <field name="generador_municipio" readonly="not is_current_version"/>
                                </group>

                                <group string="Destino">
                                    <field name="destinatario_id"
                                           string="Empresa"
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_nombre" string="Razón Social"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_estado" readonly="not is_current_version"/>
                                    <field name="destinatario_municipio" readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group col="2">
                                <group string="Control">
                                    <field name="state" readonly="1"/>
                                    <field name="is_current_version" readonly="1"/>
                                    <field name="created_by_remanifest" readonly="1"/>
                                </group>

                                <group string="Referencia">
                                    <field name="original_manifiesto_id" readonly="1"
                                           invisible="not original_manifiesto_id"/>
                                    <field name="sequence_number" readonly="1"/>
                                </group>
                            </group>
                        </page>

                        <!-- ====================================================== -->
                        <!-- GENERADOR -->
                        <!-- ====================================================== -->
                        <page string="Generador" name="generador">
                            <group col="2">
                                <group string="Empresa">
                                    <field name="generador_id"
                                           string="Empresa Generadora"
                                           placeholder="Seleccione generador..."
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                </group>
                                <group string="Firma">
                                    <field name="generador_responsable_id"
                                           string="Responsable"
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                    <field name="generador_responsable_nombre"
                                           string="Nombre en documento"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Dirección" col="2">
                                <group>
                                    <field name="generador_nombre" string="Razón Social"
                                           readonly="not is_current_version"/>
                                    <field name="generador_calle" readonly="not is_current_version"/>
                                    <field name="generador_num_ext" string="Núm. Exterior"
                                           readonly="not is_current_version"/>
                                    <field name="generador_num_int" string="Núm. Interior"
                                           readonly="not is_current_version"/>
                                    <field name="generador_colonia" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="generador_municipio" readonly="not is_current_version"/>
                                    <field name="generador_estado" readonly="not is_current_version"/>
                                    <field name="generador_codigo_postal" string="C.P."
                                           readonly="not is_current_version"/>
                                    <field name="generador_telefono" readonly="not is_current_version"/>
                                    <field name="generador_email" readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Validación" col="2">
                                <group>
                                    <field name="generador_fecha" string="Fecha del documento"
                                           readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="generador_sello" readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Declaración del Generador (Sección 7)" col="1">
                                <field name="declaracion_generador" nolabel="1" readonly="1"/>
                            </group>
                        </page>

                        <!-- ====================================================== -->
                        <!-- RESIDUOS -->
                        <!-- ====================================================== -->
                        <page string="Residuos" name="residuos">
                            

                            <field name="residuo_ids" readonly="not is_current_version">
                                <list editable="bottom">
                                    <field name="product_id"
                                           placeholder="Seleccionar residuo..."
                                           options="{'no_create': True, 'no_create_edit': True}"/>
                                    <field name="nombre_residuo" string="Descripción"/>
                                    <field name="residue_type" string="Tipo" optional="show"/>
                                    <field name="clasificacion_corrosivo" string="C" width="35px"/>
                                    <field name="clasificacion_reactivo" string="R" width="35px"/>
                                    <field name="clasificacion_explosivo" string="E" width="35px"/>
                                    <field name="clasificacion_toxico" string="T" width="35px"/>
                                    <field name="clasificacion_inflamable" string="I" width="35px"/>
                                    <field name="clasificacion_biologico" string="B" width="35px"/>
                                    <field name="packaging_id" string="Embalaje" optional="show"/>
                                    <field name="envase_capacidad" string="Capacidad"/>
                                    <field name="cantidad"/>
                                    <field name="unidad" readonly="1"/>
                                    <field name="etiqueta_si" string="Etiq. Sí" optional="show"/>
                                    <field name="etiqueta_no" string="Etiq. No" optional="show"/>
                                    <field name="lot_id" readonly="1" optional="show"/>
                                    <field name="clasificaciones_display" string="CRETIB" optional="hide"/>
                                    <field name="envase_tipo" string="Envase (Legacy)" optional="hide"/>
                                </list>

                                <form string="Detalle del Residuo">
                                    <sheet>
                                        <group col="2">
                                            <group string="Identificación">
                                                <field name="product_id"
                                                       options="{'no_create': True, 'no_create_edit': True}"/>
                                                <field name="nombre_residuo"/>
                                                <field name="residue_type"/>
                                                <field name="lot_id" readonly="1"/>
                                            </group>
                                            <group string="Cantidad y Envase">
                                                <field name="packaging_id" string="Embalaje"/>
                                                <field name="envase_tipo" string="Envase (Legacy)"/>
                                                <field name="envase_capacidad"/>
                                                <field name="cantidad"/>
                                                <field name="unidad" readonly="1"/>
                                                <field name="etiqueta_si"/>
                                                <field name="etiqueta_no"/>
                                            </group>
                                        </group>

                                        <group string="Clasificación CRETIB" col="6">
                                            <field name="clasificacion_corrosivo"/>
                                            <field name="clasificacion_reactivo"/>
                                            <field name="clasificacion_explosivo"/>
                                            <field name="clasificacion_toxico"/>
                                            <field name="clasificacion_inflamable"/>
                                            <field name="clasificacion_biologico"/>
                                        </group>
                                    </sheet>
                                </form>
                            </field>

                            <group string="Instrucciones Especiales de Manejo (Sección 6)" col="1">
                                <field name="instrucciones_especiales"
                                       nolabel="1"
                                       placeholder="Instrucciones especiales para el manejo seguro de los residuos listados..."
                                       readonly="not is_current_version"/>
                            </group>
                        </page>

                        <!-- ====================================================== -->
                        <!-- TRANSPORTISTA -->
                        <!-- ====================================================== -->
                        <page string="Transportista" name="transportista">
                            <group col="2">
                                <group string="Empresa">
                                    <field name="transportista_id"
                                           string="Empresa Transportista"
                                           placeholder="Seleccione transportista..."
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                </group>
                                <group string="Operación">
                                    <field name="chofer_id" string="Chofer"
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                    <field name="vehicle_id" string="Vehículo"
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Dirección (Sección 8)" col="2">
                                <group>
                                    <field name="transportista_nombre" string="Razón Social"
                                           readonly="not is_current_version"/>
                                    <field name="transportista_calle" readonly="not is_current_version"/>
                                    <field name="transportista_num_ext" string="Núm. Exterior"
                                           readonly="not is_current_version"/>
                                    <field name="transportista_num_int" string="Núm. Interior"
                                           readonly="not is_current_version"/>
                                    <field name="transportista_colonia" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="transportista_municipio" readonly="not is_current_version"/>
                                    <field name="transportista_estado" readonly="not is_current_version"/>
                                    <field name="transportista_codigo_postal" string="C.P."
                                           readonly="not is_current_version"/>
                                    <field name="transportista_telefono" readonly="not is_current_version"/>
                                    <field name="transportista_email" readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Autorizaciones y Vehículo (Secciones 9-12)" col="2">
                                <group>
                                    <field name="numero_autorizacion_semarnat"
                                           string="Aut. SEMARNAT"
                                           readonly="not is_current_version"/>
                                    <field name="numero_permiso_sct"
                                           string="Permiso SCT"
                                           readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="tipo_vehiculo" string="Tipo de Vehículo"
                                           readonly="not is_current_version"/>
                                    <field name="numero_placa" string="Placas"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Ruta de Transporte (Sección 13)" col="1">
                                <field name="ruta_empresa" nolabel="1"
                                       placeholder="Descripción de la ruta desde la empresa generadora hasta el punto de entrega..."
                                       readonly="not is_current_version"/>
                            </group>

                            <group string="Firma y Responsable" col="2">
                                <group>
                                    <field name="transportista_responsable_id"
                                           string="Responsable"
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                    <field name="transportista_responsable_nombre"
                                           string="Nombre en documento"
                                           readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="transportista_fecha" string="Fecha de firma"
                                           readonly="not is_current_version"/>
                                    <field name="transportista_sello"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Declaración del Transportista (Sección 14)" col="1">
                                <field name="declaracion_transportista" nolabel="1" readonly="1"/>
                            </group>
                        </page>

                        <!-- ====================================================== -->
                        <!-- DESTINATARIO -->
                        <!-- ====================================================== -->
                        <page string="Destinatario" name="destinatario">
                            <group col="2">
                                <group string="Empresa">
                                    <field name="destinatario_id"
                                           string="Empresa Destinataria"
                                           placeholder="Seleccione destinatario..."
                                           options="{'no_create': True, 'no_create_edit': True}"
                                           readonly="not is_current_version"/>
                                </group>
                                <group string="Recepción">
                                    <field name="nombre_persona_recibe"
                                           string="Persona que Recibe"
                                           readonly="not is_current_version"/>
                                    <field name="numero_autorizacion_semarnat_destinatario"
                                           string="Aut. SEMARNAT"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Dirección (Sección 15)" col="2">
                                <group>
                                    <field name="destinatario_nombre" string="Razón Social"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_calle" readonly="not is_current_version"/>
                                    <field name="destinatario_num_ext" string="Núm. Exterior"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_num_int" string="Núm. Interior"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_colonia" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="destinatario_municipio" readonly="not is_current_version"/>
                                    <field name="destinatario_estado" readonly="not is_current_version"/>
                                    <field name="destinatario_codigo_postal" string="C.P."
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_telefono" readonly="not is_current_version"/>
                                    <field name="destinatario_email" readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Recepción y Observaciones (Secciones 16-18)" col="2">
                                <group>
                                    <field name="destinatario_responsable_nombre"
                                           string="Nombre del Responsable"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_fecha" string="Fecha de firma"
                                           readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="observaciones_destinatario"
                                           string="Observaciones"
                                           readonly="not is_current_version"/>
                                    <field name="destinatario_sello"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="Declaración del Destinatario (Sección 19)" col="1">
                                <field name="declaracion_destinatario" nolabel="1" readonly="1"/>
                            </group>
                        </page>

                        <!-- ====================================================== -->
                        <!-- DOCUMENTO FÍSICO -->
                        <!-- ====================================================== -->
                        <page string="Documento Físico" name="documento_fisico">
                            <group col="2">
                                <group string="Archivo">
                                    <field name="documento_fisico_filename"
                                           readonly="not is_current_version"/>
                                    <field name="tiene_documento_fisico" readonly="1"
                                           widget="boolean_toggle"/>
                                </group>
                                <group/>
                            </group>

                            <group string="Vista previa" col="1">
                                <div class="ma_pdf_viewer_wrap">
                                    <field name="documento_fisico"
                                           filename="documento_fisico_filename"
                                           readonly="not is_current_version"
                                           widget="pdf_viewer"
                                           options="{'accepted_file_extensions': '.pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff'}"/>
                                </div>
                            </group>
                        </page>

                        <!-- ====================================================== -->
                        <!-- VERSIONES -->
                        <!-- ====================================================== -->
                        <page string="Versiones" name="versiones" invisible="version &lt;= 1">
                            <group col="2">
                                <group string="Versión actual">
                                    <field name="version" readonly="1" string="Nº de Versión"/>
                                    <field name="is_current_version" readonly="1"/>
                                </group>
                                <group string="Origen">
                                    <field name="original_manifiesto_id" readonly="1"
                                           string="Manifiesto Original"/>
                                    <field name="created_by_remanifest" readonly="1"/>
                                </group>
                            </group>

                            <group string="Motivo de la remanifestación" col="1"
                                   invisible="not created_by_remanifest">
                                <field name="change_reason" nolabel="1"
                                       placeholder="Describa el motivo de esta remanifestación..."
                                       readonly="not is_current_version"/>
                            </group>

                          

                            <div class="mt-3">
                                <button name="action_view_all_versions" type="object"
                                        string="Ver Todas las Versiones en Lista Completa"
                                        class="btn btn-outline-secondary btn-sm"
                                        icon="fa-list"/>
                            </div>
                        </page>

                    </notebook>

                    <!-- invisibles técnicos -->
                    <field name="is_current_version" invisible="1"/>
                    <field name="original_manifiesto_id" invisible="1"/>
                    <field name="created_by_remanifest" invisible="1"/>
                    <field name="tiene_documento_fisico" invisible="1"/>
                    <field name="sequence_number" invisible="1"/>
                    <field name="tipo_manifiesto" invisible="1"/>
                    <field name="service_order_id" invisible="1"/>

                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- ================================================================== -->
    <!-- BÚSQUEDA -->
    <!-- ================================================================== -->

    <record id="view_manifiesto_ambiental_search" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.search</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="arch" type="xml">
            <search string="Buscar Manifiestos">
                <field name="numero_manifiesto" string="Nº Manifiesto"/>
                <field name="numero_registro_ambiental"/>
                <field name="generador_nombre" string="Generador"/>
                <field name="transportista_nombre" string="Transportista"/>
                <field name="destinatario_nombre" string="Destinatario"/>
                <field name="sequence_number" string="Secuencia"/>
                <separator/>
                <filter string="Entradas" name="tipo_entrada"
                        domain="[('tipo_manifiesto','=','entrada')]"
                        icon="fa-sign-in"/>
                <filter string="Salidas" name="tipo_salida"
                        domain="[('tipo_manifiesto','=','salida')]"
                        icon="fa-sign-out"/>
                <separator/>
                <filter string="Versión Actual" name="current_versions"
                        domain="[('is_current_version','=',True)]"/>
                <filter string="Históricas" name="historical_versions"
                        domain="[('is_current_version','=',False)]"/>
                <filter string="Remanifestados" name="remanifested"
                        domain="[('version','>',1)]"/>
                <separator/>
                <filter string="Con Doc. Físico" name="with_physical_doc"
                        domain="[('tiene_documento_fisico','=',True)]"/>
                <filter string="Sin Doc. Físico" name="without_physical_doc"
                        domain="[('tiene_documento_fisico','=',False)]"/>
                <separator/>
                <filter string="Borrador" name="draft" domain="[('state','=','draft')]"/>
                <filter string="Confirmado" name="confirmed" domain="[('state','=','confirmed')]"/>
                <filter string="En Tránsito" name="in_transit" domain="[('state','=','in_transit')]"/>
                <filter string="Entregado" name="delivered" domain="[('state','=','delivered')]"/>
                <separator/>
                <filter string="Tipo" name="group_tipo" context="{'group_by':'tipo_manifiesto'}"/>
                <filter string="Estado" name="group_state" context="{'group_by':'state'}"/>
                <filter string="Generador" name="group_generator" context="{'group_by':'generador_nombre'}"/>
                <filter string="Fecha" name="group_date" context="{'group_by':'generador_fecha:month'}"/>
            </search>
        </field>
    </record>

    <!-- ================================================================== -->
    <!-- VISTAS DE VERSIONES -->
    <!-- ================================================================== -->

    <record id="view_manifiesto_ambiental_version_list" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.version.list</field>
        <field name="model">manifiesto.ambiental.version</field>
        <field name="arch" type="xml">
            <list string="Historial de Versiones" default_order="creation_date desc">
                <field name="manifiesto_id"/>
                <field name="version_number" string="Ver."/>
                <field name="creation_date"/>
                <field name="created_by"/>
                <field name="state_at_creation" string="Estado"/>
                <field name="tenia_documento_fisico" string="Doc." widget="boolean_toggle"/>
                <field name="generador_nombre" optional="show"/>
                <field name="transportista_nombre" optional="show"/>
                <field name="destinatario_nombre" optional="show"/>
                <field name="total_residuos" optional="show"/>
                <field name="change_reason" string="Motivo"/>
                <button name="action_download_file" type="object"
                        string="Descargar" class="btn-link" icon="fa-download"/>
                <button name="action_view_file" type="object"
                        string="Ver" class="btn-link" icon="fa-eye"/>
                <button name="action_download_documento_fisico" type="object"
                        string="Doc. Físico" class="btn-link" icon="fa-paperclip"
                        invisible="not tenia_documento_fisico"/>
            </list>
        </field>
    </record>

    <record id="view_manifiesto_ambiental_version_form" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.version.form</field>
        <field name="model">manifiesto.ambiental.version</field>
        <field name="arch" type="xml">
            <form string="Versión del Manifiesto" create="false" edit="false">
                <header>
                    <button name="action_download_file" string="Descargar PDF"
                            type="object" class="btn-primary" icon="fa-download"/>
                    <button name="action_view_file" string="Ver PDF"
                            type="object" class="btn-secondary" icon="fa-eye"/>
                    <button name="action_download_documento_fisico" string="Descargar Doc. Físico"
                            type="object" class="btn-success" icon="fa-paperclip"
                            invisible="not tenia_documento_fisico"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="display_name"/></h1>
                    </div>
                    <group col="2">
                        <group string="Información de la Versión">
                            <field name="manifiesto_id"/>
                            <field name="version_number"/>
                            <field name="creation_date"/>
                            <field name="created_by"/>
                            <field name="state_at_creation"/>
                        </group>
                        <group string="Archivos">
                            <field name="tenia_documento_fisico"/>
                            <field name="pdf_filename"/>
                            <field name="pdf_file" filename="pdf_filename"/>
                            <field name="documento_fisico_filename_original"
                                   invisible="not tenia_documento_fisico"/>
                            <field name="documento_fisico_original"
                                   filename="documento_fisico_filename_original"
                                   invisible="not tenia_documento_fisico"/>
                        </group>
                    </group>
                    <group string="Motivo del Cambio" col="1" invisible="not change_reason">
                        <field name="change_reason" nolabel="1"/>
                    </group>
                    <group string="Referencia Rápida" col="4">
                        <field name="generador_nombre"/>
                        <field name="transportista_nombre"/>
                        <field name="destinatario_nombre"/>
                        <field name="total_residuos"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="view_manifiesto_ambiental_version_search" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.version.search</field>
        <field name="model">manifiesto.ambiental.version</field>
        <field name="arch" type="xml">
            <search string="Buscar Versiones">
                <field name="manifiesto_id"/>
                <field name="created_by"/>
                <field name="change_reason"/>
                <field name="generador_nombre"/>
                <separator/>
                <filter string="Con Doc. Físico" name="with_physical_doc"
                        domain="[('tenia_documento_fisico','=',True)]"/>
                <filter string="Sin Doc. Físico" name="without_physical_doc"
                        domain="[('tenia_documento_fisico','=',False)]"/>
                <separator/>
                <filter string="Manifiesto" name="group_manifiesto"
                        context="{'group_by':'manifiesto_id'}"/>
                <filter string="Creado por" name="group_user"
                        context="{'group_by':'created_by'}"/>
                <filter string="Fecha" name="group_date"
                        context="{'group_by':'creation_date:month'}"/>
                <filter string="Estado" name="group_state"
                        context="{'group_by':'state_at_creation'}"/>
            </search>
        </field>
    </record>

</odoo>```

## ./views/product_views.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- Extensión del formulario de productos para residuos peligrosos -->
    <record id="view_product_template_form_residuo_peligroso" model="ir.ui.view">
        <field name="name">product.template.form.residuo.peligroso</field>
        <field name="model">product.template</field>
        <field name="inherit_id" ref="product.product_template_form_view"/>
        <field name="arch" type="xml">
            <notebook position="inside">
                <page string="Residuo Peligroso" name="residuo_peligroso">
                    <group string="Configuración de Residuo Peligroso" col="2">
                        <field name="es_residuo_peligroso"/>
                        <div invisible="not es_residuo_peligroso" 
                             style="color: #28a745; font-weight: bold;">
                            ℹ️ Este producto está configurado como residuo peligroso.
                            Se activará automáticamente el seguimiento por lotes.
                        </div>
                    </group>
                    
                    <group string="Clasificación CRETIB" 
                           invisible="not es_residuo_peligroso" 
                           col="3">
                        <field name="clasificacion_corrosivo"/>
                        <field name="clasificacion_reactivo"/>
                        <field name="clasificacion_explosivo"/>
                        <field name="clasificacion_toxico"/>
                        <field name="clasificacion_inflamable"/>
                        <field name="clasificacion_biologico"/>
                    </group>
                    
                    <group string="Información del Envase" 
                           invisible="not es_residuo_peligroso" 
                           col="2">
                        <field name="envase_tipo_default"/>
                        <field name="envase_capacidad_default"/>
                    </group>
                    
                    <div invisible="not es_residuo_peligroso" 
                         class="alert alert-info" 
                         style="margin: 10px;">
                        <strong>Nota importante:</strong>
                        <ul>
                            <li>La unidad de medida para residuos peligrosos siempre será en kilogramos (kg)</li>
                            <li>Se activará automáticamente el seguimiento por lotes</li>
                            <li>Los lotes se generarán automáticamente con el número de manifiesto</li>
                        </ul>
                    </div>
                </page>
            </notebook>
        </field>
    </record>

    <!-- Acción para productos de residuos peligrosos -->
    <record id="action_product_residuo_peligroso" model="ir.actions.act_window">
        <field name="name">Productos - Residuos Peligrosos</field>
        <field name="res_model">product.template</field>
        <field name="view_mode">list,form</field>
        <field name="domain">[('es_residuo_peligroso', '=', True)]</field>
        <field name="context">{'default_es_residuo_peligroso': True, 'default_type': 'product'}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Crear su primer Producto de Residuo Peligroso
            </p>
            <p>
                Los productos de residuos peligrosos son utilizados en los manifiestos ambientales.
                Estos productos tienen seguimiento por lotes automático y clasificación CRETIB.
            </p>
        </field>
    </record>

    <!-- Vista de lista para productos de residuos peligrosos -->
    <record id="view_product_template_residuo_peligroso_list" model="ir.ui.view">
        <field name="name">product.template.residuo.peligroso.list</field>
        <field name="model">product.template</field>
        <field name="arch" type="xml">
            <list string="Productos - Residuos Peligrosos">
                <field name="name"/>
                <field name="clasificacion_corrosivo" string="C"/>
                <field name="clasificacion_reactivo" string="R"/>
                <field name="clasificacion_explosivo" string="E"/>
                <field name="clasificacion_toxico" string="T"/>
                <field name="clasificacion_inflamable" string="I"/>
                <field name="clasificacion_biologico" string="B"/>
                <field name="envase_tipo_default"/>
                <field name="envase_capacidad_default"/>
                <field name="type"/>
            </list>
        </field>
    </record>
</odoo>```

## ./views/recepcion_extension_views.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="view_residuo_recepcion_form_manifiesto" model="ir.ui.view">
        <field name="name">residuo.recepcion.form.manifiesto</field>
        <field name="model">residuo.recepcion</field>
        <field name="inherit_id" ref="residuo_recepcion_sai.view_residuo_recepcion_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='sale_order_id']" position="after">
                <field name="manifiesto_id" readonly="1" invisible="not manifiesto_id"/>
            </xpath>
        </field>
    </record>

    <record id="view_residuo_recepcion_list_manifiesto" model="ir.ui.view">
        <field name="name">residuo.recepcion.list.manifiesto</field>
        <field name="model">residuo.recepcion</field>
        <field name="inherit_id" ref="residuo_recepcion_sai.view_residuo_recepcion_list"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='sale_order_id']" position="after">
                <field name="manifiesto_id" optional="show"/>
            </xpath>
        </field>
    </record>

    <record id="view_residuo_recepcion_search_manifiesto" model="ir.ui.view">
        <field name="name">residuo.recepcion.search.manifiesto</field>
        <field name="model">residuo.recepcion</field>
        <field name="inherit_id" ref="residuo_recepcion_sai.view_residuo_recepcion_search"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='sale_order_id']" position="after">
                <field name="manifiesto_id"/>
            </xpath>
        </field>
    </record>
</odoo>```

## ./views/res_partner_views.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- 1. MEJORA EN DIRECCIÓN: Números en la misma línea que la calle -->
    <record id="view_partner_form_address_numbers" model="ir.ui.view">
        <field name="name">res.partner.form.address.numbers</field>
        <field name="model">res.partner</field>
        <field name="inherit_id" ref="base.view_partner_form"/>
        <field name="arch" type="xml">
            <!-- Insertamos un div con clase o_row después de la calle (street) -->
            <xpath expr="//field[@name='street']" position="after">
                <div class="o_row" style="margin-top: 4px;">
                    <div class="o_col">
                        <label for="street_number" string="No. Ext." class="oe_edit_only" style="font-weight: bold; font-size: 0.9em; margin-right: 5px;"/>
                        <field name="street_number" placeholder="123" style="width: 40%;"/>
                    </div>
                    <div class="o_col" style="margin-left: 10px;">
                        <label for="street_number2" string="No. Int." class="oe_edit_only" style="font-weight: bold; font-size: 0.9em; margin-right: 5px;"/>
                        <field name="street_number2" placeholder="4B" style="width: 40%;"/>
                    </div>
                </div>
            </xpath>
        </field>
    </record>

    <!-- 2. MEJORA EN DATOS AMBIENTALES: Mejor estructura y estilo -->
    <record id="view_partner_form_manifiesto_fields" model="ir.ui.view">
        <field name="name">res.partner.form.manifiesto.fields</field>
        <field name="model">res.partner</field>
        <field name="inherit_id" ref="base.view_partner_form"/>
        <field name="arch" type="xml">
            <notebook position="inside">
                <page string="Datos Ambientales" name="environmental_data" icon="fa-leaf">
                    
                    <!-- Encabezado con Clasificación (Toggles) -->
                    <group>
                        <group string="Tipo de Actor Ambiental">
                            <field name="es_generador" widget="boolean_toggle"/>
                            <field name="es_transportista" widget="boolean_toggle"/>
                            <field name="es_destinatario" widget="boolean_toggle"/>
                        </group>
                        
                        <!-- Panel Informativo dinámico (Opcional, solo visual) -->
                        <group>
                            <div class="alert alert-info" role="alert" style="margin-bottom:0px;" 
                                 invisible="not es_generador and not es_transportista and not es_destinatario">
                                <i class="fa fa-info-circle"/> 
                                <span invisible="not es_generador"> Este contacto generará residuos.</span>
                                <span invisible="not es_transportista"> Proveedor de logística.</span>
                                <span invisible="not es_destinatario"> Sitio de disposición final.</span>
                            </div>
                        </group>
                    </group>

                    <separator string="Documentación y Permisos"/>

                    <group>
                        <!-- Columna Izquierda: Generador y Destino -->
                        <group>
                            <field name="numero_registro_ambiental" 
                                   invisible="not es_generador"
                                   placeholder="Ej. NRA-123456"
                                   decoration-bf="1"/>
                                   
                            <field name="numero_autorizacion_semarnat" 
                                   invisible="not es_transportista and not es_destinatario"
                                   placeholder="Ej. AUT-SEM-001"/>
                        </group>

                        <!-- Columna Derecha: Transportista (SCT y Vehículo) -->
                        <group invisible="not es_transportista">
                            <field name="numero_permiso_sct" 
                                   placeholder="Ej. SCT-TX-999"/>
                            
                            <label for="tipo_vehiculo" string="Unidad de Transporte"/>
                            <div class="o_row">
                                <field name="tipo_vehiculo" placeholder="Tipo (ej. Torton)"/>
                                <span class="text-muted">Placa:</span>
                                <field name="numero_placa" placeholder="ABC-123"/>
                            </div>
                        </group>
                    </group>
                </page>
            </notebook>
        </field>
    </record>
</odoo>```

## ./views/service_order_manifiesto_button.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <record id="view_service_order_form_manifiesto_button" model="ir.ui.view">
    <field name="name">service.order.form.manifiesto.button</field>
    <field name="model">service.order</field>
    <field name="inherit_id" ref="service_order.view_service_order_form"/>
    <field name="arch" type="xml">
      
      <!-- 1. Smart Button (Contador) en la parte superior -->
      <xpath expr="//div[@name='button_box']" position="inside">
        <button name="action_view_manifiestos"
                type="object"
                class="oe_stat_button"
                icon="fa-file-text-o"
                invisible="manifiesto_count == 0">
            <field name="manifiesto_count" widget="statinfo" string="Manifiestos"/>
        </button>
      </xpath>

      <!-- 2. Botón de Acción en el Header -->
      <xpath expr="//header/button[@name='action_cancel']" position="after">
        <button name="action_create_manifiesto"
                string="Crear Manifiesto"
                type="object"
                class="btn-primary"/>
      </xpath>
      
    </field>
  </record>
</odoo>```

## ./views/views_discrepancia.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>

    <!-- Acción para discrepancias -->
    <record id="action_manifiesto_discrepancia" model="ir.actions.act_window">
        <field name="name">Reportes de Discrepancias</field>
        <field name="res_model">manifiesto.discrepancia</field>
        <field name="view_mode">list,form</field>
    </record>

    <!-- Lista -->
    <record id="view_manifiesto_discrepancia_list" model="ir.ui.view">
        <field name="name">manifiesto.discrepancia.list</field>
        <field name="model">manifiesto.discrepancia</field>
        <field name="arch" type="xml">
            <list string="Reportes de Discrepancias" default_order="fecha_inspeccion desc">
                <field name="name"/>
                <field name="numero_manifiesto"/>
                <field name="fecha_manifiesto"/>
                <field name="generador_nombre"/>
                <field name="transportista_nombre"/>
                <field name="fecha_inspeccion"/>
                <field name="revisado_por"/>
                <field name="tiene_discrepancias" string="Hay Diferencias" widget="boolean_toggle"/>
                <field name="state" decoration-success="state == 'done'" decoration-warning="state == 'draft'"/>
            </list>
        </field>
    </record>

    <!-- Formulario -->
    <record id="view_manifiesto_discrepancia_form" model="ir.ui.view">
        <field name="name">manifiesto.discrepancia.form</field>
        <field name="model">manifiesto.discrepancia</field>
        <field name="arch" type="xml">
            <form string="Reporte de Discrepancias">
                <header>
                    <button name="action_print_discrepancia"
                            string="🖨️ Imprimir Reporte"
                            type="object"
                            class="btn-primary"/>
                    <button name="action_finalizar"
                            string="Finalizar"
                            type="object"
                            class="btn-success"
                            invisible="state == 'done'"/>
                    <button name="action_borrador"
                            string="Volver a Borrador"
                            type="object"
                            invisible="state == 'draft'"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,done"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>

                    <!-- Encabezado del reporte -->
                    <group string="Datos del Manifiesto" col="2">
                        <group>
                            <field name="manifiesto_id"
                                   options="{'no_create': True, 'no_create_edit': True}"
                                   domain="[('is_current_version', '=', True)]"/>
                            <field name="numero_manifiesto" readonly="1"/>
                            <field name="fecha_manifiesto" readonly="1"/>
                            <field name="generador_nombre" readonly="1"/>
                        </group>
                        <group>
                            <field name="transportista_nombre" readonly="1"/>
                            <field name="numero_placa" readonly="1"/>
                            <field name="operador_nombre"/>
                            <field name="fecha_inspeccion"/>
                            <field name="revisado_por"/>
                        </group>
                    </group>

                    <!-- Tabla de discrepancias -->
                    <notebook>
                        <page string="Discrepancias por Residuo">
                            <field name="linea_ids">
                                <list editable="bottom">
                                    <field name="sequence" widget="handle"/>
                                    <field name="residuo_manifiesto_id"
                                           string="Residuo (autocompletar)"
                                           optional="show"/>
                                    <field name="nombre_residuo"/>
                                    <field name="cantidad_manifestada" string="Cant. Manifestada"/>
                                    <field name="contenedor_manifestado" string="Cont. Manifestado"/>
                                    <field name="cantidad_real" string="Cant. Real"/>
                                    <field name="contenedor_real" string="Cont. Real"/>
                                    <field name="tipo_discrepancia" string="Tipo"/>
                                    <field name="observacion" string="Observación"/>
                                    <field name="tiene_diferencia" string="⚠️" widget="boolean"/>
                                </list>
                                <form string="Línea de Discrepancia">
                                    <sheet>
                                        <group string="Autocompletar desde Manifiesto">
                                            <field name="residuo_manifiesto_id"
                                                   options="{'no_create': True}"/>
                                        </group>
                                        <group string="Lo que decía el Manifiesto" col="2">
                                            <field name="nombre_residuo"/>
                                            <field name="cantidad_manifestada"/>
                                            <field name="contenedor_manifestado"/>
                                        </group>
                                        <group string="Lo que se Recibió Realmente" col="2">
                                            <field name="cantidad_real"/>
                                            <field name="contenedor_real"/>
                                        </group>
                                        <group string="Resultado" col="2">
                                            <field name="tipo_discrepancia"/>
                                            <field name="tiene_diferencia" readonly="1"/>
                                            <field name="observacion"/>
                                        </group>
                                    </sheet>
                                </form>
                            </field>
                        </page>
                    </notebook>

                    <group string="Observaciones Generales">
                        <field name="observaciones_generales" nolabel="1"
                               placeholder="Observaciones adicionales del reporte..."/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Búsqueda -->
    <record id="view_manifiesto_discrepancia_search" model="ir.ui.view">
        <field name="name">manifiesto.discrepancia.search</field>
        <field name="model">manifiesto.discrepancia</field>
        <field name="arch" type="xml">
            <search>
                <field name="numero_manifiesto"/>
                <field name="generador_nombre"/>
                <field name="transportista_nombre"/>
                <field name="revisado_por"/>
                <filter string="Con Discrepancias" name="con_disc" domain="[('tiene_discrepancias','=',True)]"/>
                <filter string="Sin Discrepancias" name="sin_disc" domain="[('tiene_discrepancias','=',False)]"/>
                <filter string="Borrador" name="draft" domain="[('state','=','draft')]"/>
                <filter string="Finalizado" name="done" domain="[('state','=','done')]"/>
                <filter string="Generador" name="group_gen" context="{'group_by':'generador_nombre'}"/>
                <filter string="Fecha Inspección" name="group_fecha" context="{'group_by':'fecha_inspeccion:month'}"/>
            </search>
        </field>
    </record>

</odoo>```

