import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/contacto.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Comunicación con el paciente, como en la web: mensajes enviados (y
/// enviar uno nuevo), el asistente que redacta borradores y los enlaces al
/// portal donde el paciente ve sus citas y su saldo.

const _estadoMensaje = {
  'pendiente': ('Pendiente', Tonos.gris),
  'enviado': ('Enviado', Tonos.verde),
  'fallido': ('Falló', Tonos.rojo),
  'simulado': ('Simulado', Tonos.ambar),
  'cancelado': ('Cancelado', Tonos.gris),
};

const _estadoBorrador = {
  'borrador': ('Borrador', Tonos.azul),
  'aceptado': ('Aceptado', Tonos.verde),
  'descartado': ('Descartado', Tonos.gris),
};

const _tiposBorrador = <Opcion>[
  ('resumen_historia', 'Resumen de la historia clínica'),
  ('borrador_mensaje', 'Borrador de mensaje al paciente'),
  ('resumen_visita', 'Resumen de la visita para el paciente'),
];

final mensajesProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/messaging/messages', query: {'patient_id': id}),
);
final _proveedorProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/messaging/status'),
);
final plantillasMensajeProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/messaging/templates'),
);
final _iaEstadoProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/ai/status'),
);
final _borradoresProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/ai/suggestions'),
);
final _enlacesProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/portal'),
);

/// Enviar un mensaje. El texto de la plantilla se copia en la caja en vez de
/// mandarse a ciegas: quien envía lee exactamente lo que sale.
Future<void> enviarMensaje(BuildContext context, WidgetRef ref, String pacienteId) async {
  final plantillas = await cargarOAvisar(context, ref.read(plantillasMensajeProvider.future));
  if (plantillas == null || !context.mounted) return;
  final activas = plantillas.where((t) => t['is_active'] != false).toList();
  final texto = TextEditingController();
  String? elegida;
  var enviando = false;
  String? error;

  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (hoja) => StatefulBuilder(
      builder: (hoja, setState) => Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.viewInsetsOf(hoja).bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Enviar mensaje', style: estiloTitulo(20)),
            const SizedBox(height: 4),
            Text('Por WhatsApp, al número del paciente.', style: Theme.of(hoja).textTheme.bodySmall),
            if (activas.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text('PLANTILLAS', style: Theme.of(hoja).textTheme.labelSmall),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final t in activas)
                    ChoiceChip(
                      label: Text('${t['name']}'),
                      selected: elegida == t['code'],
                      onSelected: (_) => setState(() {
                        elegida = '${t['code']}';
                        texto.text = '${t['body'] ?? ''}';
                      }),
                    ),
                ],
              ),
            ],
            const SizedBox(height: 14),
            TextField(
              controller: texto,
              minLines: 4,
              maxLines: 8,
              decoration: const InputDecoration(labelText: 'Mensaje', alignLabelWithHint: true),
            ),
            if (error != null) ...[
              const SizedBox(height: 10),
              Text(error!, style: TextStyle(color: Theme.of(hoja).colorScheme.error)),
            ],
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: enviando
                  ? null
                  : () async {
                      if (texto.text.trim().isEmpty) {
                        setState(() => error = 'Escriba el mensaje.');
                        return;
                      }
                      setState(() {
                        enviando = true;
                        error = null;
                      });
                      try {
                        final r = await ref.read(apiProvider).post('/messaging/messages', {
                          'patient_id': pacienteId,
                          'channel': 'whatsapp',
                          'body': texto.text,
                        });
                        ref.invalidate(mensajesProvider(pacienteId));
                        if (hoja.mounted) Navigator.pop(hoja);
                        if (context.mounted) {
                          avisar(
                            context,
                            (r is Map && r['status'] == 'simulado')
                                ? 'Registrado como simulado: no hay proveedor de WhatsApp configurado.'
                                : 'Mensaje enviado',
                          );
                        }
                      } on ErrorApi catch (e) {
                        setState(() {
                          enviando = false;
                          error = e.mensaje;
                        });
                      }
                    },
              icon: const Icon(Icons.send_rounded, size: 18),
              label: Text(enviando ? 'Enviando…' : 'Enviar'),
            ),
          ],
        ),
      ),
    ),
  );
  texto.dispose();
}

class PestanaComunicacion extends ConsumerStatefulWidget {
  const PestanaComunicacion({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  ConsumerState<PestanaComunicacion> createState() => _PestanaComunicacionState();
}

class _PestanaComunicacionState extends ConsumerState<PestanaComunicacion> {
  String _seccion = 'mensajes';

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
      children: [
        SegmentedButton<String>(
          showSelectedIcon: false,
          segments: const [
            ButtonSegment(value: 'mensajes', label: Text('Mensajes')),
            ButtonSegment(value: 'asistente', label: Text('Asistente')),
            ButtonSegment(value: 'portal', label: Text('Portal')),
          ],
          selected: {_seccion},
          onSelectionChanged: (s) => setState(() => _seccion = s.first),
        ),
        const SizedBox(height: 14),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          child: KeyedSubtree(
            key: ValueKey(_seccion),
            child: switch (_seccion) {
              'asistente' => _Asistente(pacienteId: widget.pacienteId),
              'portal' => _Portal(pacienteId: widget.pacienteId),
              _ => _Mensajes(pacienteId: widget.pacienteId),
            },
          ),
        ),
      ],
    );
  }
}

Widget _cargando(AsyncValue<dynamic> v, VoidCallback reintentar, Widget Function() listo) => v.when(
  skipLoadingOnRefresh: true,
  loading: () => const Padding(
    padding: EdgeInsets.all(32),
    child: Center(child: CircularProgressIndicator()),
  ),
  error: (e, _) => EstadoError(mensaje: e is ErrorApi ? e.mensaje : 'Revise la conexión.', onReintentar: reintentar),
  data: (_) => listo(),
);

class _Mensajes extends ConsumerWidget {
  const _Mensajes({required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mensajes = ref.watch(mensajesProvider(pacienteId));
    final proveedor = ref.watch(_proveedorProvider).valueOrNull;
    final tinta = Theme.of(context).colorScheme.onSurface;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (proveedor != null)
          _Aviso(
            icono: proveedor['is_live'] == true ? Icons.check_circle_outline : Icons.info_outline,
            color: proveedor['is_live'] == true ? Tonos.verde : Tonos.ambar,
            texto: '${proveedor['message'] ?? ''}',
          ),
        _cargando(mensajes, () => ref.invalidate(mensajesProvider(pacienteId)), () {
          final l = mensajes.value!;
          if (l.isEmpty) {
            return const EstadoVacio(
              icono: Icons.chat_bubble_outline,
              titulo: 'Sin mensajes',
              detalle: 'Los recordatorios y mensajes enviados aparecen aquí.',
            );
          }
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final m in l)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 320),
                      child: Container(
                        padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF25D366).withValues(alpha: 0.12),
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(18),
                            topRight: Radius.circular(18),
                            bottomLeft: Radius.circular(18),
                            bottomRight: Radius.circular(5),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${m['body']}', style: const TextStyle(fontSize: 14, height: 1.4)),
                            const SizedBox(height: 6),
                            Wrap(
                              spacing: 8,
                              runSpacing: 4,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                Text(fechaHora(m['created_at']), style: TextStyle(fontSize: 11, color: tinta.withValues(alpha: 0.5))),
                                Pastilla(
                                  _estadoMensaje[m['status']]?.$1 ?? '${m['status']}',
                                  color: _estadoMensaje[m['status']]?.$2,
                                ),
                              ],
                            ),
                            if ((m['error'] ?? '').toString().isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(top: 4),
                                child: Text('${m['error']}', style: const TextStyle(fontSize: 11.5, color: Tonos.rojo)),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        }),
      ],
    );
  }
}

class _Asistente extends ConsumerWidget {
  const _Asistente({required this.pacienteId});

  final String pacienteId;

  Future<void> _generar(BuildContext context, WidgetRef ref) => mostrarFormulario(
    context,
    titulo: 'Nuevo borrador',
    subtitulo: 'El asistente redacta; usted revisa y decide. Nada se guarda en la historia por sí solo.',
    icono: Icons.auto_awesome_outlined,
    textoGuardar: 'Generar',
    campos: const [
      Campo('kind', 'Tipo', tipo: TipoCampo.seleccion, requerido: true, opciones: _tiposBorrador, inicial: 'resumen_historia'),
      Campo('request', 'Indicaciones (opcional)', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      await ref.read(apiProvider).post('/patients/$pacienteId/ai/suggestions', {
        'kind': v['kind'],
        'request': (v['request'] as String?)?.trim().isEmpty ?? true ? null : v['request'],
      });
      ref.invalidate(_borradoresProvider(pacienteId));
    },
  );

  Future<void> _contexto(BuildContext context, WidgetRef ref) async {
    final r = await cargarOAvisar(context, ref.read(apiProvider).mapa('/patients/$pacienteId/ai/context'));
    if (r == null || !context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Lo que ve el asistente'),
        content: SingleChildScrollView(child: SelectableText('${r['context']}', style: const TextStyle(fontSize: 13))),
        actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Cerrar'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final estado = ref.watch(_iaEstadoProvider).valueOrNull;
    final borradores = ref.watch(_borradoresProvider(pacienteId));
    final puede = ref.watch(authProvider).usuario?.puede('medical_history:write') ?? false;
    final disponible = estado?['is_available'] == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (estado != null)
          _Aviso(
            icono: disponible ? Icons.auto_awesome_outlined : Icons.info_outline,
            color: disponible ? Tonos.verde : Tonos.ambar,
            texto: '${estado['message'] ?? ''}',
          ),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _contexto(context, ref),
                icon: const Icon(Icons.visibility_outlined, size: 18),
                label: const Text('Ver contexto'),
              ),
            ),
            if (puede) ...[
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
                  onPressed: disponible ? () => _generar(context, ref) : null,
                  icon: const Icon(Icons.auto_awesome, size: 18),
                  label: const Text('Generar'),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 14),
        _cargando(borradores, () => ref.invalidate(_borradoresProvider(pacienteId)), () {
          final l = borradores.value!;
          if (l.isEmpty) {
            return const EstadoVacio(icono: Icons.auto_awesome_outlined, titulo: 'Sin borradores');
          }
          return Column(
            children: [
              for (final s in l)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: GlassCard(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 14, 8, 6),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  _tiposBorrador.firstWhere((t) => t.$1 == s['kind'], orElse: () => ('', '${s['kind']}')).$2,
                                  style: const TextStyle(fontWeight: FontWeight.w600),
                                ),
                              ),
                              Pastilla(_estadoBorrador[s['status']]?.$1 ?? '${s['status']}', color: _estadoBorrador[s['status']]?.$2),
                              const SizedBox(width: 8),
                            ],
                          ),
                          Text(fechaHora(s['created_at']), style: Theme.of(context).textTheme.bodySmall),
                          const SizedBox(height: 8),
                          Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: SelectableText('${s['output']}', style: const TextStyle(fontSize: 13.5, height: 1.45)),
                          ),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton.icon(
                                onPressed: () async {
                                  await Clipboard.setData(ClipboardData(text: '${s['output']}'));
                                  if (context.mounted) avisar(context, 'Copiado');
                                },
                                icon: const Icon(Icons.copy_rounded, size: 17),
                                label: const Text('Copiar'),
                              ),
                              if (puede && s['status'] == 'borrador') ...[
                                TextButton(
                                  onPressed: () async {
                                    if (await intentar(context, () => ref.read(apiProvider).post('/ai/suggestions/${s['id']}/discard', {'reason': null}), exito: 'Borrador descartado')) {
                                      ref.invalidate(_borradoresProvider(pacienteId));
                                    }
                                  },
                                  child: const Text('Descartar'),
                                ),
                                TextButton(
                                  onPressed: () async {
                                    if (await intentar(
                                      context,
                                      () => ref.read(apiProvider).post('/ai/suggestions/${s['id']}/accept'),
                                      exito: 'Aceptado. No se guardó en la historia: cópielo donde corresponda.',
                                    )) {
                                      ref.invalidate(_borradoresProvider(pacienteId));
                                    }
                                  },
                                  child: const Text('Aceptar'),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          );
        }),
      ],
    );
  }
}

class _Portal extends ConsumerWidget {
  const _Portal({required this.pacienteId});

  final String pacienteId;

  /// El enlace completo solo se ve al crearlo: el servidor guarda su huella,
  /// no el enlace, así que después no se puede volver a mostrar.
  Future<void> _crear(BuildContext context, WidgetRef ref) async {
    final r = await cargarOAvisar(context, ref.read(apiProvider).post('/patients/$pacienteId/portal'));
    ref.invalidate(_enlacesProvider(pacienteId));
    if (r is! Map || !context.mounted) return;
    final url = '${r['url']}';
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Enlace creado'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Envíelo ahora: por seguridad no se podrá volver a mostrar.'),
            const SizedBox(height: 12),
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
            onPressed: () async {
              final p = await cargarOAvisar(d, ref.read(apiProvider).mapa('/patients/$pacienteId'));
              if (p == null || !d.mounted) return;
              await abrirWhatsapp(
                d,
                '${p['whatsapp'] ?? p['phone'] ?? ''}',
                'Hola ${p['first_name'] ?? ''}, aquí puede ver sus citas y su saldo: $url',
              );
            },
            icon: const Icon(Icons.send_rounded, size: 17),
            label: const Text('WhatsApp'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final enlaces = ref.watch(_enlacesProvider(pacienteId));
    final puede = ref.watch(authProvider).usuario?.puede('patients:write') ?? false;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const _Aviso(
          icono: Icons.lock_outline,
          color: Tonos.azul,
          texto: 'El paciente ve sus próximas citas y su saldo, sin crear cuenta. El enlace vence y se puede revocar.',
        ),
        if (puede)
          FilledButton.icon(
            onPressed: () => _crear(context, ref),
            icon: const Icon(Icons.add_link_rounded, size: 19),
            label: const Text('Crear enlace al portal'),
          ),
        const SizedBox(height: 14),
        _cargando(enlaces, () => ref.invalidate(_enlacesProvider(pacienteId)), () {
          final l = enlaces.value!;
          if (l.isEmpty) return const EstadoVacio(icono: Icons.link_off_rounded, titulo: 'Sin enlaces');
          return Column(
            children: [
              for (final e in l)
                FilaTarjeta(
                  icono: e['is_active'] == true ? Icons.link_rounded : Icons.link_off_rounded,
                  colorIcono: e['is_active'] == true ? Tonos.verde : Tonos.gris,
                  titulo: 'Creado el ${fechaCorta(e['created_at'])}',
                  subtitulo: [
                    e['is_active'] == true ? 'Vence el ${fechaCorta(e['expires_at'])}' : (e['revoked_at'] != null ? 'Revocado' : 'Vencido'),
                    'Usado ${e['use_count'] ?? 0} ${(e['use_count'] ?? 0) == 1 ? 'vez' : 'veces'}',
                  ].join(' · '),
                  tachado: e['is_active'] != true,
                  derecha: puede && e['is_active'] == true
                      ? TextButton(
                          onPressed: () async {
                            if (!await confirmar(context, titulo: '¿Revocar el enlace?', mensaje: 'Dejará de funcionar de inmediato.', textoConfirmar: 'Revocar', peligro: true)) return;
                            if (!context.mounted) return;
                            if (await intentar(context, () => ref.read(apiProvider).post('/portal/${e['id']}/revoke', {'reason': 'Revocado desde la app'}), exito: 'Enlace revocado')) {
                              ref.invalidate(_enlacesProvider(pacienteId));
                            }
                          },
                          child: const Text('Revocar'),
                        )
                      : null,
                ),
            ],
          );
        }),
      ],
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.icono, required this.color, required this.texto});

  final IconData icono;
  final Color color;
  final String texto;

  @override
  Widget build(BuildContext context) {
    if (texto.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icono, size: 18, color: color),
          const SizedBox(width: 10),
          Expanded(child: Text(texto, style: const TextStyle(fontSize: 12.5, height: 1.4))),
        ],
      ),
    );
  }
}
