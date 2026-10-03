import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import 'cita_form.dart';

class _Busqueda {
  const _Busqueda(this.profesional, this.duracion);
  final String profesional;
  final int duracion;

  @override
  bool operator ==(Object o) =>
      o is _Busqueda && o.profesional == profesional && o.duracion == duracion;
  @override
  int get hashCode => Object.hash(profesional, duracion);
}

final _huecosProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, _Busqueda>(
      (ref, b) => ref
          .watch(apiProvider)
          .lista(
            '/insights/free-slots',
            query: {
              'professional_id': b.profesional,
              'duration': b.duracion,
              'days': 14,
              'limit': 40,
            },
          ),
    );

/// Huecos libres: los próximos horarios en que el profesional tiene sitio.
/// Un toque y queda agendado ahí.
class HuecosPage extends ConsumerStatefulWidget {
  const HuecosPage({super.key});

  @override
  ConsumerState<HuecosPage> createState() => _HuecosPageState();
}

class _HuecosPageState extends ConsumerState<HuecosPage> {
  String? _profesional;
  int _duracion = 30;

  @override
  Widget build(BuildContext context) {
    final profesionales = ref.watch(profesionalesProvider);
    return PaginaModulo(
      titulo: 'Huecos libres',
      cuerpo: profesionales.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => EstadoError(
          mensaje: '$e',
          onReintentar: () => ref.invalidate(profesionalesProvider),
        ),
        data: (lista) {
          final opciones = opcionesProfesionales(lista);
          final prof = _profesional ?? opciones.firstOrNull?.$1;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: prof,
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Profesional',
                        ),
                        items: [
                          for (final o in opciones)
                            DropdownMenuItem(value: o.$1, child: Text(o.$2)),
                        ],
                        onChanged: (v) => setState(() => _profesional = v),
                      ),
                      const SizedBox(height: 12),
                      SegmentedButton<int>(
                        showSelectedIcon: false,
                        segments: const [
                          ButtonSegment(value: 30, label: Text('30 min')),
                          ButtonSegment(value: 45, label: Text('45 min')),
                          ButtonSegment(value: 60, label: Text('1 h')),
                          ButtonSegment(value: 90, label: Text('1 h 30')),
                        ],
                        selected: {_duracion},
                        onSelectionChanged: (v) =>
                            setState(() => _duracion = v.first),
                      ),
                    ],
                  ),
                ),
              ),
              if (prof == null)
                const EstadoVacio(
                  icono: Icons.badge_outlined,
                  titulo: 'Registre un profesional primero',
                )
              else
                ref
                    .watch(_huecosProvider(_Busqueda(prof, _duracion)))
                    .when(
                      loading: () => const Padding(
                        padding: EdgeInsets.all(32),
                        child: Center(child: CircularProgressIndicator()),
                      ),
                      error: (e, _) => EstadoError(mensaje: '$e'),
                      data: (huecos) {
                        if (huecos.isEmpty) {
                          return const EstadoVacio(
                            icono: Icons.event_busy,
                            titulo: 'Sin huecos en dos semanas',
                          );
                        }
                        final porDia = <String, List<DateTime>>{};
                        for (final h in huecos) {
                          final d = DateTime.parse(
                            '${h['starts_at']}',
                          ).toLocal();
                          porDia
                              .putIfAbsent(
                                DateFormat('yyyy-MM-dd').format(d),
                                () => [],
                              )
                              .add(d);
                        }
                        final formato = DateFormat("EEEE d 'de' MMMM", 'es');
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (final e in porDia.entries) ...[
                              Seccion(
                                _capitalizar(
                                  formato.format(DateTime.parse(e.key)),
                                ),
                              ),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: [
                                  for (final hora in e.value)
                                    ActionChip(
                                      avatar: const Icon(Icons.add, size: 18),
                                      label: Text(
                                        DateFormat('HH:mm').format(hora),
                                      ),
                                      onPressed: () async {
                                        if (await editarCita(
                                          context,
                                          ref,
                                          dia: hora,
                                          hora: DateFormat(
                                            'HH:mm',
                                          ).format(hora),
                                          profesionalId: prof,
                                          duracion: _duracion,
                                        )) {
                                          ref.invalidate(_huecosProvider);
                                          if (context.mounted) {
                                            avisar(context, 'Cita agendada');
                                          }
                                        }
                                      },
                                    ),
                                ],
                              ),
                            ],
                            finDeLista,
                          ],
                        );
                      },
                    ),
            ],
          );
        },
      ),
    );
  }
}

String _capitalizar(String t) =>
    t.isEmpty ? t : t[0].toUpperCase() + t.substring(1);
