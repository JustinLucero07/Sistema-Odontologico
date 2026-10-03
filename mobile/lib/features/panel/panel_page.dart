import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/carga.dart';
import '../oportunidades/oportunidades_page.dart';

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
        padding: EdgeInsets.fromLTRB(
          16,
          8,
          16,
          28 + MediaQuery.paddingOf(context).bottom,
        ),
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
          const SizedBox(height: 16),
          if (usuario?.puede('patients:read') ?? false)
            ref
                .watch(oportunidadesProvider)
                .maybeWhen(
                  data: (d) => _BannerOportunidades(datos: d),
                  orElse: () => const SizedBox.shrink(),
                ),
          const SizedBox(height: 4),
          resumen.when(
            loading: () => const EsqueletoLista(
              filas: 3,
              conTarjetas: true,
              dentroDeLista: true,
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
          GlassCard(
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
    return GlassCard(
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

/// Aviso del día: cuántas personas conviene contactar hoy.
class _BannerOportunidades extends StatelessWidget {
  const _BannerOportunidades({required this.datos});

  final Map<String, dynamic> datos;

  @override
  Widget build(BuildContext context) {
    final total = totalOportunidades(datos);
    if (total == 0) return const SizedBox.shrink();
    int n(String k) => (datos[k] as List?)?.length ?? 0;
    final partes = [
      if (n('unconfirmed') > 0) '${n('unconfirmed')} por confirmar',
      if (n('birthdays') > 0) '${n('birthdays')} cumpleaños',
      if (n('pending_treatments') > 0)
        '${n('pending_treatments')} tratamientos sin cita',
      if (n('recall') > 0) '${n('recall')} por recuperar',
      if (n('debtors') > 0) '${n('debtors')} con saldo',
    ];
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: GestureDetector(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => const OportunidadesPage()),
        ),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF1FB3A4), Color(0xFF0D7F76), Color(0xFF074A45)],
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0D7F76).withValues(alpha: 0.35),
                blurRadius: 24,
                offset: const Offset(0, 12),
                spreadRadius: -8,
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(Icons.tips_and_updates, color: Colors.white),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$total ${total == 1 ? 'oportunidad' : 'oportunidades'} hoy',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      partes.join(' · '),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 12.5,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.white),
            ],
          ),
        ),
      ),
    );
  }
}
