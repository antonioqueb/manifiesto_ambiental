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

    # =========================================================================
    # VERSIONADO
    # =========================================================================
    version = fields.Integer(string='Versión', default=1, readonly=True)
    is_current_version = fields.Boolean(string='Versión Actual', default=True)
    original_manifiesto_id = fields.Many2one('manifiesto.ambiental', string='Manifiesto Original')
    version_history_ids = fields.One2many('manifiesto.ambiental.version', 'manifiesto_id', string='Historial de Versiones')
    change_reason = fields.Text(string='Motivo del Cambio')
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
    numero_registro_ambiental = fields.Char(string='1. Núm. de registro ambiental', required=True)
    numero_manifiesto = fields.Char(string='2. Núm. de manifiesto', required=True, copy=False)
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
    )
    # Razón social: en manifiestos creados desde OS, contiene el nombre del CLIENTE.
    # En manifiestos manuales, se autocompleta desde generador_id pero es editable.
    generador_nombre = fields.Char(
        string='4. Nombre o razón social del generador',
        required=True,
        compute='_compute_generador_nombre',
        store=True,
        readonly=False,
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
    )
    generador_responsable_nombre = fields.Char(
        string='Nombre responsable generador',
        compute='_compute_generador_responsable_nombre',
        store=True,
        readonly=False,
    )
    generador_fecha = fields.Date(string='Fecha generador', default=fields.Date.context_today)
    generador_sello = fields.Char(string='Sello generador')

    # =========================================================================
    # 5. RESIDUOS
    # =========================================================================
    residuo_ids = fields.One2many('manifiesto.ambiental.residuo', 'manifiesto_id', string='5. Identificación de los residuos')
    instrucciones_especiales = fields.Text(string='6. Instrucciones especiales')

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
    )
    transportista_nombre = fields.Char(string='8. Nombre o razón social del transportista', required=True)
    transportista_codigo_postal = fields.Char(string='Código postal')
    transportista_calle = fields.Char(string='Calle')
    transportista_num_ext = fields.Char(string='Núm. Ext.')
    transportista_num_int = fields.Char(string='Núm. Int.')
    transportista_colonia = fields.Char(string='Colonia')
    transportista_municipio = fields.Char(string='Municipio o Delegación')
    transportista_estado = fields.Char(string='Estado')
    transportista_telefono = fields.Char(string='Teléfono')
    transportista_email = fields.Char(string='Correo electrónico')

    numero_autorizacion_semarnat = fields.Char(string='9. Núm. de autorización de la SEMARNAT')
    numero_permiso_sct = fields.Char(string='10. Núm. de permiso S.C.T.')

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        help='Unidad de transporte. Rellena automáticamente tipo y placa.',
    )
    tipo_vehiculo = fields.Char(
        string='11. Tipo de vehículo',
        compute='_compute_vehicle_fields',
        store=True,
        readonly=False,
    )
    numero_placa = fields.Char(
        string='12. Núm. de placa',
        help='Editable manualmente.',
    )

    chofer_id = fields.Many2one(
        'res.partner',
        string='Chofer',
        domain="[('is_driver', '=', True)]",
    )

    transportista_responsable_id = fields.Many2one(
        'res.partner',
        string='Responsable Transportista',
        domain="['|', ('parent_id', '=', transportista_id), ('id', '=', transportista_id)]",
    )
    transportista_responsable_nombre = fields.Char(
        string='Nombre responsable transportista',
        compute='_compute_transportista_responsable_nombre',
        store=True,
        readonly=False,
    )
    transportista_fecha = fields.Date(string='Fecha transportista', default=fields.Date.context_today)
    transportista_sello = fields.Char(string='Sello transportista')

    ruta_empresa = fields.Text(string='13. Ruta de la empresa generadora hasta su entrega')
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
    )
    destinatario_nombre = fields.Char(string='15. Nombre o razón social del destinatario', required=True)
    destinatario_codigo_postal = fields.Char(string='Código postal')
    destinatario_calle = fields.Char(string='Calle')
    destinatario_num_ext = fields.Char(string='Núm. Ext.')
    destinatario_num_int = fields.Char(string='Núm. Int.')
    destinatario_colonia = fields.Char(string='Colonia')
    destinatario_municipio = fields.Char(string='Municipio o Delegación')
    destinatario_estado = fields.Char(string='Estado')
    destinatario_telefono = fields.Char(string='Teléfono')
    destinatario_email = fields.Char(string='Correo electrónico')
    numero_autorizacion_semarnat_destinatario = fields.Char(string='16. Núm. autorización de la SEMARNAT')
    nombre_persona_recibe = fields.Char(string='17. Nombre y cargo de la persona que recibe los residuos')
    observaciones_destinatario = fields.Text(string='18. Observaciones')
    declaracion_destinatario = fields.Text(
        string='19. Declaración del destinatario',
        default='Declaro bajo protesta de decir verdad que recibí los residuos peligrosos descritos en el manifiesto.',
        readonly=True,
    )
    destinatario_responsable_nombre = fields.Char(string='Nombre y firma del responsable')
    destinatario_fecha = fields.Date(string='Fecha', default=fields.Date.context_today)
    destinatario_sello = fields.Char(string='Sello')

    # =========================================================================
    # CONTROL
    # =========================================================================
    service_order_id = fields.Many2one('service.order', string='Orden de Servicio')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('in_transit', 'En Tránsito'),
        ('delivered', 'Entregado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)
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
                # Si el manifiesto viene de una OS, el nombre ya fue seteado
                # con el cliente y no debemos sobreescribirlo desde el compute.
                # Solo sobreescribimos si NO tiene OS vinculada (manifiesto manual).
                if not rec.service_order_id:
                    rec.generador_nombre = rec.generador_id.name or ''
            # Si tiene OS o no tiene generador_id, no tocamos el valor almacenado

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
            # Nombre/razón social:
            #   - Si hay OS vinculada → mantenemos el nombre del cliente (no sobreescribimos)
            #   - Si es manifiesto manual → sí tomamos el nombre del generador
            if not self.service_order_id:
                self.generador_nombre = p.name or ''
            # En todos los casos sí propagamos la dirección del generador
            self.generador_codigo_postal = p.zip or ''
            self.generador_calle = p.street or ''
            self.generador_num_ext = p.street_number or ''
            self.generador_num_int = p.street_number2 or ''
            self.generador_colonia = p.street2 or ''
            self.generador_municipio = p.city or ''
            self.generador_estado = p.state_id.name if p.state_id else ''
            self.generador_telefono = p.phone or ''
            self.generador_email = p.email or ''
            # Limpiar responsable si ya no pertenece al nuevo generador
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

            # Auto-rellenar dirección del generador si viene el ID pero no los campos
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
                # Nota: si viene service_order_id, el generador_nombre ya viene
                # seteado con el cliente en vals (desde action_create_manifiesto),
                # por lo que el bloque anterior no entra (generador_nombre ya existe).

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
            report = None
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
        texto = f"""
MANIFIESTO AMBIENTAL - VERSIÓN {data['version']}
{'='*50}
Número de Manifiesto: {data['numero_manifiesto']}
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