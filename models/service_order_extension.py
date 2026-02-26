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

        # 6. Vehículo
        vehicle_id = self.vehicle_id.id if self.vehicle_id else False
        numero_placa_inicial = self.numero_placa or (self.vehicle_id.license_plate if self.vehicle_id else '')

        # 7. Tipo vehículo fallback si no hay vehicle_id
        tipo_vehiculo_fallback = ''
        if not vehicle_id and self.transportista_id:
            tipo_vehiculo_fallback = self.transportista_id.tipo_vehiculo or ''

        manifiesto_vals = {
            'service_order_id': self.id,

            # --- GENERADOR ---
            'generador_id': generador.id,
            'numero_registro_ambiental': generador.numero_registro_ambiental or '',
            # Campo 4: Nombre/Razón Social = CLIENTE de la OS
            'generador_nombre': nombre_razon_social,
            # Dirección = del generador seleccionado
            'generador_codigo_postal': generador.zip or '',
            'generador_calle': generador.street or '',
            'generador_num_ext': generador.street_number or '',
            'generador_num_int': generador.street_number2 or '',
            'generador_colonia': generador.street2 or '',
            'generador_municipio': generador.city or '',
            'generador_estado': generador.state_id.name if generador.state_id else '',
            'generador_telefono': generador.phone or '',
            'generador_email': generador.email or '',
            # Responsable generador
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
            'vehicle_id': vehicle_id,
            'tipo_vehiculo': tipo_vehiculo_fallback,
            'numero_placa': numero_placa_inicial,
            'chofer_id': self.chofer_id.id if self.chofer_id else False,
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
        }