import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';

final resumenProvider = FutureProvider.autoDispose(
  (ref) => ref.watch(panelRepoProvider).resumen(),
);

class PanelPage extends ConsumerWidget {
  const PanelPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(authProvider).usuario;
    final resumen = ref.watch(resumenProvider);
    final hora = DateTime.now().hour;
    final saludo = hora < 12
        ? 'Buenos días'
        : (hora < 19 ? 'Buenas tardes' : 'Buenas noches');

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(resumenProvider),
      child: ListView(
        padding: EdgeInsets.fromLTRB(16, 8, 16, 28 + MediaQuery.paddingOf(context).bottom),
        children: [
          Text(
            '$saludo, ${usuario?.nombre ?? ''}',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            _capitalizar(
              DateFormat("EEEE d 'de' MMMM", 'es').format(DateTime.now()),
            ),
            style: TextStyle(
              fontSize: 13.5,
              color: Theme.of(
                context,
              ).colorScheme.onSurface.withValues(alpha: 0.55),
            ),
          ),
          const SizedBox(height: 20),
          resumen.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => EstadoError(
              mensaje: e is ErrorApi
                  ? e.mensaje
                  : 'Revise la conexión con la clínica.',
              onReintentar: () => ref.invalidate(resumenProvider),
            ),
            data: (datos) => _Tarjetas(datos: datos),
          ),
        ],
      ),
    );
  }
}

String _capitalizar(String t) =>
    t.isEmpty ? t : t[0].toUpperCase() + t.substring(1);

class _Tarjetas extends StatelessWidget {
  const _Tarjetas({required this.datos});

  final Map<String, dynamic> datos;

  @override
  Widget build(BuildContext context) {
    final porEstado = (datos['appointments_by_status'] as List? ?? [])
        .cast<Map<String, dynamic>>()
        .where((e) => (e['count'] as int) > 0)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.55,
          children: [
            _Kpi(
              etiqueta: 'Citas hoy',
              valor: '${datos['appointments_today'] ?? 0}',
              icono: Icons.event_available,
            ),
            _Kpi(
              etiqueta: 'Pacientes',
              valor: '${datos['total_patients'] ?? 0}',
              icono: Icons.groups,
            ),
            _Kpi(
              etiqueta: 'Tratamientos pendientes',
              valor: '${datos['treatments_pending'] ?? 0}',
              icono: Icons.assignment,
            ),
            _Kpi(
              etiqueta: 'Presupuestos aceptados',
              // Sin permiso de presupuestos el servidor manda null, no cero:
              // "$0,00" diría que no hay nada aceptado, y eso no se sabe.
              valor: datos['budget_accepted_total'] == null
                  ? '—'
                  : dinero(
                      double.tryParse('${datos['budget_accepted_total']}') ?? 0,
                    ),
              icono: Icons.request_quote,
              compacto: true,
            ),
          ],
        ),
        if (porEstado.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text(
            'Citas de los próximos 7 días',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Column(
                children: [
                  for (final fila in porEstado)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: StatusColors.of(
                                context,
                                fila['status'] as String,
                              ),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              statusLabels[fila['status']] ??
                                  '${fila['status']}',
                              style: const TextStyle(fontSize: 14),
                            ),
                          ),
                          Text(
                            '${fila['count']}',
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontFeatures: [FontFeature.tabularFigures()],
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
      ],
    );
  }
}

class _Kpi extends StatelessWidget {
  const _Kpi({
    required this.etiqueta,
    required this.valor,
    required this.icono,
    this.compacto = false,
  });

  final String etiqueta;
  final String valor;
  final IconData icono;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final primario = Theme.of(context).colorScheme.primary;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    etiqueta,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.55),
                    ),
                  ),
                ),
                Icon(icono, size: 18, color: primario),
              ],
            ),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                valor,
                style: TextStyle(
                  fontSize: compacto ? 20 : 26,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.8,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
