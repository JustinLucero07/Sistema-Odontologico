import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../shared/contacto.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../agenda/cita_form.dart';
import '../pacientes/paciente_detalle_page.dart';

final llamarHoyProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/insights/call-today'),
);

const _motivos = <String, (IconData, Color)>{
  'ortodoncia': (Icons.sentiment_very_satisfied_outlined, Color(0xFF0E7C74)),
  'reagendar': (Icons.event_repeat, Tonos.rojo),
  'tratamiento': (Icons.assignment_late_outlined, Tonos.ambar),
  'control': (Icons.person_search_outlined, Tonos.violeta),
};

String diaCorto(DateTime d) {
  final hoy = DateTime.now();
  final manana = hoy.add(const Duration(days: 1));
  bool igual(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;
  if (igual(d, hoy)) return 'Hoy';
  if (igual(d, manana)) return 'Mañana';
  return DateFormat('EEE d', 'es').format(d);
}

String horas(int min) {
  final h = min ~/ 60;
  final m = min % 60;
  if (h == 0) return '$m min';
  return m == 0 ? '$h h' : '$h h $m min';
}

class LlamarHoy extends ConsumerStatefulWidget {
  const LlamarHoy({super.key});

  @override
  ConsumerState<LlamarHoy> createState() => _LlamarHoyState();
}

class _LlamarHoyState extends ConsumerState<LlamarHoy> {
  bool _todos = false;

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(llamarHoyProvider).valueOrNull;
    if (d == null) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final tenue = TextStyle(fontSize: 12, color: scheme.onSurface.withValues(alpha: 0.6));
    final sugerencias = (d['sugerencias'] as List).cast<Map<String, dynamic>>();
    final visibles = _todos ? sugerencias : sugerencias.take(5).toList();
    final libres = (d['minutos_libres'] as num).toInt();

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.auto_awesome, color: scheme.primary),
                  const SizedBox(width: 8),
                  const Text('A quién llamar hoy', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                libres > 0
                    ? 'Hay ${horas(libres)} libres entre hoy y el próximo día de atención. '
                          'Estos pacientes son los que más probablemente acepten y asistan.'
                    : 'La agenda está llena. Conviene contactarlos para los próximos días.',
                style: tenue,
              ),
              if (sugerencias.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text('No hay a quién llamar por ahora.', style: tenue),
                ),
              for (final s in visibles) _Fila(s: s),
              if (sugerencias.length > visibles.length)
                TextButton(
                  onPressed: () => setState(() => _todos = true),
                  child: Text('Ver los ${sugerencias.length}'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Fila extends ConsumerWidget {
  const _Fila({required this.s});
  final Map<String, dynamic> s;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final (icono, color) = _motivos[s['motivo']] ?? (Icons.person_outline, scheme.primary);
    final hueco = s['hueco'] as Map<String, dynamic>?;
    final inicio = hueco == null ? null : DateTime.parse('${hueco['starts_at']}').toLocal();
    final riesgo = s['riesgo'];
    final nombre = '${s['patient_name']}';

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(border: Border(top: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(radius: 17, backgroundColor: color.withValues(alpha: 0.15), child: Icon(icono, color: color, size: 19)),
              const SizedBox(width: 10),
              Expanded(
                child: InkWell(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => PacienteDetallePage(pacienteId: '${s['patient_id']}', nombre: nombre)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 6,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(nombre, style: const TextStyle(fontWeight: FontWeight.w700)),
                          if (riesgo == 'alto') const _Etiqueta('Suele faltar', Tonos.rojo),
                          if (riesgo == 'bajo') const _Etiqueta('Cumplido', Tonos.verde),
                        ],
                      ),
                      const SizedBox(height: 2),
                      for (final r in (s['razones'] as List))
                        Text('· $r', style: TextStyle(fontSize: 12, color: scheme.onSurface.withValues(alpha: 0.65))),
                      if (inicio != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            'Proponer: ${diaCorto(inicio)} ${DateFormat('HH:mm').format(inicio)} con ${hueco!['professional_name']}',
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: scheme.primary),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              BotonesContacto(telefono: s['phone'] as String?, whatsapp: s['whatsapp'] as String?, mensaje: '${s['mensaje']}'),
              const SizedBox(width: 6),
              OutlinedButton.icon(
                key: Key('agendar-${s['patient_id']}'),
                onPressed: () async {
                  final ok = await editarCita(
                    context,
                    ref,
                    pacienteId: '${s['patient_id']}',
                    pacienteNombre: nombre,
                    dia: inicio,
                    hora: inicio == null ? null : DateFormat('HH:mm').format(inicio),
                    profesionalId: hueco?['professional_id'] as String?,
                  );
                  if (ok) ref.invalidate(llamarHoyProvider);
                },
                icon: const Icon(Icons.event, size: 18),
                label: const Text('Agendar'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Etiqueta extends StatelessWidget {
  const _Etiqueta(this.texto, this.color);
  final String texto;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
    decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(99)),
    child: Text(texto, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: color)),
  );
}
