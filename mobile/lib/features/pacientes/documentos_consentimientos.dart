import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
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

/// Prepara un consentimiento desde una plantilla (o en blanco).
Future<void> nuevoConsentimiento(BuildContext context, WidgetRef ref, String pacienteId) async {
  final plantillas = await cargarOAvisar(context, ref.read(_plantillasProvider.future));
  if (plantillas == null || !context.mounted) return;
  final activas = plantillas.where((t) => t['is_active'] != false).toList();
  await mostrarFormulario(
    context,
    titulo: 'Nuevo consentimiento',
    subtitulo: 'Elija una plantilla; el texto se copia y luego el paciente firma.',
    icono: Icons.draw_outlined,
    campos: [
      Campo('template_id', 'Plantilla', tipo: TipoCampo.seleccion, opciones: [for (final t in activas) ('${t['id']}', '${t['name']}')]),
      const Campo('title', 'Título (si no usa plantilla)'),
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

class PestanaConsentimientos extends ConsumerWidget {
  const PestanaConsentimientos({super.key, required this.pacienteId});

  final String pacienteId;

  void _detalle(BuildContext context, WidgetRef ref, Map<String, dynamic> c) {
    final api = ref.read(apiProvider);
    final firmado = c['signed_at'] != null;
    final anulado = c['voided_at'] != null;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (hoja) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.85),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            children: [
              Text('${c['title']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
              const SizedBox(height: 10),
              Text('${c['body']}', style: const TextStyle(height: 1.5)),
              const SizedBox(height: 14),
              if (firmado) Text('Firmado por ${c['signed_by_name']} el ${fechaHora(c['signed_at'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
              if (anulado) Text('Anulado: ${c['void_reason']}', style: const TextStyle(color: Tonos.rojo)),
              const SizedBox(height: 12),
              if (!firmado && !anulado)
                FilledButton.icon(
                  onPressed: () {
                    Navigator.pop(hoja);
                    mostrarFormulario(
                      context,
                      titulo: 'Registrar firma',
                      subtitulo: 'El paciente (o su representante) leyó y firmó el documento.',
                      icono: Icons.draw_outlined,
                      textoGuardar: 'Firmado',
                      campos: const [
                        Campo('signed_by_name', 'Nombre de quien firma', requerido: true),
                        Campo('signature_notes', 'Notas (ej. firmado en papel, archivado en carpeta)', tipo: TipoCampo.multilinea),
                      ],
                      alGuardar: (v) async {
                        await api.put('/consents/${c['id']}/sign', v);
                        ref.invalidate(consentimientosProvider(pacienteId));
                      },
                    );
                  },
                  icon: const Icon(Icons.draw_outlined),
                  label: const Text('Registrar firma'),
                ),
              if (!anulado)
                TextButton.icon(
                  onPressed: () {
                    Navigator.pop(hoja);
                    anularConMotivo(context, que: 'consentimiento', alAnular: (m) async {
                      await api.post('/consents/${c['id']}/void', {'reason': m});
                      ref.invalidate(consentimientosProvider(pacienteId));
                    });
                  },
                  icon: Icon(Icons.block, color: Theme.of(context).colorScheme.error),
                  label: Text('Anular', style: TextStyle(color: Theme.of(context).colorScheme.error)),
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
                  if (c['voided_at'] != null) 'Anulado' else if (c['signed_at'] != null) 'Firmado por ${c['signed_by_name']}' else 'Pendiente de firma',
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
