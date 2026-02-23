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
    'depends': ['base', 'contacts', 'service_order', 'stock', 'residuo_recepcion_sai'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
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
    _description = 'Manifiesto Ambiental'
    _rec_name = 'numero_manifiesto'
    _order = 'numero_manifiesto desc, version desc'

    # CAMPOS DE VERSIONADO
    version = fields.Integer(
        string='Versión',
        default=1,
        readonly=True,
        help='Número de versión del manifiesto'
    )
    
    is_current_version = fields.Boolean(
        string='Versión Actual',
        default=True,
        help='Indica si esta es la versión actual del manifiesto'
    )
    
    original_manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto Original',
        help='Referencia al manifiesto original (versión 1)'
    )
    
    version_history_ids = fields.One2many(
        'manifiesto.ambiental.version',
        'manifiesto_id',
        string='Historial de Versiones',
        help='Todas las versiones de este manifiesto'
    )
    
    # Campos para control de cambios
    change_reason = fields.Text(
        string='Motivo del Cambio',
        help='Razón por la cual se creó esta nueva versión'
    )
    
    created_by_remanifest = fields.Boolean(
        string='Creado por Remanifestación',
        default=False,
        help='Indica si este manifiesto fue creado por una remanifestación'
    )

    # NÚMERO DE SECUENCIA INTERNO - nunca editable, solo avanza
    sequence_number = fields.Integer(
        string='Número de Secuencia',
        readonly=True,
        copy=False,
        help='Número de secuencia interno. Avanza siempre independientemente del número de manifiesto visible.'
    )

    # DOCUMENTO FÍSICO ESCANEADO
    documento_fisico = fields.Binary(
        string='Documento Físico Escaneado',
        help='Suba aquí el manifiesto físico escaneado (papel con firmas, sellos, modificaciones manuales, etc.)'
    )
    
    documento_fisico_filename = fields.Char(
        string='Nombre del Archivo Físico',
        help='Nombre del archivo del documento físico escaneado'
    )
    
    tiene_documento_fisico = fields.Boolean(
        string='Tiene Documento Físico',
        compute='_compute_tiene_documento_fisico',
        store=True,
        help='Indica si esta versión tiene un documento físico escaneado'
    )

    # ==============================================================
    # INTEGRACIÓN CON RECEPCIÓN DE RESIDUOS
    # ==============================================================
    recepcion_ids = fields.One2many(
        'residuo.recepcion',
        'manifiesto_id',
        string='Recepciones Generadas'
    )
    
    recepcion_count = fields.Integer(
        string='No. Recepciones',
        compute='_compute_recepcion_count'
    )

    # ==============================================================
    # INTEGRACIÓN CON DISCREPANCIAS
    # ==============================================================
    discrepancia_ids = fields.One2many(
        'manifiesto.discrepancia',
        'manifiesto_id',
        string='Reportes de Discrepancias'
    )

    discrepancia_count = fields.Integer(
        string='No. Discrepancias',
        compute='_compute_discrepancia_count'
    )

    # 1. Núm. de registro ambiental
    numero_registro_ambiental = fields.Char(
        string='1. Núm. de registro ambiental',
        required=True,
        help='Número de registro ambiental del generador'
    )
    
    # 2. Núm. de manifiesto - AHORA EDITABLE, secuencia es interna
    numero_manifiesto = fields.Char(
        string='2. Núm. de manifiesto',
        required=True,
        copy=False,
        help='Número del manifiesto. Puede editarse manualmente. La secuencia interna avanza de forma independiente.'
    )
    
    # Campo computado para mostrar número con versión
    numero_manifiesto_display = fields.Char(
        string='Número de Manifiesto',
        compute='_compute_numero_manifiesto_display',
        store=True,
        help='Número de manifiesto con versión para visualización'
    )
    
    # 3. Página
    pagina = fields.Integer(
        string='3. Página',
        default=1,
        help='Número de página del manifiesto'
    )

    # 4. GENERADOR
    generador_id = fields.Many2one(
        'res.partner',
        string='Generador',
        domain=[('es_generador', '=', True)],
        help='Seleccionar el generador de residuos'
    )
    generador_nombre = fields.Char(
        string='4. Nombre o razón social del generador',
        required=True
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

    # 5. Identificación de los residuos
    residuo_ids = fields.One2many(
        'manifiesto.ambiental.residuo',
        'manifiesto_id',
        string='5. Identificación de los residuos'
    )

    # 6. Instrucciones especiales
    instrucciones_especiales = fields.Text(
        string='6. Instrucciones especiales e información adicional para el manejo seguro'
    )

    # 7. Declaración del generador
    declaracion_generador = fields.Text(
        string='7. Declaración del generador',
        default='Declaro bajo protesta de decir verdad que el contenido de este lote está total y correctamente descrito mediante el número de manifiesto, nombre del residuo, características cretib, debidamente envasado y etiquetado y que se han previsto las condiciones de seguridad para su transporte por vía terrestre de acuerdo con la legislación vigente.',
        readonly=True
    )
    generador_responsable_nombre = fields.Char(string='Nombre y firma del responsable')
    generador_fecha = fields.Date(string='Fecha', default=fields.Date.context_today)
    generador_sello = fields.Char(string='Sello')

    # 8. TRANSPORTISTA
    transportista_id = fields.Many2one(
        'res.partner',
        string='Transportista',
        domain=[('es_transportista', '=', True)],
        help='Seleccionar el transportista'
    )
    transportista_nombre = fields.Char(
        string='8. Nombre o razón social del transportista',
        required=True
    )
    transportista_codigo_postal = fields.Char(string='Código postal')
    transportista_calle = fields.Char(string='Calle')
    transportista_num_ext = fields.Char(string='Núm. Ext.')
    transportista_num_int = fields.Char(string='Núm. Int.')
    transportista_colonia = fields.Char(string='Colonia')
    transportista_municipio = fields.Char(string='Municipio o Delegación')
    transportista_estado = fields.Char(string='Estado')
    transportista_telefono = fields.Char(string='Teléfono')
    transportista_email = fields.Char(string='Correo electrónico')

    # 9. Núm. de autorización de la SEMARNAT
    numero_autorizacion_semarnat = fields.Char(
        string='9. Núm. de autorización de la SEMARNAT'
    )

    # 10. Núm. de permiso S.C.T.
    numero_permiso_sct = fields.Char(
        string='10. Núm. de permiso S.C.T.'
    )

    # 11. Tipo de vehículo
    tipo_vehiculo = fields.Char(
        string='11. Tipo de vehículo'
    )

    # 12. Núm. de placa
    numero_placa = fields.Char(
        string='12. Núm. de placa'
    )

    # 13. Ruta
    ruta_empresa = fields.Text(
        string='13. Ruta de la empresa generadora hasta su entrega'
    )

    # 14. Declaración del transportista
    declaracion_transportista = fields.Text(
        string='14. Declaración del transportista',
        default='Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto para su transporte a la empresa destinataria señalada por el generador.',
        readonly=True
    )
    transportista_responsable_nombre = fields.Char(string='Nombre y firma del responsable')
    transportista_fecha = fields.Date(string='Fecha', default=fields.Date.context_today)
    transportista_sello = fields.Char(string='Sello')

    # 15. DESTINATARIO
    destinatario_id = fields.Many2one(
        'res.partner',
        string='Destinatario',
        domain=[('es_destinatario', '=', True)],
        help='Seleccionar el destinatario final'
    )
    destinatario_nombre = fields.Char(
        string='15. Nombre o razón social del destinatario',
        required=True
    )
    destinatario_codigo_postal = fields.Char(string='Código postal')
    destinatario_calle = fields.Char(string='Calle')
    destinatario_num_ext = fields.Char(string='Núm. Ext.')
    destinatario_num_int = fields.Char(string='Núm. Int.')
    destinatario_colonia = fields.Char(string='Colonia')
    destinatario_municipio = fields.Char(string='Municipio o Delegación')
    destinatario_estado = fields.Char(string='Estado')
    destinatario_telefono = fields.Char(string='Teléfono')
    destinatario_email = fields.Char(string='Correo electrónico')

    # 16. Núm. autorización de la SEMARNAT (destinatario)
    numero_autorizacion_semarnat_destinatario = fields.Char(
        string='16. Núm. autorización de la SEMARNAT'
    )

    # 17. Nombre y cargo de la persona que recibe
    nombre_persona_recibe = fields.Char(
        string='17. Nombre y cargo de la persona que recibe los residuos'
    )

    # 18. Observaciones
    observaciones_destinatario = fields.Text(
        string='18. Observaciones'
    )

    # 19. Declaración del destinatario
    declaracion_destinatario = fields.Text(
        string='19. Declaración del destinatario',
        default='Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto.',
        readonly=True
    )
    destinatario_responsable_nombre = fields.Char(string='Nombre y firma del responsable')
    destinatario_fecha = fields.Date(string='Fecha', default=fields.Date.context_today)
    destinatario_sello = fields.Char(string='Sello')

    # Campos de control
    service_order_id = fields.Many2one(
        'service.order',
        string='Orden de Servicio',
        help='Orden de servicio origen de este manifiesto'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('in_transit', 'En Tránsito'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    # =========================================================================
    # LÓGICA DE NUMERACIÓN
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
    # MÉTODOS COMPUTADOS
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

    # =========================================================================
    # ONCHANGE
    # =========================================================================

    @api.onchange('generador_id')
    def _onchange_generador_id(self):
        if self.generador_id:
            self.numero_registro_ambiental = self.generador_id.numero_registro_ambiental or ''
            self.generador_nombre = self.generador_id.name or ''
            self.generador_codigo_postal = self.generador_id.zip or ''
            self.generador_calle = self.generador_id.street or ''
            self.generador_num_ext = self.generador_id.street_number or ''
            self.generador_num_int = self.generador_id.street_number2 or ''
            self.generador_colonia = self.generador_id.street2 or ''
            self.generador_municipio = self.generador_id.city or ''
            self.generador_estado = self.generador_id.state_id.name if self.generador_id.state_id else ''
            self.generador_telefono = self.generador_id.phone or ''
            self.generador_email = self.generador_id.email or ''

    @api.onchange('transportista_id')
    def _onchange_transportista_id(self):
        if self.transportista_id:
            self.transportista_nombre = self.transportista_id.name or ''
            self.transportista_codigo_postal = self.transportista_id.zip or ''
            self.transportista_calle = self.transportista_id.street or ''
            self.transportista_num_ext = self.transportista_id.street_number or ''
            self.transportista_num_int = self.transportista_id.street_number2 or ''
            self.transportista_colonia = self.transportista_id.street2 or ''
            self.transportista_municipio = self.transportista_id.city or ''
            self.transportista_estado = self.transportista_id.state_id.name if self.transportista_id.state_id else ''
            self.transportista_telefono = self.transportista_id.phone or ''
            self.transportista_email = self.transportista_id.email or ''
            self.numero_autorizacion_semarnat = self.transportista_id.numero_autorizacion_semarnat or ''
            self.numero_permiso_sct = self.transportista_id.numero_permiso_sct or ''
            self.tipo_vehiculo = self.transportista_id.tipo_vehiculo or ''
            self.numero_placa = self.transportista_id.numero_placa or ''

    @api.onchange('destinatario_id')
    def _onchange_destinatario_id(self):
        if self.destinatario_id:
            self.destinatario_nombre = self.destinatario_id.name or ''
            self.destinatario_codigo_postal = self.destinatario_id.zip or ''
            self.destinatario_calle = self.destinatario_id.street or ''
            self.destinatario_num_ext = self.destinatario_id.street_number or ''
            self.destinatario_num_int = self.destinatario_id.street_number2 or ''
            self.destinatario_colonia = self.destinatario_id.street2 or ''
            self.destinatario_municipio = self.destinatario_id.city or ''
            self.destinatario_estado = self.destinatario_id.state_id.name if self.destinatario_id.state_id else ''
            self.destinatario_telefono = self.destinatario_id.phone or ''
            self.destinatario_email = self.destinatario_id.email or ''
            self.numero_autorizacion_semarnat_destinatario = self.destinatario_id.numero_autorizacion_semarnat or ''

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
                            next_seq
                        )
                    else:
                        vals['numero_manifiesto'] = str(next_seq)
            
            if vals.get('generador_id'):
                partner = self.env['res.partner'].browse(vals['generador_id'])
                update_vals = {
                    'numero_registro_ambiental': partner.numero_registro_ambiental or '',
                    'generador_nombre': partner.name or '',
                    'generador_codigo_postal': partner.zip or '',
                    'generador_calle': partner.street or '',
                    'generador_num_ext': partner.street_number or '',
                    'generador_num_int': partner.street_number2 or '',
                    'generador_colonia': partner.street2 or '',
                    'generador_municipio': partner.city or '',
                    'generador_estado': partner.state_id.name if partner.state_id else '',
                    'generador_telefono': partner.phone or '',
                    'generador_email': partner.email or '',
                }
                for key, value in update_vals.items():
                    if key not in vals:
                        vals[key] = value
        
        records = super().create(vals_list)
        
        for record in records:
            if not record.original_manifiesto_id:
                record.original_manifiesto_id = record.id
        
        return records

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
    # INTEGRACIÓN CON RECEPCIÓN DE RESIDUOS
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
        """Crea un reporte de discrepancias con los residuos del manifiesto precargados"""
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
            raise UserError("No se puede remanifestar un manifiesto en estado borrador. Debe confirmarlo primero.")
        
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
                'context': {'default_change_reason': 'Nueva versión creada por remanifestación'}
            }
            
        except Exception as e:
            _logger.error(f"Error en remanifestación del manifiesto {self.numero_manifiesto}: {str(e)}")
            raise UserError(f"Error durante la remanifestación: {str(e)}")

    def action_remanifestar_sin_pdf(self):
        self.ensure_one()
        
        if not self.is_current_version:
            raise UserError("Solo se puede remanifestar la versión actual del manifiesto.")
        
        if self.state == 'draft':
            raise UserError("No se puede remanifestar un manifiesto en estado borrador. Debe confirmarlo primero.")
        
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
                'context': {'default_change_reason': 'Nueva versión creada por remanifestación (sin PDF)'}
            }
            
        except Exception as e:
            _logger.error(f"Error en remanifestación del manifiesto {self.numero_manifiesto}: {str(e)}")
            raise UserError(f"Error durante la remanifestación: {str(e)}")

    def _generate_current_pdf_corregido(self):
        try:
            self._validate_required_data()
            self.env.cr.commit()
            current_record = self.sudo().browse(self.id)
            
            report = None
            try:
                report = self.env.ref('manifiesto_ambiental.action_report_manifiesto_ambiental')
            except:
                try:
                    report = self.env['ir.actions.report'].search([
                        ('model', '=', 'manifiesto.ambiental'),
                        ('report_type', '=', 'qweb-pdf')
                    ], limit=1)
                except:
                    pass
            
            if not report:
                raise UserError("No se encontró el reporte PDF del manifiesto. Verifique la configuración.")
            
            clean_context = {
                'lang': self.env.user.lang or 'es_ES',
                'tz': self.env.user.tz or 'UTC',
            }
            
            pdf_content, format_type = report.sudo().with_context(clean_context)._render_qweb_pdf(
                report.report_name,
                res_ids=[current_record.id],
                data=None
            )
            
            if not pdf_content:
                raise UserError("El contenido del PDF generado está vacío.")
            
            pdf_data = base64.b64encode(pdf_content)
            _logger.info(f"PDF generado exitosamente para manifiesto {current_record.numero_manifiesto} versión {current_record.version}")
            return pdf_data
            
        except Exception as e:
            _logger.error(f"Error generando PDF para manifiesto {self.numero_manifiesto}: {str(e)}")
            if "'list' object has no attribute 'split'" in str(e):
                raise UserError("Error en los datos del manifiesto. Verifique que todos los campos de texto estén correctamente completados.")
            elif "unhashable type: 'list'" in str(e):
                raise UserError("Error en la configuración del reporte. Contacte al administrador del sistema.")
            elif "External ID not found" in str(e):
                raise UserError("No se encontró la plantilla del reporte PDF. Verifique la instalación del módulo.")
            elif "'Environment' object has no attribute 'context_manager'" in str(e):
                raise UserError("Error de compatibilidad. Use el método alternativo 'Remanifestar (Datos)'.")
            else:
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
        
        text_fields = [
            'numero_registro_ambiental', 'generador_nombre', 'generador_calle',
            'transportista_nombre', 'transportista_calle', 'destinatario_nombre',
            'destinatario_calle', 'instrucciones_especiales'
        ]
        for field_name in text_fields:
            value = getattr(self, field_name, None)
            if isinstance(value, (list, tuple)):
                errors.append(f"Campo {field_name} tiene formato incorrecto")
        
        if not self.residuo_ids:
            errors.append("Debe tener al menos un residuo")
        
        if errors:
            raise UserError(f"Faltan datos requeridos: {', '.join(errors)}")

    def _generate_structured_data(self):
        data = {
            'numero_manifiesto': self.numero_manifiesto or '',
            'version': self.version,
            'fecha_generacion': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'estado': self.state,
            'tiene_documento_fisico': self.tiene_documento_fisico,
            'documento_fisico_filename': self.documento_fisico_filename or '',
            'generador': {
                'numero_registro': self.numero_registro_ambiental or '',
                'nombre': self.generador_nombre or '',
                'direccion': {
                    'calle': self.generador_calle or '',
                    'num_ext': self.generador_num_ext or '',
                    'num_int': self.generador_num_int or '',
                    'colonia': self.generador_colonia or '',
                    'municipio': self.generador_municipio or '',
                    'estado': self.generador_estado or '',
                    'codigo_postal': self.generador_codigo_postal or '',
                },
                'contacto': {
                    'telefono': self.generador_telefono or '',
                    'email': self.generador_email or '',
                },
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
                'observaciones': self.observaciones_destinatario or '',
                'responsable': self.destinatario_responsable_nombre or '',
                'fecha': str(self.destinatario_fecha) if self.destinatario_fecha else '',
            },
            'residuos': []
        }
        
        for residuo in self.residuo_ids:
            data['residuos'].append({
                'nombre': residuo.nombre_residuo or '',
                'cantidad': residuo.cantidad,
                'unidad': 'kg',
                'clasificaciones': residuo.clasificaciones_display or '',
                'envase': {
                    'tipo': residuo.envase_tipo or '',
                    'capacidad': residuo.envase_capacidad or '',
                },
                'etiquetado': 'Sí' if residuo.etiqueta_si else 'No',
            })
        
        return data

    def _save_version_to_history_with_data(self, data_estructurados):
        try:
            data_text = self._format_data_as_text(data_estructurados)
            data_encoded = base64.b64encode(data_text.encode('utf-8'))
            
            version_data = {
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
            }
            
            self.env['manifiesto.ambiental.version'].create(version_data)
            _logger.info(f"Versión {self.version} guardada en historial (datos estructurados) para manifiesto {self.numero_manifiesto}")
            
        except Exception as e:
            _logger.error(f"Error guardando versión con datos: {str(e)}")
            raise UserError(f"Error al guardar la versión: {str(e)}")

    def _format_data_as_text(self, data):
        texto = f"""
MANIFIESTO AMBIENTAL - VERSIÓN {data['version']}
{'='*50}

Número de Manifiesto: {data['numero_manifiesto']}
Fecha de Generación: {data['fecha_generacion']}
Estado: {data['estado']}
Tiene Documento Físico: {'Sí' if data['tiene_documento_fisico'] else 'No'}
Archivo Físico: {data['documento_fisico_filename']}

GENERADOR
{'-'*20}
Número de Registro: {data['generador']['numero_registro']}
Nombre: {data['generador']['nombre']}
Dirección: {data['generador']['direccion']['calle']} {data['generador']['direccion']['num_ext']}
           {data['generador']['direccion']['colonia']}, {data['generador']['direccion']['municipio']}
           {data['generador']['direccion']['estado']} CP: {data['generador']['direccion']['codigo_postal']}
Teléfono: {data['generador']['contacto']['telefono']}
Email: {data['generador']['contacto']['email']}
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
Observaciones: {data['destinatario']['observaciones']}
Responsable: {data['destinatario']['responsable']}
Fecha: {data['destinatario']['fecha']}

RESIDUOS
{'-'*20}
"""
        for i, residuo in enumerate(data['residuos'], 1):
            texto += f"""
{i}. {residuo['nombre']}
   Cantidad: {residuo['cantidad']} {residuo['unidad']}
   Clasificaciones CRETIB: {residuo['clasificaciones']}
   Envase: {residuo['envase']['tipo']} - {residuo['envase']['capacidad']}
   Etiquetado: {residuo['etiquetado']}
"""
        return texto

    def _save_version_to_history(self, pdf_data):
        try:
            version_data = {
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
            }
            
            self.env['manifiesto.ambiental.version'].create(version_data)
            _logger.info(f"Versión {self.version} guardada en historial para manifiesto {self.numero_manifiesto}")
            
        except Exception as e:
            _logger.error(f"Error guardando versión en historial: {str(e)}")
            raise UserError(f"Error al guardar la versión en el historial: {str(e)}")

    def _create_new_version(self):
        try:
            next_version = self.version + 1
            new_vals = self._prepare_version_data(next_version)
            new_version = self.create(new_vals)
            self._copy_residuos_to_version(new_version)
            _logger.info(f"Nueva versión {next_version} creada para manifiesto {self.numero_manifiesto}")
            return new_version
        except Exception as e:
            _logger.error(f"Error creando nueva versión: {str(e)}")
            raise UserError(f"Error al crear la nueva versión: {str(e)}")

    def _prepare_version_data(self, next_version):
        exclude_fields = {
            'id', 'create_date', 'create_uid', 'write_date', 'write_uid',
            'version_history_ids', 'residuo_ids', '__last_update',
            'display_name'
        }
        
        new_vals = {}
        for field_name, field in self._fields.items():
            if field_name not in exclude_fields:
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
        try:
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
        except Exception as e:
            _logger.error(f"Error copiando residuos: {str(e)}")
            raise UserError(f"Error al copiar los residuos: {str(e)}")

    def _deactivate_current_version(self):
        try:
            self.write({'is_current_version': False, 'state': 'delivered'})
        except Exception as e:
            _logger.error(f"Error desactivando versión actual: {str(e)}")
            raise UserError(f"Error al desactivar la versión actual: {str(e)}")

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
            ('is_current_version', '=', True)
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


class ManifiestoAmbientalResiduo(models.Model):
    _name = 'manifiesto.ambiental.residuo'
    _description = 'Residuo del Manifiesto Ambiental'

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto/Residuo',
        help='Seleccionar el producto/residuo peligroso'
    )
    
    nombre_residuo = fields.Char(
        string='Nombre del residuo',
        required=True
    )
    
    residue_type = fields.Selection(
        [('rsu', 'RSU'), ('rme', 'RME'), ('rp', 'RP')],
        string='Tipo de Residuo',
        help='Clasificación general del residuo'
    )

    clasificacion_corrosivo = fields.Boolean(string='Corrosivo (C)')
    clasificacion_reactivo = fields.Boolean(string='Reactivo (R)')
    clasificacion_explosivo = fields.Boolean(string='Explosivo (E)')
    clasificacion_toxico = fields.Boolean(string='Tóxico (T)')
    clasificacion_inflamable = fields.Boolean(string='Inflamable (I)')
    clasificacion_biologico = fields.Boolean(string='Biológico (B)')
    
    clasificaciones_display = fields.Char(
        string='Clasificaciones CRETIB',
        compute='_compute_clasificaciones_display',
        store=True
    )
    
    envase_tipo = fields.Selection([
        ('tambor', 'Tambor'),
        ('contenedor', 'Contenedor'),
        ('tote', 'Tote'),
        ('tarima', 'Tarima'),
        ('saco', 'Saco'),
        ('caja', 'Caja'),
        ('bolsa', 'Bolsa'),
        ('tanque', 'Tanque'),
        ('otro', 'Otro'),
    ], string='Tipo de Envase')
    
    packaging_id = fields.Many2one(
        'uom.uom', 
        string='Unidad de Embalaje',
        help='Tipo de embalaje o presentación del residuo'
    )

    envase_capacidad = fields.Char(
        string='Capacidad',
        help='Capacidad del envase (ej: 200 L, 50 Kg)'
    )
    
    cantidad = fields.Float(
        string='Cantidad (kg)',
        required=True,
        help='Cantidad siempre en kilogramos'
    )
    
    unidad = fields.Char(
        string='Unidad',
        default='kg',
        readonly=True
    )
    
    etiqueta_si = fields.Boolean(string='Etiqueta - Sí', default=True)
    etiqueta_no = fields.Boolean(string='Etiqueta - No', default=False)
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Número de Lote',
        readonly=True,
        help='Lote generado automáticamente con el número de manifiesto'
    )

    @api.depends('clasificacion_corrosivo', 'clasificacion_reactivo', 'clasificacion_explosivo',
                 'clasificacion_toxico', 'clasificacion_inflamable', 'clasificacion_biologico')
    def _compute_clasificaciones_display(self):
        for record in self:
            clasificaciones = []
            if record.clasificacion_corrosivo:
                clasificaciones.append('C')
            if record.clasificacion_reactivo:
                clasificaciones.append('R')
            if record.clasificacion_explosivo:
                clasificaciones.append('E')
            if record.clasificacion_toxico:
                clasificaciones.append('T')
            if record.clasificacion_inflamable:
                clasificaciones.append('I')
            if record.clasificacion_biologico:
                clasificaciones.append('B')
            record.clasificaciones_display = ', '.join(clasificaciones)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if hasattr(self.product_id, 'es_residuo_peligroso') and self.product_id.es_residuo_peligroso:
                self.nombre_residuo = self.product_id.name
                if hasattr(self.product_id, 'clasificacion_corrosivo'):
                    self.clasificacion_corrosivo = self.product_id.clasificacion_corrosivo
                if hasattr(self.product_id, 'clasificacion_reactivo'):
                    self.clasificacion_reactivo = self.product_id.clasificacion_reactivo
                if hasattr(self.product_id, 'clasificacion_explosivo'):
                    self.clasificacion_explosivo = self.product_id.clasificacion_explosivo
                if hasattr(self.product_id, 'clasificacion_toxico'):
                    self.clasificacion_toxico = self.product_id.clasificacion_toxico
                if hasattr(self.product_id, 'clasificacion_inflamable'):
                    self.clasificacion_inflamable = self.product_id.clasificacion_inflamable
                if hasattr(self.product_id, 'clasificacion_biologico'):
                    self.clasificacion_biologico = self.product_id.clasificacion_biologico
                if hasattr(self.product_id, 'envase_tipo_default'):
                    self.envase_tipo = self.product_id.envase_tipo_default
                if hasattr(self.product_id, 'envase_capacidad_default'):
                    val = self.product_id.envase_capacidad_default
                    self.envase_capacidad = str(val) if val else ''
            else:
                self.nombre_residuo = self.product_id.name

    @api.onchange('etiqueta_si')
    def _onchange_etiqueta_si(self):
        if self.etiqueta_si:
            self.etiqueta_no = False

    @api.onchange('etiqueta_no')
    def _onchange_etiqueta_no(self):
        if self.etiqueta_no:
            self.etiqueta_si = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._create_lot_for_residuo()
        return records

    def _create_lot_for_residuo(self):
        for record in self:
            if record.product_id and record.manifiesto_id.numero_manifiesto:
                existing_lot = self.env['stock.lot'].search([
                    ('name', '=', record.manifiesto_id.numero_manifiesto),
                    ('product_id', '=', record.product_id.id),
                    ('company_id', '=', record.manifiesto_id.company_id.id)
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


class ManifiestoAmbientalVersion(models.Model):
    _name = 'manifiesto.ambiental.version'
    _description = 'Historial de Versiones del Manifiesto Ambiental'
    _order = 'creation_date desc, version_number desc'
    _rec_name = 'display_name'

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto Original',
        required=True,
        ondelete='cascade',
    )
    
    version_number = fields.Integer(string='Número de Versión', required=True)
    
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True,
    )
    
    pdf_file = fields.Binary(string='Archivo PDF')
    pdf_filename = fields.Char(string='Nombre del PDF')
    data_file = fields.Binary(string='Archivo de Datos')
    data_filename = fields.Char(string='Nombre de Datos')
    documento_fisico_original = fields.Binary(string='Documento Físico Original')
    documento_fisico_filename_original = fields.Char(string='Nombre del Documento Físico Original')
    tenia_documento_fisico = fields.Boolean(string='Tenía Documento Físico')
    
    creation_date = fields.Datetime(
        string='Fecha de Creación',
        required=True,
        default=fields.Datetime.now,
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Creado por',
        required=True,
        default=lambda self: self.env.user,
    )
    
    state_at_creation = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('in_transit', 'En Tránsito'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado'),
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
        else:
            return {'has_file': False, 'file_type': None, 'field_name': None, 'filename_field': None, 'filename': None, 'display_name': 'Sin archivo'}

    def action_download_file(self):
        file_info = self.get_available_file_info()
        if not file_info['has_file']:
            raise UserError("No hay archivo disponible para esta versión.")
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/{file_info["field_name"]}/{file_info["filename"]}?download=true',
            'target': 'self',
        }

    def action_view_file(self):
        file_info = self.get_available_file_info()
        if not file_info['has_file']:
            raise UserError("No hay archivo disponible para esta versión.")
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/{file_info["field_name"]}/{file_info["filename"]}',
            'target': 'new',
        }

    def action_download_documento_fisico(self):
        if not self.documento_fisico_original:
            raise UserError("Esta versión no tiene documento físico disponible.")
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/documento_fisico_original/{self.documento_fisico_filename_original}?download=true',
            'target': 'self',
        }

    def action_view_documento_fisico(self):
        if not self.documento_fisico_original:
            raise UserError("Esta versión no tiene documento físico disponible.")
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/documento_fisico_original/{self.documento_fisico_filename_original}',
            'target': 'new',
        }

    def unlink(self):
        if any(version.version_number == 1 for version in self):
            raise UserError("No se puede eliminar la versión 1 (original) del manifiesto.")
        return super().unlink()```

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

    # ====================================================================
    # AGREGADO: Relación y Contador para Smart Button
    # ====================================================================
    manifiesto_ids = fields.One2many(
        'manifiesto.ambiental',
        'service_order_id',
        string='Manifiestos Generados'
    )

    manifiesto_count = fields.Integer(
        string='No. Manifiestos',
        compute='_compute_manifiesto_count'
    )

    @api.depends('manifiesto_ids')
    def _compute_manifiesto_count(self):
        for rec in self:
            rec.manifiesto_count = len(rec.manifiesto_ids)

    def action_view_manifiestos(self):
        """Acción del Smart Button para ver los manifiestos vinculados"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Manifiestos Ambientales'),
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'list,form',
            'domain': [('service_order_id', '=', self.id)],
            'context': {'default_service_order_id': self.id},
        }
    # ====================================================================

    def action_create_manifiesto(self):
        self.ensure_one()
        
        # 1. Determinar el generador (prioridad: generador_id, luego partner_id)
        generador = self.generador_id if self.generador_id else self.partner_id
        
        # 2. Obtener la fecha del servicio
        fecha_servicio = None
        if hasattr(self, 'date_start') and self.date_start:
            fecha_servicio = self.date_start
        elif hasattr(self, 'scheduled_date') and self.scheduled_date:
            fecha_servicio = self.scheduled_date
        elif hasattr(self, 'service_date') and self.service_date:
            fecha_servicio = self.service_date
        elif hasattr(self, 'date_order') and self.date_order:
            fecha_servicio = self.date_order
        else:
            fecha_servicio = fields.Date.context_today(self)
        
        # 3. Lógica para obtener nombres de responsables (fix previo)
        gen_resp_nombre = ''
        if self.generador_responsable_id:
            gen_resp_nombre = self.generador_responsable_id.name
        
        trans_resp_nombre = ''
        if self.transportista_responsable_id:
            trans_resp_nombre = self.transportista_responsable_id.name

        # 4. Lógica para la ruta/ubicación
        ruta = ''
        if self.pickup_location_id:
            ruta = self.pickup_location_id.contact_address_complete or self.pickup_location_id.name
            ruta = ruta.replace('\n', ', ')
        elif self.pickup_location:
            ruta = self.pickup_location

        # 5. PREPARAR LÍNEAS DE RESIDUOS (NUEVA LÓGICA)
        residuo_lines = []
        for line in self.line_ids:
            # Solo procesar líneas que tengan un producto asociado
            if not line.product_id:
                continue

            # CONDICIONAL: Si el nombre del producto empieza con "Servicio de", se omite
            # Se usa upper() para ignorar mayúsculas/minúsculas
            prod_name = line.product_id.name or ''
            if prod_name.strip().upper().startswith('SERVICIO DE'):
                _logger.info(f"Omitiendo línea {line.name} porque inicia con 'Servicio de'")
                continue

            # Determinar la cantidad: Prioridad al peso (kg), si es 0 usamos la cantidad unitaria
            # El manifiesto siempre espera KG
            cantidad_final = line.weight_kg if line.weight_kg > 0.0 else line.product_uom_qty

            # Obtener datos CRETIB y Envase del producto
            prod = line.product_id
            
            # Obtener Capacidad: Prioridad a la línea (Char), luego default del producto
            capacidad_final = line.capacity if line.capacity else ''
            if not capacidad_final and hasattr(prod, 'envase_capacidad_default') and prod.envase_capacidad_default:
                capacidad_final = str(prod.envase_capacidad_default)

            residuo_vals = {
                'product_id': prod.id,
                'nombre_residuo': line.description or prod.name, # Usar descripción personalizada si existe
                'cantidad': cantidad_final,
                # CORRECCIÓN AQUÍ: Se lee 'residue_type' (origen) y se asigna a 'residue_type' (destino)
                'residue_type': line.residue_type, 
                'packaging_id': line.packaging_id.id if line.packaging_id else False, # Propagar Unidad de embalaje
                
                # Propagar CRETIB desde el producto
                'clasificacion_corrosivo': prod.clasificacion_corrosivo,
                'clasificacion_reactivo': prod.clasificacion_reactivo,
                'clasificacion_explosivo': prod.clasificacion_explosivo,
                'clasificacion_toxico': prod.clasificacion_toxico,
                'clasificacion_inflamable': prod.clasificacion_inflamable,
                'clasificacion_biologico': prod.clasificacion_biologico,
                
                # Propagar configuración de envase (Tipo y Capacidad)
                'envase_tipo': prod.envase_tipo_default,
                'envase_capacidad': capacidad_final,
                
                # Opciones por defecto de etiqueta
                'etiqueta_si': True,
                'etiqueta_no': False,
            }
            
            # Agregar a la lista de creación One2many (0, 0, vals)
            residuo_lines.append((0, 0, residuo_vals))

        # 6. Crear el diccionario maestro
        manifiesto_vals = {
            'service_order_id': self.id,
            
            # --- GENERADOR ---
            'generador_id': generador.id,
            'numero_registro_ambiental': generador.numero_registro_ambiental or '',
            'generador_nombre': generador.name or '',
            'generador_codigo_postal': generador.zip or '',
            'generador_calle': generador.street or '',
            'generador_num_ext': generador.street_number or '',
            'generador_num_int': generador.street_number2 or '',
            'generador_colonia': generador.street2 or '',
            'generador_municipio': generador.city or '',
            'generador_estado': generador.state_id.name if generador.state_id else '',
            'generador_telefono': generador.phone or '',
            'generador_email': generador.email or '',
            'generador_responsable_nombre': gen_resp_nombre,
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
            'transportista_estado': self.transportista_id.state_id.name if self.transportista_id and self.transportista_id.state_id else '',
            'transportista_telefono': self.transportista_id.phone if self.transportista_id else '',
            'transportista_email': self.transportista_id.email if self.transportista_id else '',
            'numero_autorizacion_semarnat': self.transportista_id.numero_autorizacion_semarnat if self.transportista_id else '',
            'numero_permiso_sct': self.transportista_id.numero_permiso_sct if self.transportista_id else '',
            'tipo_vehiculo': self.camion or (self.transportista_id.tipo_vehiculo if self.transportista_id else ''),
            'numero_placa': self.numero_placa or (self.transportista_id.numero_placa if self.transportista_id else ''),
            'transportista_responsable_nombre': trans_resp_nombre,
            'transportista_fecha': fecha_servicio,
            
            # --- DESTINATARIO ---
            'destinatario_id': self.destinatario_id.id if self.destinatario_id else self.partner_id.id,
            'destinatario_nombre': (self.destinatario_id.name if self.destinatario_id else self.partner_id.name) or '',
            'destinatario_codigo_postal': (self.destinatario_id.zip if self.destinatario_id else self.partner_id.zip) or '',
            'destinatario_calle': (self.destinatario_id.street if self.destinatario_id else self.partner_id.street) or '',
            'destinatario_num_ext': (self.destinatario_id.street_number if self.destinatario_id else self.partner_id.street_number) or '',
            'destinatario_num_int': (self.destinatario_id.street_number2 if self.destinatario_id else self.partner_id.street_number2) or '',
            'destinatario_colonia': (self.destinatario_id.street2 if self.destinatario_id else self.partner_id.street2) or '',
            'destinatario_municipio': (self.destinatario_id.city if self.destinatario_id else self.partner_id.city) or '',
            'destinatario_estado': ((self.destinatario_id.state_id.name if self.destinatario_id.state_id else '') if self.destinatario_id else (self.partner_id.state_id.name if self.partner_id.state_id else '')) or '',
            'destinatario_telefono': (self.destinatario_id.phone if self.destinatario_id else self.partner_id.phone) or '',
            'destinatario_email': (self.destinatario_id.email if self.destinatario_id else self.partner_id.email) or '',
            'numero_autorizacion_semarnat_destinatario': (self.destinatario_id.numero_autorizacion_semarnat if self.destinatario_id else self.partner_id.numero_autorizacion_semarnat) or '',
            'destinatario_fecha': fecha_servicio,
            
            # --- OTROS ---
            'nombre_persona_recibe': self.contact_name or '',
            'ruta_empresa': ruta,
            'instrucciones_especiales': self.observaciones or '',
            
            # --- RESIDUOS (AQUÍ SE ASIGNAN) ---
            'residuo_ids': residuo_lines, 
        }
        
        # 7. Crear el registro (Odoo 19 compatible con create_multi aunque pasemos un dict único aquí)
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

    <!-- ACCIÓN DEL REPORTE -->
    <record id="action_report_manifiesto_ambiental" model="ir.actions.report">
        <field name="name">Manifiesto Ambiental</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">manifiesto_ambiental.manifiesto_ambiental_document</field>
        <field name="report_file">manifiesto_ambiental.manifiesto_ambiental_document</field>
        <field name="binding_model_id" ref="model_manifiesto_ambiental"/>
        <field name="binding_type">report</field>
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

                            /* ======================================================= */
                            /* NUEVO: Ocultar el pie de página (Footer) completamente */
                            /* ======================================================= */
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

                            /* Sección 4 homogénea y a todo ancho */
                            table.section-4 { width: 100%; border-collapse: collapse; table-layout: fixed; }

                            /* Bloques de firma integrados en un solo recuadro (sin divisiones internas) */
                            table.signature-section { width: 100%; border-collapse: separate; border-spacing: 0; margin-bottom: 2px; }
                            table.signature-section > tbody > tr > td { border: none !important; padding: 0; }
                            .signature-container { border: 1px solid #666; padding: 4px; }
                            .signature-text { margin: 0 0 4px 0; }
                            .signature-fields { display: table; width: 100%; margin-top: 2px; }
                            .signature-fields .cell { display: table-cell; vertical-align: top; padding-right: 8px; }
                            .signature-fields .cell:last-child { padding-right: 0; }

                            /* Evitar saltos dentro de filas */
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
                            <!-- Definir anchos de columna para consistencia -->
                            <colgroup>
                                <col style="width:5%"/>  <!-- Tipo -->
                                <col style="width:25%"/> <!-- Nombre -->
                                <col style="width:3%"/>  <!-- C -->
                                <col style="width:3%"/>  <!-- R -->
                                <col style="width:3%"/>  <!-- E -->
                                <col style="width:3%"/>  <!-- T -->
                                <col style="width:3%"/>  <!-- I -->
                                <col style="width:3%"/>  <!-- B -->
                                <col style="width:3%"/>  <!-- M (vacío) -->
                                <col style="width:12%"/> <!-- Embalaje -->
                                <col style="width:10%"/> <!-- Capacidad -->
                                <col style="width:10%"/> <!-- Cantidad -->
                                <col style="width:3%"/>  <!-- Si -->
                                <col style="width:3%"/>  <!-- No -->
                            </colgroup>

                            <tr>
                                <th colspan="14" class="header-table">5. Identificación de los residuos</th>
                            </tr>
                            <tr>
                                <th class="header-table">Tipo</th>
                                <th class="header-table">Nombre del residuo</th>
                                <th class="header-table" colspan="7">Clasificación</th>
                                <th class="header-table" colspan="2">Envase</th>
                                <th class="header-table">Cantidad (kg)</th>
                                <th class="header-table" colspan="2">Etiqueta</th>
                            </tr>
                            <tr>
                                <th class="header-table"></th>
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

                            <!-- Filas con datos -->
                            <t t-foreach="doc.residuo_ids" t-as="residuo">
                                <tr>
                                    <!-- Nueva Columna: TIPO -->
                                    <td class="center-text">
                                        <span t-if="residuo.residue_type" t-field="residuo.residue_type" style="text-transform: uppercase;"/>
                                    </td>
                                    
                                    <td><span t-field="residuo.nombre_residuo"/></td>
                                    
                                    <td class="center-text"><span t-if="residuo.clasificacion_corrosivo">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_reactivo">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_explosivo">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_toxico">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_inflamable">X</span></td>
                                    <td class="center-text"><span t-if="residuo.clasificacion_biologico">X</span></td>
                                    <td class="center-text"></td>
                                    
                                    <!-- Columna Embalaje: Packaging ID o Envase Tipo -->
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

                            <!-- Filas vacías para completar -->
                            <t t-set="residuos_count" t-value="len(doc.residuo_ids)"/>
                            <t t-set="min_rows" t-value="18"/>
                            <t t-set="empty_rows" t-value="max(0, min_rows - residuos_count)"/>
                            <t t-foreach="range(empty_rows)" t-as="empty_row">
                                <tr style="height: 22px;">
                                    <td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td>
                                    <td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td>
                                    <td>&#160;</td><td>&#160;</td><td>&#160;</td><td>&#160;</td>
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

                        <!-- 7. DECLARACIÓN DEL GENERADOR (recuadro único) -->
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

                        <!-- 14. DECLARACIÓN DEL TRANSPORTISTA (recuadro único) -->
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

                        <!-- 19. DECLARACIÓN DEL DESTINATARIO (recuadro único) -->
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

## ./views/manifiesto_ambiental_menus.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- Menú principal de Manifiesto Ambiental -->
    <!-- AGREGADO: web_icon="nombre_modulo,ruta_imagen" -->
    <menuitem id="menu_manifiesto_ambiental_root"
              name="Manifiestos"
              sequence="50"
              web_icon="manifiesto_ambiental,static/description/icon.png"/>
    
    <!-- Submenú para Manifiestos Actuales -->
    <menuitem id="menu_manifiesto_ambiental_manifiestos"
              name="Manifiestos Actuales"
              parent="menu_manifiesto_ambiental_root"
              action="action_manifiesto_ambiental"
              sequence="10"/>
    
    <!-- Submenú para Historial de Versiones -->
    <menuitem id="menu_manifiesto_ambiental_versions"
              name="Historial de Versiones"
              parent="menu_manifiesto_ambiental_root"
              action="action_manifiesto_ambiental_version"
              sequence="20"/>
    
    <!-- Submenú para Todas las Versiones -->
    <menuitem id="menu_manifiesto_ambiental_all_versions"
              name="Todas las Versiones"
              parent="menu_manifiesto_ambiental_root"
              action="action_manifiesto_ambiental_all_versions"
              sequence="30"/>
    
    <!-- Submenú para configuración -->
    <menuitem id="menu_manifiesto_ambiental_config"
              name="Configuración"
              parent="menu_manifiesto_ambiental_root"
              sequence="90"/>

    <menuitem id="menu_manifiesto_discrepancia"
          name="Discrepancias"
          parent="menu_manifiesto_ambiental_root"
          action="action_manifiesto_discrepancia"
          sequence="40"/>

</odoo>```

## ./views/manifiesto_ambiental_views.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <!-- Acción para Manifiesto Ambiental -->
    <record id="action_manifiesto_ambiental" model="ir.actions.act_window">
        <field name="name">Manifiestos Ambientales</field>
        <field name="res_model">manifiesto.ambiental</field>
        <field name="view_mode">list,form</field>
        <field name="domain">[('is_current_version', '=', True)]</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Crear su primer Manifiesto Ambiental
            </p>
            <p>
                Los manifiestos ambientales son documentos oficiales para el control
                de residuos peligrosos durante su transporte y disposición final.
            </p>
        </field>
    </record>

    <!-- Acción para Historial de Versiones -->
    <record id="action_manifiesto_ambiental_version" model="ir.actions.act_window">
        <field name="name">Historial de Versiones</field>
        <field name="res_model">manifiesto.ambiental.version</field>
        <field name="view_mode">list,form</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                No hay versiones guardadas
            </p>
            <p>
                Aquí se mostrará el historial de todas las versiones de los manifiestos.
            </p>
        </field>
    </record>

    <!-- Acción para todas las versiones -->
    <record id="action_manifiesto_ambiental_all_versions" model="ir.actions.act_window">
        <field name="name">Todas las Versiones de Manifiestos</field>
        <field name="res_model">manifiesto.ambiental</field>
        <field name="view_mode">list,form</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                No hay manifiestos creados
            </p>
            <p>
                Aquí se muestran todas las versiones de todos los manifiestos,
                incluyendo versiones históricas y actuales.
            </p>
        </field>
    </record>

    <!-- Lista de manifiesto.ambiental -->
    <record id="view_manifiesto_ambiental_list" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.list</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="type">list</field>
        <field name="arch" type="xml">
            <list string="Manifiestos Ambientales" default_order="sequence_number desc, version desc">
                <field name="sequence_number" string="Seq." optional="show"/>
                <field name="numero_manifiesto_display"/>
                <field name="numero_registro_ambiental"/>
                <field name="generador_nombre"/>
                <field name="transportista_nombre"/>
                <field name="destinatario_nombre"/>
                <field name="version" string="Ver."/>
                <field name="is_current_version" string="Actual" widget="boolean_toggle"/>
                <field name="tiene_documento_fisico" string="Doc. Físico" widget="boolean_toggle"/>
                <field name="generador_fecha"/>
                <field name="state" decoration-success="state == 'delivered'" decoration-info="state == 'confirmed'" decoration-warning="state == 'in_transit'"/>
            </list>
        </field>
    </record>

    <!-- Formulario de manifiesto.ambiental -->
    <record id="view_manifiesto_ambiental_form" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.form</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="type">form</field>
        <field name="arch" type="xml">
            <form string="Manifiesto Ambiental">
                <header>
                    <button name="action_recibir_residuos"
                            string="📥 Recibir Residuos"
                            type="object"
                            class="btn-primary"
                            invisible="state not in ['in_transit', 'delivered'] or not is_current_version"
                            confirm="¿Desea generar la recepción de inventario para estos residuos?"/>

                    <button name="action_confirm"
                            string="Confirmar"
                            type="object"
                            class="btn-secondary"
                            invisible="state != 'draft'"/>
                    <button name="action_in_transit"
                            string="En Tránsito"
                            type="object"
                            class="btn-warning"
                            invisible="state != 'confirmed'"/>
                    <button name="action_delivered"
                            string="Entregado"
                            type="object"
                            class="btn-success"
                            invisible="state != 'in_transit'"/>
                    <button name="action_cancel"
                            string="Cancelar"
                            type="object"
                            invisible="state not in ['draft','confirmed','in_transit']"/>
                    
                    <button name="action_remanifestar"
                            string="🔄 Remanifestar (PDF)"
                            type="object"
                            class="btn-info"
                            invisible="not is_current_version or state == 'draft'"
                            confirm="¿Está seguro de que desea crear una nueva versión? Se guardará un PDF de la versión actual."/>
                    
                    <button name="action_remanifestar_sin_pdf"
                            string="🔄 Remanifestar (Datos)"
                            type="object"
                            class="btn-secondary"
                            invisible="not is_current_version or state == 'draft'"
                            confirm="¿Está seguro de que desea crear una nueva versión? Se guardarán los datos estructurados de la versión actual."/>
                    
                    <button name="action_view_version_history"
                            string="📋 Historial"
                            type="object"
                            class="btn-secondary"/>
                    <button name="action_view_current_version"
                            string="🎯 Ver Actual"
                            type="object"
                            class="btn-secondary"
                            invisible="is_current_version"/>
                    <button name="action_view_all_versions"
                            string="📊 Todas las Versiones"
                            type="object"
                            class="btn-secondary"/>
                    
                    <field name="state"
                           widget="statusbar"
                           statusbar_visible="draft,confirmed,in_transit,delivered"/>
                </header>
                <sheet>
                    <!-- SMART BUTTONS -->
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_recepciones"
                                type="object"
                                class="oe_stat_button"
                                icon="fa-truck"
                                invisible="recepcion_count == 0">
                            <field name="recepcion_count" widget="statinfo" string="Recepciones"/>
                        </button>

                        <button name="action_view_version_history"
                                type="object"
                                class="oe_stat_button"
                                icon="fa-history">
                            <field name="version" widget="statinfo" string="Versión"/>
                        </button>
                        <button name="action_view_all_versions"
                                type="object"
                                class="oe_stat_button"
                                icon="fa-files-o">
                            <div class="o_field_widget o_stat_info">
                                <span class="o_stat_text">Todas las Versiones</span>
                            </div>
                        </button>
                        <div class="oe_stat_button" style="pointer-events: none;">
                            <div class="o_field_widget o_stat_info">
                                <span class="o_stat_value">
                                    <field name="tiene_documento_fisico" widget="boolean"/>
                                </span>
                                <span class="o_stat_text">Doc. Físico</span>
                            </div>
                        </div>
                        <!-- Secuencia interna (solo informativo) -->
                        <div class="oe_stat_button" style="pointer-events: none;">
                            <div class="o_field_widget o_stat_info">
                                <span class="o_stat_value">
                                    <field name="sequence_number" readonly="1"/>
                                </span>
                                <span class="o_stat_text">Sec. Interna</span>
                            </div>
                        </div>
                    </div>

                    <!-- Alerta de versión no actual -->
                    <div class="alert alert-warning" 
                         style="margin-bottom: 20px;" 
                         invisible="is_current_version">
                        <strong>⚠️ ATENCIÓN:</strong> Esta no es la versión actual del manifiesto. 
                        <button name="action_view_current_version" 
                                type="object" 
                                class="btn btn-link p-0"
                                style="text-decoration: underline;">
                            Ir a la versión actual →
                        </button>
                    </div>

                    <!-- Alerta de versión actual -->
                    <div class="alert alert-success" 
                         style="margin-bottom: 20px;" 
                         invisible="not is_current_version">
                        <strong>✅ VERSIÓN ACTUAL:</strong> Esta es la versión más reciente del manifiesto.
                    </div>

                    <!-- TÍTULO CON NÚMERO DE MANIFIESTO EDITABLE -->
                    <div class="oe_title">
                        <label for="numero_manifiesto" string="Núm. de Manifiesto"/>
                        <h1>
                            <field name="numero_manifiesto"
                                   readonly="not is_current_version"
                                   placeholder="Número de manifiesto..."/>
                        </h1>
                        <h3 style="color: #6c757d;" invisible="version &lt;= 1">
                            <span>Versión </span>
                            <field name="version" readonly="1"/>
                            <span invisible="not is_current_version"> (Actual)</span>
                        </h3>
                    </div>
                    
                    <group string="Información Básica" col="4">
                        <field name="numero_registro_ambiental"/>
                        <field name="pagina"/>
                        <field name="service_order_id" readonly="1"/>
                        <field name="company_id" groups="base.group_multi_company"/>
                    </group>

                    <!-- Campos de control de versiones -->
                    <group string="Control de Versiones" 
                           invisible="version &lt;= 1" 
                           col="2">
                        <field name="original_manifiesto_id" readonly="1"/>
                        <field name="created_by_remanifest" readonly="1"/>
                        <field name="change_reason" 
                               placeholder="Ingrese el motivo de esta remanifestación..."
                               invisible="not is_current_version"/>
                    </group>

                    <notebook>
                        <!-- Pestaña: Generador (4) -->
                        <page string="4. Generador">
                            <group string="Seleccionar Generador" col="1">
                                <field name="generador_id" 
                                       placeholder="Seleccione un generador..."
                                       options="{'no_create': True, 'no_create_edit': True}"
                                       readonly="not is_current_version"/>
                            </group>
                            <group string="Datos del Generador" col="2">
                                <group>
                                    <field name="generador_nombre" readonly="not is_current_version"/>
                                    <field name="generador_calle" readonly="not is_current_version"/>
                                    <field name="generador_num_ext" readonly="not is_current_version"/>
                                    <field name="generador_num_int" readonly="not is_current_version"/>
                                    <field name="generador_colonia" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="generador_municipio" readonly="not is_current_version"/>
                                    <field name="generador_estado" readonly="not is_current_version"/>
                                    <field name="generador_codigo_postal" readonly="not is_current_version"/>
                                    <field name="generador_telefono" readonly="not is_current_version"/>
                                    <field name="generador_email" readonly="not is_current_version"/>
                                </group>
                            </group>
                        </page>

                        <!-- Pestaña: Identificación de Residuos (5) -->
                        <page string="5. Identificación de Residuos">
                            <div class="alert alert-info" 
                                 style="margin-bottom: 15px;"
                                 invisible="not is_current_version">
                                <strong>📋 Instrucciones:</strong>
                                <ul style="margin: 5px 0;">
                                    <li>Seleccione productos del catálogo (preferiblemente residuos peligrosos)</li>
                                    <li>Las clasificaciones CRETIB se completarán automáticamente si el producto está configurado</li>
                                    <li>La unidad siempre será en kilogramos (kg)</li>
                                    <li>Los lotes se generarán automáticamente con el número de manifiesto</li>
                                </ul>
                            </div>
                            
                            <div class="alert alert-warning" 
                                 style="margin-bottom: 15px;"
                                 invisible="is_current_version">
                                <strong>👁️ SOLO LECTURA:</strong> Esta es una versión histórica del manifiesto. 
                                Para editar residuos, vaya a la versión actual.
                            </div>
                            
                            <field name="residuo_ids" readonly="not is_current_version">
                                <list editable="bottom" edit="is_current_version">
                                    <field name="residue_type" string="Tipo" optional="show"/>
                                    <field name="product_id" 
                                           placeholder="Seleccionar producto/residuo..."
                                           options="{'no_create': True, 'no_create_edit': True}"/>
                                    <field name="nombre_residuo"/>
                                    <field name="clasificacion_corrosivo" string="C"/>
                                    <field name="clasificacion_reactivo" string="R"/>
                                    <field name="clasificacion_explosivo" string="E"/>
                                    <field name="clasificacion_toxico" string="T"/>
                                    <field name="clasificacion_inflamable" string="I"/>
                                    <field name="clasificacion_biologico" string="B"/>
                                    <field name="clasificaciones_display" string="CRETIB" optional="hide"/>
                                    <field name="packaging_id" string="Embalaje" optional="show"/>
                                    <field name="envase_tipo" string="Envase (Legacy)" optional="hide"/>
                                    <field name="envase_capacidad"/>
                                    <field name="cantidad"/>
                                    <field name="unidad" readonly="1"/>
                                    <field name="etiqueta_si"/>
                                    <field name="etiqueta_no"/>
                                    <field name="lot_id" readonly="1"/>
                                </list>
                                <form string="Residuo">
                                    <sheet>
                                        <group>
                                            <group string="Producto/Residuo">
                                                <field name="residue_type" string="Tipo de Residuo"/>
                                                <field name="product_id" 
                                                       placeholder="Seleccionar producto/residuo..."
                                                       options="{'no_create': True, 'no_create_edit': True}"/>
                                                <field name="nombre_residuo"/>
                                            </group>
                                            <group string="Trazabilidad">
                                                <field name="lot_id" readonly="1"/>
                                            </group>
                                        </group>
                                        
                                        <group string="Clasificación CRETIB" col="3">
                                            <field name="clasificacion_corrosivo"/>
                                            <field name="clasificacion_reactivo"/>
                                            <field name="clasificacion_explosivo"/>
                                            <field name="clasificacion_toxico"/>
                                            <field name="clasificacion_inflamable"/>
                                            <field name="clasificacion_biologico"/>
                                        </group>
                                        
                                        <group string="Información del Envase" col="2">
                                            <field name="packaging_id" string="Unidad de Embalaje"/>
                                            <field name="envase_tipo"/>
                                            <field name="envase_capacidad"/>
                                        </group>
                                        
                                        <group string="Cantidad y Etiquetado" col="2">
                                            <field name="cantidad"/>
                                            <field name="unidad" readonly="1"/>
                                            <field name="etiqueta_si"/>
                                            <field name="etiqueta_no"/>
                                        </group>
                                    </sheet>
                                </form>
                            </field>
                        </page>

                        <!-- Pestaña: Documento Físico Escaneado -->
                        <page string="📄 Documento Físico" name="documento_fisico">
                            <div class="alert alert-info" style="margin-bottom: 15px;">
                                <strong>📋 Documento Físico Escaneado:</strong>
                                <p style="margin: 5px 0;">
                                    Suba aquí el manifiesto físico escaneado (papel con firmas originales, sellos, 
                                    modificaciones manuales, anotaciones, etc.) si se imprimió y procesó en físico.
                                </p>
                                <ul style="margin: 5px 0;">
                                    <li>Cada versión puede tener su propio documento físico</li>
                                    <li>Al remanifestar, el documento físico anterior se guarda en el historial</li>
                                    <li>La nueva versión inicia sin documento físico para subir uno nuevo</li>
                                </ul>
                            </div>
                            
                            <div class="alert alert-warning" 
                                style="margin-bottom: 15px;"
                                invisible="is_current_version">
                                <strong>👁️ SOLO LECTURA:</strong> Esta es una versión histórica. 
                                Para subir nuevos documentos, vaya a la versión actual.
                            </div>
                            
                            <group string="Información del Documento" col="3">
                                <field name="documento_fisico_filename" readonly="not is_current_version"/>
                                <field name="tiene_documento_fisico" readonly="1"/>
                                <div invisible="not tiene_documento_fisico" 
                                    style="color: #28a745; font-weight: bold;">
                                    ✅ Documento físico disponible
                                </div>
                                <div invisible="tiene_documento_fisico" 
                                    style="color: #6c757d; font-style: italic;">
                                    📝 Sin documento físico
                                </div>
                            </group>
                            
                            <group string="Documento Físico Escaneado" col="1">
                                <div style="width: 100%; height: 600px; border: 1px solid #ddd; background: #f9f9f9;">
                                    <field name="documento_fisico" 
                                        filename="documento_fisico_filename"
                                        readonly="not is_current_version"
                                        widget="pdf_viewer"
                                        style="width: 100%; height: 580px;"
                                        options="{'accepted_file_extensions': '.pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff', 'no_download': false}"/>
                                </div>
                            </group>
                        </page>

                        <!-- Pestaña: Instrucciones Especiales (6) -->
                        <page string="6. Instrucciones Especiales">
                            <group>
                                <field name="instrucciones_especiales" 
                                       nolabel="1" 
                                       placeholder="Instrucciones especiales e información adicional para el manejo seguro"
                                       readonly="not is_current_version"/>
                            </group>
                        </page>

                        <!-- Pestaña: Declaración del Generador (7) -->
                        <page string="7. Declaración Generador">
                            <group>
                                <field name="declaracion_generador" nolabel="1" readonly="1"/>
                            </group>
                            <group string="Firma y Sello" col="3">
                                <field name="generador_responsable_nombre" readonly="not is_current_version"/>
                                <field name="generador_fecha" readonly="not is_current_version"/>
                                <field name="generador_sello" readonly="not is_current_version"/>
                            </group>
                        </page>

                        <!-- Pestaña: Transportista (8-14) -->
                        <page string="8-14. Transportista">
                            <group string="Seleccionar Transportista" col="1">
                                <field name="transportista_id" 
                                       placeholder="Seleccione un transportista..."
                                       options="{'no_create': True, 'no_create_edit': True}"
                                       readonly="not is_current_version"/>
                            </group>
                            <group string="8. Datos del Transportista" col="2">
                                <group>
                                    <field name="transportista_nombre" readonly="not is_current_version"/>
                                    <field name="transportista_calle" readonly="not is_current_version"/>
                                    <field name="transportista_num_ext" readonly="not is_current_version"/>
                                    <field name="transportista_num_int" readonly="not is_current_version"/>
                                    <field name="transportista_colonia" readonly="not is_current_version"/>
                                    <field name="transportista_municipio" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="transportista_estado" readonly="not is_current_version"/>
                                    <field name="transportista_codigo_postal" readonly="not is_current_version"/>
                                    <field name="transportista_telefono" readonly="not is_current_version"/>
                                    <field name="transportista_email" readonly="not is_current_version"/>
                                </group>
                            </group>
                            
                            <group string="9-12. Información del Transporte" col="2">
                                <group>
                                    <field name="numero_autorizacion_semarnat" readonly="not is_current_version"/>
                                    <field name="numero_permiso_sct" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="tipo_vehiculo" readonly="not is_current_version"/>
                                    <field name="numero_placa" readonly="not is_current_version"/>
                                </group>
                            </group>
                            
                            <group string="13. Ruta">
                                <field name="ruta_empresa" 
                                       nolabel="1" 
                                       placeholder="Ruta de la empresa generadora hasta su entrega"
                                       readonly="not is_current_version"/>
                            </group>

                            <group string="14. Declaración del Transportista">
                                <field name="declaracion_transportista" nolabel="1" readonly="1"/>
                            </group>
                            <group string="Firma y Sello" col="3">
                                <field name="transportista_responsable_nombre" readonly="not is_current_version"/>
                                <field name="transportista_fecha" readonly="not is_current_version"/>
                                <field name="transportista_sello" readonly="not is_current_version"/>
                            </group>
                        </page>

                        <!-- Pestaña: Destinatario (15-19) -->
                        <page string="15-19. Destinatario">
                            <group string="Seleccionar Destinatario" col="1">
                                <field name="destinatario_id" 
                                       placeholder="Seleccione un destinatario..."
                                       options="{'no_create': True, 'no_create_edit': True}"
                                       readonly="not is_current_version"/>
                            </group>
                            <group string="15. Datos del Destinatario" col="2">
                                <group>
                                    <field name="destinatario_nombre" readonly="not is_current_version"/>
                                    <field name="destinatario_calle" readonly="not is_current_version"/>
                                    <field name="destinatario_num_ext" readonly="not is_current_version"/>
                                    <field name="destinatario_num_int" readonly="not is_current_version"/>
                                    <field name="destinatario_colonia" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="destinatario_municipio" readonly="not is_current_version"/>
                                    <field name="destinatario_estado" readonly="not is_current_version"/>
                                    <field name="destinatario_codigo_postal" readonly="not is_current_version"/>
                                    <field name="destinatario_telefono" readonly="not is_current_version"/>
                                    <field name="destinatario_email" readonly="not is_current_version"/>
                                </group>
                            </group>
                            
                            <group string="16-18. Información Adicional" col="2">
                                <group>
                                    <field name="numero_autorizacion_semarnat_destinatario" readonly="not is_current_version"/>
                                    <field name="nombre_persona_recibe" readonly="not is_current_version"/>
                                </group>
                                <group>
                                    <field name="observaciones_destinatario" 
                                           placeholder="Observaciones"
                                           readonly="not is_current_version"/>
                                </group>
                            </group>

                            <group string="19. Declaración del Destinatario">
                                <field name="declaracion_destinatario" nolabel="1" readonly="1"/>
                            </group>
                            <group string="Firma y Sello" col="3">
                                <field name="destinatario_responsable_nombre" readonly="not is_current_version"/>
                                <field name="destinatario_fecha" readonly="not is_current_version"/>
                                <field name="destinatario_sello" readonly="not is_current_version"/>
                            </group>
                        </page>

                        <!-- Pestaña: Historial de Versiones -->
                        <page string="📋 Historial de Versiones" invisible="version &lt;= 1">
                            <div class="alert alert-info" style="margin-bottom: 15px;">
                                <strong>🔍 Control de Versiones:</strong> 
                                Aquí puede ver todas las versiones guardadas de este manifiesto.
                                Cada versión incluye un archivo de respaldo (PDF o datos estructurados) y 
                                el documento físico si se subió.
                            </div>
                            
                            <field name="version_history_ids" readonly="1">
                                <list string="Historial de Versiones">
                                    <field name="version_number"/>
                                    <field name="creation_date"/>
                                    <field name="created_by"/>
                                    <field name="state_at_creation"/>
                                    <field name="tenia_documento_fisico" string="Doc. Físico"/>
                                    <field name="change_reason"/>
                                    <field name="pdf_filename"/>
                                    <button name="action_download_file" 
                                            type="object" 
                                            string="📄 PDF" 
                                            class="btn-link"/>
                                    <button name="action_view_file" 
                                            type="object" 
                                            string="👁️ Ver PDF" 
                                            class="btn-link"/>
                                    <button name="action_download_documento_fisico" 
                                            type="object" 
                                            string="📎 Doc. Físico" 
                                            class="btn-link"
                                            invisible="not tenia_documento_fisico"/>
                                    <button name="action_view_documento_fisico" 
                                            type="object" 
                                            string="👁️ Ver Doc." 
                                            class="btn-link"
                                            invisible="not tenia_documento_fisico"/>
                                </list>
                            </field>
                        </page>
                    </notebook>

                    <!-- Campos ocultos para control -->
                    <group invisible="1">
                        <field name="is_current_version"/>
                        <field name="original_manifiesto_id"/>
                        <field name="created_by_remanifest"/>
                        <field name="tiene_documento_fisico"/>
                        <field name="sequence_number"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Vista de búsqueda -->
    <record id="view_manifiesto_ambiental_search" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.search</field>
        <field name="model">manifiesto.ambiental</field>
        <field name="arch" type="xml">
            <search string="Buscar Manifiestos">
                <field name="numero_manifiesto"/>
                <field name="numero_registro_ambiental"/>
                <field name="generador_nombre"/>
                <field name="transportista_nombre"/>
                <field name="destinatario_nombre"/>
                <field name="version"/>
                <field name="change_reason"/>
                <field name="sequence_number" string="Secuencia"/>
                
                <filter string="Solo Versiones Actuales" name="current_versions" domain="[('is_current_version','=',True)]"/>
                <filter string="Solo Versiones Históricas" name="historical_versions" domain="[('is_current_version','=',False)]"/>
                <filter string="Remanifestaciones" name="remanifested" domain="[('version','>',1)]"/>
                <filter string="Con Documento Físico" name="with_physical_doc" domain="[('tiene_documento_fisico','=',True)]"/>
                <filter string="Sin Documento Físico" name="without_physical_doc" domain="[('tiene_documento_fisico','=',False)]"/>
                
                <filter string="Borrador" name="draft" domain="[('state','=','draft')]"/>
                <filter string="Confirmado" name="confirmed" domain="[('state','=','confirmed')]"/>
                <filter string="En Tránsito" name="in_transit" domain="[('state','=','in_transit')]"/>
                <filter string="Entregado" name="delivered" domain="[('state','=','delivered')]"/>
                
                <filter string="Estado" name="group_state" context="{'group_by':'state'}"/>
                <filter string="Generador" name="group_generator" context="{'group_by':'generador_nombre'}"/>
                <filter string="Número de Manifiesto" name="group_number" context="{'group_by':'numero_manifiesto'}"/>
                <filter string="Versión" name="group_version" context="{'group_by':'version'}"/>
                <filter string="Tiene Doc. Físico" name="group_physical_doc" context="{'group_by':'tiene_documento_fisico'}"/>
                <filter string="Fecha" name="group_date" context="{'group_by':'generador_fecha'}"/>
            </search>
        </field>
    </record>

    <!-- Vista de Lista para Historial de Versiones -->
    <record id="view_manifiesto_ambiental_version_list" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.version.list</field>
        <field name="model">manifiesto.ambiental.version</field>
        <field name="arch" type="xml">
            <list string="Historial de Versiones" default_order="creation_date desc">
                <field name="manifiesto_id"/>
                <field name="version_number"/>
                <field name="creation_date"/>
                <field name="created_by"/>
                <field name="state_at_creation"/>
                <field name="tenia_documento_fisico" string="Doc. Físico" widget="boolean_toggle"/>
                <field name="generador_nombre"/>
                <field name="transportista_nombre"/>
                <field name="destinatario_nombre"/>
                <field name="total_residuos"/>
                <field name="change_reason"/>
                <button name="action_download_file" 
                        type="object" 
                        string="📄 PDF" 
                        class="btn-link"/>
                <button name="action_view_file" 
                        type="object" 
                        string="👁️ Ver PDF" 
                        class="btn-link"/>
                <button name="action_download_documento_fisico" 
                        type="object" 
                        string="📎 Doc. Físico" 
                        class="btn-link"
                        invisible="not tenia_documento_fisico"/>
                <button name="action_view_documento_fisico" 
                        type="object" 
                        string="👁️ Ver Doc." 
                        class="btn-link"
                        invisible="not tenia_documento_fisico"/>
            </list>
        </field>
    </record>

    <!-- Vista de Formulario para Historial de Versiones -->
    <record id="view_manifiesto_ambiental_version_form" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.version.form</field>
        <field name="model">manifiesto.ambiental.version</field>
        <field name="arch" type="xml">
            <form string="Versión del Manifiesto" create="false" edit="false">
                <header>
                    <button name="action_download_file" 
                            string="📄 Descargar PDF/Datos" 
                            type="object" 
                            class="btn-primary"/>
                    <button name="action_view_file" 
                            string="👁️ Ver PDF/Datos" 
                            type="object" 
                            class="btn-secondary"/>
                    <button name="action_download_documento_fisico" 
                            string="📎 Descargar Doc. Físico" 
                            type="object" 
                            class="btn-success"
                            invisible="not tenia_documento_fisico"/>
                    <button name="action_view_documento_fisico" 
                            string="👁️ Ver Doc. Físico" 
                            type="object" 
                            class="btn-info"
                            invisible="not tenia_documento_fisico"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <field name="display_name"/>
                        </h1>
                    </div>

                    <group string="Información de la Versión" col="2">
                        <group>
                            <field name="manifiesto_id" readonly="1"/>
                            <field name="version_number" readonly="1"/>
                            <field name="creation_date" readonly="1"/>
                            <field name="created_by" readonly="1"/>
                        </group>
                        <group>
                            <field name="state_at_creation" readonly="1"/>
                            <field name="tenia_documento_fisico" readonly="1"/>
                            <field name="pdf_filename" readonly="1"/>
                            <field name="documento_fisico_filename_original" readonly="1" invisible="not tenia_documento_fisico"/>
                        </group>
                    </group>

                    <group string="Motivo del Cambio" col="1">
                        <field name="change_reason" readonly="1" nolabel="1"/>
                    </group>

                    <group string="Datos de Referencia" col="2">
                        <group>
                            <field name="generador_nombre" readonly="1"/>
                            <field name="transportista_nombre" readonly="1"/>
                        </group>
                        <group>
                            <field name="destinatario_nombre" readonly="1"/>
                            <field name="total_residuos" readonly="1"/>
                        </group>
                    </group>

                    <group string="Archivos de Respaldo" col="2">
                        <group string="PDF/Datos del Sistema">
                            <field name="pdf_file" filename="pdf_filename" readonly="1"/>
                        </group>
                        <group string="Documento Físico Original" invisible="not tenia_documento_fisico">
                            <field name="documento_fisico_original" filename="documento_fisico_filename_original" readonly="1"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Vista de búsqueda para Historial de Versiones -->
    <record id="view_manifiesto_ambiental_version_search" model="ir.ui.view">
        <field name="name">manifiesto.ambiental.version.search</field>
        <field name="model">manifiesto.ambiental.version</field>
        <field name="arch" type="xml">
            <search string="Buscar Versiones">
                <field name="manifiesto_id"/>
                <field name="version_number"/>
                <field name="created_by"/>
                <field name="change_reason"/>
                <field name="generador_nombre"/>
                <field name="transportista_nombre"/>
                <field name="destinatario_nombre"/>
                
                <filter string="Con Documento Físico" name="with_physical_doc" domain="[('tenia_documento_fisico','=',True)]"/>
                <filter string="Sin Documento Físico" name="without_physical_doc" domain="[('tenia_documento_fisico','=',False)]"/>
                <filter string="Última Semana" name="last_week" 
                        domain="[('creation_date', '&gt;=', (context_today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'))]"/>
                <filter string="Último Mes" name="last_month" 
                        domain="[('creation_date', '&gt;=', (context_today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))]"/>
                
                <filter string="Manifiesto" name="group_manifiesto" context="{'group_by':'manifiesto_id'}"/>
                <filter string="Creado por" name="group_user" context="{'group_by':'created_by'}"/>
                <filter string="Fecha de Creación" name="group_date" context="{'group_by':'creation_date:month'}"/>
                <filter string="Estado al Guardar" name="group_state" context="{'group_by':'state_at_creation'}"/>
                <filter string="Tenía Doc. Físico" name="group_physical" context="{'group_by':'tenia_documento_fisico'}"/>
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

