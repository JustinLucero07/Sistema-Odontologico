import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/marca/marca.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/aparecer.dart';
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
    final tinta = Theme.of(context).colorScheme.onSurface;

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(resumenProvider),
      child: ListView(
        padding: EdgeInsets.fromLTRB(
          20,
          6,
          20,
          28 + MediaQuery.paddingOf(context).bottom,
        ),
        children: [
          Aparecer(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  DateFormat("EEEE d 'de' MMMM", 'es').format(DateTime.now()).toUpperCase(),
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1.6,
                    color: tinta.withValues(alpha: 0.45),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '$saludo,\n${usuario?.nombre ?? ''}',
                  style: estiloTitulo(30, color: tinta, peso: FontWeight.w800),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
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
            data: (datos) => _Contenido(
              datos: datos,
              oportunidades: (usuario?.puede('patients:read') ?? false)
                  ? ref.watch(oportunidadesProvider).valueOrNull
                  : null,
            ),
          ),
        ],
      ),
    );
  }
}

class _Contenido extends StatelessWidget {
  const _Contenido({required this.datos, required this.oportunidades});

  final Map<String, dynamic> datos;
  final Map<String, dynamic>? oportunidades;

  @override
  Widget build(BuildContext context) {
    final porEstado = (datos['appointments_by_status'] as List? ?? [])
        .cast<Map<String, dynamic>>()
        .where((e) => (e['count'] as int) > 0)
        .toList();
    final semana = porEstado.fold<int>(0, (s, e) => s + (e['count'] as int));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Aparecer(
          orden: 1,
          child: _Destacado(
            citasHoy: '${datos['appointments_today'] ?? 0}',
            semana: semana,
            porEstado: porEstado,
          ),
        ),
        if (oportunidades != null && totalOportunidades(oportunidades!) > 0) ...[
          const SizedBox(height: 12),
          Aparecer(orden: 2, child: _Oportunidades(datos: oportunidades!)),
        ],
        const SizedBox(height: 12),
        Aparecer(
          orden: 3,
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: _Cifra(
                    etiqueta: 'Pacientes',
                    valor: '${datos['total_patients'] ?? 0}',
                    icono: Icons.people_alt_outlined,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _Cifra(
                    etiqueta: 'Tratamientos pendientes',
                    valor: '${datos['treatments_pending'] ?? 0}',
                    icono: Icons.assignment_outlined,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Aparecer(
          orden: 4,
          child: _Cifra(
            etiqueta: 'Presupuestos aceptados',
            // Sin permiso de presupuestos el servidor manda null, no cero:
            // "$0,00" diría que no hay nada aceptado, y eso no se sabe.
            valor: datos['budget_accepted_total'] == null
                ? '—'
                : dinero(double.tryParse('${datos['budget_accepted_total']}') ?? 0),
            icono: Icons.request_quote_outlined,
            horizontal: true,
          ),
        ),
        if (porEstado.isNotEmpty) ...[
          const SizedBox(height: 26),
          Aparecer(
            orden: 5,
            child: Text(
              'Próximos 7 días',
              style: estiloTitulo(18, color: Theme.of(context).colorScheme.onSurface),
            ),
          ),
          const SizedBox(height: 12),
          Aparecer(orden: 6, child: _PorEstado(filas: porEstado, total: semana)),
        ],
      ],
    );
  }
}

/// Bloque principal: cuántas citas hay hoy, en tinta oscura para que sea lo
/// primero que se lee, con la distribución de la semana en una barra fina.
class _Destacado extends StatelessWidget {
  const _Destacado({required this.citasHoy, required this.semana, required this.porEstado});

  final String citasHoy;
  final int semana;
  final List<Map<String, dynamic>> porEstado;

  @override
  Widget build(BuildContext context) {
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    final fondo = oscuro ? tono(AppColors.primary, -0.62) : tono(AppColors.primary, -0.66);
    final claro = tono(AppColors.primary, 0.6);

    return GlassPanel(
      tint: fondo,
      radius: 26,
      padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: claro, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Text(
                'CITAS DE HOY',
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.5,
                  color: Colors.white.withValues(alpha: 0.7),
                ),
              ),
              const Spacer(),
              Icon(Icons.event_available_outlined, size: 20, color: Colors.white.withValues(alpha: 0.6)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            citasHoy,
            style: estiloTitulo(64, color: Colors.white, peso: FontWeight.w800).copyWith(
              height: 1.05,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          Text(
            semana == 0
                ? 'Sin citas en los próximos 7 días'
                : '$semana ${semana == 1 ? 'cita' : 'citas'} en los próximos 7 días',
            style: TextStyle(fontSize: 13.5, color: Colors.white.withValues(alpha: 0.72)),
          ),
          if (semana > 0) ...[
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: SizedBox(
                height: 6,
                child: Row(
                  children: [
                    for (var i = 0; i < porEstado.length; i++) ...[
                      if (i > 0) const SizedBox(width: 2),
                      Expanded(
                        flex: porEstado[i]['count'] as int,
                        child: ColoredBox(
                          color: StatusColors.of(context, porEstado[i]['status'] as String),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Personas a contactar hoy, con el acento dorado de la marca.
class _Oportunidades extends StatelessWidget {
  const _Oportunidades({required this.datos});

  final Map<String, dynamic> datos;

  @override
  Widget build(BuildContext context) {
    final total = totalOportunidades(datos);
    int n(String k) => (datos[k] as List?)?.length ?? 0;
    final partes = [
      if (n('unconfirmed') > 0) '${n('unconfirmed')} por confirmar',
      if (n('birthdays') > 0) '${n('birthdays')} cumpleaños',
      if (n('pending_treatments') > 0) '${n('pending_treatments')} tratamientos sin cita',
      if (n('recall') > 0) '${n('recall')} por recuperar',
      if (n('debtors') > 0) '${n('debtors')} con saldo',
    ];
    final tinta = Theme.of(context).colorScheme.onSurface;
    const oro = AppColors.accent;

    return GlassCard(
      radius: 22,
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => const OportunidadesPage()),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: oro.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(15),
              ),
              child: const Icon(Icons.auto_awesome_outlined, color: oro, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$total ${total == 1 ? 'oportunidad' : 'oportunidades'} hoy',
                    style: estiloTitulo(16, color: tinta),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    partes.join(' · '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, height: 1.35, color: tinta.withValues(alpha: 0.58)),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            Icon(Icons.arrow_forward_ios_rounded, size: 15, color: tinta.withValues(alpha: 0.35)),
          ],
        ),
      ),
    );
  }
}

class _Cifra extends StatelessWidget {
  const _Cifra({
    required this.etiqueta,
    required this.valor,
    required this.icono,
    this.horizontal = false,
  });

  final String etiqueta;
  final String valor;
  final IconData icono;
  final bool horizontal;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final tinta = scheme.onSurface;
    final icono = Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.09),
        borderRadius: BorderRadius.circular(11),
      ),
      child: Icon(this.icono, size: 18, color: scheme.primary),
    );
    final etiqueta = Text(
      this.etiqueta,
      style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w500, color: tinta.withValues(alpha: 0.58)),
    );
    final cifra = FittedBox(
      fit: BoxFit.scaleDown,
      alignment: Alignment.centerLeft,
      child: Text(
        valor,
        style: estiloTitulo(28, color: tinta, peso: FontWeight.w800).copyWith(
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
    );

    return GlassCard(
      radius: 22,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: horizontal
            ? Row(
                children: [
                  icono,
                  const SizedBox(width: 12),
                  Expanded(child: etiqueta),
                  cifra,
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  icono,
                  const SizedBox(height: 14),
                  cifra,
                  const SizedBox(height: 2),
                  etiqueta,
                ],
              ),
      ),
    );
  }
}

/// Citas de la semana por estado, con una barra proporcional por fila.
class _PorEstado extends StatelessWidget {
  const _PorEstado({required this.filas, required this.total});

  final List<Map<String, dynamic>> filas;
  final int total;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    return GlassCard(
      radius: 22,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 8),
        child: Column(
          children: [
            for (var i = 0; i < filas.length; i++) ...[
              if (i > 0) const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Row(
                  children: [
                    Container(
                      width: 9,
                      height: 9,
                      decoration: BoxDecoration(
                        color: StatusColors.of(context, filas[i]['status'] as String),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 5,
                      child: Text(
                        statusLabels[filas[i]['status']] ?? '${filas[i]['status']}',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                      ),
                    ),
                    Expanded(
                      flex: 4,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: total == 0 ? 0 : (filas[i]['count'] as int) / total,
                          minHeight: 5,
                          backgroundColor: tinta.withValues(alpha: 0.06),
                          color: StatusColors.of(context, filas[i]['status'] as String),
                        ),
                      ),
                    ),
                    SizedBox(
                      width: 36,
                      child: Text(
                        '${filas[i]['count']}',
                        textAlign: TextAlign.right,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontFeatures: [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
