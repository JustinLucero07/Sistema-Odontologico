import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/ui.dart';

final _articulosProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref
          .watch(apiProvider)
          .lista('/inventory/items', query: {'include_inactive': true}),
    );
final _proveedoresProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref.watch(apiProvider).lista('/inventory/suppliers'),
    );
final _catalogoInvProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/inventory/catalog'),
);

String _cant(dynamic v) {
  final n = numero(v);
  return n == n.roundToDouble() ? n.toStringAsFixed(0) : n.toStringAsFixed(2);
}

/// Inventario: existencias que salen de los movimientos, alertas de mínimo y
/// caducidad, artículos y proveedores.
class InventarioPage extends ConsumerStatefulWidget {
  const InventarioPage({super.key});

  @override
  ConsumerState<InventarioPage> createState() => _InventarioPageState();
}

class _InventarioPageState extends ConsumerState<InventarioPage> {
  bool _soloAlerta = false;
  String _busqueda = '';

  Api get _api => ref.read(apiProvider);

  Future<void> _editarArticulo(Map<String, dynamic>? a) async {
    final catalogo = await cargarOAvisar(
      context,
      ref.read(_catalogoInvProvider.future),
    );
    if (catalogo == null) return;
    if (!mounted) return;
    final proveedores = await cargarOAvisar(
      context,
      ref.read(_proveedoresProvider.future),
    );
    if (proveedores == null) return;
    if (!mounted) return;
    final unidades = [
      for (final u in (catalogo['units'] as List? ?? []))
        ('${u['code']}', '${u['label']}'),
    ];
    await mostrarFormulario(
      context,
      titulo: a == null ? 'Nuevo artículo' : 'Editar artículo',
      icono: Icons.inventory_2_outlined,
      campos: [
        Campo('name', 'Nombre', requerido: true, inicial: a?['name']),
        Campo(
          'unit',
          'Unidad',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: unidades,
          inicial: a?['unit'] ?? 'unidad',
          mitad: true,
        ),
        Campo(
          'minimum_stock',
          'Stock mínimo',
          tipo: TipoCampo.numero,
          requerido: true,
          inicial: a == null ? '0' : _cant(a['minimum_stock']),
          mitad: true,
        ),
        Campo('sku', 'Código', inicial: a?['sku'], mitad: true),
        Campo('category', 'Categoría', inicial: a?['category'], mitad: true),
        Campo(
          'unit_cost',
          'Costo unitario',
          tipo: TipoCampo.dinero,
          inicial: a?['unit_cost'],
          mitad: true,
        ),
        Campo(
          'supplier_id',
          'Proveedor',
          tipo: TipoCampo.seleccion,
          opciones: [
            for (final p in proveedores) ('${p['id']}', '${p['name']}'),
          ],
          inicial: a?['supplier_id'],
          mitad: true,
        ),
        Campo(
          'notes',
          'Notas',
          tipo: TipoCampo.multilinea,
          inicial: a?['notes'],
        ),
        Campo(
          'is_active',
          'Activo',
          tipo: TipoCampo.interruptor,
          inicial: a?['is_active'] ?? true,
        ),
      ],
      alGuardar: (v) async {
        if (a == null) {
          await _api.post('/inventory/items', v);
        } else {
          await _api.put('/inventory/items/${a['id']}', v);
        }
        ref.invalidate(_articulosProvider);
      },
    );
  }

  Future<void> _movimiento(Map<String, dynamic> a) async {
    final catalogo = await cargarOAvisar(
      context,
      ref.read(_catalogoInvProvider.future),
    );
    if (catalogo == null) return;
    if (!mounted) return;
    final motivos = [
      for (final r in (catalogo['reasons'] as List? ?? []))
        (
          '${r['code']}',
          '${r['label']} (${(r['sign'] as num? ?? 0) > 0 ? 'suma' : 'resta'})',
        ),
    ];
    await mostrarFormulario(
      context,
      titulo: 'Movimiento · ${a['name']}',
      subtitulo:
          'Hay ${_cant(a['on_hand'])} ${a['unit']}. La cantidad es positiva; el motivo decide si suma o resta.',
      icono: Icons.swap_vert,
      campos: [
        Campo(
          'reason',
          'Motivo',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: motivos,
        ),
        const Campo(
          'quantity',
          'Cantidad',
          tipo: TipoCampo.numero,
          requerido: true,
          mitad: true,
        ),
        const Campo(
          'unit_cost',
          'Costo unitario',
          tipo: TipoCampo.dinero,
          mitad: true,
        ),
        const Campo('lot_number', 'Lote', mitad: true),
        const Campo(
          'expires_on',
          'Caduca el',
          tipo: TipoCampo.fecha,
          mitad: true,
        ),
        const Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
      ],
      alGuardar: (v) async {
        await _api.post('/inventory/items/${a['id']}/movements', v);
        ref.invalidate(_articulosProvider);
      },
    );
  }

  Future<void> _editarProveedor(Map<String, dynamic>? p) => mostrarFormulario(
    context,
    titulo: p == null ? 'Nuevo proveedor' : 'Editar proveedor',
    icono: Icons.local_shipping_outlined,
    campos: [
      Campo('name', 'Nombre', requerido: true, inicial: p?['name']),
      Campo('contact_name', 'Contacto', inicial: p?['contact_name']),
      Campo(
        'phone',
        'Teléfono',
        tipo: TipoCampo.telefono,
        inicial: p?['phone'],
        mitad: true,
      ),
      Campo(
        'email',
        'Correo',
        tipo: TipoCampo.correo,
        inicial: p?['email'],
        mitad: true,
      ),
      Campo('notes', 'Notas', tipo: TipoCampo.multilinea, inicial: p?['notes']),
      Campo(
        'is_active',
        'Activo',
        tipo: TipoCampo.interruptor,
        inicial: p?['is_active'] ?? true,
      ),
    ],
    alGuardar: (v) async {
      if (p == null) {
        await _api.post('/inventory/suppliers', v);
      } else {
        await _api.put('/inventory/suppliers/${p['id']}', v);
      }
      ref.invalidate(_proveedoresProvider);
    },
  );

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Builder(
        builder: (context) => PaginaModulo(
          titulo: 'Inventario',
          inferior: const TabBar(
            tabs: [
              Tab(text: 'Artículos'),
              Tab(text: 'Proveedores'),
            ],
          ),
          accion: FloatingActionButton.extended(
            onPressed: () {
              if (DefaultTabController.of(context).index == 0) {
                _editarArticulo(null);
              } else {
                _editarProveedor(null);
              }
            },
            icon: const Icon(Icons.add),
            label: const Text('Nuevo'),
          ),
          cuerpo: TabBarView(children: [_articulos(), _proveedores()]),
        ),
      ),
    );
  }

  Widget _articulos() {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_articulosProvider),
      child: Asincrono(
        valor: ref.watch(_articulosProvider),
        alReintentar: () => ref.invalidate(_articulosProvider),
        listo: (todos) {
          final alertas = todos.where((a) => a['below_minimum'] == true).length;
          final lista = todos.where((a) {
            if (_soloAlerta && a['below_minimum'] != true) return false;
            return _busqueda.isEmpty ||
                '${a['name']}'.toLowerCase().contains(_busqueda);
          }).toList();
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              TextField(
                decoration: const InputDecoration(
                  hintText: 'Buscar artículo',
                  prefixIcon: Icon(Icons.search),
                ),
                onChanged: (t) =>
                    setState(() => _busqueda = t.trim().toLowerCase()),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  FilterChip(
                    label: Text('Con alerta ($alertas)'),
                    selected: _soloAlerta,
                    onSelected: (v) => setState(() => _soloAlerta = v),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              if (lista.isEmpty)
                const EstadoVacio(
                  icono: Icons.inventory_2_outlined,
                  titulo: 'Sin artículos',
                ),
              for (final a in lista)
                FilaTarjeta(
                  icono: Icons.inventory_2_outlined,
                  colorIcono: a['below_minimum'] == true
                      ? Tonos.rojo
                      : Tonos.verde,
                  titulo: '${a['name']}',
                  tachado: a['is_active'] == false,
                  subtitulo: [
                    'Mínimo ${_cant(a['minimum_stock'])}',
                    if (a['next_expiry'] != null)
                      'caduca ${fechaCorta(a['next_expiry'])}',
                    if (a['supplier_name'] != null) '${a['supplier_name']}',
                    if (a['unit_cost'] != null) dinero(numero(a['unit_cost'])),
                  ].join(' · '),
                  derecha: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '${_cant(a['on_hand'])} ${a['unit']}',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      if (a['below_minimum'] == true)
                        const Pastilla('Bajo mínimo', color: Tonos.rojo),
                    ],
                  ),
                  alTocar: () => showModalBottomSheet<void>(
                    context: context,
                    showDragHandle: true,
                    builder: (hoja) => SafeArea(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          ListTile(
                            leading: const Icon(Icons.swap_vert),
                            title: const Text('Registrar movimiento'),
                            subtitle: const Text(
                              'Compra, uso en paciente, ajuste…',
                            ),
                            onTap: () {
                              Navigator.pop(hoja);
                              _movimiento(a);
                            },
                          ),
                          ListTile(
                            leading: const Icon(Icons.edit_outlined),
                            title: const Text('Editar artículo'),
                            onTap: () {
                              Navigator.pop(hoja);
                              _editarArticulo(a);
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              finDeLista,
            ],
          );
        },
      ),
    );
  }

  Widget _proveedores() {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_proveedoresProvider),
      child: Asincrono(
        valor: ref.watch(_proveedoresProvider),
        alReintentar: () => ref.invalidate(_proveedoresProvider),
        listo: (lista) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (lista.isEmpty)
              const EstadoVacio(
                icono: Icons.local_shipping_outlined,
                titulo: 'Sin proveedores',
              ),
            for (final p in lista)
              FilaTarjeta(
                icono: Icons.local_shipping_outlined,
                titulo: '${p['name']}',
                tachado: p['is_active'] == false,
                subtitulo: [
                  if (p['contact_name'] != null) '${p['contact_name']}',
                  if (p['phone'] != null) '${p['phone']}',
                  if (p['email'] != null) '${p['email']}',
                ].join(' · '),
                derecha: const Icon(Icons.edit_outlined, size: 20),
                alTocar: () => _editarProveedor(p),
              ),
            finDeLista,
          ],
        ),
      ),
    );
  }
}
