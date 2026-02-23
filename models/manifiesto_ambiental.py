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
        """
        Obtiene el siguiente número de secuencia global.
        Usa MAX directo en BD para evitar duplicados en concurrencia.
        """
        self.env.cr.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM manifiesto_ambiental"
        )
        return self.env.cr.fetchone()[0]

    def _generate_manifiesto_number(self, generador_partner, fecha_servicio=None, sequence_num=None):
        """
        Genera el número de manifiesto con nomenclatura personalizada:
        Iniciales de Razón Social + Fecha (DDMMAAAA)
        Ejemplo: DENSO MEXICO, S.A. DE C.V. -> DM-28042025

        sequence_num se usa como sufijo en caso de colisión de nombre+fecha.
        """
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
        
        # Verificar colisión de nombre visible
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
        """Computa si la versión tiene documento físico"""
        for record in self:
            record.tiene_documento_fisico = bool(record.documento_fisico)

    @api.depends('recepcion_ids')
    def _compute_recepcion_count(self):
        """Computa el número de recepciones vinculadas"""
        for rec in self:
            rec.recepcion_count = len(rec.recepcion_ids)

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
    # CREATE - LÓGICA CENTRAL DE SECUENCIA
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Solo asignar secuencia y número en manifiestos nuevos (no remanifestaciones)
            if not vals.get('created_by_remanifest'):
                # 1. Siempre asignar el siguiente sequence_number interno
                next_seq = self._get_next_sequence_number()
                vals['sequence_number'] = next_seq

                # 2. Solo generar numero_manifiesto si no viene ya en vals
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
            
            # Auto-llenar datos del generador si se proporciona generador_id
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
        """Genera Recepción de Residuos propagando CRETIB desde el manifiesto."""
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
        """Abre la vista de recepciones asociadas"""
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
    # REMANIFESTACIÓN
    # =========================================================================

    def action_remanifestar(self):
        """
        Acción para remanifestar con PDF
        """
        self.ensure_one()
        
        if not self.is_current_version:
            raise UserError("Solo se puede remanifestar la versión actual del manifiesto.")
        
        if self.state == 'draft':
            raise UserError("No se puede remanifestar un manifiesto en estado borrador. Debe confirmarlo primero.")
        
        try:
            # 1. Generar y guardar PDF de la versión actual
            pdf_data = self._generate_current_pdf_corregido()
            
            # 2. Guardar la versión actual en el historial con PDF
            self._save_version_to_history(pdf_data)
            
            # 3. Crear nueva versión basada en la actual
            new_version = self._create_new_version()
            
            # 4. Desactivar versión actual anterior
            self._deactivate_current_version()
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manifiesto.ambiental',
                'view_mode': 'form',
                'res_id': new_version.id,
                'target': 'current',
                'context': {
                    'default_change_reason': 'Nueva versión creada por remanifestación'
                }
            }
            
        except Exception as e:
            _logger.error(f"Error en remanifestación del manifiesto {self.numero_manifiesto}: {str(e)}")
            raise UserError(f"Error durante la remanifestación: {str(e)}")

    def action_remanifestar_sin_pdf(self):
        """
        Acción para remanifestar SIN generar PDF
        """
        self.ensure_one()
        
        if not self.is_current_version:
            raise UserError("Solo se puede remanifestar la versión actual del manifiesto.")
        
        if self.state == 'draft':
            raise UserError("No se puede remanifestar un manifiesto en estado borrador. Debe confirmarlo primero.")
        
        try:
            # 1. Generar datos estructurados de la versión actual
            data_estructurados = self._generate_structured_data()
            
            # 2. Guardar la versión actual en el historial con datos estructurados
            self._save_version_to_history_with_data(data_estructurados)
            
            # 3. Crear nueva versión basada en la actual
            new_version = self._create_new_version()
            
            # 4. Desactivar versión actual anterior
            self._deactivate_current_version()
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'manifiesto.ambiental',
                'view_mode': 'form',
                'res_id': new_version.id,
                'target': 'current',
                'context': {
                    'default_change_reason': 'Nueva versión creada por remanifestación (sin PDF)'
                }
            }
            
        except Exception as e:
            _logger.error(f"Error en remanifestación del manifiesto {self.numero_manifiesto}: {str(e)}")
            raise UserError(f"Error durante la remanifestación: {str(e)}")

    def _generate_current_pdf_corregido(self):
        """
        Genera el PDF de la versión actual - VERSIÓN CORREGIDA PARA ODOO 18/19
        """
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
        """
        Valida que todos los datos requeridos estén presentes antes de generar PDF
        """
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
        """
        Genera datos estructurados del manifiesto para guardar como texto
        """
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
            residuo_data = {
                'nombre': residuo.nombre_residuo or '',
                'cantidad': residuo.cantidad,
                'unidad': 'kg',
                'clasificaciones': residuo.clasificaciones_display or '',
                'envase': {
                    'tipo': residuo.envase_tipo or '',
                    'capacidad': residuo.envase_capacidad or '',
                },
                'etiquetado': 'Sí' if residuo.etiqueta_si else 'No',
            }
            data['residuos'].append(residuo_data)
        
        return data

    def _save_version_to_history_with_data(self, data_estructurados):
        """
        Guarda la versión actual en el historial con datos estructurados
        """
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
        """
        Formatea los datos estructurados como texto legible
        """
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
        """
        Guarda la versión actual en el historial con su PDF
        """
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
        """
        Crea una nueva versión del manifiesto basada en la actual
        """
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
        """
        Prepara los datos para crear una nueva versión
        """
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
            # Mantener el mismo numero_manifiesto y sequence_number del original
            'numero_manifiesto': self.numero_manifiesto,
            'sequence_number': self.sequence_number,
        })
        
        return new_vals

    def _copy_residuos_to_version(self, new_version):
        """
        Copia los residuos a la nueva versión del manifiesto
        """
        try:
            for residuo in self.residuo_ids:
                residuo_vals = {
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
                }
                self.env['manifiesto.ambiental.residuo'].create(residuo_vals)
                
        except Exception as e:
            _logger.error(f"Error copiando residuos: {str(e)}")
            raise UserError(f"Error al copiar los residuos: {str(e)}")

    def _deactivate_current_version(self):
        """
        Desactiva la versión actual para que no sea la principal
        """
        try:
            self.write({
                'is_current_version': False,
                'state': 'delivered'
            })
        except Exception as e:
            _logger.error(f"Error desactivando versión actual: {str(e)}")
            raise UserError(f"Error al desactivar la versión actual: {str(e)}")

    # =========================================================================
    # NAVEGACIÓN DE VERSIONES
    # =========================================================================

    def action_view_version_history(self):
        """Ver el historial de versiones"""
        return {
            'name': f'Historial de Versiones - {self.numero_manifiesto}',
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.ambiental.version',
            'view_mode': 'list,form',
            'domain': [('manifiesto_id', '=', self.original_manifiesto_id.id)],
            'context': {'default_manifiesto_id': self.original_manifiesto_id.id},
        }

    def action_view_current_version(self):
        """Navegar a la versión actual del manifiesto"""
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
        """Ver todas las versiones del manifiesto"""
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
        """Autocompletar campos basados en el producto seleccionado"""
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
        """Crear automáticamente el lote al crear el residuo"""
        records = super().create(vals_list)
        records._create_lot_for_residuo()
        return records

    def _create_lot_for_residuo(self):
        """Crear lote automáticamente usando el número de manifiesto"""
        for record in self:
            if record.product_id and record.manifiesto_id.numero_manifiesto:
                existing_lot = self.env['stock.lot'].search([
                    ('name', '=', record.manifiesto_id.numero_manifiesto),
                    ('product_id', '=', record.product_id.id),
                    ('company_id', '=', record.manifiesto_id.company_id.id)
                ], limit=1)
                
                if not existing_lot:
                    lot_vals = {
                        'name': record.manifiesto_id.numero_manifiesto,
                        'product_id': record.product_id.id,
                        'company_id': record.manifiesto_id.company_id.id,
                    }
                    lot = self.env['stock.lot'].create(lot_vals)
                    record.lot_id = lot.id
                else:
                    record.lot_id = existing_lot.id


class ManifiestoAmbientalVersion(models.Model):
    """
    Modelo para almacenar el historial de versiones de los manifiestos
    """
    _name = 'manifiesto.ambiental.version'
    _description = 'Historial de Versiones del Manifiesto Ambiental'
    _order = 'creation_date desc, version_number desc'
    _rec_name = 'display_name'

    manifiesto_id = fields.Many2one(
        'manifiesto.ambiental',
        string='Manifiesto Original',
        required=True,
        ondelete='cascade',
        help='Referencia al manifiesto original (versión 1)'
    )
    
    version_number = fields.Integer(
        string='Número de Versión',
        required=True,
        help='Número de versión guardada'
    )
    
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True,
        help='Nombre de visualización de la versión'
    )
    
    # Archivos PDF
    pdf_file = fields.Binary(
        string='Archivo PDF',
        help='PDF de esta versión del manifiesto'
    )
    
    pdf_filename = fields.Char(
        string='Nombre del PDF',
        help='Nombre del archivo PDF'
    )
    
    # Archivos de datos estructurados
    data_file = fields.Binary(
        string='Archivo de Datos',
        help='Datos estructurados de esta versión del manifiesto'
    )
    
    data_filename = fields.Char(
        string='Nombre de Datos',
        help='Nombre del archivo de datos estructurados'
    )
    
    # Documento físico histórico
    documento_fisico_original = fields.Binary(
        string='Documento Físico Original',
        help='Documento físico escaneado que tenía esta versión del manifiesto'
    )
    
    documento_fisico_filename_original = fields.Char(
        string='Nombre del Documento Físico Original',
        help='Nombre del archivo del documento físico de esta versión'
    )
    
    tenia_documento_fisico = fields.Boolean(
        string='Tenía Documento Físico',
        help='Indica si esta versión histórica tenía un documento físico escaneado'
    )
    
    # Metadatos
    creation_date = fields.Datetime(
        string='Fecha de Creación',
        required=True,
        default=fields.Datetime.now,
        help='Fecha y hora en que se guardó esta versión'
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Creado por',
        required=True,
        default=lambda self: self.env.user,
        help='Usuario que creó esta versión'
    )
    
    state_at_creation = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('in_transit', 'En Tránsito'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado'),
    ], string='Estado al Guardar', help='Estado del manifiesto cuando se guardó esta versión')
    
    change_reason = fields.Text(
        string='Motivo del Cambio',
        help='Razón por la cual se guardó esta versión'
    )
    
    # Datos de referencia
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
        """
        Determinar qué tipo de archivo tiene disponible esta versión
        """
        if self.pdf_file and self.pdf_filename:
            return {
                'has_file': True,
                'file_type': 'pdf',
                'field_name': 'pdf_file',
                'filename_field': 'pdf_filename',
                'filename': self.pdf_filename,
                'display_name': 'PDF'
            }
        elif self.data_file and self.data_filename:
            return {
                'has_file': True,
                'file_type': 'data',
                'field_name': 'data_file',
                'filename_field': 'data_filename', 
                'filename': self.data_filename,
                'display_name': 'Datos'
            }
        else:
            return {
                'has_file': False,
                'file_type': None,
                'field_name': None,
                'filename_field': None,
                'filename': None,
                'display_name': 'Sin archivo'
            }

    def action_download_file(self):
        """
        Acción para descargar el archivo de esta versión
        """
        file_info = self.get_available_file_info()
        
        if not file_info['has_file']:
            raise UserError("No hay archivo disponible para esta versión.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/{file_info["field_name"]}/{file_info["filename"]}?download=true',
            'target': 'self',
        }

    def action_view_file(self):
        """
        Acción para visualizar el archivo de esta versión
        """
        file_info = self.get_available_file_info()
        
        if not file_info['has_file']:
            raise UserError("No hay archivo disponible para esta versión.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/{file_info["field_name"]}/{file_info["filename"]}',
            'target': 'new',
        }

    def action_download_documento_fisico(self):
        """
        Acción para descargar el documento físico original de esta versión
        """
        if not self.documento_fisico_original:
            raise UserError("Esta versión no tiene documento físico disponible.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/documento_fisico_original/{self.documento_fisico_filename_original}?download=true',
            'target': 'self',
        }

    def action_view_documento_fisico(self):
        """
        Acción para visualizar el documento físico original de esta versión
        """
        if not self.documento_fisico_original:
            raise UserError("Esta versión no tiene documento físico disponible.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/documento_fisico_original/{self.documento_fisico_filename_original}',
            'target': 'new',
        }

    def debug_version_files(self):
        """
        Método para debugear qué archivos tiene cada versión
        """
        _logger.info(f"=== DEBUG VERSIÓN {self.version_number} ===")
        _logger.info(f"pdf_file: {'SÍ' if self.pdf_file else 'NO'}")
        _logger.info(f"pdf_filename: {self.pdf_filename}")
        _logger.info(f"data_file: {'SÍ' if self.data_file else 'NO'}")
        _logger.info(f"data_filename: {self.data_filename}")
        _logger.info(f"documento_fisico_original: {'SÍ' if self.documento_fisico_original else 'NO'}")
        _logger.info("=====================================")
        
        return self.get_available_file_info()

    def unlink(self):
        """
        Prevenir eliminación accidental de versiones históricas
        """
        if any(version.version_number == 1 for version in self):
            raise UserError("No se puede eliminar la versión 1 (original) del manifiesto.")
        return super().unlink()