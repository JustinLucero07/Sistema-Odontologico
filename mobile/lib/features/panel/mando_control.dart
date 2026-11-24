import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../pacientes/comprobantes.dart';

/// Lo mismo que la web en /dashboard/control.
final mandoProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/dashboard/control'),
);

const _meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

class MandoControl extends ConsumerWidget {
  const MandoControl({super.key});

  Future<void> _meta(BuildContext context, WidgetRef ref, Map<String, dynamic> d, String mes) async {
    final r = await mostrarFormulario(
      context,
      titulo: 'Meta de cobros de $mes',
      subtitulo: 'Lo que la consulta quiere cobrar este mes. Vacío = sin meta.',
      icono: Icons.flag_outlined,
      textoGuardar: 'Guardar meta',
      campos: [
        Campo('monthly_goal', 'Meta en dólares', tipo: TipoCampo.dinero, inicial: d['monthly_goal'] == null ? null : numero(d['monthly_goal']).toStringAsFixed(2)),
      ],
      alGuardar: (v) => ref.read(apiProvider).put('/dashboard/goal', {'monthly_goal': v['monthly_goal']}),
    );
    if (r != null) ref.invalidate(mandoProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final d = ref.watch(mandoProvider).valueOrNull;
    if (d == null) return const SizedBox.shrink();
    final puedeMeta = ref.watch(authProvider).usuario?.puede('settings:manage') ?? false;
    final scheme = Theme.of(context).colorScheme;
    final mes = _meses[DateTime.parse('${d['today']}').month - 1];
    final conDinero = d['collected_month'] != null;
    final cobrado = numero(d['collected_month']);
    final meta = d['monthly_goal'] == null ? null : numero(d['monthly_goal']);
    final progreso = (d['goal_progress'] as num?)?.toDouble() ?? 0;
    final total = (d['workdays_total'] as num).toInt();
    final ritmo = total == 0 ? 0.0 : (d['workdays_elapsed'] as num) / total;
    final diferencia = ((progreso - ritmo) * 100).round();
    final serie = (d['daily_income'] as List?)?.cast<Map<String, dynamic>>();
    final estilo = TextStyle(fontSize: 12.5, color: scheme.onSurfaceVariant);
    Widget kicker(String t) => Text(t.toUpperCase(), style: TextStyle(fontSize: 10.5, letterSpacing: 1.2, fontWeight: FontWeight.w700, color: scheme.onSurfaceVariant));
    Widget contador(double valor, {double tam = 30}) => TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: valor),
      duration: const Duration(milliseconds: 1100),
      curve: Curves.easeOutCubic,
      builder: (_, v, _) => Text(dinero(v), style: TextStyle(fontSize: tam, fontWeight: FontWeight.w800, letterSpacing: -0.8)),
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (conDinero)
            GlassCard(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(child: kicker('Meta de $mes')),
                        if (puedeMeta)
                          IconButton(
                            visualDensity: VisualDensity.compact,
                            onPressed: () => _meta(context, ref, d, mes),
                            icon: Icon(meta == null ? Icons.flag_outlined : Icons.edit_outlined, size: 20),
                          ),
                      ],
                    ),
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.end,
                      spacing: 8,
                      children: [
                        contador(cobrado),
                        if (meta != null) Padding(padding: const EdgeInsets.only(bottom: 5), child: Text('de ${dinero(meta)}', style: estilo)),
                      ],
                    ),
                    if (meta != null) ...[
                      const SizedBox(height: 12),
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: SizedBox(
                          height: 22,
                          child: LayoutBuilder(
                            builder: (_, c) => Stack(
                              clipBehavior: Clip.none,
                              children: [
                                Positioned(
                                  left: 0,
                                  right: 0,
                                  top: 4,
                                  child: Container(height: 14, decoration: BoxDecoration(color: scheme.onSurface.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(99))),
                                ),
                                TweenAnimationBuilder<double>(
                                  tween: Tween(begin: 0, end: progreso.clamp(0, 1)),
                                  duration: const Duration(milliseconds: 1200),
                                  curve: Curves.easeOutCubic,
                                  builder: (_, v, _) => Positioned(
                                    left: 0,
                                    top: 4,
                                    child: Container(
                                      width: c.maxWidth * v,
                                      height: 14,
                                      decoration: BoxDecoration(color: progreso >= 1 ? Tonos.verde : scheme.primary, borderRadius: BorderRadius.circular(99)),
                                    ),
                                  ),
                                ),
                                Positioned(
                                  left: c.maxWidth * ritmo.clamp(0, 1) - 1.5,
                                  top: 0,
                                  child: Container(width: 3, height: 22, decoration: BoxDecoration(color: scheme.onSurface.withValues(alpha: 0.5), borderRadius: BorderRadius.circular(2))),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        progreso >= 1
                            ? '¡Meta cumplida! ${(progreso * 100).round()} %'
                            : '${(progreso * 100).round()} % · ${diferencia >= 0 ? 'por encima' : 'por debajo'} del ritmo (${diferencia >= 0 ? '+' : '−'}${diferencia.abs()} pts)',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: diferencia >= 0 || progreso >= 1 ? Tonos.verde : Tonos.rojo),
                      ),
                      if (progreso < 1 && d['needed_per_workday'] != null)
                        Text(
                          'Faltan ${dinero(math.max(0, meta - cobrado))} · ${dinero(numero(d['needed_per_workday']))} por día hábil (${d['workdays_left']} días)',
                          style: estilo,
                        ),
                    ] else
                      Padding(
                        padding: const EdgeInsets.only(top: 6, right: 8),
                        child: Text('Ponle una meta al mes y verás si vas al ritmo y cuánto cobrar por día.', style: estilo),
                      ),
                    if (d['projection_month'] != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text('Proyección al cierre: ${dinero(numero(d['projection_month']))}', style: estilo),
                      ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: GlassCard(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        kicker('Hoy'),
                        if (conDinero) ...[
                          const SizedBox(height: 4),
                          contador(numero(d['collected_today']), tam: 22),
                          Text('en ${d['payments_today']} ${d['payments_today'] == 1 ? 'pago' : 'pagos'}', style: estilo),
                        ],
                        const SizedBox(height: 8),
                        _linea(Tonos.azul, d['appointments_confirmed'], 'confirmadas'),
                        _linea(Tonos.ambar, d['appointments_pending_confirm'], 'por confirmar'),
                        _linea(Tonos.verde, d['appointments_attended'], 'atendidas'),
                        _linea(Tonos.rojo, d['no_shows_today'], 'no asistieron'),
                      ],
                    ),
                  ),
                ),
              ),
              if (serie != null) ...[
                const SizedBox(width: 10),
                Expanded(
                  child: GlassCard(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          kicker('30 días'),
                          const SizedBox(height: 4),
                          contador(serie.fold<double>(0, (s, x) => s + numero(x['amount'])), tam: 22),
                          const SizedBox(height: 10),
                          SizedBox(
                            height: 70,
                            child: TweenAnimationBuilder<double>(
                              tween: Tween(begin: 0, end: 1),
                              duration: const Duration(milliseconds: 900),
                              curve: Curves.easeOutCubic,
                              builder: (_, k, _) => CustomPaint(
                                size: Size.infinite,
                                painter: _Barras([for (final x in serie) numero(x['amount'])], scheme.primary, k),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              if ((d['receipts_pending'] as num? ?? 0) > 0)
                InkWell(
                  key: const Key('chip-comprobantes'),
                  borderRadius: BorderRadius.circular(99),
                  onTap: () async {
                    await showModalBottomSheet<void>(
                      context: context,
                      isScrollControlled: true,
                      showDragHandle: true,
                      builder: (_) => SafeArea(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                          child: ComprobantesPortal(
                            puedeCobrar: ref.read(authProvider).usuario?.puede('payments:write') ?? false,
                          ),
                        ),
                      ),
                    );
                    ref.invalidate(mandoProvider);
                  },
                  child: Pastilla(
                    '${d['receipts_pending']} ${d['receipts_pending'] == 1 ? 'comprobante por revisar' : 'comprobantes por revisar'}',
                    color: Tonos.rojo,
                  ),
                ),
              if (d['ortho_overdue'] != null)
                Pastilla(
                  '${d['ortho_overdue']} ${d['ortho_overdue'] == 1 ? 'ortodoncia atrasada' : 'ortodoncias atrasadas'}',
                  color: (d['ortho_overdue'] as num) > 0 ? Tonos.rojo : Tonos.gris,
                ),
              Pastilla('${d['new_patients_month']} ${d['new_patients_month'] == 1 ? 'paciente nuevo' : 'pacientes nuevos'} este mes'),
              Pastilla('${d['no_shows_month']} no asistieron este mes', color: (d['no_shows_month'] as num) > 0 ? Tonos.ambar : Tonos.gris),
            ],
          ),
        ],
      ),
    );
  }

  Widget _linea(Color c, dynamic n, String t) => Padding(
    padding: const EdgeInsets.only(top: 3),
    child: Row(
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text('$n', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
        const SizedBox(width: 4),
        Flexible(child: Text(t, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5))),
      ],
    ),
  );
}

class _Barras extends CustomPainter {
  _Barras(this.valores, this.color, this.k);
  final List<double> valores;
  final Color color;
  final double k;

  @override
  void paint(Canvas canvas, Size size) {
    if (valores.isEmpty) return;
    final maximo = valores.reduce(math.max);
    final paso = size.width / valores.length;
    for (var i = 0; i < valores.length; i++) {
      final h = maximo <= 0 ? 1.0 : math.max(valores[i] > 0 ? 3.0 : 1.0, valores[i] / maximo * size.height) * k;
      final p = Paint()..color = color.withValues(alpha: i == valores.length - 1 ? 0.95 : 0.45);
      canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(i * paso + 0.5, size.height - h, math.max(1.5, paso - 1.5), h), const Radius.circular(2)),
        p,
      );
    }
  }

  @override
  bool shouldRepaint(_Barras o) => o.k != k || o.valores != valores;
}
