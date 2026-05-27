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

    def _get_partner_nombre_en_manifiesto(self, partner):
        """
        Devuelve el nombre documental que debe copiarse al manifiesto.

        Prioridad:
        1. res.partner.nombre_en_manifiesto
        2. res.partner.name

        Es una máscara documental. No modifica el nombre real del contacto.
        """
        if not partner:
            return ''

        if hasattr(partner, '_get_nombre_en_manifiesto'):
            return partner._get_nombre_en_manifiesto()

        nombre_mascara = ''
        if 'nombre_en_manifiesto' in partner._fields:
            nombre_mascara = (partner.nombre_en_manifiesto or '').strip()

        return nombre_mascara or (partner.name or '')

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

    MANIFIESTO_OPEN_STATES = ('draft', 'confirmed', 'in_transit')

    def _get_manifiesto_fecha_servicio(self):
        self.ensure_one()
        return (
            getattr(self, 'date_start', None) or
            getattr(self, 'scheduled_date', None) or
            getattr(self, 'service_date', None) or
            getattr(self, 'date_order', None) or
            fields.Date.context_today(self)
        )

    def _prepare_manifiesto_residuo_lines(self):
        self.ensure_one()

        residuo_lines = []

        for line in self.line_ids:
            if not line.product_id:
                continue

            prod = line.product_id

            manifest_description = ''
            if 'manifest_description' in line._fields:
                manifest_description = (line.manifest_description or '').strip()

            nombre_residuo_final = (
                manifest_description or
                line.description or
                prod.name or
                'Sin descripción'
            )

            weight_kg = getattr(line, 'weight_kg', 0.0) or 0.0
            cantidad_final = weight_kg if weight_kg > 0.0 else line.product_uom_qty

            capacidad_final = getattr(line, 'capacity', False) or ''
            if not capacidad_final and hasattr(prod, 'envase_capacidad_default') and prod.envase_capacidad_default:
                capacidad_final = str(prod.envase_capacidad_default)

            residuo_lines.append((0, 0, {
                'product_id': prod.id,
                'nombre_residuo': nombre_residuo_final,
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

        return residuo_lines

    def _prepare_manifiesto_vals_from_order(self):
        self.ensure_one()

        # 1. Generador
        generador = self.generador_id if self.generador_id else self.partner_id
        nombre_razon_social = self._get_partner_nombre_en_manifiesto(generador)

        # 2. Fecha del servicio
        fecha_servicio = self._get_manifiesto_fecha_servicio()

        # 3. Ruta
        ruta = ''
        if self.pickup_location_id:
            ruta = self.pickup_location_id.contact_address_complete or self.pickup_location_id.name or ''
            ruta = ruta.replace('\n', ', ')
        elif self.pickup_location:
            ruta = self.pickup_location

        # 4. Líneas de residuos
        residuo_lines = self._prepare_manifiesto_residuo_lines()

        # 5. Destinatario
        dest = self.destinatario_id if self.destinatario_id else self.partner_id

        # 6. Vehículo y placa
        vehicle = self.vehicle_id
        vehicle_id = vehicle.id if vehicle else False
        numero_placa = self.numero_placa or (vehicle.license_plate if vehicle else '') or ''

        # 7. Tipo de vehículo
        tipo_vehiculo = ''
        if vehicle:
            brand = vehicle.model_id.brand_id.name if vehicle.model_id and vehicle.model_id.brand_id else ''
            model = vehicle.model_id.name if vehicle.model_id else ''
            tipo_vehiculo = f"{brand} {model}".strip() or vehicle.name or ''

        if not tipo_vehiculo and self.transportista_id:
            tipo_vehiculo = self.transportista_id.tipo_vehiculo or ''

        # 8. Chofer
        chofer_id = self.chofer_id.id if self.chofer_id else False

        # 9. Responsable destinatario
        # manifiesto.ambiental no tiene campo destinatario_responsable_id.
        # Por eso solo se guarda el nombre en destinatario_responsable_nombre.
        destinatario_responsable = False
        if 'destinatario_responsable_id' in self._fields:
            destinatario_responsable = self.destinatario_responsable_id

        destinatario_responsable_nombre = (
            destinatario_responsable.name
            if destinatario_responsable
            else (self.contact_name or '')
        )

        # 10. Instrucciones especiales oficiales del manifiesto
        # No se debe usar self.observaciones porque son notas internas de la OS.
        instrucciones_manifiesto = ''
        for field_name in (
            'manifiesto_instrucciones_especiales',
            'manifest_instructions',
            'special_handling_instructions',
        ):
            if field_name in self._fields:
                instrucciones_manifiesto = getattr(self, field_name) or ''
                break

        return {
            'service_order_id': self.id,

            # --- GENERADOR ---
            'generador_id': generador.id if generador else False,
            'numero_registro_ambiental': generador.numero_registro_ambiental if generador else '',
            'generador_nombre': nombre_razon_social,
            'generador_codigo_postal': generador.zip if generador else '',
            'generador_calle': generador.street if generador else '',
            'generador_num_ext': generador.street_number if generador else '',
            'generador_num_int': generador.street_number2 if generador else '',
            'generador_colonia': generador.street2 if generador else '',
            'generador_municipio': generador.city if generador else '',
            'generador_estado': generador.state_id.name if generador and generador.state_id else '',
            'generador_telefono': generador.phone if generador else '',
            'generador_email': generador.email if generador else '',
            'generador_responsable_id': self.generador_responsable_id.id if self.generador_responsable_id else False,
            'generador_responsable_nombre': self.generador_responsable_id.name if self.generador_responsable_id else '',
            'generador_fecha': fecha_servicio,

            # --- TRANSPORTISTA ---
            'transportista_id': self.transportista_id.id if self.transportista_id else False,
            'transportista_nombre': self._get_partner_nombre_en_manifiesto(self.transportista_id),
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

            # --- VEHÍCULO, PLACA, CHOFER ---
            'vehicle_id': vehicle_id,
            'tipo_vehiculo': tipo_vehiculo,
            'numero_placa': numero_placa,
            'chofer_id': chofer_id,

            # --- RESPONSABLE TRANSPORTISTA ---
            'transportista_responsable_id': self.transportista_responsable_id.id if self.transportista_responsable_id else False,
            'transportista_responsable_nombre': self.transportista_responsable_id.name if self.transportista_responsable_id else '',
            'transportista_fecha': fecha_servicio,

            # --- DESTINATARIO ---
            'destinatario_id': dest.id if dest else False,
            'destinatario_nombre': self._get_partner_nombre_en_manifiesto(dest),
            'destinatario_codigo_postal': dest.zip if dest else '',
            'destinatario_calle': dest.street if dest else '',
            'destinatario_num_ext': dest.street_number if dest else '',
            'destinatario_num_int': dest.street_number2 if dest else '',
            'destinatario_colonia': dest.street2 if dest else '',
            'destinatario_municipio': dest.city if dest else '',
            'destinatario_estado': dest.state_id.name if dest and dest.state_id else '',
            'destinatario_telefono': dest.phone if dest else '',
            'destinatario_email': dest.email if dest else '',
            'numero_autorizacion_semarnat_destinatario': dest.numero_autorizacion_semarnat if dest else '',
            'destinatario_fecha': fecha_servicio,
            'destinatario_responsable_nombre': destinatario_responsable_nombre,

            # --- OTROS ---
            'nombre_persona_recibe': self.contact_name or '',
            'ruta_empresa': ruta,
            'instrucciones_especiales': instrucciones_manifiesto,

            # --- RESIDUOS ---
            'residuo_ids': residuo_lines,
        }

    def _find_open_manifiesto(self):
        self.ensure_one()
        return self.env['manifiesto.ambiental'].search([
            ('service_order_id', '=', self.id),
            ('state', 'in', list(self.MANIFIESTO_OPEN_STATES)),
            ('is_current_version', '=', True),
        ], order='id desc', limit=1)

    def _sync_existing_manifiesto_from_order(self, manifiesto, manifiesto_vals):
        """
        Actualiza el manifiesto activo de la orden sin cambiar su folio.

        Para proteger datos operativos, las líneas se reemplazan solo si el
        manifiesto sigue en borrador o confirmado y aún no tiene recepciones.
        """
        self.ensure_one()
        manifiesto.ensure_one()

        update_vals = dict(manifiesto_vals)

        residuo_lines = update_vals.pop('residuo_ids', [])

        # Nunca sobrescribir control/documentación existente desde la orden.
        for protected_field in (
            'numero_manifiesto',
            'sequence_number',
            'state',
            'original_manifiesto_id',
            'version',
            'is_current_version',
            'created_by_remanifest',
        ):
            update_vals.pop(protected_field, None)

        if manifiesto.state in ('draft', 'confirmed') and not manifiesto.recepcion_ids:
            update_vals['residuo_ids'] = [(5, 0, 0)] + residuo_lines

        manifiesto.write(update_vals)
        return manifiesto

    def _get_manifiesto_action(self, manifiesto):
        return {
            'name': 'Manifiesto Ambiental',
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'form',
            'res_id': manifiesto.id,
            'target': 'current',
        }

    def action_create_manifiesto(self):
        self.ensure_one()

        manifiesto_vals = self._prepare_manifiesto_vals_from_order()

        manifiesto = self._find_open_manifiesto()
        if manifiesto:
            manifiesto = self._sync_existing_manifiesto_from_order(
                manifiesto,
                manifiesto_vals,
            )
        else:
            manifiesto = self.env['manifiesto.ambiental'].create(manifiesto_vals)

        return self._get_manifiesto_action(manifiesto)
