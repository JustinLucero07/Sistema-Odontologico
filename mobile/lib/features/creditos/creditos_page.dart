import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

final _filtroProvider = StateProvider.autoDispose<String?>((ref) => null);

final _resumenCreditosProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>(
      (ref) => ref.watch(apiProvider).mapa('/credits/summary'),
    );

final _creditosProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) {
      final filtro = ref.watch(_filtroProvider);
      return ref
          .watch(apiProvider)
          .lista('/credits', query: {'status': filtro});
    });

final creditoProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>(
      (ref, id) => ref.watch(apiProvider).mapa('/credits/$id'),
    );

const _estados = <Opcion>[
  ('al_dia', 'Al día'),
  ('vencido', 'Con atraso'),
  ('pagado', 'Pagados'),
  ('anulado', 'Anulados'),
];

Color colorCredito(String? estado) => switch (estado) {
  'vencido' => Tonos.rojo,
  'pagado' => Tonos.verde,
  'anulado' => Tonos.gris,
  _ => Tonos.azul,
};

/// Créditos: tratamientos pagados en cuotas, quién va al día y quién no.
class CreditosPage extends ConsumerWidget {
  const CreditosPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filtro = ref.watch(_filtroProvider);
    return PaginaModulo(
      titulo: 'Créditos',
      cuerpo: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(_creditosProvider);
          ref.invalidate(_resumenCreditosProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ref
                .watch(_resumenCreditosProvider)
                .maybeWhen(
                  data: (r) => RejillaKpi(
                    hijos: [
                      Kpi(
                        etiqueta: 'Créditos activos',
                        valor: '${r['active_count']}',
                        icono: Icons.credit_score,
                      ),
                      Kpi(
                        etiqueta: 'Por cobrar',
                        valor: dinero(numero(r['outstanding'])),
                        icono: Icons.account_balance_wallet_outlined,
                      ),
                      Kpi(
                        etiqueta: 'Vencido',
                        valor: dinero(numero(r['overdue_amount'])),
                        icono: Icons.warning_amber,
                        color: Tonos.rojo,
                        detalle: '${r['overdue_count']} con atraso',
                      ),
                      Kpi(
                        etiqueta: 'Cobrado este mes',
                        valor: dinero(numero(r['collected_this_month'])),
                        icono: Icons.trending_up,
                        color: Tonos.verde,
                      ),
                    ],
                  ),
                  orElse: () => const SizedBox(height: 8),
                ),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final (codigo, etiqueta) in [
                    (null, 'Todos'),
                    ..._estados,
                  ])
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(etiqueta),
                        selected: filtro == codigo,
                        onSelected: (_) =>
                            ref.read(_filtroProvider.notifier).state = codigo,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            ref
                .watch(_creditosProvider)
                .when(
                  loading: () =>
                      const EsqueletoLista(filas: 4, dentroDeLista: true),
                  error: (e, _) => EstadoError(
                    mensaje: '$e',
                    onReintentar: () => ref.invalidate(_creditosProvider),
                  ),
                  data: (lista) => lista.isEmpty
                      ? const EstadoVacio(
                          icono: Icons.credit_score,
                          titulo: 'No hay créditos',
                          detalle:
                              'Financie un tratamiento desde la cuenta del paciente.',
                        )
                      : Column(
                          children: [
                            for (final c in lista)
                              FilaTarjeta(
                                icono: Icons.credit_score,
                                colorIcono: colorCredito(c['status']),
                                titulo: '${c['patient_name']}',
                                subtitulo:
                                    '${c['charge_description']} · '
                                    '${c['installment_count']} cuotas ${'${c['frequency_label']}'.toLowerCase()}'
                                    '${c['next_due_on'] != null ? ' · próxima ${fechaCorta(c['next_due_on'])}' : ''}',
                                derecha: Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Text(
                                      dinero(numero(c['pending'])),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Pastilla(
                                      etiquetaDe(_estados, c['status']),
                                      color: colorCredito(c['status']),
                                    ),
                                  ],
                                ),
                                alTocar: () => abrirCredito(
                                  context,
                                  '${c['id']}',
                                  alCambiar: () {
                                    ref.invalidate(_creditosProvider);
                                    ref.invalidate(_resumenCreditosProvider);
                                  },
                                ),
                              ),
                          ],
                        ),
                ),
            finDeLista,
          ],
        ),
      ),
    );
  }
}

Future<void> abrirCredito(
  BuildContext context,
  String id, {
  VoidCallback? alCambiar,
}) => Navigator.of(context).push(
  MaterialPageRoute<void>(
    builder: (_) => CreditoDetallePage(id: id, alCambiar: alCambiar),
  ),
);

/// Detalle de un crédito: calendario de cuotas, pagos y acciones.
class CreditoDetallePage extends ConsumerWidget {
  const CreditoDetallePage({super.key, required this.id, this.alCambiar});

  final String id;
  final VoidCallback? alCambiar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    void refrescar() {
      ref.invalidate(creditoProvider(id));
      alCambiar?.call();
    }

    return PaginaModulo(
      titulo: 'Crédito',
      cuerpo: Asincrono(
        valor: ref.watch(creditoProvider(id)),
        alReintentar: () => ref.invalidate(creditoProvider(id)),
        esqueleto: const EsqueletoLista(filas: 5, conTarjetas: true),
        listo: (c) {
          final activo = c['status'] == 'al_dia' || c['status'] == 'vencido';
          final cuotas = (c['installments'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          final pagos = (c['payments'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          final total = numero(c['total']);
          final pagado = numero(c['paid']);

          Future<void> cobrar() async {
            final formas = await cargarOAvisar(
              context,
              ref.read(formasPagoProvider.future),
            );
            if (formas == null) return;
            if (!context.mounted) return;
            await mostrarFormulario(
              context,
              titulo: 'Cobrar cuota',
              subtitulo:
                  'Pendiente ${dinero(numero(c['pending']))}. El pago cubre las cuotas de la más antigua a la más nueva.',
              icono: Icons.payments_outlined,
              textoGuardar: 'Registrar cobro',
              campos: [
                Campo(
                  'amount',
                  'Importe',
                  tipo: TipoCampo.dinero,
                  requerido: true,
                  inicial: c['next_amount'] ?? c['pending'],
                  mitad: true,
                ),
                Campo(
                  'method',
                  'Forma de pago',
                  tipo: TipoCampo.seleccion,
                  requerido: true,
                  opciones: formas,
                  inicial: 'efectivo',
                  mitad: true,
                ),
                const Campo(
                  'reference',
                  'Referencia (transferencia o tarjeta)',
                ),
                const Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
              ],
              alGuardar: (v) async {
                await api.post('/credits/$id/payments', v);
                refrescar();
              },
            );
          }

          Future<void> garante() => mostrarFormulario(
            context,
            titulo: 'Garante y notas',
            icono: Icons.person_outline,
            campos: [
              Campo(
                'guarantor_name',
                'Nombre del garante',
                inicial: c['guarantor_name'],
              ),
              Campo(
                'guarantor_id_number',
                'Cédula',
                inicial: c['guarantor_id_number'],
                mitad: true,
              ),
              Campo(
                'guarantor_phone',
                'Teléfono',
                tipo: TipoCampo.telefono,
                inicial: c['guarantor_phone'],
                mitad: true,
              ),
              Campo(
                'notes',
                'Notas',
                tipo: TipoCampo.multilinea,
                inicial: c['notes'],
              ),
            ],
            alGuardar: (v) async {
              await api.put('/credits/$id', v);
              refrescar();
            },
          );

          Future<void> reestructurar() async {
            final opciones = await cargarOAvisar(
              context,
              api.mapa('/credits/options'),
            );
            if (opciones == null) return;
            final frecuencias = [
              for (final f in (opciones['frequencies'] as List? ?? []))
                ('${f['code']}', '${f['label']}'),
            ];
            if (!context.mounted) return;
            await mostrarFormulario(
              context,
              titulo: 'Reestructurar',
              subtitulo:
                  'Lo pagado se conserva; el saldo se reparte en cuotas nuevas.',
              icono: Icons.event_repeat,
              campos: [
                const Campo(
                  'installment_count',
                  'Número de cuotas',
                  tipo: TipoCampo.entero,
                  requerido: true,
                  mitad: true,
                ),
                Campo(
                  'frequency',
                  'Frecuencia',
                  tipo: TipoCampo.seleccion,
                  requerido: true,
                  opciones: frecuencias,
                  inicial: c['frequency'],
                  mitad: true,
                ),
                const Campo(
                  'first_due_on',
                  'Primera cuota',
                  tipo: TipoCampo.fecha,
                  requerido: true,
                ),
              ],
              alGuardar: (v) async {
                await api.post('/credits/$id/restructure', v);
                refrescar();
              },
            );
          }

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              GlassPanel(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${c['patient_name']}',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        Pastilla(
                          etiquetaDe(_estados, c['status']),
                          color: colorCredito(c['status']),
                        ),
                      ],
                    ),
                    Text('${c['charge_description']}'),
                    const SizedBox(height: 14),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: total == 0 ? 0 : pagado / total,
                        minHeight: 8,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Pagado ${dinero(pagado)} de ${dinero(total)} · '
                      'pendiente ${dinero(numero(c['pending']))}',
                      style: const TextStyle(fontSize: 13),
                    ),
                    if (numero(c['overdue']) > 0)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(
                          'Vencido ${dinero(numero(c['overdue']))} · ${c['days_late']} días de atraso',
                          style: const TextStyle(
                            color: Tonos.rojo,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    const SizedBox(height: 6),
                    Text(
                      'Entrada ${dinero(numero(c['down_payment']))} · '
                      'interés ${c['monthly_rate']}% mensual · '
                      '${c['installment_count']} cuotas ${'${c['frequency_label']}'.toLowerCase()}',
                      style: TextStyle(
                        fontSize: 12,
                        color: Theme.of(
                          context,
                        ).colorScheme.onSurface.withValues(alpha: 0.55),
                      ),
                    ),
                    if (c['guarantor_name'] != null)
                      Text(
                        'Garante: ${c['guarantor_name']} ${c['guarantor_phone'] ?? ''}',
                        style: const TextStyle(fontSize: 12.5),
                      ),
                  ],
                ),
              ),
              if (activo) ...[
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: cobrar,
                  icon: const Icon(Icons.payments_outlined),
                  label: const Text('Cobrar cuota'),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: garante,
                        icon: const Icon(Icons.person_outline, size: 18),
                        label: const Text('Garante'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: reestructurar,
                        icon: const Icon(Icons.event_repeat, size: 18),
                        label: const Text('Reestructurar'),
                      ),
                    ),
                  ],
                ),
                TextButton.icon(
                  onPressed: () => anularConMotivo(
                    context,
                    que: 'crédito',
                    alAnular: (motivo) async {
                      await api.post('/credits/$id/void', {'reason': motivo});
                      refrescar();
                    },
                  ),
                  style: TextButton.styleFrom(
                    foregroundColor: Theme.of(context).colorScheme.error,
                  ),
                  icon: const Icon(Icons.block, size: 18),
                  label: const Text('Anular crédito (solo sin pagos)'),
                ),
              ],
              const Seccion('Cuotas'),
              for (final q in cuotas)
                FilaTarjeta(
                  icono: q['status'] == 'pagada'
                      ? Icons.check_circle
                      : Icons.event_outlined,
                  colorIcono: switch (q['status']) {
                    'pagada' => Tonos.verde,
                    'vencida' => Tonos.rojo,
                    'parcial' => Tonos.ambar,
                    _ => Tonos.azul,
                  },
                  titulo: 'Cuota ${q['number']} · ${fechaCorta(q['due_on'])}',
                  subtitulo:
                      'Pagado ${dinero(numero(q['paid']))}'
                      '${numero(q['interest']) > 0 ? ' · interés ${dinero(numero(q['interest']))}' : ''}'
                      '${(q['days_late'] ?? 0) > 0 ? ' · ${q['days_late']} días de atraso' : ''}',
                  derecha: Text(
                    dinero(numero(q['amount'])),
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              if (pagos.isNotEmpty) ...[
                const Seccion('Pagos recibidos'),
                for (final p in pagos)
                  FilaTarjeta(
                    icono: Icons.receipt_long,
                    colorIcono: Tonos.verde,
                    titulo: dinero(numero(p['amount'])),
                    subtitulo:
                        '${fechaCorta(p['received_on'])} · ${p['method_label']}'
                        '${p['voided_at'] != null ? ' · Anulado' : ''}',
                    tachado: p['voided_at'] != null,
                  ),
              ],
              finDeLista,
            ],
          );
        },
      ),
    );
  }
}
