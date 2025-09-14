# models/service_order_extension.py - REEMPLAZAR COMPLETAMENTE en módulo manifiesto_ambiental

from odoo import models, fields

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    def action_create_manifiesto(self):
        self.ensure_one()
        
        # Determinar el generador (prioridad: generador_id, luego partner_id)
        generador = self.generador_id if self.generador_id else self.partner_id
        
        # Obtener la fecha del servicio para el número de manifiesto
        fecha_servicio = None
        if hasattr(self, 'date_start') and self.date_start:
            fecha_servicio = self.date_start
        elif hasattr(self, 'scheduled_date') and self.scheduled_date:
            fecha_servicio = self.scheduled_date
        elif hasattr(self, 'service_date') and self.service_date:
            fecha_servicio = self.service_date
        else:
            fecha_servicio = fields.Date.context_today(self)
        
        # Crear el manifiesto con datos completos pero SIN RESIDUOS AUTOMÁTICOS
        manifiesto_vals = {
            'service_order_id': self.id,
            
            # Datos del generador
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
            'generador_responsable_nombre': self.generador_responsable or '',
            'generador_fecha': fecha_servicio,  # ← IMPORTANTE: Fecha para la nomenclatura
            
            # Datos del transportista
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
            'tipo_vehiculo': self.camion or '',
            'numero_placa': self.numero_placa or '',
            'transportista_responsable_nombre': self.transportista_responsable or '',
            'transportista_fecha': fecha_servicio,
            
            # Datos del destinatario (prioridad: destinatario_id, luego partner_id)
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
            
            # Información adicional
            'nombre_persona_recibe': self.contact_name or '',
            'ruta_empresa': self.pickup_location or '',
            'instrucciones_especiales': self.observaciones or '',
        }
        
        manifiesto = self.env['manifiesto.ambiental'].create(manifiesto_vals)
        
        # NO crear residuos automáticamente - el usuario los agregará manualmente
        # desde el catálogo de productos de residuos peligrosos
        
        return {
            'name': 'Manifiesto Ambiental',
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.ambiental',
            'view_mode': 'form',
            'res_id': manifiesto.id,
            'target': 'current',
        }