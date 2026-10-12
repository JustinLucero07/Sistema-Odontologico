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
final _fijosProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/finance/recurring-expenses'),
);
final _diasProyeccion = StateProvider.autoDispose<int>((ref) => 30);
final _proyeccionProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref
      .watch(apiProvider)
      .mapa('/finance/projection', query: {'days': ref.watch(_diasProyeccion)}),
);
final _egresosProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/finance/expenses'),
);

/// Finanzas: resultado del periodo (ventas, ingresos, egresos, utilidad),
/// cobros y egresos con su alta, edición y anulación, gastos fijos del mes y
/// la proyección de lo que entra y sale en los próximos días.
class FinanzasPage extends ConsumerWidget {
  const FinanzasPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 5,
      child: Builder(
        builder: (context) {
          final pestana = DefaultTabController.of(context);
          return ListenableBuilder(
            listenable: pestana,
            builder: (context, _) => PaginaModulo(
              titulo: 'Finanzas',
              inferior: const TabBar(
                isScrollable: true,
                tabAlignment: TabAlignment.start,
                tabs: [
                  Tab(text: 'Resumen'),
                  Tab(text: 'Cobros'),
                  Tab(text: 'Egresos'),
                  Tab(text: 'Gastos fijos'),
                  Tab(text: 'Proyección'),
                ],
              ),
              accion: pestana.index == 3
                  ? FloatingActionButton.extended(
                      onPressed: () => editarGastoFijo(context, ref, null),
                      icon: const Icon(Icons.add),
                      label: const Text('Gasto fijo'),
                    )
                  : pestana.index == 4
                  ? null
                  : FloatingActionButton.extended(
                      onPressed: () => editarEgreso(context, ref, null),
                      icon: const Icon(Icons.add),
                      label: const Text('Egreso'),
                    ),
              cuerpo: const TabBarView(
                children: [
                  _Resumen(),
                  _Cobros(),
                  _Egresos(),
                  _Fijos(),
                  _Proyeccion(),
                ],
              ),
            ),
          );
        },
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

/// Alta y edición de un gasto fijo (arriendo, internet, sueldo…).
Future<void> editarGastoFijo(
  BuildContext context,
  WidgetRef ref,
  Map<String, dynamic>? g,
) async {
  final api = ref.read(apiProvider);
  final categorias = await cargarOAvisar(context, ref.read(categoriasEgresoProvider.future));
  if (categorias == null || !context.mounted) return;
  final formas = await cargarOAvisar(context, ref.read(formasPagoProvider.future));
  if (formas == null || !context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: g == null ? 'Nuevo gasto fijo' : 'Editar gasto fijo',
    subtitulo: 'Lo que pagas todos los meses. Cada mes lo registras con un toque.',
    icono: Icons.event_repeat,
    campos: [
      Campo('description', 'Descripción', requerido: true, inicial: g?['description'], ayuda: 'Ej. Arriendo del consultorio'),
      Campo('category', 'Categoría', tipo: TipoCampo.seleccion, requerido: true, opciones: categorias, inicial: g?['category'], mitad: true),
      Campo('amount', 'Importe mensual', tipo: TipoCampo.dinero, requerido: true, inicial: g?['amount'], mitad: true),
      Campo('day_of_month', 'Día del mes (1-28)', tipo: TipoCampo.entero, requerido: true, inicial: g?['day_of_month'] ?? 1, mitad: true),
      Campo('method', 'Forma de pago', tipo: TipoCampo.seleccion, requerido: true, opciones: formas, inicial: g?['method'] ?? 'transferencia', mitad: true),
      Campo('supplier_name', 'Proveedor', inicial: g?['supplier_name']),
      Campo('is_active', 'Activo', tipo: TipoCampo.interruptor, inicial: g?['is_active'] ?? true),
    ],
    alGuardar: (v) async {
      if (g == null) {
        await api.post('/finance/recurring-expenses', v);
      } else {
        await api.put('/finance/recurring-expenses/${g['id']}', v);
      }
      ref.invalidate(_fijosProvider);
      ref.invalidate(_proyeccionProvider);
    },
  );
}

class _Fijos extends ConsumerWidget {
  const _Fijos();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_fijosProvider),
      child: Asincrono(
        valor: ref.watch(_fijosProvider),
        alReintentar: () => ref.invalidate(_fijosProvider),
        listo: (lista) {
          if (lista.isEmpty) {
            return ListView(
              children: const [
                EstadoVacio(
                  icono: Icons.event_repeat,
                  titulo: 'Sin gastos fijos',
                  detalle: 'Agrega el arriendo, internet, sueldos… y cada mes los registras con un toque.',
                ),
              ],
            );
          }
          final activos = lista.where((g) => g['is_active'] == true);
          final mensual = activos.fold<double>(0, (a, g) => a + numero(g['amount']));
          final pendientes = activos.where((g) => g['due_this_month'] == true).toList();
          final porPagar = pendientes.fold<double>(0, (a, g) => a + numero(g['amount']));
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              RejillaKpi(
                hijos: [
                  Kpi(etiqueta: 'Gasto fijo al mes', valor: dinero(mensual), icono: Icons.event_repeat, color: Tonos.rojo),
                  Kpi(
                    etiqueta: 'Por registrar este mes · ${pendientes.length}',
                    valor: dinero(porPagar),
                    icono: Icons.pending_actions,
                    color: Tonos.ambar,
                  ),
                ],
              ),
              const Seccion('Tus gastos fijos'),
              for (final g in lista)
                FilaTarjeta(
                  icono: g['due_this_month'] == true ? Icons.pending_actions : Icons.check_circle_outline,
                  colorIcono: g['is_active'] != true
                      ? Tonos.gris
                      : g['due_this_month'] == true
                      ? Tonos.ambar
                      : Tonos.verde,
                  titulo: '${g['description']}',
                  subtitulo: [
                    'Día ${g['day_of_month']}',
                    '${g['category_label']}',
                    if (g['is_active'] != true)
                      'Pausado'
                    else if (g['due_this_month'] == true)
                      'Pendiente este mes'
                    else
                      'Registrado este mes',
                  ].join(' · '),
                  tachado: g['is_active'] != true,
                  alTocar: () => _acciones(context, ref, api, g),
                  derecha: Text(dinero(numero(g['amount'])), style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
              finDeLista,
            ],
          );
        },
      ),
    );
  }

  void _acciones(BuildContext context, WidgetRef ref, Api api, Map<String, dynamic> g) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (hoja) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (g['due_this_month'] == true)
              ListTile(
                leading: const Icon(Icons.task_alt, color: Tonos.verde),
                title: Text('Registrar pago de este mes (${dinero(numero(g['amount']))})'),
                subtitle: const Text('Se crea el egreso con fecha de hoy.'),
                onTap: () async {
                  Navigator.pop(hoja);
                  if (await intentar(
                    context,
                    () => api.post('/finance/recurring-expenses/${g['id']}/register', {}),
                    exito: 'Egreso registrado',
                  )) {
                    ref.invalidate(_fijosProvider);
                    ref.invalidate(_egresosProvider);
                    ref.invalidate(_resumenProvider);
                    ref.invalidate(_proyeccionProvider);
                  }
                },
              ),
            ListTile(
              leading: const Icon(Icons.edit_outlined),
              title: const Text('Editar'),
              onTap: () {
                Navigator.pop(hoja);
                editarGastoFijo(context, ref, g);
              },
            ),
            ListTile(
              leading: Icon(Icons.delete_outline, color: Theme.of(context).colorScheme.error),
              title: const Text('Eliminar'),
              subtitle: const Text('Los egresos ya registrados se conservan.'),
              onTap: () async {
                Navigator.pop(hoja);
                if (await confirmar(context, titulo: '¿Eliminar «${g['description']}»?', textoConfirmar: 'Eliminar', peligro: true) &&
                    context.mounted &&
                    await intentar(context, () => api.delete('/finance/recurring-expenses/${g['id']}'))) {
                  ref.invalidate(_fijosProvider);
                  ref.invalidate(_proyeccionProvider);
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _Proyeccion extends ConsumerWidget {
  const _Proyeccion();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dias = ref.watch(_diasProyeccion);
    final tenue = Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.55);
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_proyeccionProvider),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Wrap(
            spacing: 8,
            children: [
              for (final d in const [15, 30, 60, 90])
                ChoiceChip(
                  label: Text('$d días'),
                  selected: dias == d,
                  onSelected: (_) => ref.read(_diasProyeccion.notifier).state = d,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Asincrono(
            valor: ref.watch(_proyeccionProvider),
            alReintentar: () => ref.invalidate(_proyeccionProvider),
            esqueleto: const SizedBox(
              height: 420,
              child: EsqueletoLista(filas: 4, conTarjetas: true),
            ),
            listo: (p) {
              final items = ((p['items'] as List?) ?? []).cast<Map<String, dynamic>>();
              final neto = numero(p['net']);
              final porFecha = <String, List<Map<String, dynamic>>>{};
              for (final i in items) {
                porFecha.putIfAbsent('${i['on']}', () => []).add(i);
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  RejillaKpi(
                    hijos: [
                      Kpi(etiqueta: 'Por entrar', valor: dinero(numero(p['expected_in'])), icono: Icons.south_west, color: Tonos.verde),
                      Kpi(etiqueta: 'Por salir', valor: dinero(numero(p['expected_out'])), icono: Icons.north_east, color: Tonos.rojo),
                      Kpi(
                        etiqueta: 'Balance previsto',
                        valor: dinero(neto),
                        icono: Icons.account_balance_wallet_outlined,
                        color: neto >= 0 ? Tonos.verde : Tonos.rojo,
                      ),
                      Kpi(
                        etiqueta: 'Cuotas vencidas',
                        valor: dinero(numero(p['overdue_in'])),
                        icono: Icons.warning_amber_rounded,
                        color: Tonos.ambar,
                      ),
                    ],
                  ),
                  if (items.isEmpty)
                    const EstadoVacio(
                      icono: Icons.event_available,
                      titulo: 'Nada previsto',
                      detalle: 'Aquí aparecen las cuotas de créditos y los gastos fijos que vienen.',
                    ),
                  for (final MapEntry(key: fecha, value: del) in porFecha.entries) ...[
                    Padding(
                      padding: const EdgeInsets.fromLTRB(4, 14, 4, 6),
                      child: Text(fechaCorta(fecha), style: TextStyle(fontWeight: FontWeight.w700, color: tenue)),
                    ),
                    for (final i in del)
                      FilaTarjeta(
                        icono: i['kind'] == 'gasto_fijo' ? Icons.event_repeat : Icons.payments_outlined,
                        colorIcono: numero(i['amount']) < 0 ? Tonos.rojo : Tonos.verde,
                        titulo: '${i['label']}',
                        subtitulo: i['patient_name'] == null ? 'Gasto fijo' : '${i['patient_name']}',
                        derecha: Text(
                          '${numero(i['amount']) < 0 ? '−' : '+'} ${dinero(numero(i['amount']).abs())}',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            color: numero(i['amount']) < 0 ? Tonos.rojo : Tonos.verde,
                          ),
                        ),
                      ),
                  ],
                  finDeLista,
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
