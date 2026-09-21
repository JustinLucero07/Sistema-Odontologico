import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import '../../core/models/cita.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../pacientes/paciente_detalle_page.dart';

final diaAgendaProvider = StateProvider<DateTime>((ref) => DateTime.now());

final citasDelDiaProvider = FutureProvider.autoDispose<List<Cita>>((ref) {
  final dia = ref.watch(diaAgendaProvider);
  return ref.watch(agendaRepoProvider).citasDelDia(dia);
});

class AgendaPage extends ConsumerWidget {
  const AgendaPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dia = ref.watch(diaAgendaProvider);
    final citas = ref.watch(citasDelDiaProvider);

    return Column(
      children: [
        _BarraDia(dia: dia),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => ref.invalidate(citasDelDiaProvider),
            child: citas.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => ListView(
                children: [
                  EstadoError(
                    mensaje: e is ErrorApi
                        ? e.mensaje
                        : 'Revise la conexión con la clínica.',
                    onReintentar: () => ref.invalidate(citasDelDiaProvider),
                  ),
                ],
              ),
              data: (lista) {
                if (lista.isEmpty) {
                  return ListView(
                    children: const [
                      EstadoVacio(
                        icono: Icons.event_available,
                        titulo: 'Sin citas este día',
                        detalle:
                            'Desliza hacia abajo para actualizar, o cambia de día arriba.',
                      ),
                    ],
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                  itemCount: lista.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, i) => _TarjetaCita(cita: lista[i]),
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}

class _BarraDia extends ConsumerWidget {
  const _BarraDia({required this.dia});

  final DateTime dia;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hoy = DateTime.now();
    final esHoy =
        dia.year == hoy.year && dia.month == hoy.month && dia.day == hoy.day;
    final formato = DateFormat("EEEE d 'de' MMMM", 'es');

    void mover(int dias) {
      ref.read(diaAgendaProvider.notifier).state = dia.add(
        Duration(days: dias),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
      child: Row(
        children: [
          IconButton(
            onPressed: () => mover(-1),
            icon: const Icon(Icons.chevron_left),
            tooltip: 'Día anterior',
          ),
          Expanded(
            child: GestureDetector(
              onTap: () async {
                final elegido = await showDatePicker(
                  context: context,
                  initialDate: dia,
                  firstDate: DateTime(hoy.year - 2),
                  lastDate: DateTime(hoy.year + 2),
                  locale: const Locale('es'),
                );
                if (elegido != null) {
                  ref.read(diaAgendaProvider.notifier).state = elegido;
                }
              },
              child: Column(
                children: [
                  Text(
                    // Solo la primera letra sube: `toUpperCase` por palabra
                    // daría «Domingo 27 De Septiembre».
                    _capitalizar(formato.format(dia)),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  if (esHoy)
                    Text(
                      'Hoy',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                ],
              ),
            ),
          ),
          IconButton(
            onPressed: () => mover(1),
            icon: const Icon(Icons.chevron_right),
            tooltip: 'Día siguiente',
          ),
        ],
      ),
    );
  }
}

String _capitalizar(String texto) =>
    texto.isEmpty ? texto : texto[0].toUpperCase() + texto.substring(1);

class _TarjetaCita extends ConsumerWidget {
  const _TarjetaCita({required this.cita});

  final Cita cita;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final color = StatusColors.of(context, cita.estado);
    final cancelada = cita.estado == 'cancelada' || cita.estado == 'no_asistio';

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => PacienteDetallePage(
              pacienteId: cita.pacienteId,
              nombre: cita.pacienteNombre,
            ),
          ),
        ),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // La franja de color es un refuerzo; el estado siempre va
              // escrito al lado, porque el color solo nunca debe llevarlo.
              Container(width: 4, color: color),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            DateFormat('HH:mm').format(cita.inicio),
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.3,
                              color: color,
                              fontFeatures: const [
                                FontFeature.tabularFigures(),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '${cita.duracionMinutos} min',
                            style: TextStyle(
                              fontSize: 12,
                              color: Theme.of(
                                context,
                              ).colorScheme.onSurface.withValues(alpha: 0.5),
                            ),
                          ),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 9,
                              vertical: 3,
                            ),
                            decoration: BoxDecoration(
                              color: color.withValues(alpha: 0.14),
                              borderRadius: BorderRadius.circular(99),
                            ),
                            child: Text(
                              statusLabels[cita.estado] ?? cita.estado,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: color,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        cita.pacienteNombre,
                        style: TextStyle(
                          fontSize: 15.5,
                          fontWeight: FontWeight.w600,
                          decoration: cancelada
                              ? TextDecoration.lineThrough
                              : null,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        [
                          cita.profesionalNombre,
                          if (cita.tratamientoNombre != null)
                            cita.tratamientoNombre!,
                        ].join(' · '),
                        style: TextStyle(
                          fontSize: 12.5,
                          color: Theme.of(
                            context,
                          ).colorScheme.onSurface.withValues(alpha: 0.55),
                        ),
                      ),
                      if (!cancelada && cita.estado != 'atendida') ...[
                        const SizedBox(height: 10),
                        _AccionesEstado(cita: cita),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Los pasos que de verdad se dan junto al sillón, con el pulgar.
class _AccionesEstado extends ConsumerWidget {
  const _AccionesEstado({required this.cita});

  final Cita cita;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Solo el siguiente paso razonable, no los siete estados posibles.
    final siguientes = switch (cita.estado) {
      'programada' => [('confirmada', 'Confirmar')],
      'confirmada' => [('en_espera', 'Llegó')],
      'en_espera' => [('en_atencion', 'Pasa')],
      'en_atencion' => [('atendida', 'Atendida')],
      _ => <(String, String)>[],
    };
    if (siguientes.isEmpty) return const SizedBox.shrink();

    Future<void> cambiar(String estado) async {
      try {
        await ref.read(agendaRepoProvider).cambiarEstado(cita.id, estado);
        ref.invalidate(citasDelDiaProvider);
      } on ErrorApi catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(e.mensaje)));
        }
      }
    }

    return Wrap(
      spacing: 8,
      children: [
        for (final (estado, etiqueta) in siguientes)
          FilledButton.tonal(
            onPressed: () => cambiar(estado),
            style: FilledButton.styleFrom(
              minimumSize: const Size(0, 36),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              visualDensity: VisualDensity.compact,
            ),
            child: Text(etiqueta),
          ),
        OutlinedButton(
          onPressed: () => cambiar('no_asistio'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 36),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            visualDensity: VisualDensity.compact,
          ),
          child: const Text('No asistió'),
        ),
      ],
    );
  }
}
