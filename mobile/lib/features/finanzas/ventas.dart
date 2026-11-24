import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../core/marca/marca.dart' show colorDeHex;
import '../../shared/widgets/formulario.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/abrir_pdf.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../facturacion/facturacion_page.dart';
import '../pacientes/paciente_detalle_page.dart';

class _Filtro {
  const _Filtro({
    this.periodo = 'mes',
    this.pago = '',
    this.factura = '',
    this.texto = '',
    this.profesional = '',
  });
  final String periodo, pago, factura, texto, profesional;

  _Filtro con({
    String? periodo,
    String? pago,
    String? factura,
    String? texto,
    String? profesional,
  }) => _Filtro(
    periodo: periodo ?? this.periodo,
    pago: pago ?? this.pago,
    factura: factura ?? this.factura,
    texto: texto ?? this.texto,
    profesional: profesional ?? this.profesional,
  );

  (String, String) get rango {
    final hoy = DateTime.now();
    final f = DateFormat('yyyy-MM-dd');
    return switch (periodo) {
      'anterior' => (
        f.format(DateTime(hoy.year, hoy.month - 1, 1)),
        f.format(DateTime(hoy.year, hoy.month, 0)),
      ),
      'anio' => (f.format(DateTime(hoy.year, 1, 1)), f.format(hoy)),
      _ => (f.format(DateTime(hoy.year, hoy.month, 1)), f.format(hoy)),
    };
  }

  @override
  bool operator ==(Object o) =>
      o is _Filtro &&
      o.periodo == periodo &&
      o.pago == pago &&
      o.factura == factura &&
      o.texto == texto &&
      o.profesional == profesional;

  @override
  int get hashCode => Object.hash(periodo, pago, factura, texto, profesional);
}

final _filtroProvider = StateProvider.autoDispose<_Filtro>(
  (ref) => const _Filtro(),
);

final ventasProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) {
  final f = ref.watch(_filtroProvider);
  final (desde, hasta) = f.rango;
  return ref
      .watch(apiProvider)
      .mapa(
        '/sales',
        query: {
          'desde': desde,
          'hasta': hasta,
          if (f.pago.isNotEmpty) 'pago': f.pago,
          if (f.factura.isNotEmpty) 'factura': f.factura,
          if (f.texto.trim().isNotEmpty) 'q': f.texto.trim(),
          if (f.profesional.isNotEmpty) 'profesional': f.profesional,
        },
      );
});

final porProfesionalProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) {
    final (desde, hasta) = ref.watch(_filtroProvider.select((f) => f.rango));
    return ref
        .watch(apiProvider)
        .mapa(
          '/sales/by-professional',
          query: {'desde': desde, 'hasta': hasta},
        );
  },
);

final _modoProvider = StateProvider.autoDispose<String>((ref) => 'ventas');

const _origen = {
  'ortodoncia': 'Ortodoncia',
  'credito': 'Crédito',
  'presupuesto': 'Presupuesto',
  'manual': 'Cargo',
};
const _estado = {
  'pendiente': 'Por cobrar',
  'parcial': 'Abonada',
  'pagada': 'Pagada',
  'anulada': 'Anulada',
};

Color _colorEstado(String e) => switch (e) {
  'pagada' => Tonos.verde,
  'pendiente' => Tonos.rojo,
  'parcial' => Tonos.ambar,
  _ => Tonos.gris,
};

String _fecha(dynamic iso) =>
    DateFormat('dd/MM/yy').format(DateTime.parse('$iso'));

class VentasVista extends ConsumerStatefulWidget {
  const VentasVista({super.key});

  @override
  ConsumerState<VentasVista> createState() => _VentasVistaState();
}

class _VentasVistaState extends ConsumerState<VentasVista> {
  final _buscar = TextEditingController();

  @override
  void dispose() {
    _buscar.dispose();
    super.dispose();
  }

  Future<void> _facturar(List<Map<String, dynamic>> ventas) async {
    if (ventas.isEmpty) return;
    final ok = await emitirFactura(
      context,
      ref,
      pacienteId: '${ventas.first['patient_id']}',
      pacienteNombre: '${ventas.first['paciente']}',
      cargos: [for (final v in ventas) '${v['id']}'],
    );
    if (ok) ref.invalidate(ventasProvider);
  }

  @override
  Widget build(BuildContext context) {
    final f = ref.watch(_filtroProvider);
    final puedeFacturar =
        ref.watch(authProvider).usuario?.puede('invoices:write') ?? false;
    final scheme = Theme.of(context).colorScheme;
    void cambiar(_Filtro n) => ref.read(_filtroProvider.notifier).state = n;
    final modo = ref.watch(_modoProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(ventasProvider);
        ref.invalidate(porProfesionalProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
        children: [
          SegmentedButton<String>(
            showSelectedIcon: false,
            segments: const [
              ButtonSegment(
                value: 'ventas',
                icon: Icon(Icons.receipt_long, size: 18),
                label: Text('Ventas'),
              ),
              ButtonSegment(
                value: 'profesional',
                icon: Icon(Icons.badge_outlined, size: 18),
                label: Text('Por profesional'),
              ),
            ],
            selected: {modo},
            onSelectionChanged: (v) =>
                ref.read(_modoProvider.notifier).state = v.first,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final (k, t) in const [
                ('mes', 'Este mes'),
                ('anterior', 'Mes anterior'),
                ('anio', 'Este año'),
              ])
                ChoiceChip(
                  label: Text(t),
                  selected: f.periodo == k,
                  onSelected: (_) => cambiar(f.con(periodo: k)),
                ),
            ],
          ),
          if (modo == 'profesional') ...[
            const SizedBox(height: 10),
            _PorProfesional(
              alElegir: (id) {
                cambiar(f.con(profesional: id));
                ref.read(_modoProvider.notifier).state = 'ventas';
              },
            ),
          ] else ...[
            if (f.profesional.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: InputChip(
                  label: Text(
                    f.profesional == 'sin'
                        ? 'Sin profesional asignado'
                        : 'Filtrado por profesional',
                  ),
                  onDeleted: () => cambiar(f.con(profesional: '')),
                ),
              ),
            const SizedBox(height: 8),
            TextField(
              controller: _buscar,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Paciente, cédula o concepto',
                isDense: true,
              ),
              onSubmitted: (t) => cambiar(f.con(texto: t)),
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final (k, t) in const [
                    ('', 'Todas'),
                    ('pendiente', 'Por cobrar'),
                    ('parcial', 'Abonadas'),
                    ('pagada', 'Pagadas'),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: FilterChip(
                        label: Text(t),
                        selected: f.pago == k,
                        onSelected: (_) => cambiar(f.con(pago: k)),
                      ),
                    ),
                  const SizedBox(width: 6),
                  for (final (k, t) in const [
                    ('sin_facturar', 'Sin facturar'),
                    ('facturada', 'Facturadas'),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: FilterChip(
                        label: Text(t),
                        selected: f.factura == k,
                        onSelected: (v) => cambiar(f.con(factura: v ? k : '')),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            ref
                .watch(ventasProvider)
                .when(
                  loading: () => const Padding(
                    padding: EdgeInsets.all(40),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (e, _) => EstadoError(
                    mensaje: e is ErrorApi
                        ? e.mensaje
                        : 'No se pudieron cargar las ventas.',
                    onReintentar: () => ref.invalidate(ventasProvider),
                  ),
                  data: (d) {
                    final r = d['resumen'] as Map<String, dynamic>;
                    final items = (d['items'] as List)
                        .cast<Map<String, dynamic>>();
                    final lista = d['facturacion_lista'] == true;
                    final grupos = <String, List<Map<String, dynamic>>>{};
                    for (final v in items) {
                      grupos.putIfAbsent('${v['patient_id']}', () => []).add(v);
                    }
                    final orden = grupos.values.toList()
                      ..sort(
                        (a, b) => b
                            .fold<double>(0, (s, v) => s + numero(v['monto']))
                            .compareTo(
                              a.fold<double>(
                                0,
                                (s, v) => s + numero(v['monto']),
                              ),
                            ),
                      );
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        GridView.count(
                          crossAxisCount: 2,
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          mainAxisSpacing: 8,
                          crossAxisSpacing: 8,
                          childAspectRatio: 2.3,
                          children: [
                            _Cifra(
                              'Vendido',
                              r['vendido'],
                              '${r['ventas']} ventas · ${r['pacientes']} pacientes',
                              null,
                            ),
                            _Cifra(
                              'Cobrado',
                              r['cobrado'],
                              'De estas ventas',
                              Tonos.verde,
                            ),
                            _Cifra(
                              'Por cobrar',
                              r['pendiente'],
                              'Saldo pendiente',
                              Tonos.rojo,
                            ),
                            _Cifra(
                              'Sin facturar',
                              r['sin_facturar'],
                              'Facturado ${dinero(numero(r['facturado']))}',
                              Tonos.ambar,
                            ),
                          ],
                        ),
                        if (numero(r['abonos_sin_asignar']) > 0)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              'Además hay ${dinero(numero(r['abonos_sin_asignar']))} en abonos a cuenta sin asignar a una venta.',
                              style: TextStyle(
                                fontSize: 12,
                                color: scheme.onSurface.withValues(alpha: 0.6),
                              ),
                            ),
                          ),
                        if (puedeFacturar && !lista)
                          Padding(
                            padding: const EdgeInsets.only(top: 10),
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Tonos.ambar.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Text(
                                'Para emitir facturas electrónicas falta: ${(d['faltantes'] as List).join(' ')}',
                                style: const TextStyle(fontSize: 12.5),
                              ),
                            ),
                          ),
                        const SizedBox(height: 12),
                        if (items.isEmpty)
                          const EstadoVacio(
                            icono: Icons.receipt_long,
                            titulo: 'Sin ventas',
                            detalle: 'No hay ventas con estos filtros.',
                          ),
                        for (final g in orden)
                          _GrupoPaciente(
                            ventas: g,
                            puedeFacturar: puedeFacturar && lista,
                            alFacturar: _facturar,
                          ),
                      ],
                    );
                  },
                ),
          ],
        ],
      ),
    );
  }
}

class _Cifra extends StatelessWidget {
  const _Cifra(this.titulo, this.valor, this.detalle, this.color);
  final String titulo, detalle;
  final dynamic valor;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final tenue = Theme.of(
      context,
    ).colorScheme.onSurface.withValues(alpha: 0.6);
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              titulo,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: tenue,
              ),
            ),
            FittedBox(
              child: Text(
                dinero(numero(valor)),
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.w800,
                  color: color,
                ),
              ),
            ),
            Text(
              detalle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10.5, color: tenue),
            ),
          ],
        ),
      ),
    );
  }
}

class _GrupoPaciente extends ConsumerWidget {
  const _GrupoPaciente({
    required this.ventas,
    required this.puedeFacturar,
    required this.alFacturar,
  });
  final List<Map<String, dynamic>> ventas;
  final bool puedeFacturar;
  final Future<void> Function(List<Map<String, dynamic>>) alFacturar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final p = ventas.first;
    final vivas = ventas.where((v) => v['anulada'] != true);
    final total = vivas.fold<double>(0, (s, v) => s + numero(v['monto']));
    final pendiente = vivas.fold<double>(
      0,
      (s, v) => s + numero(v['pendiente']),
    );
    final facturables = ventas.where((v) => v['facturable'] == true).toList();
    final tenue = Theme.of(
      context,
    ).colorScheme.onSurface.withValues(alpha: 0.6);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 8, 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => PacienteDetallePage(
                            pacienteId: '${p['patient_id']}',
                            nombre: '${p['paciente']}',
                          ),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${p['paciente']}',
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                          Text(
                            'Total ${dinero(total)}${pendiente > 0 ? ' · Pendiente ${dinero(pendiente)}' : ' · Al día'}',
                            style: TextStyle(
                              fontSize: 12,
                              color: pendiente > 0 ? Tonos.rojo : tenue,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (puedeFacturar && facturables.isNotEmpty)
                    TextButton.icon(
                      key: Key('facturar-${p['patient_id']}'),
                      onPressed: () => alFacturar(facturables),
                      icon: const Icon(Icons.request_quote_outlined, size: 18),
                      label: Text('Facturar ${facturables.length}'),
                    ),
                ],
              ),
              for (final v in ventas)
                InkWell(
                  onTap: () => _detalle(context, ref, v),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 62,
                          child: Text(
                            _fecha(v['fecha']),
                            style: TextStyle(fontSize: 12, color: tenue),
                          ),
                        ),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${v['descripcion']}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  decoration: v['anulada'] == true
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                              Text(
                                '${v['profesional'] ?? 'Sin profesional'}',
                                style: TextStyle(fontSize: 11.5, color: tenue),
                              ),
                              Text(
                                v['factura'] != null
                                    ? 'Factura ${v['factura']['numero']}'
                                    : v['facturable'] == true
                                    ? 'Sin facturar'
                                    : '${v['motivo'] ?? ''}',
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: v['factura'] != null
                                      ? Theme.of(context).colorScheme.primary
                                      : Tonos.ambar,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              dinero(numero(v['monto'])),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Pastilla(
                              _estado[v['estado_pago']] ??
                                  '${v['estado_pago']}',
                              color: _colorEstado('${v['estado_pago']}'),
                            ),
                          ],
                        ),
                        const Icon(Icons.chevron_right),
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

  void _detalle(BuildContext context, WidgetRef ref, Map<String, dynamic> v) {
    final pagos = (v['pagos'] as List).cast<Map<String, dynamic>>();
    final factura = v['factura'] as Map<String, dynamic>?;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (hoja) {
        final tenue = TextStyle(
          fontSize: 12.5,
          color: Theme.of(hoja).colorScheme.onSurface.withValues(alpha: 0.6),
        );
        return SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  '${v['descripcion']}',
                  style: Theme.of(hoja).textTheme.titleLarge,
                ),
                Text(
                  '${v['paciente']} · ${_fecha(v['fecha'])} · ${_origen[v['origen']] ?? ''}',
                  style: tenue,
                ),
                const SizedBox(height: 10),
                Text(
                  'Valor ${dinero(numero(v['monto']))} · Cobrado ${dinero(numero(v['pagado']))} · Pendiente ${dinero(numero(v['pendiente']))}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const Seccion('Profesional'),
                _ElegirProfesional(venta: v),
                const Seccion('Pagos'),
                if (pagos.isEmpty) Text('Sin pagos registrados.', style: tenue),
                for (final p in pagos)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    title: Text(
                      '${dinero(numero(p['monto']))} · ${p['medio']}',
                    ),
                    subtitle: Text(
                      '${_fecha(p['fecha'])} · ${p['referencia'] ?? 'Sin referencia'}',
                    ),
                    trailing: p['comprobante_id'] == null
                        ? null
                        : TextButton(
                            onPressed: () => abrirArchivo(
                              hoja,
                              ref,
                              '/portal-receipts/${p['comprobante_id']}/file',
                              'comprobante-${p['comprobante_id']}',
                              tipo: null,
                            ),
                            child: const Text('Comprobante'),
                          ),
                  ),
                const Seccion('Factura electrónica'),
                if (factura != null) ...[
                  Text(
                    '${factura['numero']} · ${factura['estado']} · ${_fecha(factura['fecha'])}',
                  ),
                  const SizedBox(height: 6),
                  OutlinedButton.icon(
                    onPressed: () {
                      Navigator.pop(hoja);
                      verFactura(context, ref, '${factura['id']}');
                    },
                    icon: const Icon(Icons.open_in_new, size: 18),
                    label: const Text('Ver factura'),
                  ),
                ] else if (v['facturable'] == true) ...[
                  Text('Todavía no tiene factura.', style: tenue),
                  if (puedeFacturar) ...[
                    const SizedBox(height: 6),
                    FilledButton.icon(
                      onPressed: () {
                        Navigator.pop(hoja);
                        alFacturar([v]);
                      },
                      icon: const Icon(Icons.request_quote_outlined, size: 18),
                      label: const Text('Facturar esta venta'),
                    ),
                  ],
                ] else
                  Text('${v['motivo'] ?? ''}', style: tenue),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ElegirProfesional extends ConsumerStatefulWidget {
  const _ElegirProfesional({required this.venta});
  final Map<String, dynamic> venta;

  @override
  ConsumerState<_ElegirProfesional> createState() => _ElegirProfesionalState();
}

class _ElegirProfesionalState extends ConsumerState<_ElegirProfesional> {
  late String _valor = '${widget.venta['professional_id'] ?? ''}';

  @override
  Widget build(BuildContext context) {
    final puede =
        ref.watch(authProvider).usuario?.puede('payments:write') ?? false;
    final profs = ref.watch(profesionalesProvider).valueOrNull ?? const [];
    if (!puede) {
      return Text('${widget.venta['profesional'] ?? 'Sin profesional'}');
    }
    return DropdownButtonFormField<String>(
      key: const Key('profesional-venta'),
      initialValue: _valor,
      isExpanded: true,
      decoration: const InputDecoration(isDense: true),
      items: [
        const DropdownMenuItem(value: '', child: Text('Sin profesional')),
        for (final p in profs)
          DropdownMenuItem(
            value: '${p['id']}',
            child: Text('${p['first_name']} ${p['last_name']}'),
          ),
      ],
      onChanged: (v) async {
        if (v == null || v == _valor) return;
        setState(() => _valor = v);
        try {
          await ref.read(apiProvider).put(
            '/finance/charges/${widget.venta['id']}/professional',
            {'professional_id': v.isEmpty ? null : v},
          );
          ref.invalidate(ventasProvider);
          ref.invalidate(porProfesionalProvider);
          if (context.mounted) avisar(context, 'Profesional actualizado');
        } catch (_) {
          if (context.mounted) {
            avisar(context, 'No se pudo cambiar el profesional.');
          }
        }
      },
    );
  }
}

class _PorProfesional extends ConsumerWidget {
  const _PorProfesional({required this.alElegir});
  final ValueChanged<String> alElegir;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final d = ref.watch(porProfesionalProvider);
    final tenue = Theme.of(
      context,
    ).colorScheme.onSurface.withValues(alpha: 0.6);
    return d.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(40),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => EstadoError(
        mensaje: e is ErrorApi ? e.mensaje : 'No se pudo cargar.',
        onReintentar: () => ref.invalidate(porProfesionalProvider),
      ),
      data: (d) {
        final filas = (d['filas'] as List).cast<Map<String, dynamic>>();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Vendido ${dinero(numero(d['total_vendido']))} · Cobrado ${dinero(numero(d['total_cobrado_periodo']))} · Comisiones ${dinero(numero(d['total_comisiones']))}',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              'La comisión se calcula sobre lo cobrado en el periodo. El % se define en Configuración › Profesionales.',
              style: TextStyle(fontSize: 12, color: tenue),
            ),
            const SizedBox(height: 10),
            if (filas.isEmpty)
              const EstadoVacio(
                icono: Icons.badge_outlined,
                titulo: 'Sin ventas en el periodo',
              ),
            for (final f in filas)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GlassCard(
                  onTap: () => alElegir('${f['professional_id'] ?? 'sin'}'),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 10,
                              height: 10,
                              decoration: BoxDecoration(
                                color:
                                    colorDeHex('${f['color'] ?? ''}') ??
                                    Tonos.gris,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '${f['nombre']}',
                                style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                            if (f['comision'] != null)
                              Pastilla(
                                'Comisión ${dinero(numero(f['comision']))} (${numero(f['comision_porcentaje']).toStringAsFixed(0)}%)',
                                color: Tonos.verde,
                              )
                            else if (f['professional_id'] != null)
                              Pastilla('Sin %', color: Tonos.gris),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 14,
                          runSpacing: 4,
                          children: [
                            _Dato('Ventas', '${f['ventas']}'),
                            _Dato('Pacientes', '${f['pacientes']}'),
                            _Dato('Vendido', dinero(numero(f['vendido']))),
                            _Dato(
                              'Cobrado',
                              dinero(numero(f['cobrado_periodo'])),
                            ),
                            _Dato('Pendiente', dinero(numero(f['pendiente']))),
                            _Dato(
                              'Ticket prom.',
                              dinero(numero(f['ticket_promedio'])),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato(this.titulo, this.valor);
  final String titulo, valor;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        titulo,
        style: TextStyle(
          fontSize: 10.5,
          color: Theme.of(
            context,
          ).colorScheme.onSurface.withValues(alpha: 0.55),
        ),
      ),
      Text(valor, style: const TextStyle(fontWeight: FontWeight.w700)),
    ],
  );
}
