import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/odontograma/condiciones.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/odontograma/odontograma_widget.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../agenda/cita_form.dart';
import 'pestanas.dart';
import '../../shared/contacto.dart';

final _fichaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>(
      (ref, id) => ref.watch(pacientesRepoProvider).ficha(id),
    );

final _odontogramaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>?, String>(
      (ref, id) => ref.watch(pacientesRepoProvider).odontograma(id),
    );

const _soloPiezaCompleta = {
  'corona',
  'puente',
  'implante',
  'ausente',
  'extraccion_indicada',
  'extraccion_realizada',
  'endodoncia',
  'protesis',
  'movilidad',
  'diente_retenido',
};

const _pestanas = [
  'Ficha',
  'Historia',
  'Odontograma',
  'Tratamientos',
  'Clínico',
  'Imágenes',
  'Citas',
  'Cuenta',
];

/// La ficha del paciente con todo lo que tiene la web: datos, historia
/// clínica, odontograma, tratamientos, evoluciones y recetas, imágenes, citas
/// y cuenta. El botón flotante cambia según la pestaña.
class PacienteDetallePage extends ConsumerStatefulWidget {
  const PacienteDetallePage({
    super.key,
    required this.pacienteId,
    required this.nombre,
  });

  final String pacienteId;
  final String nombre;

  @override
  ConsumerState<PacienteDetallePage> createState() =>
      _PacienteDetallePageState();
}

class _PacienteDetallePageState extends ConsumerState<PacienteDetallePage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(
    length: _pestanas.length,
    vsync: this,
  )..addListener(() => setState(() {}));

  String get _id => widget.pacienteId;

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Widget? _boton() {
    final u = ref.watch(authProvider).usuario;
    bool puede(String p) => u?.puede(p) ?? false;
    FloatingActionButton fab(IconData i, String t, VoidCallback f) =>
        FloatingActionButton.extended(
          heroTag: 'fab-paciente',
          onPressed: f,
          icon: Icon(i),
          label: Text(t),
        );
    switch (_tabs.index) {
      case 0 when puede('patients:write'):
        return fab(Icons.edit_outlined, 'Editar datos', () async {
          final p = await cargarOAvisar(
            context,
            ref.read(_fichaProvider(_id).future),
          );
          if (p == null) return;
          if (!mounted) return;
          if (await editarPaciente(context, ref, paciente: p) != null) {
            ref.invalidate(_fichaProvider(_id));
          }
        });
      case 1 when puede('medical_history:write'):
        return fab(Icons.note_add_outlined, 'Nueva versión', () async {
          final h = await cargarOAvisar(
            context,
            ref.read(historiaProvider(_id).future),
          );
          if (h == null) return;
          if (mounted) await nuevaVersionHistoria(context, ref, _id, h);
        });
      case 3 when puede('treatment_plans:write'):
        return fab(
          Icons.assignment_add,
          'Nuevo plan',
          () => editarPlan(context, ref, _id),
        );
      case 4:
        return fab(
          Icons.edit_note,
          'Registrar',
          () => menuClinico(context, ref, _id),
        );
      case 5 when puede('imaging:write'):
        return fab(
          Icons.add_a_photo_outlined,
          'Subir',
          () => menuImagen(context, ref, _id),
        );
      case 6 when puede('appointments:write'):
        return fab(Icons.event_available, 'Agendar', () async {
          if (await editarCita(
            context,
            ref,
            pacienteId: _id,
            pacienteNombre: widget.nombre,
          )) {
            ref.invalidate(citasPacienteProvider(_id));
          }
        });
      case 7 when puede('payments:write'):
        return fab(Icons.payments_outlined, 'Cobrar', () async {
          final d = await cargarOAvisar(
            context,
            ref.read(cuentaProvider(_id).future),
          );
          if (d == null) return;
          if (!mounted) return;
          menuCuenta(
            context,
            ref,
            _id,
            (d.cuenta['charges'] as List? ?? []).cast<Map<String, dynamic>>(),
          );
        });
      default:
        return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          flexibleSpace: const GlassAppBarBackground(),
          title: Text(widget.nombre, overflow: TextOverflow.ellipsis),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(56),
            child: _PestanasVidrio(controlador: _tabs),
          ),
        ),
        body: TabBarView(
          controller: _tabs,
          children: [
            _Ficha(pacienteId: _id),
            PestanaHistoria(pacienteId: _id),
            _Odontograma(pacienteId: _id),
            PestanaTratamientos(pacienteId: _id),
            PestanaClinica(pacienteId: _id),
            PestanaImagenes(pacienteId: _id),
            PestanaCitas(pacienteId: _id),
            PestanaCuenta(pacienteId: _id),
          ],
        ),
        floatingActionButton: _boton(),
      ),
    );
  }
}

class _Ficha extends ConsumerWidget {
  const _Ficha({required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ficha = ref.watch(_fichaProvider(pacienteId));
    final puedeBaja =
        ref.watch(authProvider).usuario?.puede('patients:delete') ?? false;
    final scheme = Theme.of(context).colorScheme;

    return ficha.when(
      loading: () => const EsqueletoLista(filas: 4, conTarjetas: true),
      error: (e, _) => EstadoError(
        mensaje: e is ErrorApi ? e.mensaje : 'No se pudo cargar la ficha.',
        onReintentar: () => ref.invalidate(_fichaProvider(pacienteId)),
      ),
      data: (p) {
        final nombre = '${p['first_name']} ${p['last_name']}';
        final iniciales =
            '${'${p['first_name']}'.characters.firstOrNull ?? ''}${'${p['last_name']}'.characters.firstOrNull ?? ''}'
                .toUpperCase();
        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(_fichaProvider(pacienteId)),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              GlassPanel(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 28,
                      backgroundColor: scheme.primary,
                      child: Text(
                        iniciales,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 18,
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            nombre,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          Text(
                            [
                              if (p['age'] != null) '${p['age']} años',
                              if (p['sex'] != null) etiquetaDe(sexos, p['sex']),
                              if (p['national_id'] != null)
                                'Cédula ${p['national_id']}',
                            ].join(' · '),
                            style: TextStyle(
                              fontSize: 13,
                              color: scheme.onSurface.withValues(alpha: 0.6),
                            ),
                          ),
                        ],
                      ),
                    ),
                    BotonesContacto(
                      telefono: p['phone'] as String?,
                      whatsapp: p['whatsapp'] as String?,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              _Bloque(
                titulo: 'Contacto',
                icono: Icons.call_outlined,
                datos: [
                  ('Teléfono', p['phone']),
                  ('WhatsApp', p['whatsapp']),
                  ('Correo', p['email']),
                ],
              ),
              _Bloque(
                titulo: 'Domicilio y trabajo',
                icono: Icons.home_outlined,
                datos: [
                  ('Dirección', p['address']),
                  ('Ciudad', p['city']),
                  ('Ocupación', p['occupation']),
                  (
                    'Nacimiento',
                    p['birth_date'] == null
                        ? null
                        : fechaCorta(p['birth_date']),
                  ),
                ],
              ),
              _Bloque(
                titulo: 'Emergencia',
                icono: Icons.contact_emergency_outlined,
                color: Tonos.rojo,
                datos: [
                  ('Contacto', p['emergency_contact_name']),
                  ('Teléfono', p['emergency_contact_phone']),
                ],
              ),
              if (p['notes'] != null && '${p['notes']}'.isNotEmpty)
                _Bloque(
                  titulo: 'Observaciones',
                  icono: Icons.sticky_note_2_outlined,
                  color: Tonos.ambar,
                  datos: [('', p['notes'])],
                ),
              if (puedeBaja) ...[
                const SizedBox(height: 6),
                TextButton.icon(
                  style: TextButton.styleFrom(foregroundColor: scheme.error),
                  onPressed: () async {
                    final ok = await confirmar(
                      context,
                      titulo: '¿Dar de baja a $nombre?',
                      mensaje:
                          'Dejará de aparecer en la lista y la agenda. Su historia clínica no se borra.',
                      textoConfirmar: 'Dar de baja',
                      peligro: true,
                    );
                    if (!ok || !context.mounted) return;
                    if (await intentar(
                      context,
                      () =>
                          ref.read(apiProvider).delete('/patients/$pacienteId'),
                      exito: 'Paciente dado de baja',
                    )) {
                      if (context.mounted) Navigator.of(context).pop();
                    }
                  },
                  icon: const Icon(Icons.person_off_outlined),
                  label: const Text('Dar de baja'),
                ),
              ],
              finDeLista,
            ],
          ),
        );
      },
    );
  }
}

class _Bloque extends StatelessWidget {
  const _Bloque({
    required this.titulo,
    required this.icono,
    required this.datos,
    this.color,
  });

  final String titulo;
  final IconData icono;
  final List<(String, dynamic)> datos;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final c = color ?? scheme.primary;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: c.withValues(alpha: 0.13),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(icono, size: 17, color: c),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    titulo.toUpperCase(),
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                      color: scheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              for (final (etiqueta, valor) in datos)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: etiqueta.isEmpty
                      ? Text(
                          '${valor ?? '—'}',
                          style: const TextStyle(height: 1.45),
                        )
                      : Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 100,
                              child: Text(
                                etiqueta,
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: scheme.onSurface.withValues(
                                    alpha: 0.55,
                                  ),
                                ),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                valor == null || '$valor'.isEmpty
                                    ? '—'
                                    : '$valor',
                                style: TextStyle(
                                  color: valor == null || '$valor'.isEmpty
                                      ? scheme.onSurface.withValues(alpha: 0.35)
                                      : null,
                                ),
                              ),
                            ),
                          ],
                        ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Odontograma extends ConsumerStatefulWidget {
  const _Odontograma({required this.pacienteId});

  final String pacienteId;

  @override
  ConsumerState<_Odontograma> createState() => _OdontogramaState();
}

class _OdontogramaState extends ConsumerState<_Odontograma> {
  bool _temporal = false;
  String? _seleccionado;

  String get pacienteId => widget.pacienteId;

  @override
  Widget build(BuildContext context) {
    final odontograma = ref.watch(_odontogramaProvider(pacienteId));
    final scheme = Theme.of(context).colorScheme;
    final tenue = scheme.onSurface.withValues(alpha: 0.55);

    return odontograma.when(
      loading: () => const EsqueletoBloque(),
      error: (e, _) => EstadoError(
        mensaje: e is ErrorApi
            ? e.mensaje
            : 'No se pudo cargar el odontograma.',
        onReintentar: () => ref.invalidate(_odontogramaProvider(pacienteId)),
      ),
      data: (datos) {
        final todas = (datos?['conditions'] as List? ?? [])
            .cast<Map<String, dynamic>>();
        final piezas = [
          ...filaArcada('upper', temporal: _temporal),
          ...filaArcada('lower', temporal: _temporal),
        ];
        final hayTemporales = todas.any(
          (c) => '5678'.contains('${c['fdi_number']}'[0]),
        );

        final dientes = <String, Diente>{};
        for (final fdi in piezas) {
          final delDiente = todas.where((c) => c['fdi_number'] == fdi);
          final completa = delDiente
              .where((c) => c['surface'] == 'whole')
              .map((c) => c['condition'] as String)
              .firstOrNull;
          final ausente = esPiezaAusente(completa);
          final indicada = completa == 'extraccion_indicada';
          dientes[fdi] = Diente(
            fdi: fdi,
            arcada: '15'.contains(fdi[0]) || '26'.contains(fdi[0])
                ? 'upper'
                : 'lower',
            ausente: ausente,
            aspa: indicada ? condicionDe(completa!).color : null,
            relleno: completa == null || ausente || indicada
                ? null
                : condicionDe(completa).color,
            caras: {
              for (final c in delDiente.where((c) => c['surface'] != 'whole'))
                c['surface'] as String: condicionDe(
                  c['condition'] as String,
                ).color,
            },
          );
        }

        // Hallazgos agrupados por condición, igual que el resumen de la web.
        final visibles = todas.where((c) => piezas.contains(c['fdi_number']));
        final hallazgos = <String, Set<String>>{};
        for (final c in visibles) {
          hallazgos
              .putIfAbsent(c['condition'] as String, () => <String>{})
              .add(c['fdi_number'] as String);
        }
        final afectadas = visibles.map((c) => c['fdi_number']).toSet().length;

        return ListView(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
          children: [
            if (datos == null)
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: EstadoVacio(
                  icono: Icons.healing,
                  titulo: 'Sin odontograma registrado',
                  detalle:
                      'Se muestra la boca sana. Toque una pieza para registrar un hallazgo.',
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 0, 4, 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Versión del ${DateFormat('dd/MM/yyyy').format(DateTime.parse(datos['created_at']).toLocal())}',
                        style: TextStyle(fontSize: 12.5, color: tenue),
                      ),
                    ),
                    Text(
                      afectadas == 0
                          ? 'Sin hallazgos'
                          : '$afectadas ${afectadas == 1 ? 'pieza' : 'piezas'} con hallazgos',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: afectadas == 0 ? tenue : scheme.primary,
                      ),
                    ),
                  ],
                ),
              ),
            if (datos != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _Cifra(
                      valor: _piezasCon(visibles, const [
                        'caries',
                        'restauracion_defectuosa',
                        'tratamiento_pendiente',
                        'extraccion_indicada',
                        'fractura',
                      ]),
                      etiqueta: 'por tratar',
                      alerta: true,
                    ),
                    _Cifra(
                      valor: _piezasCon(visibles, const ['caries']),
                      etiqueta: 'caries',
                    ),
                    _Cifra(
                      valor: _piezasCon(visibles, const [
                        'ausente',
                        'extraccion_realizada',
                      ]),
                      etiqueta: 'ausentes',
                    ),
                  ],
                ),
              ),
            if (hayTemporales || _temporal)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: SegmentedButton<bool>(
                  showSelectedIcon: false,
                  segments: const [
                    ButtonSegment(value: false, label: Text('Permanente')),
                    ButtonSegment(value: true, label: Text('Temporal')),
                  ],
                  selected: {_temporal},
                  onSelectionChanged: (v) => setState(() {
                    _temporal = v.first;
                    _seleccionado = null;
                  }),
                ),
              ),
            GlassCard(
              clipBehavior: Clip.antiAlias,
              // Dieciséis piezas en el ancho de un teléfono quedan pequeñas.
              // Pellizcar para ampliar es el gesto que cualquiera prueba
              // primero; girar el teléfono también ensancha la arcada.
              child: InteractiveViewer(
                minScale: 1,
                maxScale: 4,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    vertical: 14,
                    horizontal: 4,
                  ),
                  child: OdontogramaWidget(
                    dientes: dientes,
                    temporal: _temporal,
                    seleccionado: _seleccionado,
                    onTocarDiente: (fdi) => _verPieza(fdi, todas),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 10, 4, 0),
              child: Text(
                'Pellizque para ampliar · toque una pieza para ver su detalle',
                style: TextStyle(
                  fontSize: 12,
                  color: scheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (hallazgos.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
                child: Text(
                  'Hallazgos',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 6,
                  ),
                  child: Column(
                    children: [
                      for (final entrada in hallazgos.entries)
                        _FilaHallazgo(
                          condicion: condicionDe(entrada.key),
                          piezas: entrada.value.toList()..sort(),
                          seleccionado: _seleccionado,
                          onTocar: (fdi) => _verPieza(fdi, todas),
                        ),
                    ],
                  ),
                ),
              ),
            ] else
              // Sin hallazgos no hay colores que explicar, pero quien abre la
              // pestaña por primera vez necesita saber qué significan.
              Wrap(
                spacing: 14,
                runSpacing: 8,
                children: [
                  for (final c in condiciones.take(8)) _Leyenda(condicion: c),
                ],
              ),
          ],
        );
      },
    );
  }

  int _piezasCon(Iterable<Map<String, dynamic>> filas, List<String> codigos) =>
      filas
          .where((c) => codigos.contains(c['condition']))
          .map((c) => c['fdi_number'])
          .toSet()
          .length;

  /// Detalle de una pieza en una hoja inferior: en un teléfono es más cómodo
  /// que un aviso que desaparece solo.
  /// Guarda una versión nueva del odontograma (nunca se sobrescribe).
  Future<void> _guardar(List<Map<String, dynamic>> condiciones) async {
    await ref.read(apiProvider).post('/patients/$pacienteId/odontogram', {
      'conditions': [
        for (final c in condiciones)
          {
            'fdi_number': c['fdi_number'],
            'surface': c['surface'],
            'condition': c['condition'],
            'notes': c['notes'],
          },
      ],
    });
    ref.invalidate(_odontogramaProvider(pacienteId));
  }

  Future<void> _agregarHallazgo(
    String fdi,
    List<Map<String, dynamic>> todas,
  ) async {
    await mostrarFormulario(
      context,
      titulo: 'Hallazgo en la pieza $fdi',
      subtitulo: 'Se guarda como versión nueva del odontograma.',
      icono: Icons.healing,
      campos: [
        Campo(
          'condition',
          'Condición',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: [for (final c in condiciones) (c.codigo, c.etiqueta)],
        ),
        Campo(
          'surface',
          'Superficie',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: [
            for (final e in etiquetasSuperficie.entries) (e.key, e.value),
          ],
          inicial: 'whole',
          ayuda: 'Corona, implante, ausente… se aplican a la pieza completa.',
        ),
        const Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
      ],
      alGuardar: (v) async {
        final codigo = '${v['condition']}';
        final superficie = _soloPiezaCompleta.contains(codigo)
            ? 'whole'
            : '${v['surface']}';
        final resto = todas.where((c) {
          if (c['fdi_number'] != fdi) return true;
          if (superficie == 'whole') return false;
          return c['surface'] != 'whole' && c['surface'] != superficie;
        }).toList();
        await _guardar([
          ...resto,
          {
            'fdi_number': fdi,
            'surface': superficie,
            'condition': codigo,
            'notes': v['notes'],
          },
        ]);
      },
    );
  }

  Future<void> _verPieza(String fdi, List<Map<String, dynamic>> todas) async {
    final delDiente = todas.where((c) => c['fdi_number'] == fdi).toList();
    final puedeEditar =
        ref.read(authProvider).usuario?.puede('odontogram:write') ?? false;
    setState(() => _seleccionado = fdi);
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (hoja) {
        final scheme = Theme.of(hoja).colorScheme;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Pieza $fdi', style: Theme.of(hoja).textTheme.titleLarge),
                const SizedBox(height: 2),
                Text(
                  delDiente.isEmpty
                      ? 'Sana, sin hallazgos registrados.'
                      : '${delDiente.length} ${delDiente.length == 1 ? 'hallazgo' : 'hallazgos'}',
                  style: TextStyle(
                    color: scheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(height: 10),
                for (final c in delDiente)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 7),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(top: 3),
                          child: _Punto(
                            color: condicionDe(c['condition'] as String).color,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                condicionDe(c['condition'] as String).etiqueta,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                etiquetasSuperficie[c['surface']] ??
                                    '${c['surface']}',
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: scheme.onSurface.withValues(
                                    alpha: 0.6,
                                  ),
                                ),
                              ),
                              if ((c['notes'] as String?)?.isNotEmpty ?? false)
                                Padding(
                                  padding: const EdgeInsets.only(top: 2),
                                  child: Text(
                                    c['notes'] as String,
                                    style: const TextStyle(fontSize: 13),
                                  ),
                                ),
                            ],
                          ),
                        ),
                        if (puedeEditar)
                          IconButton(
                            tooltip: 'Quitar',
                            icon: const Icon(Icons.delete_outline, size: 20),
                            onPressed: () async {
                              Navigator.pop(hoja);
                              await intentar(
                                context,
                                () => _guardar(
                                  todas.where((x) => x != c).toList(),
                                ),
                                exito: 'Hallazgo quitado (nueva versión)',
                              );
                            },
                          ),
                      ],
                    ),
                  ),
                if (puedeEditar) ...[
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: () {
                      Navigator.pop(hoja);
                      _agregarHallazgo(fdi, todas);
                    },
                    icon: const Icon(Icons.add),
                    label: const Text('Agregar hallazgo'),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
    if (mounted) setState(() => _seleccionado = null);
  }
}

/// Cifra en cápsula de vidrio, igual que en la web.
class _Cifra extends StatelessWidget {
  const _Cifra({
    required this.valor,
    required this.etiqueta,
    this.alerta = false,
  });

  final int valor;
  final String etiqueta;
  final bool alerta;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final rojo = alerta && valor > 0;
    final color = rojo ? scheme.error : scheme.onSurface;
    return Opacity(
      opacity: valor == 0 ? 0.6 : 1,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: rojo
              ? scheme.error.withValues(alpha: 0.1)
              : scheme.surface.withValues(alpha: 0.5),
          border: Border.all(
            color: rojo
                ? Colors.transparent
                : scheme.onSurface.withValues(alpha: 0.1),
          ),
        ),
        child: Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: '$valor ',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
              ),
              TextSpan(text: etiqueta),
            ],
          ),
          style: TextStyle(fontSize: 12.5, color: color),
        ),
      ),
    );
  }
}

class _Punto extends StatelessWidget {
  const _Punto({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    width: 12,
    height: 12,
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(4),
      border: Border.all(
        color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.25),
      ),
    ),
  );
}

// El color nunca va solo: cada uno se nombra.
class _Leyenda extends StatelessWidget {
  const _Leyenda({required this.condicion});

  final Condicion condicion;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      _Punto(color: condicion.color),
      const SizedBox(width: 6),
      Text(condicion.etiqueta, style: const TextStyle(fontSize: 12.5)),
    ],
  );
}

class _FilaHallazgo extends StatelessWidget {
  const _FilaHallazgo({
    required this.condicion,
    required this.piezas,
    required this.onTocar,
    this.seleccionado,
  });

  final Condicion condicion;
  final List<String> piezas;
  final String? seleccionado;
  final void Function(String fdi) onTocar;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _Punto(color: condicion.color),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  condicion.etiqueta,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              Text(
                '${piezas.length}',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: scheme.onSurface.withValues(alpha: 0.6),
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final fdi in piezas)
                Material(
                  color: fdi == seleccionado
                      ? scheme.primary.withValues(alpha: 0.2)
                      : scheme.primary.withValues(alpha: 0.09),
                  borderRadius: BorderRadius.circular(999),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(999),
                    onTap: () => onTocar(fdi),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 11,
                        vertical: 5,
                      ),
                      child: Text(
                        fdi,
                        style: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700,
                          color: scheme.primary,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Pestañas como selector segmentado de vidrio: una cápsula con la opción
/// activa iluminada, en vez de la línea subrayada de Material.
class _PestanasVidrio extends StatelessWidget {
  const _PestanasVidrio({required this.controlador});

  final TabController controlador;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: GlassPanel(
        radius: 24,
        elevated: false,
        padding: const EdgeInsets.all(4),
        child: TabBar(
          controller: controlador,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          dividerColor: Colors.transparent,
          indicatorSize: TabBarIndicatorSize.tab,
          splashBorderRadius: BorderRadius.circular(20),
          labelColor: scheme.primary,
          unselectedLabelColor: scheme.onSurface.withValues(alpha: 0.6),
          labelStyle: const TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13.5,
          ),
          indicator: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            color: dark ? Colors.white.withValues(alpha: 0.1) : Colors.white,
            boxShadow: dark
                ? null
                : const [
                    BoxShadow(
                      color: Color(0x220A2325),
                      blurRadius: 12,
                      offset: Offset(0, 4),
                    ),
                  ],
          ),
          tabs: [for (final t in _pestanas) Tab(height: 36, text: t)],
        ),
      ),
    );
  }
}
