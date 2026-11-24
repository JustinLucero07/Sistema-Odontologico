import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../pacientes/paciente_detalle_page.dart';

final especialidadProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((ref) async {
  final r = await ref.watch(apiProvider).get('/dashboard/specialty');
  return r is Map<String, dynamic> ? r : null;
});

const temasEspecialidad = <String, (Color, IconData, String)>{
  'ortodoncia': (Color(0xFF4F46E5), Icons.sentiment_very_satisfied_outlined, 'ORTODONCIA'),
  'estetica': (Color(0xFFD0457E), Icons.auto_awesome_outlined, 'ESTÉTICA DENTAL'),
  'pediatria': (Color(0xFFE0614A), Icons.child_care_outlined, 'ODONTOPEDIATRÍA'),
};

const _iconos = <String, IconData>{
  'event_available': Icons.event_available,
  'date_range': Icons.date_range,
  'schedule': Icons.schedule,
  'sentiment_very_satisfied': Icons.sentiment_very_satisfied_outlined,
  'request_quote': Icons.request_quote_outlined,
  'auto_awesome': Icons.auto_awesome_outlined,
  'compare': Icons.compare_outlined,
  'share': Icons.share_outlined,
  'child_care': Icons.child_care_outlined,
  'person_search': Icons.person_search_outlined,
  'mood': Icons.mood,
  'cake': Icons.cake_outlined,
  'groups': Icons.groups_outlined,
};

class EspecialidadPanel extends ConsumerWidget {
  const EspecialidadPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final d = ref.watch(especialidadProvider).valueOrNull;
    if (d == null) return const SizedBox.shrink();
    final tema = temasEspecialidad['${d['foco']}'];
    if (tema == null) return const SizedBox.shrink();
    final (color, icono, kicker) = tema;
    final scheme = Theme.of(context).colorScheme;
    final tenue = scheme.onSurface.withValues(alpha: 0.6);
    final cifras = (d['cifras'] as List).cast<Map<String, dynamic>>();
    final lista = (d['lista'] as List).cast<Map<String, dynamic>>();

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: GlassCard(
        child: Container(
          decoration: BoxDecoration(border: Border(top: BorderSide(color: color, width: 3))),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
                    child: Icon(icono, color: color),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(kicker, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: 1.1, color: color)),
                        Text('${d['titulo']}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text('${d['subtitulo']}', style: TextStyle(fontSize: 12, color: tenue)),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 2.1,
                children: [
                  for (final c in cifras)
                    Container(
                      padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                      decoration: BoxDecoration(
                        color: scheme.surfaceContainerHighest.withValues(alpha: 0.6),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        children: [
                          Icon(_iconos[c['icono']] ?? Icons.circle_outlined, size: 20, color: c['tono'] == 'alerta' ? Tonos.rojo : color),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${c['valor']}',
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.w800,
                                    height: 1.1,
                                    color: c['tono'] == 'alerta' ? Tonos.rojo : null,
                                  ),
                                ),
                                Text(
                                  '${c['etiqueta']}',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(fontSize: 10.5, height: 1.15, color: tenue),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
              if (d['lista_titulo'] != null) ...[
                const SizedBox(height: 12),
                Text('${d['lista_titulo']}', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: tenue)),
                if (lista.isEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text('${d['lista_vacia'] ?? ''}', style: TextStyle(fontSize: 12.5, color: tenue)),
                  ),
                for (final f in lista.take(5))
                  InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => PacienteDetallePage(pacienteId: '${f['patient_id']}', nombre: '${f['nombre']}'),
                      ),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 7),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 46,
                            child: Text(
                              f['hora'] == null ? '' : DateFormat('HH:mm').format(DateTime.parse('${f['hora']}').toLocal()),
                              style: TextStyle(fontWeight: FontWeight.w800, color: color),
                            ),
                          ),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${f['nombre']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                                Text('${f['detalle']}', style: TextStyle(fontSize: 11.5, color: tenue)),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right, color: tenue),
                        ],
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
