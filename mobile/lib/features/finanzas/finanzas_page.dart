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

final _resumenProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/finance/summary'),
);
final _cobrosProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/finance/payments'),
);
final _egresosProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/finance/expenses'),
);

/// Finanzas: resultado del periodo (ventas, ingresos, egresos, utilidad),
/// cobros y egresos con su alta, edición y anulación.
class FinanzasPage extends ConsumerWidget {
  const FinanzasPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 3,
      child: PaginaModulo(
        titulo: 'Finanzas',
        inferior: const TabBar(
          tabs: [
            Tab(text: 'Resumen'),
            Tab(text: 'Cobros'),
            Tab(text: 'Egresos'),
          ],
        ),
        accion: FloatingActionButton.extended(
          onPressed: () => editarEgreso(context, ref, null),
          icon: const Icon(Icons.add),
          label: const Text('Egreso'),
        ),
        cuerpo: const TabBarView(children: [_Resumen(), _Cobros(), _Egresos()]),
      ),
    );
  }
}

Future<void> editarEgreso(
  BuildContext context,
  WidgetRef ref,
  Map<String, dynamic>? egreso,
) async {
  final api = ref.read(apiProvider);
  final categorias = await cargarOAvisar(
    context,
    ref.read(categoriasEgresoProvider.future),
  );
  if (categorias == null) return;
  if (!context.mounted) return;
  final formas = await cargarOAvisar(
    context,
    ref.read(formasPagoProvider.future),
  );
  if (formas == null) return;
  if (!context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: egreso == null ? 'Nuevo egreso' : 'Editar egreso',
    subtitulo: egreso == null
        ? 'Un gasto de la clínica: insumos, laboratorio, servicios…'
        : 'El importe no se edita: si está mal, anule y registre de nuevo.',
    icono: Icons.trending_down,
    campos: [
      Campo(
        'spent_on',
        'Fecha',
        tipo: TipoCampo.fecha,
        requerido: true,
        inicial: egreso?['spent_on'] ?? hoyIso(),
        mitad: true,
      ),
      Campo(
        'category',
        'Categoría',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: categorias,
        inicial: egreso?['category'],
        mitad: true,
      ),
      Campo(
        'description',
        'Descripción',
        requerido: true,
        inicial: egreso?['description'],
      ),
      if (egreso == null) ...[
        const Campo(
          'amount',
          'Importe',
          tipo: TipoCampo.dinero,
          requerido: true,
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
      ],
      Campo(
        'supplier_name',
        'Proveedor',
        inicial: egreso?['supplier_name'],
        mitad: true,
      ),
      Campo(
        'receipt_number',
        'N.º factura',
        inicial: egreso?['receipt_number'],
        mitad: true,
      ),
      Campo(
        'notes',
        'Notas',
        tipo: TipoCampo.multilinea,
        inicial: egreso?['notes'],
      ),
    ],
    alGuardar: (v) async {
      if (egreso == null) {
        await api.post('/finance/expenses', v);
      } else {
        await api.put('/finance/expenses/${egreso['id']}', v);
      }
      ref.invalidate(_egresosProvider);
      ref.invalidate(_resumenProvider);
    },
  );
}

class _Resumen extends ConsumerWidget {
  const _Resumen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_resumenProvider),
      child: Asincrono(
        valor: ref.watch(_resumenProvider),
        alReintentar: () => ref.invalidate(_resumenProvider),
        esqueleto: const EsqueletoLista(filas: 3, conTarjetas: true),
        listo: (r) {
          final porMetodo = (r['income_by_method'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          final porCategoria = (r['expenses_by_category'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          final meses = (r['monthly'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          final neto = numero(r['net']);
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'Del ${fechaCorta(r['date_from'])} al ${fechaCorta(r['date_to'])}',
                style: TextStyle(
                  fontSize: 12.5,
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.55),
                ),
              ),
              const SizedBox(height: 10),
              RejillaKpi(
                hijos: [
                  Kpi(
                    etiqueta: 'Ventas',
                    valor: dinero(numero(r['sales'])),
                    icono: Icons.sell_outlined,
                  ),
                  Kpi(
                    etiqueta: 'Ingresos',
                    valor: dinero(numero(r['income'])),
                    icono: Icons.trending_up,
                    color: Tonos.verde,
                  ),
                  Kpi(
                    etiqueta: 'Egresos',
                    valor: dinero(numero(r['expenses'])),
                    icono: Icons.trending_down,
                    color: Tonos.rojo,
                  ),
                  Kpi(
                    etiqueta: 'Utilidad',
                    valor: dinero(neto),
                    icono: Icons.savings_outlined,
                    color: neto >= 0 ? Tonos.verde : Tonos.rojo,
                  ),
                  Kpi(
                    etiqueta: 'Por cobrar',
                    valor: dinero(numero(r['receivables'])),
                    icono: Icons.hourglass_bottom,
                    color: Tonos.ambar,
                  ),
                ],
              ),
              if (meses.isNotEmpty) ...[
                const Seccion('Últimos meses'),
                GlassCard(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: _BarrasMes(meses: meses),
                  ),
                ),
              ],
              if (porMetodo.isNotEmpty) ...[
                const Seccion('Ingresos por forma de pago'),
                for (final m in porMetodo)
                  FilaTarjeta(
                    icono: Icons.account_balance_wallet_outlined,
                    titulo: '${m['label']}',
                    subtitulo: '${m['count']} cobros',
                    derecha: Text(
                      dinero(numero(m['total'])),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
              ],
              if (porCategoria.isNotEmpty) ...[
                const Seccion('Egresos por categoría'),
                for (final c in porCategoria)
                  FilaTarjeta(
                    icono: Icons.category_outlined,
                    colorIcono: Tonos.rojo,
                    titulo: '${c['label']}',
                    derecha: Text(
                      dinero(numero(c['total'])),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
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

/// Ingresos y egresos por mes en barras dobles.
class _BarrasMes extends StatelessWidget {
  const _BarrasMes({required this.meses});

  final List<Map<String, dynamic>> meses;

  @override
  Widget build(BuildContext context) {
    final maximo = meses
        .expand((m) => [numero(m['income']), numero(m['expenses'])])
        .fold<double>(1, (a, b) => b > a ? b : a);
    final tenue = Theme.of(
      context,
    ).colorScheme.onSurface.withValues(alpha: 0.55);
    return Column(
      children: [
        SizedBox(
          height: 130,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              for (final m in meses)
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          _barra(numero(m['income']) / maximo, Tonos.verde),
                          const SizedBox(width: 3),
                          _barra(numero(m['expenses']) / maximo, Tonos.rojo),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${m['month']}'.length >= 7
                            ? '${m['month']}'.substring(5, 7)
                            : '${m['month']}',
                        style: TextStyle(fontSize: 10.5, color: tenue),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _leyenda('Ingresos', Tonos.verde),
            const SizedBox(width: 16),
            _leyenda('Egresos', Tonos.rojo),
          ],
        ),
      ],
    );
  }

  Widget _barra(double fraccion, Color color) => Container(
    width: 9,
    height: 4 + 100 * fraccion.clamp(0, 1),
    decoration: BoxDecoration(
      color: color,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
    ),
  );

  Widget _leyenda(String texto, Color color) => Row(
    children: [
      Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(3),
        ),
      ),
      const SizedBox(width: 5),
      Text(texto, style: const TextStyle(fontSize: 12)),
    ],
  );
}

class _Cobros extends ConsumerWidget {
  const _Cobros();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_cobrosProvider),
      child: Asincrono(
        valor: ref.watch(_cobrosProvider),
        alReintentar: () => ref.invalidate(_cobrosProvider),
        listo: (lista) => lista.isEmpty
            ? ListView(
                children: const [
                  EstadoVacio(
                    icono: Icons.payments_outlined,
                    titulo: 'Sin cobros en el periodo',
                  ),
                ],
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final p in lista)
                    FilaTarjeta(
                      icono: Icons.payments_outlined,
                      colorIcono: Tonos.verde,
                      titulo: '${p['patient_name']}',
                      subtitulo: [
                        fechaCorta(p['received_on']),
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
              ),
      ),
    );
  }
}

class _Egresos extends ConsumerWidget {
  const _Egresos();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_egresosProvider),
      child: Asincrono(
        valor: ref.watch(_egresosProvider),
        alReintentar: () => ref.invalidate(_egresosProvider),
        listo: (lista) => lista.isEmpty
            ? ListView(
                children: const [
                  EstadoVacio(
                    icono: Icons.trending_down,
                    titulo: 'Sin egresos registrados',
                    detalle: 'Registre los gastos con el botón «Egreso».',
                  ),
                ],
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final e in lista)
                    FilaTarjeta(
                      icono: Icons.receipt_outlined,
                      colorIcono: Tonos.rojo,
                      titulo: '${e['description']}',
                      subtitulo: [
                        fechaCorta(e['spent_on']),
                        '${e['category_label']}',
                        '${e['method_label']}',
                        if (e['voided_at'] != null)
                          'Anulado: ${e['void_reason']}',
                      ].join(' · '),
                      tachado: e['voided_at'] != null,
                      alTocar: e['voided_at'] != null
                          ? null
                          : () => _acciones(context, ref, api, e),
                      derecha: Text(
                        dinero(numero(e['amount'])),
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                  finDeLista,
                ],
              ),
      ),
    );
  }

  void _acciones(
    BuildContext context,
    WidgetRef ref,
    Api api,
    Map<String, dynamic> e,
  ) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (hoja) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.edit_outlined),
              title: const Text('Editar'),
              onTap: () {
                Navigator.pop(hoja);
                editarEgreso(context, ref, e);
              },
            ),
            ListTile(
              leading: Icon(
                Icons.block,
                color: Theme.of(context).colorScheme.error,
              ),
              title: const Text('Anular'),
              onTap: () {
                Navigator.pop(hoja);
                anularConMotivo(
                  context,
                  que: 'egreso',
                  alAnular: (motivo) async {
                    await api.post('/finance/expenses/${e['id']}/void', {
                      'reason': motivo,
                    });
                    ref.invalidate(_egresosProvider);
                    ref.invalidate(_resumenProvider);
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
