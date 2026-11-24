import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import 'condiciones.dart';

Future<List<Map<String, dynamic>>?> mostrarDictado(BuildContext context) {
  return showModalBottomSheet<List<Map<String, dynamic>>>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => const _HojaDictado(),
  );
}

List<Map<String, dynamic>> aplicarHallazgos(
  List<Map<String, dynamic>> actuales,
  List<Map<String, dynamic>> nuevos,
) {
  final r = [...actuales];
  for (final h in nuevos) {
    final fdi = h['fdi_number'];
    final cara = h['surface'];
    if (h['condition'] == 'sano') {
      r.removeWhere((c) => c['fdi_number'] == fdi && (cara == 'whole' || c['surface'] == cara));
      continue;
    }
    final repetido = r.any((c) => c['fdi_number'] == fdi && c['surface'] == cara && c['condition'] == h['condition']);
    if (!repetido) r.add({'fdi_number': fdi, 'surface': cara, 'condition': h['condition'], 'notes': null});
  }
  return r;
}

class _HojaDictado extends ConsumerStatefulWidget {
  const _HojaDictado();

  @override
  ConsumerState<_HojaDictado> createState() => _HojaDictadoState();
}

class _HojaDictadoState extends ConsumerState<_HojaDictado> {
  final _texto = TextEditingController();
  Timer? _espera;
  List<Map<String, dynamic>> _hallazgos = [];
  List<String> _sinEntender = [];
  String? _error;

  @override
  void dispose() {
    _espera?.cancel();
    _texto.dispose();
    super.dispose();
  }

  void _cambio(String t) {
    _espera?.cancel();
    _espera = Timer(const Duration(milliseconds: 400), () => _interpretar(t));
  }

  Future<void> _interpretar(String t) async {
    if (t.trim().isEmpty) {
      setState(() {
        _hallazgos = [];
        _sinEntender = [];
      });
      return;
    }
    try {
      final r = await ref.read(apiProvider).post('/odontogram/dictation', {'texto': t}) as Map;
      if (!mounted) return;
      setState(() {
        _error = null;
        _hallazgos = (r['hallazgos'] as List).cast<Map<String, dynamic>>();
        _sinEntender = (r['sin_entender'] as List).cast<String>();
      });
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo interpretar el dictado.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final tenue = TextStyle(fontSize: 12.5, color: scheme.onSurface.withValues(alpha: 0.6));
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Icon(Icons.mic, color: scheme.primary),
                  const SizedBox(width: 8),
                  Text('Dictar hallazgos', style: Theme.of(context).textTheme.titleLarge),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Toque el micrófono del teclado y hable. Ej.: «36 caries oclusal, 11 corona, falta el 18».',
                style: tenue,
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('dictado-texto'),
                controller: _texto,
                autofocus: true,
                minLines: 3,
                maxLines: 6,
                onChanged: _cambio,
                decoration: const InputDecoration(hintText: 'Hable o escriba aquí…'),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(_error!, style: TextStyle(color: scheme.error, fontSize: 12.5)),
                ),
              if (_hallazgos.isNotEmpty) ...[
                const SizedBox(height: 12),
                const Text('Se registrará:', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    for (final h in _hallazgos)
                      Chip(
                        visualDensity: VisualDensity.compact,
                        avatar: CircleAvatar(radius: 5, backgroundColor: condicionDe('${h['condition']}').color),
                        label: Text(
                          '${h['fdi_number']} · ${condicionDe('${h['condition']}').etiqueta}'
                          '${h['surface'] == 'whole' ? '' : ' · ${(etiquetasSuperficie[h['surface']] ?? '${h['surface']}').toLowerCase()}'}',
                        ),
                      ),
                  ],
                ),
              ],
              if (_sinEntender.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text('No entendí: ${_sinEntender.join(' · ')}', style: tenue),
                ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _hallazgos.isEmpty ? null : () => Navigator.pop(context, _hallazgos),
                  icon: const Icon(Icons.check),
                  label: Text('Aplicar ${_hallazgos.isEmpty ? '' : _hallazgos.length} al odontograma'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
