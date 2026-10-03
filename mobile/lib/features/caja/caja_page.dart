import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

class _DatosCaja {
  const _DatosCaja(this.sesion, this.reporte, this.cobros);
  final Map<String, dynamic>? sesion;
  final Map<String, dynamic> reporte;
  final List<Map<String, dynamic>> cobros;
}

final _cajaProvider = FutureProvider.autoDispose<_DatosCaja>((ref) async {
  final api = ref.watch(apiProvider);
  final hoy = hoyIso();
  final sesion = await api.get('/finance/cash-session');
  final reporte = await api.mapa('/finance/daily-report');
  final cobros = await api.lista(
    '/finance/payments',
    query: {'date_from': hoy, 'date_to': hoy},
  );
  return _DatosCaja(
    sesion is Map ? sesion.cast<String, dynamic>() : null,
    reporte,
    cobros,
  );
});

/// Caja del día: apertura con fondo, lo que entra y sale en efectivo, y el
/// cierre con arqueo. Igual que en la web.
class CajaPage extends ConsumerWidget {
  const CajaPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final datos = ref.watch(_cajaProvider);
    final api = ref.read(apiProvider);

    Future<void> abrir() => mostrarFormulario(
      context,
      titulo: 'Abrir caja',
      subtitulo: 'Cuente el dinero con el que empieza el día.',
      icono: Icons.lock_open,
      textoGuardar: 'Abrir caja',
      campos: const [
        Campo(
          'opening_float',
          'Fondo inicial',
          tipo: TipoCampo.dinero,
          inicial: '0',
          requerido: true,
        ),
      ],
      alGuardar: (v) async {
        await api.post('/finance/cash-session/open', v);
        ref.invalidate(_cajaProvider);
      },
    );

    Future<void> cerrar(Map<String, dynamic> sesion) => mostrarFormulario(
      context,
      titulo: 'Cerrar caja',
      subtitulo:
          'Debería haber ${dinero(numero(sesion['expected_now']))} en efectivo.',
      icono: Icons.lock,
      textoGuardar: 'Cerrar caja',
      campos: const [
        Campo(
          'counted_cash',
          'Efectivo contado',
          tipo: TipoCampo.dinero,
          requerido: true,
        ),
        Campo('notes', 'Observaciones', tipo: TipoCampo.multilinea),
      ],
      alGuardar: (v) async {
        await api.post('/finance/cash-session/close', v);
        ref.invalidate(_cajaProvider);
      },
    );

    return PaginaModulo(
      titulo: 'Caja del día',
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_cajaProvider),
        child: Asincrono(
          valor: datos,
          alReintentar: () => ref.invalidate(_cajaProvider),
          esqueleto: const EsqueletoLista(filas: 4, conTarjetas: true),
          listo: (d) {
            final s = d.sesion;
            final r = d.reporte;
            final metodos = (r['by_method'] as List? ?? [])
                .cast<Map<String, dynamic>>();
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                GlassPanel(
                  tint: s == null
                      ? null
                      : Theme.of(context).colorScheme.primary,
                  padding: const EdgeInsets.all(18),
                  child: s == null
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'La caja está cerrada',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 4),
                            const Text(
                              'Ábrala para registrar los cobros en efectivo del día.',
                            ),
                            const SizedBox(height: 14),
                            FilledButton.icon(
                              onPressed: abrir,
                              icon: const Icon(Icons.lock_open),
                              label: const Text('Abrir caja'),
                            ),
                          ],
                        )
                      : DefaultTextStyle(
                          style: const TextStyle(color: Colors.white),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Caja abierta desde ${fechaHora(s['opened_at'])}',
                                style: const TextStyle(fontSize: 12.5),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                dinero(numero(s['expected_now'])),
                                style: const TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -1,
                                ),
                              ),
                              const Text('Efectivo que debería haber ahora'),
                              const SizedBox(height: 12),
                              Text(
                                'Fondo ${dinero(numero(s['opening_float']))} · '
                                'Entró ${dinero(numero(s['cash_in']))} · '
                                'Salió ${dinero(numero(s['cash_out']))}',
                                style: const TextStyle(fontSize: 12.5),
                              ),
                              const SizedBox(height: 14),
                              FilledButton.icon(
                                style: FilledButton.styleFrom(
                                  backgroundColor: Colors.white,
                                  foregroundColor: const Color(0xFF0B5F58),
                                ),
                                onPressed: () => cerrar(s),
                                icon: const Icon(Icons.lock),
                                label: const Text('Cerrar caja (arqueo)'),
                              ),
                            ],
                          ),
                        ),
                ),
                const SizedBox(height: 14),
                RejillaKpi(
                  hijos: [
                    Kpi(
                      etiqueta: 'Cobrado hoy',
                      valor: dinero(numero(r['total'])),
                      icono: Icons.payments_outlined,
                      detalle: '${r['payment_count'] ?? 0} cobros',
                    ),
                    Kpi(
                      etiqueta: 'Egresos hoy',
                      valor: dinero(numero(r['expenses_total'])),
                      icono: Icons.trending_down,
                      color: Tonos.rojo,
                      detalle: '${r['expenses_count'] ?? 0} gastos',
                    ),
                  ],
                ),
                if (metodos.isNotEmpty) ...[
                  const Seccion('Por forma de pago'),
                  GlassCard(
                    child: Column(
                      children: [
                        for (final m in metodos)
                          ListTile(
                            dense: true,
                            title: Text('${m['label']}'),
                            subtitle: Text('${m['count']} cobros'),
                            trailing: Text(
                              dinero(numero(m['total'])),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
                const Seccion('Cobros de hoy'),
                if (d.cobros.isEmpty)
                  const EstadoVacio(
                    icono: Icons.receipt_long,
                    titulo: 'Todavía no hay cobros hoy',
                  )
                else
                  for (final p in d.cobros)
                    FilaTarjeta(
                      icono: Icons.payments_outlined,
                      titulo: '${p['patient_name']}',
                      subtitulo: [
                        '${p['method_label']}',
                        if (p['concept'] != null) '${p['concept']}',
                        if (p['voided_at'] != null) 'Anulado',
                      ].join(' · '),
                      tachado: p['voided_at'] != null,
                      derecha: Text(
                        dinero(numero(p['amount'])),
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                finDeLista,
              ],
            );
          },
        ),
      ),
    );
  }
}
