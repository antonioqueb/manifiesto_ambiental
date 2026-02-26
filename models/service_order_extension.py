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
            'tipo_vehiculo': self.vehicle_id.name or (self.transportista_id.tipo_vehiculo if self.transportista_id else ''),
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
        }