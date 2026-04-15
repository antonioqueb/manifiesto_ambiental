Aquí va la documentación técnica compacta de este módulo, basada en el código adjunto del archivo. 

## Documentación técnica — `manifiesto_ambiental`

### Objetivo

Módulo para gestión de manifiestos ambientales de residuos peligrosos en Odoo 19, con creación manual o desde orden de servicio, versionado, impresión PDF, integración con recepción de residuos y reporte de discrepancias. 

### Identificación

* **Módulo:** `manifiesto_ambiental`
* **Versión:** `19.0.2.1.0`
* **Autor:** Alphaqueb Consulting
* **Dependencias:** `mail`, `base`, `contacts`, `service_order`, `stock`, `residuo_recepcion_sai`, `fleet` 

### Modelos

**Nuevos**

* `manifiesto.ambiental`
* `manifiesto.ambiental.residuo`
* `manifiesto.ambiental.version`
* `manifiesto.discrepancia`
* `manifiesto.discrepancia.linea`

**Extendidos**

* `service.order`
* `res.partner`
* `product.template`
* `product.product`
* `residuo.recepcion` 

---

## 1. Flujo principal

### 1.1 Creación desde orden de servicio

La orden de servicio extiende `service.order` con `manifiesto_ids`, `manifiesto_count`, `action_view_manifiestos()` y `action_create_manifiesto()`. El botón **Crear Manifiesto** construye un `manifiesto.ambiental` usando datos de la OS: generador, transportista, destinatario, vehículo, chofer, ruta, observaciones y líneas de residuos. 

### 1.2 Reglas de armado del manifiesto desde OS

* **Generador base:** `generador_id` o fallback a `partner_id`
* **Razón social del campo 4:** siempre `partner_id.name` o fallback al generador
* **Fecha del servicio:** `date_start`, `scheduled_date`, `service_date`, `date_order` o fecha actual
* **Ruta:** `pickup_location_id.contact_address_complete` o `pickup_location`
* **Destinatario:** `destinatario_id` o `partner_id`
* **Placa:** prioridad a `service.order.numero_placa`; fallback a `vehicle.license_plate`
* **Tipo de vehículo:** marca + modelo del `fleet.vehicle`; fallback al `transportista.tipo_vehiculo` 

### 1.3 Construcción de residuos

Las líneas `residuo_ids` se generan desde `line_ids` de la OS.
Reglas:

* omite líneas sin `product_id`
* omite productos cuyo nombre inicie con `SERVICIO DE`
* la cantidad se toma de `weight_kg` si es mayor a 0; si no, de `product_uom_qty`
* hereda clasificación CRETIB y defaults de envase desde el producto
* `packaging_id` y `residue_type` se copian desde la línea de la OS. 

---

## 2. Modelo `manifiesto.ambiental`

### 2.1 Herencia y comportamiento

`manifiesto.ambiental` hereda `mail.thread` y `mail.activity.mixin`, por lo que tiene chatter, tracking y actividades. Usa:

* `_rec_name = 'numero_manifiesto'`
* `_order = 'numero_manifiesto desc, version desc'` 

### 2.2 Campos de control

Campos principales de control:

* `tipo_manifiesto`: `entrada` / `salida`
* `numero_registro_ambiental`
* `numero_manifiesto`
* `numero_manifiesto_display`
* `pagina`
* `service_order_id`
* `state`
* `company_id` 

### 2.3 Estados

Estados soportados:

* `draft`
* `confirmed`
* `in_transit`
* `delivered`
* `cancel`

Transiciones:

* `action_confirm()`
* `action_in_transit()`
* `action_delivered()`
* `action_cancel()` 

---

## 3. Numeración

### 3.1 Secuencia interna

El módulo maneja `sequence_number` como consecutivo interno. Se calcula por SQL con:
`SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM manifiesto_ambiental`. 

### 3.2 Generación de `numero_manifiesto`

Si no se proporciona `numero_manifiesto`, el método `create()` lo genera con `_generate_manifiesto_number()`:

* toma la razón social del generador
* elimina palabras corporativas comunes (`SA`, `CV`, etc.)
* construye iniciales significativas
* concatena fecha `DDMMYYYY`
* si ya existe un número base igual, agrega sufijo `-NN` 

### 3.3 Display del número

`numero_manifiesto_display` agrega la versión cuando `version > 1`, ejemplo:
`ABC-01012026 (v2)`. 

---

## 4. Versionado y remanifestación

### 4.1 Campos de versionado

* `version`
* `is_current_version`
* `original_manifiesto_id`
* `version_history_ids`
* `change_reason`
* `created_by_remanifest` 

### 4.2 Comportamiento

Al crear un manifiesto nuevo, si no tiene `original_manifiesto_id`, se asigna a sí mismo como manifiesto original. 

### 4.3 Remanifestación

Se soportan dos flujos:

* `action_remanifestar()`: guarda respaldo PDF en historial
* `action_remanifestar_sin_pdf()`: guarda TXT estructurado en historial

Ambos:

* solo aplican sobre la versión actual
* no permiten remanifestar en borrador
* crean una nueva versión con `state='draft'`
* preservan `numero_manifiesto` y `sequence_number`
* copian residuos a la nueva versión
* desactivan la versión anterior con `is_current_version=False` y `state='delivered'` 

### 4.4 Historial

`manifiesto.ambiental.version` almacena:

* `pdf_file` / `pdf_filename`
* `data_file` / `data_filename`
* `documento_fisico_original`
* `documento_fisico_filename_original`
* `tenia_documento_fisico`
* fecha, usuario, estado al guardar y motivo del cambio 

No se permite eliminar la versión 1. 

---

## 5. Generador, transportista y destinatario

### 5.1 Generador

El manifiesto almacena datos normalizados del generador:

* partner `generador_id`
* nombre, dirección, municipio, estado, CP, teléfono, email
* responsable
* fecha y sello. 

`_onchange_generador_id()` autocompleta estos valores desde `res.partner`. Si el manifiesto no viene de orden de servicio, también actualiza `generador_nombre` con el nombre del partner. 

### 5.2 Transportista

Se almacenan:

* `transportista_id`
* datos fiscales/de contacto
* `numero_autorizacion_semarnat`
* `numero_permiso_sct`
* `vehicle_id`
* `tipo_vehiculo`
* `numero_placa`
* `chofer_id`
* responsable, fecha y sello. 

`_onchange_transportista_id()` completa datos desde `res.partner`.
`_onchange_vehicle_id()` completa `tipo_vehiculo` y `numero_placa`. 

### 5.3 Destinatario

Se almacenan:

* `destinatario_id`
* nombre, dirección, contacto
* autorización SEMARNAT
* persona que recibe
* observaciones
* responsable, fecha y sello. 

`_onchange_destinatario_id()` llena estos valores desde `res.partner`. 

---

## 6. Residuos

### 6.1 Modelo `manifiesto.ambiental.residuo`

Cada línea de residuo contiene:

* `product_id`
* `nombre_residuo`
* `residue_type`
* clasificación CRETIB por booleanos
* `clasificaciones_display`
* `envase_tipo`
* `packaging_id`
* `envase_cantidad`
* `envase_capacidad`
* `cantidad`
* `unidad='kg'`
* `etiqueta_si`
* `etiqueta_no`
* `lot_id` readonly. 

### 6.2 Clasificación CRETIB

El campo computado `clasificaciones_display` concatena las letras activas:

* C
* R
* E
* T
* I
* B 

### 6.3 Autocompletado desde producto

`_onchange_product_id()`:

* si el producto está marcado como residuo peligroso, copia nombre, CRETIB, tipo de envase y capacidad por defecto
* si no, solo copia el nombre del producto. 

### 6.4 Etiquetado

Los campos `etiqueta_si` y `etiqueta_no` son excluyentes por onchange. 

---

## 7. Lotes

### 7.1 Generación automática

Cuando se crea una línea de residuo, `create()` ejecuta `_create_lot_for_residuo()`. Ese método:

* busca un `stock.lot` con `name = manifiesto.numero_manifiesto`
* filtra también por `product_id` y `company_id`
* si no existe, crea el lote
* si existe, reutiliza el lote encontrado
* asigna el lote a `lot_id` en la línea de residuo. 

### 7.2 Naturaleza técnica del lote

En este módulo el lote no tiene campos custom sobre `stock.lot`. La personalización está en la línea `manifiesto.ambiental.residuo`; el lote generado es un lote estándar de Odoo identificado por:

* nombre del manifiesto
* producto
* compañía. 

---

## 8. Productos de residuos peligrosos

### 8.1 Extensión de producto

`product.template` agrega:

* `es_residuo_peligroso`
* flags CRETIB
* `envase_tipo_default`
* `envase_capacidad_default` 

### 8.2 Reglas automáticas

Cuando `es_residuo_peligroso=True`:

* el `type` se fuerza a `product`
* las variantes `product.product` se ponen con `tracking='lot'` en `create()` y `write()`. 

### 8.3 Método auxiliar

`product.product.get_clasificaciones_cretib()` devuelve las letras activas del producto en formato string separado por comas. 

---

## 9. Integración con recepción

### 9.1 Extensión de `residuo.recepcion`

Se agrega `manifiesto_id` como referencia readonly al manifiesto origen. También se inserta el campo en vistas form, list y search. 

### 9.2 Acción `action_recibir_residuos()`

Solo funciona si:

* el manifiesto está en `in_transit` o `delivered`
* existen `residuo_ids`

Genera un `residuo.recepcion` con:

* `partner_id = generador_id`
* `company_id`
* `fecha_recepcion`
* líneas derivadas de cada residuo
* `lote_asignado = numero_manifiesto`
* clasificación CRETIB copiada línea por línea. 

---

## 10. Discrepancias

### 10.1 Modelo

`manifiesto.discrepancia` representa un reporte de recepción comparativa contra el manifiesto. Tiene:

* referencia a manifiesto
* datos relacionados del encabezado
* operador
* fecha de inspección
* revisó
* observaciones generales
* estado `draft/done`
* líneas `linea_ids`
* bandera `tiene_discrepancias` calculada. 

### 10.2 Nombre automático

`name` se calcula como:
`DISC-{numero_manifiesto}-{DDMMYYYY}`. 

### 10.3 Generación desde manifiesto

`action_crear_discrepancia()` crea el reporte precargando una línea por cada residuo del manifiesto con:

* nombre
* cantidad manifestada
* contenedor manifestado
* cantidad real inicial igual a la manifestada
* contenedor real inicial igual al manifestado
* `tipo_discrepancia='ok'` 

### 10.4 Cálculo de diferencia

En `manifiesto.discrepancia.linea`, `tiene_diferencia` se activa cuando:

* la diferencia absoluta de cantidad es mayor a `0.001`
* o el contenedor real y manifestado no coinciden textual y normalizadamente. 

Tipos soportados:

* `ok`
* `cantidad`
* `contenedor`
* `no_manifestado`
* `faltante`
* `ambos`
* `otro` 

---

## 11. Documento físico

### 11.1 Campos

El manifiesto soporta archivo binario físico con:

* `documento_fisico`
* `documento_fisico_filename`
* `tiene_documento_fisico` computado. 

### 11.2 Vista

La pestaña **Documento Físico** usa `widget="pdf_viewer"` y acepta:
`.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`. 

### 11.3 Relación con historial

Cuando se remanifiesta, el documento físico actual también puede guardarse dentro del historial de versiones como `documento_fisico_original`. 

---

## 12. Tracking y auditoría

### 12.1 Tracking en manifiesto

Muchos campos del manifiesto están definidos con `tracking=True`, por lo que los cambios se registran en chatter. 

### 12.2 Tracking en residuos

`manifiesto.ambiental.residuo.write()` construye un diff legible para campos rastreados y publica un mensaje en el chatter del manifiesto padre con:

* residuo afectado
* etiqueta de campo
* valor anterior
* valor nuevo. 

### 12.3 Eventos automáticos

También se publica en chatter:

* alta de residuo en `create()`
* baja de residuo en `unlink()` 

---

## 13. UI y vistas

### 13.1 Vista principal

La vista form usa clase `o_manifiesto_ambiental_form_v2` y SCSS propio registrado en `web.assets_backend`. La UI incluye:

* statusbar de estados
* botones de acción operativa
* smart buttons
* hero superior
* notebook por secciones
* chatter. 

### 13.2 Secciones del formulario

Pestañas implementadas:

* `Resumen`
* `Generador`
* `Residuos`
* `Transportista`
* `Destinatario`
* `Documento Físico`
* `Versiones` 

### 13.3 Smart buttons

Se exponen accesos rápidos a:

* historial de versiones
* discrepancias
* recepciones
* indicador de documento físico. 

---

## 14. Reportes

### 14.1 Manifiesto

`action_print_manifiesto()` selecciona el reporte correcto según `tipo_manifiesto`:

* entrada: `manifiesto_ambiental.action_report_manifiesto_ambiental`
* salida: `salida_acopio_manifiesto.action_report_manifiesto_salida` si existe. 

### 14.2 Discrepancia

`action_print_discrepancia()` imprime `manifiesto_ambiental.action_report_discrepancia`. 

---

## 15. Extensión de `res.partner`

Campos agregados:

* `street_number`
* `street_number2`
* `numero_registro_ambiental`
* `numero_autorizacion_semarnat`
* `numero_permiso_sct`
* `tipo_vehiculo`
* `numero_placa`
* `es_generador`
* `es_transportista`
* `es_destinatario` 

Las vistas agregan una pestaña **Datos Ambientales** para clasificación del partner y captura de permisos/datos ambientales. 

---

## 16. Resumen técnico corto

`manifiesto_ambiental` es un módulo de control documental y operativo para residuos peligrosos. Genera manifiestos desde OS o manualmente, normaliza actores ambientales, crea líneas de residuos con clasificación CRETIB, genera o reutiliza lotes estándar por número de manifiesto, permite recepción y discrepancias, soporta documento físico escaneado y maneja versionado formal por remanifestación. 
