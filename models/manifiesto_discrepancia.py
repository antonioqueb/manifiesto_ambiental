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

    discrepancy_log_id = fields.Many2one(
        'discrepancy.log',
        string='Corrección de Inventario Vinculada',
        readonly=True,
        copy=False,
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

    def action_crear_correccion_inventario(self):
        """Solo la discrepancia de manifiesto puede generar/vincular una
        corrección de inventario: crea un `discrepancy.log` (módulo
        `gestion_discrepancias`) a partir de las líneas con diferencia real de
        cantidad, para tramitarla por el único camino que puede tocar stock."""
        self.ensure_one()
        if self.discrepancy_log_id:
            return self.action_view_discrepancy_log()

        lineas_calificadas = self.linea_ids.filtered(
            lambda l: l.tiene_diferencia and l.tipo_discrepancia in ('cantidad', 'faltante', 'ambos')
        )
        if not lineas_calificadas:
            raise UserError(_(
                'No hay líneas con diferencia de cantidad (tipo "Diferencia en Cantidad", '
                '"Material Faltante" o "Diferencia en Cantidad y Contenedor") en este reporte; '
                'no se requiere una corrección de inventario.'
            ))

        picking = self.manifiesto_id.recepcion_ids.filtered('picking_id')[:1].picking_id
        if not picking:
            raise UserError(_(
                'Este manifiesto todavía no tiene una recepción de inventario con transferencia '
                'asociada. Reciba los residuos (botón "Recibir Residuos") antes de generar la '
                'corrección de inventario.'
            ))

        log_lines = []
        for linea in lineas_calificadas:
            product = linea.residuo_manifiesto_id.product_id
            if not product:
                continue
            log_lines.append((0, 0, {
                'product_id': product.id,
                'expected_qty': linea.cantidad_manifestada,
                'received_qty': linea.cantidad_real,
                'product_uom': product.uom_id.id,
            }))
        if not log_lines:
            raise UserError(_(
                'Ninguna de las líneas con diferencia tiene un producto resoluble desde el '
                'manifiesto; no se puede generar la corrección de inventario automáticamente.'
            ))

        discrepancy_log = self.env['discrepancy.log'].create({
            'picking_id': picking.id,
            'measurement_mode': 'kg',
            'description': _('Generado desde el reporte de discrepancias de manifiesto %s.') % self.name,
            'manifiesto_discrepancia_id': self.id,
            'line_ids': log_lines,
        })
        self.discrepancy_log_id = discrepancy_log.id
        return self.action_view_discrepancy_log()

    def action_view_discrepancy_log(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'discrepancy.log',
            'view_mode': 'form',
            'res_id': self.discrepancy_log_id.id,
        }

    def action_solicitar_remanifestacion(self):
        """Solo la discrepancia de manifiesto puede disparar la remanifestación
        del manifiesto vinculado (reutiliza `action_remanifestar` tal cual)."""
        self.ensure_one()
        if not self.tiene_discrepancias:
            raise UserError(_(
                'No hay diferencias registradas en este reporte; no se requiere remanifestación.'
            ))
        if self.manifiesto_id.state == 'draft':
            raise UserError(_('El manifiesto está en borrador; la remanifestación no aplica.'))
        nota = _('Remanifestación solicitada desde el reporte de discrepancias %s.') % self.name
        manifiesto = self.manifiesto_id
        manifiesto.change_reason = (
            (manifiesto.change_reason + '\n' + nota) if manifiesto.change_reason else nota
        )
        return manifiesto.action_remanifestar()


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
            self.contenedor_real = self.contenedor_manifestado


class DiscrepancyLog(models.Model):
    """Extiende el `discrepancy.log` de `gestion_discrepancias` (dependencia de
    este módulo) únicamente con el vínculo hacia la discrepancia de manifiesto
    que lo originó, para trazabilidad en ambos sentidos."""
    _inherit = 'discrepancy.log'

    manifiesto_discrepancia_id = fields.Many2one(
        'manifiesto.discrepancia',
        string='Discrepancia de Manifiesto de Origen',
        readonly=True,
        copy=False,
    )

    def action_view_manifiesto_discrepancia(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manifiesto.discrepancia',
            'view_mode': 'form',
            'res_id': self.manifiesto_discrepancia_id.id,
        }