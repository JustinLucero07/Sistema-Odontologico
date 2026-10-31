import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/contacto.dart';
import '../../shared/widgets/firma.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

// ---------------------------------------------------------------- Documentos

final documentosProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/documents', query: {'include_archived': true}),
);
final _tiposDocumentoProvider = FutureProvider.autoDispose<List<Opcion>>((ref) async {
  final l = await ref.watch(apiProvider).lista('/documents/types');
  return [for (final t in l) ('${t['code']}', '${t['label']}')];
});

/// Sube un documento (foto de un informe, una orden, un consentimiento
/// firmado en papel…) desde la cámara o la galería.
Future<void> subirDocumento(BuildContext context, WidgetRef ref, String pacienteId, ImageSource origen) async {
  final archivo = await ImagePicker().pickImage(source: origen, maxWidth: 2400, imageQuality: 88);
  if (archivo == null || !context.mounted) return;
  final tipos = await cargarOAvisar(context, ref.read(_tiposDocumentoProvider.future));
  if (tipos == null || !context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: 'Datos del documento',
    icono: Icons.upload_file,
    textoGuardar: 'Subir',
    campos: [
      const Campo('title', 'Título', requerido: true),
      Campo('document_type', 'Tipo', tipo: TipoCampo.seleccion, requerido: true, opciones: tipos, inicial: tipos.isNotEmpty ? tipos.last.$1 : null),
      const Campo('description', 'Descripción', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      final form = await formDataDesde(archivo.path, v);
      await ref.read(apiProvider).post('/patients/$pacienteId/documents', form);
      ref.invalidate(documentosProvider(pacienteId));
    },
  );
}

void menuDocumento(BuildContext context, WidgetRef ref, String pacienteId) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (hoja) => SafeArea(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(
          leading: const Icon(Icons.photo_camera_outlined),
          title: const Text('Tomar foto del documento'),
          onTap: () { Navigator.pop(hoja); subirDocumento(context, ref, pacienteId, ImageSource.camera); },
        ),
        ListTile(
          leading: const Icon(Icons.photo_library_outlined),
          title: const Text('Elegir de la galería'),
          onTap: () { Navigator.pop(hoja); subirDocumento(context, ref, pacienteId, ImageSource.gallery); },
        ),
      ]),
    ),
  );
}

class PestanaDocumentos extends ConsumerWidget {
  const PestanaDocumentos({super.key, required this.pacienteId});

  final String pacienteId;

  Future<void> _editar(BuildContext context, WidgetRef ref, Map<String, dynamic> d) async {
    final tipos = await cargarOAvisar(context, ref.read(_tiposDocumentoProvider.future));
    if (tipos == null || !context.mounted) return;
    await mostrarFormulario(
      context,
      titulo: 'Editar documento',
      icono: Icons.edit_outlined,
      campos: [
        Campo('title', 'Título', requerido: true, inicial: d['title']),
        Campo('document_type', 'Tipo', tipo: TipoCampo.seleccion, requerido: true, opciones: tipos, inicial: d['document_type']),
        Campo('description', 'Descripción', tipo: TipoCampo.multilinea, inicial: d['description']),
      ],
      alGuardar: (v) async {
        await ref.read(apiProvider).put('/documents/${d['id']}', v);
        ref.invalidate(documentosProvider(pacienteId));
      },
    );
  }

  Future<void> _ver(BuildContext context, WidgetRef ref, Map<String, dynamic> d) async {
    if (!'${d['mime_type'] ?? ''}'.startsWith('image/')) {
      avisar(context, 'Este archivo se abre desde la web (computadora).');
      return;
    }
    final r = await cargarOAvisar(context, ref.read(apiProvider).bytes('/documents/${d['id']}/download'));
    if (r == null || !context.mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(backgroundColor: Colors.black, foregroundColor: Colors.white, title: Text('${d['title']}')),
        body: InteractiveViewer(maxScale: 6, child: Center(child: Image.memory(Uint8List.fromList(r)))),
      ),
    ));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(documentosProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(documentosProvider(pacienteId)),
        alReintentar: () => ref.invalidate(documentosProvider(pacienteId)),
        listo: (lista) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (lista.isEmpty)
              const EstadoVacio(icono: Icons.folder_open, titulo: 'Sin documentos', detalle: 'Suba informes, órdenes o papeles firmados con el botón de abajo.'),
            for (final d in lista)
              FilaTarjeta(
                icono: '${d['mime_type'] ?? ''}'.startsWith('image/') ? Icons.image_outlined : Icons.description_outlined,
                colorIcono: d['archived_at'] != null ? Tonos.gris : null,
                titulo: '${d['title']}',
                subtitulo: [
                  fechaCorta(d['created_at']),
                  '${d['document_type_label'] ?? d['document_type']}',
                  if (d['archived_at'] != null) 'Archivado',
                ].join(' · '),
                tachado: d['archived_at'] != null,
                derecha: const Icon(Icons.more_vert, size: 18),
                alTocar: () => showModalBottomSheet<void>(
                  context: context,
                  showDragHandle: true,
                  builder: (hoja) => SafeArea(
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      ListTile(leading: const Icon(Icons.visibility_outlined), title: const Text('Ver'), onTap: () { Navigator.pop(hoja); _ver(context, ref, d); }),
                      if (d['archived_at'] == null) ...[
                        ListTile(leading: const Icon(Icons.edit_outlined), title: const Text('Editar datos'), onTap: () { Navigator.pop(hoja); _editar(context, ref, d); }),
                        ListTile(
                          leading: Icon(Icons.archive_outlined, color: Theme.of(context).colorScheme.error),
                          title: const Text('Archivar'),
                          subtitle: const Text('No se borra: se puede restaurar.'),
                          onTap: () {
                            Navigator.pop(hoja);
                            anularConMotivo(context, que: 'documento (archivar)', alAnular: (m) async {
                              await api.post('/documents/${d['id']}/archive', {'reason': m});
                              ref.invalidate(documentosProvider(pacienteId));
                            });
                          },
                        ),
                      ] else
                        ListTile(
                          leading: const Icon(Icons.unarchive_outlined),
                          title: const Text('Restaurar'),
                          onTap: () async {
                            Navigator.pop(hoja);
                            if (await intentar(context, () => api.post('/documents/${d['id']}/restore'), exito: 'Documento restaurado')) {
                              ref.invalidate(documentosProvider(pacienteId));
                            }
                          },
                        ),
                    ]),
                  ),
                ),
              ),
            finDeLista,
          ],
        ),
      ),
    );
  }
}

// ----------------------------------------------------------- Consentimientos

final consentimientosProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/consents'),
);
final _plantillasProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/consents/templates'),
);
final _profesionalesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/professionals'),
);

const parentescos = ['Paciente', 'Madre', 'Padre', 'Tutor legal', 'Cónyuge', 'Hijo/a', 'Otro representante'];

/// Prepara un consentimiento desde una plantilla (o en blanco). Los datos del
/// paciente, la pieza y el profesional se escriben solos en el texto.
Future<void> nuevoConsentimiento(BuildContext context, WidgetRef ref, String pacienteId) async {
  final plantillas = await cargarOAvisar(context, ref.read(_plantillasProvider.future));
  if (plantillas == null || !context.mounted) return;
  final profesionales = await cargarOAvisar(context, ref.read(_profesionalesProvider.future)) ?? const [];
  if (!context.mounted) return;
  final activas = plantillas.where((t) => t['is_active'] != false).toList();
  final activos = profesionales.where((p) => p['is_active'] != false).toList();
  await mostrarFormulario(
    context,
    titulo: 'Nuevo consentimiento',
    subtitulo: activas.isEmpty
        ? 'Aún no hay plantillas: agréguelas desde Más → Consentimientos → Biblioteca.'
        : 'Elija una plantilla; el texto se completa con los datos del paciente.',
    icono: Icons.draw_outlined,
    campos: [
      Campo('template_id', 'Plantilla', tipo: TipoCampo.seleccion, opciones: [for (final t in activas) ('${t['id']}', '${t['name']}')]),
      Campo(
        'professional_id',
        'Profesional',
        tipo: TipoCampo.seleccion,
        opciones: [for (final p in activos) ('${p['id']}', '${p['first_name']} ${p['last_name']}')],
        inicial: activos.length == 1 ? '${activos.first['id']}' : null,
      ),
      const Campo('tooth', 'Pieza o zona (opcional)', ayuda: 'Ej. 36, 18-28, arcada superior'),
      const Campo('notes', 'Observaciones del profesional (opcional)', tipo: TipoCampo.multilinea),
      const Campo('title', 'Título (si no usa plantilla)', seccion: 'Sin plantilla'),
      const Campo('body', 'Texto (si no usa plantilla)', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      if (v['template_id'] == null && (v['title'] == null || v['body'] == null)) {
        throw ErrorApi('Elija una plantilla o escriba el título y el texto.');
      }
      await ref.read(apiProvider).post('/patients/$pacienteId/consents', v);
      ref.invalidate(consentimientosProvider(pacienteId));
    },
  );
}

Uint8List? _bytesDeDataUrl(String? dataUrl) {
  if (dataUrl == null || !dataUrl.contains(',')) return null;
  try {
    return base64Decode(dataUrl.split(',').last);
  } catch (_) {
    return null;
  }
}

/// Firma presencial en la pantalla del teléfono o la tablet.
class FirmarConsentimientoPage extends ConsumerStatefulWidget {
  const FirmarConsentimientoPage({super.key, required this.consentimiento, required this.paciente});

  final Map<String, dynamic> consentimiento;
  final Map<String, dynamic> paciente;

  @override
  ConsumerState<FirmarConsentimientoPage> createState() => _FirmarConsentimientoPageState();
}

class _FirmarConsentimientoPageState extends ConsumerState<FirmarConsentimientoPage> {
  final _firma = ControladorFirma();
  final _firmaProfesional = ControladorFirma();
  late final _nombre = TextEditingController(text: '${widget.paciente['first_name']} ${widget.paciente['last_name']}');
  late final _cedula = TextEditingController(text: '${widget.paciente['national_id'] ?? ''}');
  final _testigo = TextEditingController();
  String _parentesco = 'Paciente';
  bool _conProfesional = false;
  bool _guardando = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_nombre, _cedula, _testigo]) {
      c.dispose();
    }
    _firma.dispose();
    _firmaProfesional.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    final imagen = await _firma.comoDataUrl();
    if (imagen == null) {
      setState(() => _error = 'Falta la firma: dibújela en el recuadro.');
      return;
    }
    if (_nombre.text.trim().isEmpty) {
      setState(() => _error = 'Escriba el nombre de quien firma.');
      return;
    }
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      await ref.read(apiProvider).put('/consents/${widget.consentimiento['id']}/sign', {
        'signed_by_name': _nombre.text.trim(),
        'signer_id_number': _cedula.text.trim().isEmpty ? null : _cedula.text.trim(),
        'signer_relationship': _parentesco.toLowerCase(),
        'signature_image': imagen,
        'professional_signature_image': _conProfesional ? await _firmaProfesional.comoDataUrl() : null,
        'witness_name': _testigo.text.trim().isEmpty ? null : _testigo.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } on ErrorApi catch (e) {
      setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.consentimiento;
    return PaginaModulo(
      titulo: 'Firmar consentimiento',
      cuerpo: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text('${c['title']}', style: estiloTitulo(20)),
              const SizedBox(height: 8),
              GlassCard(
                child: ExpansionTile(
                  title: const Text('Leer el texto completo'),
                  childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  children: [Text('${c['body']}', style: const TextStyle(height: 1.5))],
                ),
              ),
              const Seccion('Quién firma'),
              DropdownButtonFormField<String>(
                initialValue: _parentesco,
                decoration: const InputDecoration(labelText: 'Relación con el paciente'),
                items: [for (final p in parentescos) DropdownMenuItem(value: p, child: Text(p))],
                onChanged: (v) => setState(() {
                  _parentesco = v ?? 'Paciente';
                  if (_parentesco != 'Paciente') {
                    _nombre.clear();
                    _cedula.clear();
                  }
                }),
              ),
              const SizedBox(height: 10),
              TextField(controller: _nombre, decoration: const InputDecoration(labelText: 'Nombre completo')),
              const SizedBox(height: 10),
              TextField(controller: _cedula, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Cédula')),
              const SizedBox(height: 10),
              TextField(controller: _testigo, decoration: const InputDecoration(labelText: 'Testigo (opcional)')),
              const Seccion('Firma'),
              PanelFirma(controlador: _firma, etiqueta: _parentesco == 'Paciente' ? 'Firma del paciente' : 'Firma del representante'),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                value: _conProfesional,
                onChanged: (v) => setState(() => _conProfesional = v),
                title: const Text('Agregar la firma del profesional'),
              ),
              if (_conProfesional) PanelFirma(controlador: _firmaProfesional, etiqueta: 'Firma del profesional'),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _guardando ? null : _guardar,
                icon: const Icon(Icons.draw_outlined),
                label: Text(_guardando ? 'Guardando…' : 'Firmar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class PestanaConsentimientos extends ConsumerWidget {
  const PestanaConsentimientos({super.key, required this.pacienteId});

  final String pacienteId;

  Future<void> _firmar(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
    final paciente = await cargarOAvisar(context, ref.read(apiProvider).mapa('/patients/$pacienteId'));
    if (paciente == null || !context.mounted) return;
    final ok = await Navigator.of(context).push<bool>(
      MaterialPageRoute(fullscreenDialog: true, builder: (_) => FirmarConsentimientoPage(consentimiento: c, paciente: paciente)),
    );
    if (ok == true) {
      ref.invalidate(consentimientosProvider(pacienteId));
      if (context.mounted) avisar(context, 'Consentimiento firmado');
    }
  }

  /// Enlace para que el paciente firme desde su propio teléfono.
  Future<void> _enviar(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
    final paciente = await cargarOAvisar(context, ref.read(apiProvider).mapa('/patients/$pacienteId'));
    if (paciente == null || !context.mounted) return;
    final tieneCorreo = '${paciente['email'] ?? ''}'.isNotEmpty;
    final porCorreo = tieneCorreo &&
        await confirmar(
          context,
          titulo: 'Enviar para firmar',
          mensaje: 'Se genera un enlace que vence en 7 días y sirve una sola vez. ¿Enviarlo también al correo ${paciente['email']}?',
          textoConfirmar: 'Sí, por correo',
        );
    if (!context.mounted) return;
    final r = await cargarOAvisar(context, ref.read(apiProvider).post('/consents/${c['id']}/sign-link', {'send_email': porCorreo}));
    if (r is! Map || !context.mounted) return;
    ref.invalidate(consentimientosProvider(pacienteId));
    final url = '${r['url']}';
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Enlace para firmar'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(r['emailed'] == true ? 'Enviado a ${paciente['email']}.' : 'Envíelo al paciente:'),
            if (r['email_error'] != null) Text('${r['email_error']}', style: const TextStyle(color: Tonos.rojo, fontSize: 13)),
            const SizedBox(height: 10),
            SelectableText(url, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
        actions: [
          TextButton.icon(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: url));
              if (d.mounted) avisar(d, 'Enlace copiado');
            },
            icon: const Icon(Icons.copy_rounded, size: 17),
            label: const Text('Copiar'),
          ),
          FilledButton.icon(
            style: FilledButton.styleFrom(minimumSize: const Size(120, 44)),
            onPressed: () => abrirWhatsapp(
              d,
              '${paciente['whatsapp'] ?? paciente['phone'] ?? ''}',
              'Hola ${paciente['first_name']}, le enviamos el consentimiento «${c['title']}» para que lo lea y lo firme desde su teléfono: $url',
            ),
            icon: const Icon(Icons.send_rounded, size: 17),
            label: const Text('WhatsApp'),
          ),
        ],
      ),
    );
  }

  Future<void> _pdf(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
    if (kIsWeb) {
      avisar(context, 'Abra el PDF desde la versión web.');
      return;
    }
    final bytes = await cargarOAvisar(context, ref.read(apiProvider).bytes('/consents/${c['id']}/pdf'));
    if (bytes == null) return;
    final dir = await getTemporaryDirectory();
    final archivo = File('${dir.path}/consentimiento-${c['id']}.pdf');
    await archivo.writeAsBytes(bytes, flush: true);
    final r = await OpenFilex.open(archivo.path, type: 'application/pdf');
    if (r.type != ResultType.done && context.mounted) avisar(context, 'No hay una aplicación para abrir PDF.');
  }

  void _detalle(BuildContext context, WidgetRef ref, Map<String, dynamic> c) {
    final api = ref.read(apiProvider);
    final firmado = c['signed_at'] != null;
    final anulado = c['voided_at'] != null;
    final firma = _bytesDeDataUrl(c['signature_image'] as String?);
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (hoja) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.88),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            children: [
              Text('${c['title']}', style: estiloTitulo(20)),
              const SizedBox(height: 10),
              Text('${c['body']}', style: const TextStyle(height: 1.5)),
              const SizedBox(height: 14),
              if (firmado) ...[
                if (firma != null)
                  Container(
                    height: 90,
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFE7E3DA))),
                    child: Image.memory(firma, fit: BoxFit.contain),
                  ),
                const SizedBox(height: 6),
                Text(
                  'Firmado por ${c['signed_by_name']}${c['signer_relationship'] != null && c['signer_relationship'] != 'paciente' ? ' (${c['signer_relationship']})' : ''} '
                  'el ${fechaHora(c['signed_at'])} · ${c['signed_channel'] == 'remoto' ? 'a distancia' : 'presencial'}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ],
              if (anulado) Text('Anulado: ${c['void_reason']}', style: const TextStyle(color: Tonos.rojo)),
              if (!firmado && !anulado && c['sign_token_expires_at'] != null)
                Text('Enlace enviado · vence ${fechaCorta(c['sign_token_expires_at'])}', style: const TextStyle(color: Tonos.gris)),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (!firmado && !anulado) ...[
                    FilledButton.icon(
                      style: FilledButton.styleFrom(minimumSize: const Size(0, 46)),
                      onPressed: () {
                        Navigator.pop(hoja);
                        _firmar(context, ref, c);
                      },
                      icon: const Icon(Icons.draw_outlined),
                      label: const Text('Firmar aquí'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () {
                        Navigator.pop(hoja);
                        _enviar(context, ref, c);
                      },
                      icon: const Icon(Icons.send_to_mobile_outlined),
                      label: const Text('Enviar para firmar'),
                    ),
                  ],
                  OutlinedButton.icon(
                    onPressed: () => _pdf(context, ref, c),
                    icon: const Icon(Icons.picture_as_pdf_outlined),
                    label: const Text('PDF'),
                  ),
                  if (!anulado)
                    TextButton.icon(
                      onPressed: () {
                        Navigator.pop(hoja);
                        anularConMotivo(context, que: firmado ? 'consentimiento (revocación)' : 'consentimiento', alAnular: (m) async {
                          await api.post('/consents/${c['id']}/void', {'reason': m});
                          ref.invalidate(consentimientosProvider(pacienteId));
                        });
                      },
                      icon: Icon(Icons.block, color: Theme.of(context).colorScheme.error),
                      label: Text(firmado ? 'Registrar revocación' : 'Anular', style: TextStyle(color: Theme.of(context).colorScheme.error)),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(consentimientosProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(consentimientosProvider(pacienteId)),
        alReintentar: () => ref.invalidate(consentimientosProvider(pacienteId)),
        listo: (lista) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (lista.isEmpty)
              const EstadoVacio(icono: Icons.draw_outlined, titulo: 'Sin consentimientos', detalle: 'Prepare uno desde una plantilla con el botón de abajo.'),
            for (final c in lista)
              FilaTarjeta(
                icono: c['signed_at'] != null ? Icons.verified_outlined : Icons.draw_outlined,
                colorIcono: c['voided_at'] != null ? Tonos.gris : (c['signed_at'] != null ? Tonos.verde : Tonos.ambar),
                titulo: '${c['title']}',
                subtitulo: [
                  fechaCorta(c['created_at']),
                  if (c['voided_at'] != null)
                    'Anulado'
                  else if (c['signed_at'] != null)
                    'Firmado por ${c['signed_by_name']}${c['signed_channel'] == 'remoto' ? ' (a distancia)' : ''}'
                  else if (c['sign_token_expires_at'] != null)
                    'Enlace enviado, pendiente de firma'
                  else
                    'Pendiente de firma',
                ].join(' · '),
                tachado: c['voided_at'] != null,
                derecha: const Icon(Icons.chevron_right),
                alTocar: () => _detalle(context, ref, c),
              ),
            finDeLista,
          ],
        ),
      ),
    );
  }
}
