import 'dart:io';

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/api.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/contacto.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Facturación electrónica (SRI): las mismas funciones que la web — emitir,
/// ver el estado ante el SRI, reintentar, descartar, notas de crédito, PDF,
/// envío al paciente y la configuración de la firma.

const estadosFactura = {
  'pendiente': ('Pendiente de envío', Tonos.ambar),
  'recibida': ('En autorización', Tonos.ambar),
  'autorizada': ('Autorizada', Tonos.verde),
  'devuelta': ('Devuelta por el SRI', Tonos.rojo),
  'no_autorizada': ('No autorizada', Tonos.rojo),
  'descartada': ('Descartada', Tonos.gris),
};

String tituloComprobante(Map<String, dynamic> f) =>
    '${f['doc_type'] == '01' ? 'Factura' : 'Nota de crédito'} ${f['number']}';

final facturasProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/invoices'),
);
final facturasPacienteProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/invoices'),
);
final configFacturacionProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/invoicing/settings'),
);
final catalogosFacturacionProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/invoicing/catalogs'),
);
final facturaProvider = FutureProvider.autoDispose.family<Map<String, dynamic>, String>(
  (ref, id) => ref.watch(apiProvider).mapa('/invoices/$id'),
);

void _refrescar(WidgetRef ref, [String? pacienteId]) {
  ref.invalidate(facturasProvider);
  ref.invalidate(configFacturacionProvider);
  if (pacienteId != null) ref.invalidate(facturasPacienteProvider(pacienteId));
}

List<Opcion> _opciones(Map<String, dynamic> catalogos, String clave) => [
  for (final o in (catalogos[clave] as List? ?? [])) ('${(o as Map)['code']}', '${o['label']}'),
];

// ------------------------------------------------------------------ Página

class FacturacionPage extends ConsumerWidget {
  const FacturacionPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(authProvider).usuario;
    final configura = usuario?.puede('settings:manage') ?? false;
    final emite = usuario?.puede('invoices:write') ?? false;
    final config = ref.watch(configFacturacionProvider).valueOrNull;
    final faltan = (config?['missing'] as List? ?? []).isNotEmpty;

    return DefaultTabController(
      length: configura ? 2 : 1,
      child: PaginaModulo(
        titulo: 'Facturación',
        inferior: configura
            ? const TabBar(tabs: [Tab(text: 'Comprobantes'), Tab(text: 'Configuración')])
            : null,
        accion: emite && !faltan
            ? FloatingActionButton.extended(
                onPressed: () => emitirFactura(context, ref),
                icon: const Icon(Icons.add),
                label: const Text('Factura'),
              )
            : null,
        cuerpo: configura
            ? const TabBarView(children: [_Comprobantes(), _Configuracion()])
            : const _Comprobantes(),
      ),
    );
  }
}

class _Comprobantes extends ConsumerStatefulWidget {
  const _Comprobantes();

  @override
  ConsumerState<_Comprobantes> createState() => _ComprobantesState();
}

class _ComprobantesState extends ConsumerState<_Comprobantes> {
  String _filtro = 'todos';

  bool _pasa(Map<String, dynamic> f) => switch (_filtro) {
    'autorizada' => f['status'] == 'autorizada',
    'proceso' => f['status'] == 'pendiente' || f['status'] == 'recibida',
    'problemas' => f['status'] == 'devuelta' || f['status'] == 'no_autorizada',
    _ => true,
  };

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(configFacturacionProvider).valueOrNull;
    return RefreshIndicator(
      onRefresh: () async => _refrescar(ref),
      child: Asincrono(
        valor: ref.watch(facturasProvider),
        alReintentar: () => ref.invalidate(facturasProvider),
        listo: (lista) {
          final mes = DateTime.now().toIso8601String().substring(0, 7);
          double facturado = 0;
          for (final f in lista) {
            if (f['status'] == 'autorizada' && '${f['issue_date']}'.startsWith(mes)) {
              facturado += numero(f['total']) * (f['doc_type'] == '01' ? 1 : -1);
            }
          }
          final problemas = lista.where((f) => f['status'] == 'devuelta' || f['status'] == 'no_autorizada').length;
          final visibles = lista.where(_pasa).toList();
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            children: [
              if (config != null) _AvisoConfig(config: config),
              RejillaKpi(
                hijos: [
                  Kpi(etiqueta: 'Facturado este mes', valor: dinero(facturado), icono: Icons.receipt_long),
                  Kpi(
                    etiqueta: 'Con problemas',
                    valor: '$problemas',
                    icono: Icons.error_outline,
                    color: problemas > 0 ? Tonos.rojo : null,
                  ),
                ],
              ),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (final (codigo, nombre) in const [
                      ('todos', 'Todos'),
                      ('autorizada', 'Autorizadas'),
                      ('proceso', 'En proceso'),
                      ('problemas', 'Con problemas'),
                    ])
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(nombre),
                          selected: _filtro == codigo,
                          onSelected: (_) => setState(() => _filtro = codigo),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              if (visibles.isEmpty)
                EstadoVacio(
                  icono: Icons.receipt_long,
                  titulo: lista.isEmpty ? 'Sin facturas todavía' : 'Nada con ese filtro',
                  detalle: lista.isEmpty ? 'Emita la primera con el botón «Factura» o desde la cuenta del paciente.' : null,
                ),
              for (final f in visibles) FilaFactura(factura: f),
              finDeLista,
            ],
          );
        },
      ),
    );
  }
}

class _AvisoConfig extends StatelessWidget {
  const _AvisoConfig({required this.config});

  final Map<String, dynamic> config;

  @override
  Widget build(BuildContext context) {
    final faltan = (config['missing'] as List? ?? []).cast<String>();
    final pruebas = config['environment'] == '1';
    if (faltan.isEmpty && !pruebas) return const SizedBox.shrink();
    final color = faltan.isNotEmpty ? Tonos.rojo : Tonos.ambar;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(faltan.isNotEmpty ? Icons.error_outline : Icons.science_outlined, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              faltan.isNotEmpty
                  ? 'Para facturar falta:\n• ${faltan.join('\n• ')}'
                  : 'Ambiente de PRUEBAS del SRI: estas facturas no tienen validez tributaria.',
              style: const TextStyle(fontSize: 13, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

class FilaFactura extends ConsumerWidget {
  const FilaFactura({super.key, required this.factura, this.pacienteId});

  final Map<String, dynamic> factura;
  final String? pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final f = factura;
    final estado = estadosFactura[f['status']];
    final nota = f['doc_type'] == '04';
    return FilaTarjeta(
      icono: nota ? Icons.undo : Icons.receipt_long,
      colorIcono: nota ? Tonos.ambar : null,
      titulo: '${f['buyer_name']}',
      subtitulo: '${tituloComprobante(f)} · ${fechaCorta(f['issue_date'])}${f['environment'] == '1' ? ' · pruebas' : ''}',
      tachado: f['status'] == 'descartada',
      derecha: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '${nota ? '−' : ''}${dinero(numero(f['total']))}',
            style: const TextStyle(fontWeight: FontWeight.w700, fontFeatures: [FontFeature.tabularFigures()]),
          ),
          const SizedBox(height: 4),
          Pastilla(estado?.$1 ?? '${f['status']}', color: estado?.$2),
        ],
      ),
      alTocar: () => verFactura(context, ref, '${f['id']}', pacienteId: pacienteId),
    );
  }
}

// ------------------------------------------------------------------ Emitir

/// Abre el editor de una factura nueva; devuelve la creada (o null).
Future<void> emitirFactura(BuildContext context, WidgetRef ref, {String? pacienteId, String? pacienteNombre}) async {
  final creada = await Navigator.of(context).push<Map<String, dynamic>>(
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (_) => EditorFactura(pacienteId: pacienteId, pacienteNombre: pacienteNombre),
    ),
  );
  if (creada == null || !context.mounted) return;
  _refrescar(ref, pacienteId);
  await verFactura(context, ref, '${creada['id']}', pacienteId: pacienteId);
}

class _LineaManual {
  final descripcion = TextEditingController();
  final precio = TextEditingController();
  final cantidad = TextEditingController(text: '1');
  String iva = '0';

  void dispose() {
    descripcion.dispose();
    precio.dispose();
    cantidad.dispose();
  }
}

class EditorFactura extends ConsumerStatefulWidget {
  const EditorFactura({super.key, this.pacienteId, this.pacienteNombre});

  final String? pacienteId;
  final String? pacienteNombre;

  @override
  ConsumerState<EditorFactura> createState() => _EditorFacturaState();
}

class _EditorFacturaState extends ConsumerState<EditorFactura> {
  late String? _pacienteId = widget.pacienteId;
  late String? _pacienteNombre = widget.pacienteNombre;
  List<Map<String, dynamic>> _cargos = [];
  final Map<String, bool> _elegidos = {};
  final Map<String, String> _ivaCargo = {};
  final List<_LineaManual> _manuales = [];
  late String _comprador = widget.pacienteId != null ? 'paciente' : 'final';
  String _formaPago = '01';
  final _obs = TextEditingController();
  final _tipoId = ValueNotifier('05');
  final _idNum = TextEditingController();
  final _nombre = TextEditingController();
  final _correo = TextEditingController();
  final _telefono = TextEditingController();
  final _direccion = TextEditingController();
  bool _enviando = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (_pacienteId != null) {
      _cargarCargos();
    } else {
      _manuales.add(_LineaManual());
    }
  }

  @override
  void dispose() {
    for (final m in _manuales) {
      m.dispose();
    }
    for (final c in [_obs, _idNum, _nombre, _correo, _telefono, _direccion]) {
      c.dispose();
    }
    _tipoId.dispose();
    super.dispose();
  }

  Future<void> _cargarCargos() async {
    final lista = await cargarOAvisar(context, ref.read(apiProvider).lista('/patients/$_pacienteId/invoiceable-charges'));
    if (!mounted || lista == null) return;
    setState(() {
      _cargos = lista;
      for (final c in lista) {
        _elegidos['${c['id']}'] = true;
        _ivaCargo['${c['id']}'] = '0';
      }
      if (lista.isEmpty && _manuales.isEmpty) _manuales.add(_LineaManual());
    });
  }

  Future<void> _elegirPaciente() async {
    final elegido = await elegirConBusqueda(
      context,
      titulo: 'Paciente',
      buscar: (t) async {
        final r = await ref.read(apiProvider).lista('/patients', query: {'search': t, 'limit': 20});
        return [for (final p in r) ('${p['id']}', '${p['first_name']} ${p['last_name']}')];
      },
    );
    if (elegido == null) return;
    setState(() {
      _pacienteId = elegido.$1;
      _pacienteNombre = elegido.$2;
      _comprador = 'paciente';
    });
    await _cargarCargos();
  }

  double _tarifa(Map<String, dynamic> catalogos, String codigo) {
    for (final v in (catalogos['vat'] as List? ?? [])) {
      if ((v as Map)['code'] == codigo) return double.tryParse('${v['rate']}') ?? 0;
    }
    return 0;
  }

  (double, double) _separar(double total, double tarifa) {
    double r2(double n) => (n * 100).roundToDouble() / 100;
    final base = tarifa == 0 ? r2(total) : r2(total / (1 + tarifa / 100));
    return (base, r2(base * tarifa / 100));
  }

  (double, double, int) _totales(Map<String, dynamic> catalogos) {
    double base = 0, iva = 0;
    var lineas = 0;
    for (final c in _cargos) {
      if (_elegidos['${c['id']}'] != true) continue;
      final s = _separar(numero(c['amount']), _tarifa(catalogos, _ivaCargo['${c['id']}'] ?? '0'));
      base += s.$1;
      iva += s.$2;
      lineas++;
    }
    for (final m in _manuales) {
      final precio = double.tryParse(m.precio.text.replaceAll(',', '.')) ?? 0;
      final cantidad = double.tryParse(m.cantidad.text.replaceAll(',', '.')) ?? 1;
      if (m.descripcion.text.trim().isEmpty || precio <= 0) continue;
      final s = _separar(precio * cantidad, _tarifa(catalogos, m.iva));
      base += s.$1;
      iva += s.$2;
      lineas++;
    }
    return (base, iva, lineas);
  }

  Future<void> _emitir() async {
    setState(() {
      _error = null;
      _enviando = true;
    });
    final items = [
      for (final c in _cargos)
        if (_elegidos['${c['id']}'] == true) {'charge_id': c['id'], 'vat_code': _ivaCargo['${c['id']}'] ?? '0'},
      for (final m in _manuales)
        if (m.descripcion.text.trim().isNotEmpty && (double.tryParse(m.precio.text.replaceAll(',', '.')) ?? 0) > 0)
          {
            'description': m.descripcion.text.trim(),
            'quantity': m.cantidad.text.replaceAll(',', '.').trim().isEmpty ? '1' : m.cantidad.text.replaceAll(',', '.').trim(),
            'unit_price': m.precio.text.replaceAll(',', '.').trim(),
            'price_includes_vat': true,
            'vat_code': m.iva,
          },
    ];
    try {
      final r = await ref.read(apiProvider).post('/invoices', {
        'patient_id': _pacienteId,
        'items': items,
        'payment_method': _formaPago,
        'notes': _obs.text.trim().isEmpty ? null : _obs.text.trim(),
        'buyer': switch (_comprador) {
          'final' => {'id_type': '07', 'id_number': '9999999999999', 'name': 'CONSUMIDOR FINAL'},
          'otro' => {
            'id_type': _tipoId.value,
            'id_number': _idNum.text.trim(),
            'name': _nombre.text.trim(),
            'email': _correo.text.trim().isEmpty ? null : _correo.text.trim(),
            'phone': _telefono.text.trim().isEmpty ? null : _telefono.text.trim(),
            'address': _direccion.text.trim().isEmpty ? null : _direccion.text.trim(),
          },
          _ => null,
        },
      });
      if (mounted) Navigator.pop(context, (r as Map).cast<String, dynamic>());
    } on ErrorApi catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final catalogos = ref.watch(catalogosFacturacionProvider).valueOrNull ?? const {};
    final config = ref.watch(configFacturacionProvider).valueOrNull;
    final ivas = _opciones(catalogos, 'vat');
    final (base, iva, lineas) = _totales(catalogos);
    final tinta = Theme.of(context).colorScheme.onSurface;

    Widget selectorIva(String valor, ValueChanged<String> alCambiar) => DropdownButton<String>(
      value: ivas.any((o) => o.$1 == valor) ? valor : null,
      isDense: true,
      underline: const SizedBox.shrink(),
      items: [for (final o in ivas) DropdownMenuItem(value: o.$1, child: Text(o.$2, style: const TextStyle(fontSize: 13)))],
      onChanged: (v) => setState(() => alCambiar(v ?? '0')),
    );

    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(flexibleSpace: const GlassAppBarBackground(), title: const Text('Nueva factura')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            if (config != null) _AvisoConfig(config: config),
            const Seccion('Paciente'),
            GlassCard(
              child: ListTile(
                leading: const Icon(Icons.person_outline),
                title: Text(_pacienteNombre ?? (_pacienteId != null ? 'Paciente de esta ficha' : 'Sin paciente')),
                subtitle: _pacienteId == null ? const Text('Opcional: para facturar cargos de su cuenta') : null,
                trailing: widget.pacienteId == null ? const Icon(Icons.search) : null,
                onTap: widget.pacienteId == null ? _elegirPaciente : null,
              ),
            ),
            if (_cargos.isNotEmpty) ...[
              const Seccion('Cargos sin facturar'),
              GlassCard(
                child: Column(
                  children: [
                    for (final c in _cargos)
                      CheckboxListTile(
                        value: _elegidos['${c['id']}'] ?? false,
                        onChanged: (v) => setState(() => _elegidos['${c['id']}'] = v ?? false),
                        title: Text('${c['description']}'),
                        subtitle: Row(
                          children: [
                            Text('${dinero(numero(c['amount']))} · '),
                            selectorIva(_ivaCargo['${c['id']}'] ?? '0', (v) => _ivaCargo['${c['id']}'] = v),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ],
            const Seccion('Otros conceptos'),
            for (final m in _manuales)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: GlassCard(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 4, 8),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: m.descripcion,
                                onChanged: (_) => setState(() {}),
                                decoration: const InputDecoration(labelText: 'Descripción'),
                              ),
                            ),
                            IconButton(
                              tooltip: 'Quitar',
                              onPressed: () => setState(() {
                                _manuales.remove(m);
                                m.dispose();
                              }),
                              icon: const Icon(Icons.close),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            SizedBox(
                              width: 70,
                              child: TextField(
                                controller: m.cantidad,
                                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                onChanged: (_) => setState(() {}),
                                decoration: const InputDecoration(labelText: 'Cant.'),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: TextField(
                                controller: m.precio,
                                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                onChanged: (_) => setState(() {}),
                                decoration: const InputDecoration(labelText: 'Precio con IVA', prefixText: '\$ '),
                              ),
                            ),
                            const SizedBox(width: 8),
                            selectorIva(m.iva, (v) => m.iva = v),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            OutlinedButton.icon(
              onPressed: () => setState(() => _manuales.add(_LineaManual())),
              icon: const Icon(Icons.add),
              label: const Text('Agregar concepto'),
            ),
            const Seccion('Comprador'),
            SegmentedButton<String>(
              showSelectedIcon: false,
              segments: [
                if (_pacienteId != null) const ButtonSegment(value: 'paciente', label: Text('Paciente')),
                const ButtonSegment(value: 'otro', label: Text('Otro')),
                const ButtonSegment(value: 'final', label: Text('Cons. final')),
              ],
              selected: {_comprador},
              onSelectionChanged: (s) => setState(() => _comprador = s.first),
            ),
            const SizedBox(height: 8),
            if (_comprador == 'paciente')
              Text(
                'Con la cédula y el correo de su ficha. Sin cédula válida se factura a consumidor final.',
                style: TextStyle(fontSize: 12.5, color: tinta.withValues(alpha: 0.6)),
              )
            else if (_comprador == 'final')
              Text('Solo hasta \$ 50,00 por factura.', style: TextStyle(fontSize: 12.5, color: tinta.withValues(alpha: 0.6)))
            else ...[
              ValueListenableBuilder(
                valueListenable: _tipoId,
                builder: (_, tipo, __) => DropdownButtonFormField<String>(
                  initialValue: tipo,
                  decoration: const InputDecoration(labelText: 'Tipo de identificación'),
                  items: [
                    for (final o in _opciones(catalogos, 'id_types').where((o) => o.$1 != '07'))
                      DropdownMenuItem(value: o.$1, child: Text(o.$2)),
                  ],
                  onChanged: (v) => _tipoId.value = v ?? '05',
                ),
              ),
              const SizedBox(height: 10),
              TextField(controller: _idNum, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Número')),
              const SizedBox(height: 10),
              TextField(controller: _nombre, decoration: const InputDecoration(labelText: 'Nombre o razón social')),
              const SizedBox(height: 10),
              TextField(controller: _correo, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Correo')),
              const SizedBox(height: 10),
              TextField(controller: _telefono, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Teléfono')),
              const SizedBox(height: 10),
              TextField(controller: _direccion, decoration: const InputDecoration(labelText: 'Dirección')),
            ],
            const Seccion('Pago'),
            DropdownButtonFormField<String>(
              initialValue: _formaPago,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Forma de pago (SRI)'),
              items: [
                for (final o in _opciones(catalogos, 'payment_methods'))
                  DropdownMenuItem(value: o.$1, child: Text(o.$2, overflow: TextOverflow.ellipsis)),
              ],
              onChanged: (v) => setState(() => _formaPago = v ?? '01'),
            ),
            const SizedBox(height: 10),
            TextField(controller: _obs, decoration: const InputDecoration(labelText: 'Observación (opcional)')),
            const SizedBox(height: 18),
            GlassCard(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    _filaTotal('Subtotal', base),
                    _filaTotal('IVA', iva),
                    const Divider(height: 18),
                    _filaTotal('Total', base + iva, grande: true),
                  ],
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _enviando || lineas == 0 || (config?['missing'] as List? ?? []).isNotEmpty ? null : _emitir,
              icon: const Icon(Icons.receipt_long),
              label: Text(_enviando ? 'Enviando al SRI…' : 'Emitir factura'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _filaTotal(String etiqueta, double valor, {bool grande = false}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      children: [
        Expanded(child: Text(etiqueta, style: grande ? estiloTitulo(17) : null)),
        Text(dinero(valor), style: grande ? estiloTitulo(20, peso: FontWeight.w800) : const TextStyle(fontWeight: FontWeight.w600)),
      ],
    ),
  );
}

// ------------------------------------------------------------------ Detalle

Future<void> verFactura(BuildContext context, WidgetRef ref, String id, {String? pacienteId}) async {
  await Navigator.of(context).push(
    MaterialPageRoute<void>(builder: (_) => DetalleFactura(id: id, pacienteId: pacienteId)),
  );
  _refrescar(ref, pacienteId);
}

class DetalleFactura extends ConsumerWidget {
  const DetalleFactura({super.key, required this.id, this.pacienteId});

  final String id;
  final String? pacienteId;

  Future<void> _accion(BuildContext context, WidgetRef ref, Future<void> Function() hacer, String exito) async {
    if (await intentar(context, hacer, exito: exito)) {
      ref.invalidate(facturaProvider(id));
      _refrescar(ref, pacienteId);
    }
  }

  Future<void> _pdf(BuildContext context, WidgetRef ref, Map<String, dynamic> f) async {
    if (kIsWeb) {
      avisar(context, 'Abra el PDF desde la versión web.');
      return;
    }
    final bytes = await cargarOAvisar(context, ref.read(apiProvider).bytes('/invoices/$id/pdf'));
    if (bytes == null) return;
    final dir = await getTemporaryDirectory();
    final archivo = File('${dir.path}/${f['doc_type'] == '01' ? 'factura' : 'nota-credito'}-${f['number']}.pdf');
    await archivo.writeAsBytes(bytes, flush: true);
    final r = await OpenFilex.open(archivo.path, type: 'application/pdf');
    if (r.type != ResultType.done && context.mounted) avisar(context, 'No hay una aplicación para abrir PDF.');
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(authProvider).usuario;
    final emite = usuario?.puede('invoices:write') ?? false;
    final valor = ref.watch(facturaProvider(id));
    final api = ref.read(apiProvider);
    return PaginaModulo(
      titulo: valor.valueOrNull == null ? 'Comprobante' : tituloComprobante(valor.value!),
      cuerpo: Asincrono(
        valor: valor,
        alReintentar: () => ref.invalidate(facturaProvider(id)),
        listo: (f) {
          final estado = '${f['status']}';
          final total = numero(f['total']);
          final acreditado = numero(f['credited']);
          final disponible = ((total - acreditado) * 100).roundToDouble() / 100;
          final mensajes = (f['sri_messages'] as List? ?? []).cast<Map>();
          final tinta = Theme.of(context).colorScheme.onSurface;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Row(
                children: [
                  Pastilla(estadosFactura[estado]?.$1 ?? estado, color: estadosFactura[estado]?.$2),
                  if (f['environment'] == '1') ...[const SizedBox(width: 8), const Pastilla('Pruebas', color: Tonos.ambar)],
                ],
              ),
              const SizedBox(height: 14),
              Text(dinero(total), style: estiloTitulo(34, color: tinta, peso: FontWeight.w800)),
              Text('${f['buyer_name']} · ${f['buyer_id']}', style: TextStyle(color: tinta.withValues(alpha: 0.6))),
              const Seccion('Datos'),
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _dato('Emitida', fechaCorta(f['issue_date'])),
                      if (f['authorized_at'] != null) _dato('Autorizada', fechaHora(f['authorized_at'])),
                      if (f['reason'] != null) _dato('Motivo', '${f['reason']}'),
                      if (f['buyer_email'] != null) _dato('Correo', '${f['buyer_email']}${f['emailed_at'] != null ? ' · enviado' : ''}'),
                      if (f['discard_reason'] != null) _dato('Descartada', '${f['discard_reason']}'),
                      const SizedBox(height: 6),
                      Text('CLAVE DE ACCESO', style: Theme.of(context).textTheme.labelSmall),
                      SelectableText('${f['access_key']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
                    ],
                  ),
                ),
              ),
              const Seccion('Detalle'),
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    children: [
                      for (final l in (f['lines'] as List? ?? []).cast<Map>())
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              Expanded(child: Text('${l['description']}')),
                              Text('IVA ${numero(l['vat_rate']).toStringAsFixed(0)} %  ', style: TextStyle(fontSize: 12, color: tinta.withValues(alpha: 0.5))),
                              Text(dinero(numero(l['subtotal']))),
                            ],
                          ),
                        ),
                      const Divider(),
                      _dato('Subtotal', dinero(numero(f['subtotal']))),
                      _dato('IVA', dinero(numero(f['vat']))),
                      if (acreditado > 0) _dato('Notas de crédito', '− ${dinero(acreditado)}'),
                    ],
                  ),
                ),
              ),
              if (mensajes.isNotEmpty && estado != 'autorizada') ...[
                const Seccion('Respuesta del SRI'),
                for (final m in mensajes)
                  FilaTarjeta(
                    icono: Icons.error_outline,
                    colorIcono: Tonos.rojo,
                    titulo: '${m['mensaje']}',
                    subtitulo: [if ('${m['identificador']}'.isNotEmpty) 'Código ${m['identificador']}', if ('${m['informacion']}'.isNotEmpty) '${m['informacion']}'].join(' · '),
                  ),
              ],
              if (f['last_error'] != null && estado != 'descartada')
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text('${f['last_error']}', style: TextStyle(fontSize: 12.5, color: tinta.withValues(alpha: 0.6))),
                ),
              const Seccion('Acciones'),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(onPressed: () => _pdf(context, ref, f), icon: const Icon(Icons.picture_as_pdf_outlined), label: const Text('PDF')),
                  if (estado == 'autorizada' && f['buyer_phone'] != null)
                    OutlinedButton.icon(
                      onPressed: () => abrirWhatsapp(
                        context,
                        '${f['buyer_phone']}',
                        'Hola ${f['buyer_name']}, su ${f['doc_type'] == '01' ? 'factura' : 'nota de crédito'} electrónica ${f['number']} '
                            'por ${dinero(total)} fue autorizada por el SRI. Clave de acceso: ${f['access_key']}',
                      ),
                      icon: const Icon(Icons.chat_outlined),
                      label: const Text('WhatsApp'),
                    ),
                  if (emite && estado == 'autorizada')
                    OutlinedButton.icon(
                      onPressed: () => mostrarFormulario(
                        context,
                        titulo: 'Enviar por correo',
                        icono: Icons.mail_outline,
                        textoGuardar: 'Enviar',
                        campos: [Campo('email', 'Correo', tipo: TipoCampo.correo, requerido: true, inicial: f['buyer_email'])],
                        alGuardar: (v) async {
                          await api.post('/invoices/$id/email', {'email': v['email']});
                          ref.invalidate(facturaProvider(id));
                        },
                      ),
                      icon: const Icon(Icons.mail_outline),
                      label: const Text('Correo'),
                    ),
                  if (emite && ['pendiente', 'recibida', 'devuelta', 'no_autorizada'].contains(estado))
                    FilledButton.icon(
                      style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
                      onPressed: () => _accion(context, ref, () => api.post('/invoices/$id/retry'), 'Enviado al SRI'),
                      icon: const Icon(Icons.sync),
                      label: Text(estado == 'recibida' ? 'Consultar SRI' : 'Reintentar'),
                    ),
                  if (emite && (estado == 'devuelta' || estado == 'no_autorizada'))
                    OutlinedButton.icon(
                      onPressed: () => mostrarFormulario(
                        context,
                        titulo: 'Descartar comprobante',
                        subtitulo: 'Deja de contar como factura y sus cargos quedan libres para facturar de nuevo.',
                        icono: Icons.block,
                        peligro: true,
                        textoGuardar: 'Descartar',
                        campos: const [Campo('reason', 'Motivo', tipo: TipoCampo.multilinea, requerido: true)],
                        alGuardar: (v) async {
                          await api.post('/invoices/$id/discard', {'reason': v['reason']});
                          ref.invalidate(facturaProvider(id));
                          _refrescar(ref, pacienteId);
                        },
                      ),
                      icon: const Icon(Icons.block),
                      label: const Text('Descartar'),
                    ),
                  if (emite && f['doc_type'] == '01' && estado == 'autorizada' && disponible > 0)
                    OutlinedButton.icon(
                      onPressed: () => mostrarFormulario(
                        context,
                        titulo: 'Nota de crédito',
                        subtitulo: 'Disponible: ${dinero(disponible)}. Deje el monto vacío para anular la factura completa.',
                        icono: Icons.undo,
                        textoGuardar: 'Emitir',
                        campos: const [
                          Campo('reason', 'Motivo', requerido: true),
                          Campo('amount', 'Monto con IVA (opcional)', tipo: TipoCampo.dinero),
                        ],
                        alGuardar: (v) async {
                          final nota = await api.post('/invoices/$id/credit-note', {
                            'reason': v['reason'],
                            'amount': v['amount'] == null || '${v['amount']}'.isEmpty ? null : '${v['amount']}',
                          });
                          ref.invalidate(facturaProvider(id));
                          _refrescar(ref, pacienteId);
                          if (context.mounted && nota is Map) {
                            avisar(context, '${tituloComprobante(nota.cast<String, dynamic>())}: ${estadosFactura[nota['status']]?.$1 ?? nota['status']}');
                          }
                        },
                      ),
                      icon: const Icon(Icons.undo),
                      label: const Text('Nota de crédito'),
                    ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _dato(String etiqueta, String valor) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 110, child: Text(etiqueta, style: const TextStyle(fontSize: 13, color: Tonos.gris))),
        Expanded(child: Text(valor, style: const TextStyle(fontSize: 14))),
      ],
    ),
  );
}

// ------------------------------------------------------------------ Configuración

class _Configuracion extends ConsumerStatefulWidget {
  const _Configuracion();

  @override
  ConsumerState<_Configuracion> createState() => _ConfiguracionState();
}

class _ConfiguracionState extends ConsumerState<_Configuracion> {
  bool _subiendo = false;

  Future<void> _guardar(Map<String, dynamic> datos, [String exito = 'Configuración guardada']) async {
    if (await intentar(context, () => ref.read(apiProvider).put('/invoicing/settings', datos), exito: exito)) {
      ref.invalidate(configFacturacionProvider);
    }
  }

  Future<void> _subirFirma() async {
    final elegido = await FilePicker.pickFiles(type: FileType.any, withData: true);
    final archivo = elegido?.files.single;
    if (archivo?.bytes == null || !mounted) return;
    await mostrarFormulario(
      context,
      titulo: 'Clave de la firma',
      subtitulo: archivo!.name,
      icono: Icons.key_outlined,
      textoGuardar: 'Guardar firma',
      campos: const [Campo('password', 'Clave del archivo .p12', requerido: true)],
      alGuardar: (v) async {
        setState(() => _subiendo = true);
        try {
          await ref.read(apiProvider).post(
            '/invoicing/certificate',
            FormData.fromMap({
              'file': MultipartFile.fromBytes(archivo.bytes!, filename: archivo.name),
              'password': v['password'],
            }),
          );
          ref.invalidate(configFacturacionProvider);
        } finally {
          if (mounted) setState(() => _subiendo = false);
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Asincrono(
      valor: ref.watch(configFacturacionProvider),
      alReintentar: () => ref.invalidate(configFacturacionProvider),
      listo: (c) {
        final tieneFirma = c['has_certificate'] == true;
        final vencida = c['certificate_expired'] == true;
        final faltan = (c['missing'] as List? ?? []).cast<String>();
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
          children: [
            if (faltan.isNotEmpty) _AvisoConfig(config: c),
            const Seccion('Firma electrónica'),
            FilaTarjeta(
              icono: tieneFirma && !vencida ? Icons.verified_user_outlined : Icons.key_off_outlined,
              colorIcono: tieneFirma && !vencida ? Tonos.verde : Tonos.rojo,
              titulo: tieneFirma ? '${c['certificate_subject']}' : 'Sin firma electrónica',
              subtitulo: tieneFirma
                  ? '${vencida ? 'Vencida' : 'Vence'} el ${fechaCorta(c['certificate_valid_until'])} · guardada cifrada'
                  : 'Suba el archivo .p12 y su clave',
            ),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _subiendo ? null : _subirFirma,
                    icon: const Icon(Icons.upload_file),
                    label: Text(tieneFirma ? 'Reemplazar firma' : 'Subir firma .p12'),
                  ),
                ),
                if (tieneFirma) ...[
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () async {
                      if (!await confirmar(context, titulo: '¿Quitar la firma?', mensaje: 'Sin firma no se puede facturar.', textoConfirmar: 'Quitar', peligro: true)) return;
                      if (!context.mounted) return;
                      if (await intentar(context, () => ref.read(apiProvider).delete('/invoicing/certificate'))) {
                        ref.invalidate(configFacturacionProvider);
                      }
                    },
                    child: const Text('Quitar'),
                  ),
                ],
              ],
            ),
            const Seccion('Ambiente del SRI'),
            SegmentedButton<String>(
              showSelectedIcon: false,
              segments: const [
                ButtonSegment(value: '1', label: Text('Pruebas')),
                ButtonSegment(value: '2', label: Text('Producción')),
              ],
              selected: {'${c['environment']}'},
              onSelectionChanged: (s) async {
                final nuevo = s.first;
                if (nuevo == '2' &&
                    !await confirmar(
                      context,
                      titulo: '¿Pasar a producción?',
                      mensaje: 'Las facturas tendrán validez tributaria. Hágalo cuando el SRI le haya habilitado la producción y sus facturas de prueba salgan autorizadas.',
                      textoConfirmar: 'Pasar a producción',
                    )) {
                  return;
                }
                await _guardar({'environment': nuevo});
              },
            ),
            const Seccion('Numeración'),
            FilaTarjeta(
              icono: Icons.tag,
              titulo: 'Siguiente factura: ${c['establishment']}-${c['emission_point']}-${'${c['next_invoice_number']}'.padLeft(9, '0')}',
              subtitulo: 'Tóquelo para continuar desde otro número',
              derecha: const Icon(Icons.edit_outlined, size: 20),
              alTocar: () => mostrarFormulario(
                context,
                titulo: 'Siguiente número de factura',
                subtitulo: 'Si ya facturaba con otro sistema en este punto de emisión, continúe desde el siguiente.',
                icono: Icons.tag,
                campos: [Campo('n', 'Número', tipo: TipoCampo.entero, requerido: true, inicial: c['next_invoice_number'])],
                alGuardar: (v) async {
                  await ref.read(apiProvider).put('/invoicing/settings', {'next_invoice_number': v['n']});
                  ref.invalidate(configFacturacionProvider);
                },
              ),
            ),
            const Seccion('Envío al paciente'),
            GlassCard(
              child: SwitchListTile(
                value: c['send_email'] == true,
                onChanged: (v) => _guardar({'send_email': v}),
                title: const Text('Enviar por correo el PDF y el XML al autorizarse'),
                subtitle: c['email_configured'] == true
                    ? null
                    : const Text('El correo saliente aún no está configurado en el servidor: use WhatsApp o el PDF.'),
              ),
            ),
            const SizedBox(height: 8),
            FilaTarjeta(
              icono: Icons.account_balance_outlined,
              titulo: 'Agente de retención',
              subtitulo: '${c['retention_agent'] ?? 'No aplica'}',
              derecha: const Icon(Icons.edit_outlined, size: 20),
              alTocar: () => mostrarFormulario(
                context,
                titulo: 'Agente de retención',
                subtitulo: 'Número de resolución, solo si el SRI lo designó como agente.',
                icono: Icons.account_balance_outlined,
                campos: [Campo('r', 'Resolución', inicial: c['retention_agent'])],
                alGuardar: (v) async {
                  await ref.read(apiProvider).put('/invoicing/settings', {'retention_agent': v['r'] ?? ''});
                  ref.invalidate(configFacturacionProvider);
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Facturas del paciente, para la pestaña Cuenta de su ficha.
class FacturasDelPaciente extends ConsumerWidget {
  const FacturasDelPaciente({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!(ref.watch(authProvider).usuario?.puede('invoices:read') ?? false)) return const SizedBox.shrink();
    final lista = ref.watch(facturasPacienteProvider(pacienteId)).valueOrNull ?? const [];
    if (lista.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Seccion('Facturas electrónicas'),
        for (final f in lista) FilaFactura(factura: f, pacienteId: pacienteId),
      ],
    );
  }
}
