import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../widgets/glass.dart';
import '../widgets/ui.dart';
import 'condiciones.dart';

final lineaTiempoProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, pacienteId) => ref.watch(apiProvider).lista('/patients/$pacienteId/odontogram/timeline'),
);

const _caras = {
  'mesial': 'mesial',
  'distal': 'distal',
  'vestibular': 'vestibular',
  'lingual': 'lingual',
  'oclusal': 'oclusal',
};

class LineaTiempoOdontograma extends ConsumerStatefulWidget {
  const LineaTiempoOdontograma({super.key, required this.pacienteId, required this.alCambiar, this.alTocarPieza});

  final String pacienteId;

  /// Hallazgos de la versión elegida; null = la vigente.
  final ValueChanged<List<Map<String, dynamic>>?> alCambiar;
  final ValueChanged<String>? alTocarPieza;

  @override
  ConsumerState<LineaTiempoOdontograma> createState() => _LineaTiempoState();
}

class _LineaTiempoState extends ConsumerState<LineaTiempoOdontograma> {
  int _i = 0;
  Timer? _reloj;
  bool _iniciado = false;

  @override
  void dispose() {
    _reloj?.cancel();
    super.dispose();
  }

  void _ir(List<Map<String, dynamic>> v, int i) {
    final k = i.clamp(0, v.length - 1);
    setState(() => _i = k);
    widget.alCambiar(k == v.length - 1 ? null : (v[k]['conditions'] as List).cast<Map<String, dynamic>>());
  }

  void _alternar(List<Map<String, dynamic>> v) {
    if (_reloj != null) {
      setState(() {
        _reloj!.cancel();
        _reloj = null;
      });
      return;
    }
    if (_i >= v.length - 1) _ir(v, 0);
    setState(() {
      _reloj = Timer.periodic(const Duration(milliseconds: 1700), (_) {
        if (!mounted) return;
        if (_i >= v.length - 1) {
          setState(() {
            _reloj?.cancel();
            _reloj = null;
          });
          return;
        }
        _ir(v, _i + 1);
      });
    });
  }

  String _texto(Map<String, dynamic> c) {
    final cara = c['surface'] == 'whole' ? '' : ' (${_caras[c['surface']] ?? c['surface']})';
    return '${condicionDe('${c['condition']}').etiqueta} · ${c['fdi_number']}$cara';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ref
        .watch(lineaTiempoProvider(widget.pacienteId))
        .when(
          loading: () => const Padding(padding: EdgeInsets.all(16), child: LinearProgressIndicator()),
          error: (_, _) => const SizedBox.shrink(),
          data: (v) {
            if (v.isEmpty) {
              return const Padding(
                padding: EdgeInsets.only(bottom: 10),
                child: Text('Todavía no hay versiones guardadas. Cada vez que se guarda el odontograma se agrega un punto.'),
              );
            }
            if (!_iniciado) {
              _iniciado = true;
              WidgetsBinding.instance.addPostFrameCallback((_) => _ir(v, 0));
            }
            final actual = v[_i.clamp(0, v.length - 1)];
            final fecha = DateTime.parse('${actual['created_at']}').toLocal();
            final agregados = (actual['added'] as List).cast<Map<String, dynamic>>();
            final quitados = (actual['removed'] as List).cast<Map<String, dynamic>>();
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GlassCard(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.timeline, color: scheme.primary),
                          const SizedBox(width: 8),
                          const Expanded(child: Text('Línea de tiempo', style: TextStyle(fontWeight: FontWeight.w800))),
                          IconButton(
                            onPressed: _i > 0 ? () => _ir(v, _i - 1) : null,
                            icon: const Icon(Icons.chevron_left),
                          ),
                          IconButton.filledTonal(
                            onPressed: v.length > 1 ? () => _alternar(v) : null,
                            icon: Icon(_reloj != null ? Icons.pause : Icons.play_arrow),
                          ),
                          IconButton(
                            onPressed: _i < v.length - 1 ? () => _ir(v, _i + 1) : null,
                            icon: const Icon(Icons.chevron_right),
                          ),
                        ],
                      ),
                      if (v.length > 1)
                        Slider(
                          value: _i.toDouble(),
                          max: (v.length - 1).toDouble(),
                          divisions: v.length - 1,
                          label: DateFormat('d MMM y', 'es').format(fecha),
                          onChanged: (x) => _ir(v, x.round()),
                        ),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              toBeginningOfSentenceCase(DateFormat("EEEE d 'de' MMMM 'de' y", 'es').format(fecha)),
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          Text('${_i + 1} de ${v.length}', style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant)),
                        ],
                      ),
                      Text(
                        [
                          _i == 0 ? 'Inicial' : 'Seguimiento',
                          if (_i == v.length - 1) 'vigente',
                          if (actual['author_name'] != null) '${actual['author_name']}',
                        ].join(' · '),
                        style: TextStyle(fontSize: 12.5, color: scheme.onSurfaceVariant),
                      ),
                      if (actual['notes'] != null)
                        Text('${actual['notes']}', style: TextStyle(fontSize: 12.5, fontStyle: FontStyle.italic, color: scheme.onSurfaceVariant)),
                      const SizedBox(height: 8),
                      Text(_i == 0 ? 'Así empezó:' : 'Cambios en esta visita:', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          for (final c in agregados)
                            ActionChip(
                              visualDensity: VisualDensity.compact,
                              backgroundColor: Tonos.verde.withValues(alpha: 0.12),
                              side: BorderSide(color: Tonos.verde.withValues(alpha: 0.4)),
                              label: Text('+ ${_texto(c)}', style: const TextStyle(color: Tonos.verde, fontSize: 12, fontWeight: FontWeight.w600)),
                              onPressed: () => widget.alTocarPieza?.call('${c['fdi_number']}'),
                            ),
                          for (final c in quitados)
                            ActionChip(
                              visualDensity: VisualDensity.compact,
                              backgroundColor: Tonos.rojo.withValues(alpha: 0.1),
                              side: BorderSide(color: Tonos.rojo.withValues(alpha: 0.35)),
                              label: Text(
                                '− ${_texto(c)}',
                                style: const TextStyle(color: Tonos.rojo, fontSize: 12, fontWeight: FontWeight.w600, decoration: TextDecoration.lineThrough),
                              ),
                              onPressed: () => widget.alTocarPieza?.call('${c['fdi_number']}'),
                            ),
                          if (agregados.isEmpty && quitados.isEmpty)
                            Text('Sin cambios respecto a la anterior.', style: TextStyle(fontSize: 12.5, color: scheme.onSurfaceVariant)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
  }
}
