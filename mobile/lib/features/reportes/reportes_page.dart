import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

enum _Rango { mes, treinta, trimestre, anio }

final _rangoProvider = StateProvider.autoDispose<_Rango>((ref) => _Rango.mes);

(String, String) _fechas(_Rango r) {
  final hoy = DateTime.now();
  final f = DateFormat('yyyy-MM-dd');
  final desde = switch (r) {
    _Rango.mes => DateTime(hoy.year, hoy.month, 1),
    _Rango.treinta => hoy.subtract(const Duration(days: 29)),
    _Rango.trimestre => hoy.subtract(const Duration(days: 89)),
    _Rango.anio => DateTime(hoy.year, 1, 1),
  };
  return (f.format(desde), f.format(hoy));
}

class _Reportes {
  const _Reportes(
    this.resumen,
    this.financiero,
    this.clinico,
    this.citas,
    this.pacientes,
  );
  final Map<String, dynamic> resumen;
  final Map<String, dynamic> financiero;
  final Map<String, dynamic> clinico;
  final Map<String, dynamic> citas;
  final Map<String, dynamic> pacientes;
}

final _reportesProvider = FutureProvider.autoDispose<_Reportes>((ref) async {
  final (desde, hasta) = _fechas(ref.watch(_rangoProvider));
  final api = ref.watch(apiProvider);
  final q = {'date_from': desde, 'date_to': hasta};
  final r = await Future.wait([
    api.mapa('/reports/summary', query: q),
    api.mapa('/reports/financial', query: q),
    api.mapa('/reports/clinical', query: q),
    api.mapa('/reports/appointments', query: q),
    api.mapa('/reports/patients', query: q),
  ]);
  return _Reportes(r[0], r[1], r[2], r[3], r[4]);
});

/// Reportes: los mismos indicadores que la web, por periodo.
class ReportesPage extends ConsumerWidget {
  const ReportesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rango = ref.watch(_rangoProvider);
    return PaginaModulo(
      titulo: 'Reportes',
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_reportesProvider),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final (r, t) in const [
                    (_Rango.mes, 'Este mes'),
                    (_Rango.treinta, '30 días'),
                    (_Rango.trimestre, '90 días'),
                    (_Rango.anio, 'Este año'),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(t),
                        selected: rango == r,
                        onSelected: (_) =>
                            ref.read(_rangoProvider.notifier).state = r,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            ref
                .watch(_reportesProvider)
                .when(
                  loading: () => const EsqueletoLista(
                    filas: 4,
                    conTarjetas: true,
                    dentroDeLista: true,
                  ),
                  error: (e, _) => Text('$e'),
                  data: (d) => _contenido(context, d),
                ),
            finDeLista,
          ],
        ),
      ),
    );
  }

  Widget _contenido(BuildContext context, _Reportes d) {
    final s = d.resumen;
    final f = d.financiero;
    final c = d.clinico;
    final a = d.citas;
    final p = d.pacientes;
    String pct(dynamic v) =>
        v == null ? '—' : '${(numero(v) * 100).toStringAsFixed(1)} %';
    List<Map<String, dynamic>> l(dynamic v) =>
        (v as List? ?? []).cast<Map<String, dynamic>>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        RejillaKpi(
          hijos: [
            Kpi(
              etiqueta: 'Cobrado',
              valor: dinero(numero(s['collected'])),
              icono: Icons.payments_outlined,
              color: Tonos.verde,
            ),
            Kpi(
              etiqueta: 'Por cobrar',
              valor: dinero(numero(s['outstanding'])),
              icono: Icons.hourglass_bottom,
              color: Tonos.ambar,
            ),
            Kpi(
              etiqueta: 'Citas',
              valor: '${s['appointments']}',
              icono: Icons.event,
              detalle: 'Inasistencia ${pct(s['no_show_rate'])}',
            ),
            Kpi(
              etiqueta: 'Pacientes nuevos',
              valor: '${s['new_patients']}',
              icono: Icons.person_add_alt,
            ),
            Kpi(
              etiqueta: 'Tratamientos hechos',
              valor: '${s['treatments_completed']}',
              icono: Icons.medical_services_outlined,
            ),
            Kpi(
              etiqueta: 'Conversión presupuestos',
              valor: pct((c['budgets'] as Map?)?['conversion_rate']),
              icono: Icons.request_quote_outlined,
            ),
          ],
        ),
        _Barras(
          titulo: 'Cobrado por forma de pago',
          filas: l(f['by_method']),
          esDinero: true,
        ),
        _Barras(
          titulo: 'Cobrado por profesional',
          filas: l(f['by_professional']),
          esDinero: true,
        ),
        _Barras(
          titulo: 'Antigüedad de la deuda',
          filas: [
            for (final b in l(f['aging']))
              {'label': b['label'], 'amount': b['amount'], 'count': b['count']},
          ],
          esDinero: true,
          color: Tonos.ambar,
        ),
        _Barras(
          titulo: 'Tratamientos realizados',
          filas: l(c['by_treatment']),
          esDinero: true,
        ),
        _Barras(
          titulo: 'Diagnósticos más frecuentes',
          filas: l(c['top_diagnoses']),
          color: Tonos.violeta,
        ),
        _Barras(
          titulo: 'Citas por estado',
          filas: l(a['by_status']),
          color: Tonos.azul,
        ),
        _Barras(
          titulo: 'Pacientes por edad',
          filas: l(p['by_age_band']),
          color: Tonos.azul,
        ),
      ],
    );
  }
}

/// Barras horizontales con su etiqueta y valor (mismo estilo que la web).
class _Barras extends StatelessWidget {
  const _Barras({
    required this.titulo,
    required this.filas,
    this.esDinero = false,
    this.color,
  });

  final String titulo;
  final List<Map<String, dynamic>> filas;
  final bool esDinero;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    if (filas.isEmpty) return const SizedBox.shrink();
    final c = color ?? Theme.of(context).colorScheme.primary;
    double valor(Map<String, dynamic> f) =>
        esDinero ? numero(f['amount']) : numero(f['count'] ?? f['amount']);
    final maximo = filas.map(valor).fold<double>(1, (a, b) => b > a ? b : a);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Seccion(titulo),
        GlassCard(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                for (final f in filas)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '${f['label']}',
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                            Text(
                              esDinero
                                  ? dinero(numero(f['amount']))
                                  : '${f['count'] ?? f['amount']}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 5),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: valor(f) / maximo,
                            minHeight: 7,
                            color: c,
                            backgroundColor: c.withValues(alpha: 0.12),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
