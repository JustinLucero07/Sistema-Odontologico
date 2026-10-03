import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/ui.dart';

final _soloAbiertasProvider = StateProvider.autoDispose<bool>((ref) => true);

final ordenesLabProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) {
      final abiertas = ref.watch(_soloAbiertasProvider);
      return ref
          .watch(apiProvider)
          .lista('/laboratory/orders', query: {'open_only': abiertas});
    });
final _laboratoriosProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref.watch(apiProvider).lista('/laboratory/laboratories'),
    );
final _catalogoLabProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/laboratory/catalog'),
);

List<Opcion> _opciones(Map<String, dynamic> c, String clave) => [
  for (final e in (c[clave] as List? ?? [])) ('${e['code']}', '${e['label']}'),
];

Color colorOrden(String? estado) => switch (estado) {
  'borrador' => Tonos.gris,
  'enviado' || 'en_proceso' => Tonos.azul,
  'recibido' || 'probado' => Tonos.ambar,
  'instalado' => Tonos.verde,
  'rechazado' => Tonos.rojo,
  'cancelado' => Tonos.gris,
  _ => Tonos.violeta,
};

/// Alta o edición de una orden de laboratorio. Si se da [pacienteId], no se
/// pregunta el paciente (se abre desde su ficha).
Future<void> editarOrdenLab(
  BuildContext context,
  WidgetRef ref, {
  Map<String, dynamic>? orden,
  String? pacienteId,
  String? pacienteNombre,
}) async {
  final api = ref.read(apiProvider);
  final catalogo = await cargarOAvisar(
    context,
    ref.read(_catalogoLabProvider.future),
  );
  if (catalogo == null) return;
  if (!context.mounted) return;
  final labs = await cargarOAvisar(
    context,
    ref.read(_laboratoriosProvider.future),
  );
  if (labs == null) return;
  if (!context.mounted) return;
  if (labs.isEmpty) {
    avisar(
      context,
      'Primero registre un laboratorio en la pestaña Laboratorios.',
    );
    return;
  }
  await mostrarFormulario(
    context,
    titulo: orden == null ? 'Nueva orden' : 'Editar orden',
    subtitulo: orden == null ? 'Trabajo enviado al laboratorio dental.' : null,
    icono: Icons.precision_manufacturing_outlined,
    campos: [
      if (orden == null && pacienteId == null)
        Campo(
          'patient_id',
          'Paciente',
          tipo: TipoCampo.buscar,
          requerido: true,
          buscar: buscadorPacientes(api),
        ),
      Campo(
        'laboratory_id',
        'Laboratorio',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: [for (final l in labs) ('${l['id']}', '${l['name']}')],
        inicial: orden?['laboratory_id'],
      ),
      Campo(
        'work_type',
        'Tipo de trabajo',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: _opciones(catalogo, 'work_types'),
        inicial: orden?['work_type'],
      ),
      Campo(
        'description',
        'Descripción',
        tipo: TipoCampo.multilinea,
        requerido: true,
        inicial: orden?['description'],
      ),
      Campo(
        'fdi',
        'Piezas (FDI)',
        ayuda: 'Separadas por coma: 11, 21',
        inicial: (orden?['fdi_numbers'] as List?)?.join(', '),
        mitad: true,
      ),
      Campo('shade', 'Color', inicial: orden?['shade'], mitad: true),
      Campo('material', 'Material', inicial: orden?['material'], mitad: true),
      Campo(
        'due_on',
        'Fecha de entrega',
        tipo: TipoCampo.fecha,
        inicial: orden?['due_on'],
        mitad: true,
      ),
      Campo('cost', 'Costo', tipo: TipoCampo.dinero, inicial: orden?['cost']),
      Campo(
        'notes',
        'Notas',
        tipo: TipoCampo.multilinea,
        inicial: orden?['notes'],
      ),
    ],
    alGuardar: (v) async {
      final fdi = '${v.remove('fdi') ?? ''}'
          .split(RegExp(r'[,\s]+'))
          .where((e) => e.isNotEmpty)
          .toList();
      final datos = {...v, 'fdi_numbers': fdi};
      if (orden == null) {
        if (pacienteId != null) datos['patient_id'] = pacienteId;
        await api.post('/laboratory/orders', datos);
      } else {
        await api.put('/laboratory/orders/${orden['id']}', datos);
      }
      ref.invalidate(ordenesLabProvider);
    },
  );
}

Future<void> cambiarEstadoOrden(
  BuildContext context,
  WidgetRef ref,
  Map<String, dynamic> orden,
) async {
  final api = ref.read(apiProvider);
  final catalogo = await cargarOAvisar(
    context,
    ref.read(_catalogoLabProvider.future),
  );
  if (catalogo == null) return;
  if (!context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: 'Cambiar estado',
    subtitulo: '${orden['patient_name']} · ${orden['description']}',
    icono: Icons.timeline,
    campos: [
      Campo(
        'status',
        'Nuevo estado',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: _opciones(catalogo, 'statuses'),
        inicial: orden['status'],
      ),
      const Campo('note', 'Nota', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      await api.put('/laboratory/orders/${orden['id']}/status', v);
      ref.invalidate(ordenesLabProvider);
    },
  );
}

/// Tarjeta de una orden con sus acciones.
class TarjetaOrdenLab extends ConsumerWidget {
  const TarjetaOrdenLab({
    super.key,
    required this.orden,
    this.conPaciente = true,
  });

  final Map<String, dynamic> orden;
  final bool conPaciente;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = orden;
    return FutureBuilder<Map<String, dynamic>>(
      future: ref.read(_catalogoLabProvider.future),
      builder: (context, snap) {
        final estados = snap.hasData
            ? _opciones(snap.data!, 'statuses')
            : <Opcion>[];
        final tipos = snap.hasData
            ? _opciones(snap.data!, 'work_types')
            : <Opcion>[];
        final atraso = (o['days_overdue'] as num? ?? 0) > 0;
        return FilaTarjeta(
          icono: Icons.precision_manufacturing_outlined,
          colorIcono: atraso ? Tonos.rojo : colorOrden(o['status']),
          titulo: conPaciente
              ? '${o['patient_name']}'
              : etiquetaDe(tipos, o['work_type']),
          subtitulo: [
            if (conPaciente) etiquetaDe(tipos, o['work_type']),
            '${o['laboratory_name']}',
            if (o['due_on'] != null) 'entrega ${fechaCorta(o['due_on'])}',
            if (atraso) '${o['days_overdue']} días de atraso',
            if (o['cost'] != null) dinero(numero(o['cost'])),
          ].join(' · '),
          derecha: Pastilla(
            etiquetaDe(estados, o['status']),
            color: colorOrden(o['status']),
          ),
          alTocar: () => showModalBottomSheet<void>(
            context: context,
            showDragHandle: true,
            builder: (hoja) => SafeArea(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ListTile(
                    title: Text('${o['description']}'),
                    subtitle: Text(
                      (o['events'] as List? ?? [])
                          .map(
                            (e) =>
                                '${fechaCorta(e['created_at'])} ${etiquetaDe(estados, e['status'])}',
                          )
                          .join('\n'),
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.timeline),
                    title: const Text('Cambiar estado'),
                    onTap: () {
                      Navigator.pop(hoja);
                      cambiarEstadoOrden(context, ref, o);
                    },
                  ),
                  ListTile(
                    leading: const Icon(Icons.edit_outlined),
                    title: const Text('Editar orden'),
                    onTap: () {
                      Navigator.pop(hoja);
                      editarOrdenLab(context, ref, orden: o);
                    },
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class LaboratorioPage extends ConsumerWidget {
  const LaboratorioPage({super.key});

  Future<void> _editarLab(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic>? l,
  ) => mostrarFormulario(
    context,
    titulo: l == null ? 'Nuevo laboratorio' : 'Editar laboratorio',
    icono: Icons.science_outlined,
    campos: [
      Campo('name', 'Nombre', requerido: true, inicial: l?['name']),
      Campo('contact_name', 'Contacto', inicial: l?['contact_name']),
      Campo(
        'phone',
        'Teléfono',
        tipo: TipoCampo.telefono,
        inicial: l?['phone'],
        mitad: true,
      ),
      Campo(
        'email',
        'Correo',
        tipo: TipoCampo.correo,
        inicial: l?['email'],
        mitad: true,
      ),
      Campo('address', 'Dirección', inicial: l?['address']),
      Campo(
        'default_turnaround_days',
        'Días de entrega habituales',
        tipo: TipoCampo.entero,
        inicial: l?['default_turnaround_days'],
      ),
      Campo('notes', 'Notas', tipo: TipoCampo.multilinea, inicial: l?['notes']),
      Campo(
        'is_active',
        'Activo',
        tipo: TipoCampo.interruptor,
        inicial: l?['is_active'] ?? true,
      ),
    ],
    alGuardar: (v) async {
      final api = ref.read(apiProvider);
      if (l == null) {
        await api.post('/laboratory/laboratories', v);
      } else {
        await api.put('/laboratory/laboratories/${l['id']}', v);
      }
      ref.invalidate(_laboratoriosProvider);
    },
  );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final abiertas = ref.watch(_soloAbiertasProvider);
    return DefaultTabController(
      length: 2,
      child: Builder(
        builder: (context) => PaginaModulo(
          titulo: 'Laboratorio',
          inferior: const TabBar(
            tabs: [
              Tab(text: 'Órdenes'),
              Tab(text: 'Laboratorios'),
            ],
          ),
          accion: FloatingActionButton.extended(
            onPressed: () => DefaultTabController.of(context).index == 0
                ? editarOrdenLab(context, ref)
                : _editarLab(context, ref, null),
            icon: const Icon(Icons.add),
            label: const Text('Nuevo'),
          ),
          cuerpo: TabBarView(
            children: [
              RefreshIndicator(
                onRefresh: () async => ref.invalidate(ordenesLabProvider),
                child: Asincrono(
                  valor: ref.watch(ordenesLabProvider),
                  alReintentar: () => ref.invalidate(ordenesLabProvider),
                  listo: (lista) => ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      Row(
                        children: [
                          FilterChip(
                            label: const Text('Solo abiertas'),
                            selected: abiertas,
                            onSelected: (v) =>
                                ref.read(_soloAbiertasProvider.notifier).state =
                                    v,
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      if (lista.isEmpty)
                        const EstadoVacio(
                          icono: Icons.precision_manufacturing_outlined,
                          titulo: 'Sin órdenes',
                        ),
                      for (final o in lista) TarjetaOrdenLab(orden: o),
                      finDeLista,
                    ],
                  ),
                ),
              ),
              RefreshIndicator(
                onRefresh: () async => ref.invalidate(_laboratoriosProvider),
                child: Asincrono(
                  valor: ref.watch(_laboratoriosProvider),
                  alReintentar: () => ref.invalidate(_laboratoriosProvider),
                  listo: (lista) => ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (lista.isEmpty)
                        const EstadoVacio(
                          icono: Icons.science_outlined,
                          titulo: 'Sin laboratorios',
                        ),
                      for (final l in lista)
                        FilaTarjeta(
                          icono: Icons.science_outlined,
                          titulo: '${l['name']}',
                          tachado: l['is_active'] == false,
                          subtitulo: [
                            if (l['contact_name'] != null)
                              '${l['contact_name']}',
                            if (l['phone'] != null) '${l['phone']}',
                            if (l['default_turnaround_days'] != null)
                              '${l['default_turnaround_days']} días',
                          ].join(' · '),
                          derecha: const Icon(Icons.edit_outlined, size: 20),
                          alTocar: () => _editarLab(context, ref, l),
                        ),
                      finDeLista,
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
