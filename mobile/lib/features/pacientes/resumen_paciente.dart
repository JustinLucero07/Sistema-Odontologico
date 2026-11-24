import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Los mismos datos que la web en /patients/{id}/briefing.
final resumenPacienteProvider = FutureProvider.autoDispose.family<Map<String, dynamic>, String>(
  (ref, id) => ref.watch(apiProvider).mapa('/patients/$id/briefing'),
);

const _iconos = <String, IconData>{
  'event': Icons.event,
  'event_busy': Icons.event_busy,
  'waving_hand': Icons.waving_hand_outlined,
  'warning': Icons.warning_amber,
  'favorite': Icons.favorite_border,
  'medication': Icons.medication_outlined,
  'pregnant_woman': Icons.pregnant_woman,
  'assignment_late': Icons.assignment_late_outlined,
  'sentiment_very_satisfied': Icons.sentiment_very_satisfied_outlined,
  'schedule': Icons.schedule,
  'push_pin': Icons.push_pin_outlined,
  'priority_high': Icons.priority_high,
  'assignment': Icons.assignment_outlined,
  'request_quote': Icons.request_quote_outlined,
  'draw': Icons.draw_outlined,
  'history': Icons.history,
  'account_balance_wallet': Icons.account_balance_wallet_outlined,
  'savings': Icons.savings_outlined,
  'check_circle': Icons.check_circle_outline,
  'cake': Icons.cake_outlined,
};

class ResumenPaciente extends ConsumerStatefulWidget {
  const ResumenPaciente({super.key, required this.pacienteId});
  final String pacienteId;

  @override
  ConsumerState<ResumenPaciente> createState() => _ResumenPacienteState();
}

class _ResumenPacienteState extends ConsumerState<ResumenPaciente> {
  String? _texto;
  String? _error;
  bool _generando = false;

  Future<void> _resumir() async {
    setState(() {
      _generando = true;
      _error = null;
    });
    try {
      final r = await ref.read(apiProvider).post('/patients/${widget.pacienteId}/briefing/ai', {}) as Map;
      setState(() => _texto = '${r['texto']}');
    } on ErrorApi catch (e) {
      setState(() => _error = e.mensaje);
    } catch (_) {
      setState(() => _error = 'No se pudo generar el resumen.');
    } finally {
      if (mounted) setState(() => _generando = false);
    }
  }

  Color _color(String tono, ColorScheme s) => switch (tono) {
    'alerta' => Tonos.rojo,
    'ok' => Tonos.verde,
    'dinero' => Tonos.ambar,
    _ => s.primary,
  };

  @override
  Widget build(BuildContext context) {
    final r = ref.watch(resumenPacienteProvider(widget.pacienteId)).valueOrNull;
    if (r == null) return const SizedBox.shrink();
    final datos = (r['datos'] as List).cast<Map<String, dynamic>>();
    final ia = r['ia_disponible'] == true;
    if (datos.isEmpty && !ia) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.assignment_ind_outlined, color: scheme.primary),
                  const SizedBox(width: 8),
                  const Expanded(child: Text('Antes de atender', style: TextStyle(fontWeight: FontWeight.w800))),
                  if (ia)
                    TextButton.icon(
                      onPressed: _generando ? null : _resumir,
                      icon: _generando
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.auto_awesome, size: 18),
                      label: Text(_texto == null ? 'Resumen con IA' : 'Otra vez'),
                    ),
                ],
              ),
              if (_texto != null) ...[
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: scheme.primary.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_texto!, style: const TextStyle(height: 1.4)),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Borrador de IA. Revíselo antes de usarlo.',
                              style: TextStyle(fontSize: 11.5, color: scheme.onSurfaceVariant),
                            ),
                          ),
                          IconButton(
                            visualDensity: VisualDensity.compact,
                            icon: const Icon(Icons.copy, size: 18),
                            onPressed: () async {
                              await Clipboard.setData(ClipboardData(text: _texto!));
                              if (context.mounted) avisar(context, 'Resumen copiado.');
                            },
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(_error!, style: const TextStyle(color: Tonos.rojo, fontSize: 12.5)),
                ),
              const SizedBox(height: 8),
              for (final d in datos)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(_iconos[d['icono']] ?? Icons.info_outline, size: 18, color: _color('${d['tono']}', scheme)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${d['texto']}',
                          style: TextStyle(
                            fontSize: 13,
                            color: d['tono'] == 'alerta' ? Tonos.rojo : null,
                            fontWeight: d['tono'] == 'alerta' ? FontWeight.w600 : null,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
