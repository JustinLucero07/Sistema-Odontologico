import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/odontograma/condiciones.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/odontograma/odontograma_widget.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/glass.dart';

final _fichaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>(
      (ref, id) => ref.watch(pacientesRepoProvider).ficha(id),
    );

final _odontogramaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>?, String>(
      (ref, id) => ref.watch(pacientesRepoProvider).odontograma(id),
    );

final _cuentaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>(
      (ref, id) => ref.watch(pacientesRepoProvider).cuenta(id),
    );

class PacienteDetallePage extends ConsumerWidget {
  const PacienteDetallePage({
    super.key,
    required this.pacienteId,
    required this.nombre,
  });

  final String pacienteId;
  final String nombre;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(authProvider).usuario;

    return DefaultTabController(
      length: 3,
      child: AmbientBackground(
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(
            flexibleSpace: const GlassAppBarBackground(),
            title: Text(nombre, overflow: TextOverflow.ellipsis),
            bottom: const PreferredSize(
              preferredSize: Size.fromHeight(56),
              child: _PestanasVidrio(),
            ),
          ),
          body: TabBarView(
            children: [
              _Ficha(pacienteId: pacienteId),
              _Odontograma(pacienteId: pacienteId),
              _Cuenta(pacienteId: pacienteId),
            ],
          ),
          floatingActionButton: (usuario?.puede('imaging:write') ?? false)
              ? _BotonAcciones(pacienteId: pacienteId, nombre: nombre)
              : null,
        ),
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

    return ficha.when(
      loading: () => const EsqueletoLista(filas: 4, conTarjetas: true),
      error: (e, _) => EstadoError(
        mensaje: e is ErrorApi ? e.mensaje : 'No se pudo cargar la ficha.',
        onReintentar: () => ref.invalidate(_fichaProvider(pacienteId)),
      ),
      data: (p) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          GlassCard(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _dato(context, 'Cédula', p['national_id']),
                  _dato(context, 'Teléfono', p['phone']),
                  _dato(context, 'WhatsApp', p['whatsapp']),
                  _dato(context, 'Correo', p['email']),
                  _dato(context, 'Dirección', p['address']),
                  _dato(
                    context,
                    'Fecha de nacimiento',
                    p['birth_date'] != null
                        ? DateFormat(
                            'dd/MM/yyyy',
                          ).format(DateTime.parse(p['birth_date']))
                        : null,
                  ),
                ],
              ),
            ),
          ),
          if (p['notes'] != null && '${p['notes']}'.isNotEmpty) ...[
            const SizedBox(height: 12),
            GlassCard(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Notas',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 6),
                    Text('${p['notes']}', style: const TextStyle(height: 1.5)),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _dato(BuildContext context, String etiqueta, dynamic valor) {
    final texto = valor == null || '$valor'.isEmpty ? '—' : '$valor';
    final vacio = texto == '—';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              etiqueta,
              style: TextStyle(
                fontSize: 12.5,
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.55),
              ),
            ),
          ),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(
                fontSize: 14.5,
                // Un campo vacío se ve vacío: escribirlo en el mismo tono que
                // un dato real hace que parezca que hay información.
                color: vacio
                    ? Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.35)
                    : null,
              ),
            ),
          ),
        ],
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
                      'Se muestra la boca sana. Regístrelo desde la versión de escritorio.',
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
                    onTocarDiente: (fdi) => _verPieza(
                      fdi,
                      todas.where((c) => c['fdi_number'] == fdi).toList(),
                    ),
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
                          onTocar: (fdi) => _verPieza(
                            fdi,
                            todas.where((c) => c['fdi_number'] == fdi).toList(),
                          ),
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
  Future<void> _verPieza(
    String fdi,
    List<Map<String, dynamic>> delDiente,
  ) async {
    setState(() => _seleccionado = fdi);
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        final scheme = Theme.of(context).colorScheme;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Pieza $fdi',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
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
                      ],
                    ),
                  ),
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

class _Cuenta extends ConsumerWidget {
  const _Cuenta({required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cuenta = ref.watch(_cuentaProvider(pacienteId));

    return cuenta.when(
      loading: () => const EsqueletoLista(filas: 4, conTarjetas: true),
      error: (e, _) => EstadoError(
        mensaje: e is ErrorApi
            ? e.mensaje
            : 'No se pudo cargar el estado de cuenta.',
        onReintentar: () => ref.invalidate(_cuentaProvider(pacienteId)),
      ),
      data: (datos) {
        final saldo = double.tryParse('${datos['balance']}') ?? 0;
        final cargos = (datos['charges'] as List? ?? [])
            .cast<Map<String, dynamic>>();

        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            GlassCard(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Saldo',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: Theme.of(
                          context,
                        ).colorScheme.onSurface.withValues(alpha: 0.55),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      dinero(saldo),
                      style: const TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -1,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                    Text(
                      saldo > 0
                          ? 'El paciente debe'
                          : (saldo < 0
                                ? 'Saldo a favor del paciente'
                                : 'Cuenta saldada'),
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Theme.of(
                          context,
                        ).colorScheme.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (cargos.isEmpty)
              const EstadoVacio(
                icono: Icons.receipt_long,
                titulo: 'Sin cargos registrados',
              )
            else ...[
              Text('Cargos', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              for (final c in cargos)
                GlassCard(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text('${c['description']}'),
                    subtitle: Text(
                      '${DateFormat('dd/MM/yyyy').format(DateTime.parse(c['issued_on']))}'
                      ' · pagado ${dinero(double.tryParse('${c['paid']}') ?? 0)}',
                    ),
                    trailing: Text(
                      dinero(double.tryParse('${c['pending']}') ?? 0),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                ),
            ],
          ],
        );
      },
    );
  }
}

/// Lo que el móvil aporta y el escritorio no puede: la cámara en la mano.
class _BotonAcciones extends ConsumerWidget {
  const _BotonAcciones({required this.pacienteId, required this.nombre});

  final String pacienteId;
  final String nombre;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FloatingActionButton.extended(
      onPressed: () => _abrirHoja(context, ref),
      icon: const Icon(Icons.add_a_photo),
      label: const Text('Registrar'),
    );
  }

  void _abrirHoja(BuildContext context, WidgetRef ref) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (hoja) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera),
              title: const Text('Tomar foto o radiografía'),
              subtitle: const Text('Se sube a la ficha del paciente'),
              onTap: () {
                Navigator.pop(hoja);
                _capturar(context, ref, ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Elegir de la galería'),
              onTap: () {
                Navigator.pop(hoja);
                _capturar(context, ref, ImageSource.gallery);
              },
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.edit_note),
              title: const Text('Registrar evolución'),
              onTap: () {
                Navigator.pop(hoja);
                _registrarEvolucion(context, ref);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _capturar(
    BuildContext context,
    WidgetRef ref,
    ImageSource origen,
  ) async {
    final archivo = await ImagePicker().pickImage(
      source: origen,
      // Una foto de 12 MP son ~6 MB por la red móvil de la clínica. 2000 px de
      // lado basta de sobra para mirar una radiografía en pantalla.
      maxWidth: 2000,
      imageQuality: 88,
    );
    if (archivo == null || !context.mounted) return;

    final datos = await showDialog<(String, String, String)>(
      context: context,
      builder: (_) => const _DialogoImagen(),
    );
    if (datos == null || !context.mounted) return;

    final (titulo, tipo, piezas) = datos;
    try {
      await ref
          .read(pacientesRepoProvider)
          .subirImagen(
            pacienteId: pacienteId,
            rutaArchivo: archivo.path,
            titulo: titulo,
            tipo: tipo,
            piezas: piezas,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Imagen subida a la ficha')),
        );
      }
    } on ErrorApi catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.mensaje)));
      }
    }
  }

  Future<void> _registrarEvolucion(BuildContext context, WidgetRef ref) async {
    final datos = await showDialog<(String, String, String)>(
      context: context,
      builder: (_) => const _DialogoEvolucion(),
    );
    if (datos == null || !context.mounted) return;

    final (procedimiento, piezas, indicaciones) = datos;
    try {
      await ref
          .read(pacientesRepoProvider)
          .registrarEvolucion(
            pacienteId: pacienteId,
            procedimiento: procedimiento,
            piezas: piezas,
            indicaciones: indicaciones,
          );
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Evolución registrada')));
      }
    } on ErrorApi catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.mensaje)));
      }
    }
  }
}

class _DialogoImagen extends StatefulWidget {
  const _DialogoImagen();

  @override
  State<_DialogoImagen> createState() => _DialogoImagenState();
}

class _DialogoImagenState extends State<_DialogoImagen> {
  final _titulo = TextEditingController();
  final _piezas = TextEditingController();
  // Lo que sale de la cámara de un teléfono es casi siempre una foto de la
  // boca; una radiografía viene del sensor, no del móvil.
  String _tipo = 'foto_intraoral';

  static const _tipos = {
    'panoramica': 'Radiografía panorámica',
    'periapical': 'Radiografía periapical',
    'bitewing': 'Bitewing',
    'foto_intraoral': 'Fotografía intraoral',
    'foto_extraoral': 'Fotografía extraoral',
    'otro': 'Otra imagen',
  };

  @override
  void dispose() {
    _titulo.dispose();
    _piezas.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Datos de la imagen'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _titulo,
              autofocus: true,
              // Sin esto el botón decide si está activo al abrir el diálogo y
              // no vuelve a mirar: queda gris aunque ya haya un título escrito.
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(labelText: 'Título'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _tipo,
              decoration: const InputDecoration(labelText: 'Tipo de estudio'),
              items: [
                for (final e in _tipos.entries)
                  DropdownMenuItem(value: e.key, child: Text(e.value)),
              ],
              onChanged: (v) => setState(() => _tipo = v ?? 'otro'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _piezas,
              decoration: const InputDecoration(
                labelText: 'Piezas (FDI)',
                hintText: '16, 17',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          style: _botonDialogo,
          onPressed: _titulo.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (
                  _titulo.text.trim(),
                  _tipo,
                  _piezas.text.replaceAll(' ', ''),
                )),
          child: const Text('Subir'),
        ),
      ],
    );
  }
}

class _DialogoEvolucion extends StatefulWidget {
  const _DialogoEvolucion();

  @override
  State<_DialogoEvolucion> createState() => _DialogoEvolucionState();
}

class _DialogoEvolucionState extends State<_DialogoEvolucion> {
  final _procedimiento = TextEditingController();
  final _piezas = TextEditingController();
  final _indicaciones = TextEditingController();

  @override
  void dispose() {
    _procedimiento.dispose();
    _piezas.dispose();
    _indicaciones.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Registrar evolución'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _procedimiento,
              autofocus: true,
              onChanged: (_) => setState(() {}),
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Procedimiento realizado',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _piezas,
              decoration: const InputDecoration(
                labelText: 'Piezas (FDI)',
                hintText: '46',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _indicaciones,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Indicaciones al paciente',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, (
            _procedimiento.text.trim(),
            _piezas.text.replaceAll(' ', ''),
            _indicaciones.text.trim(),
          )),
          child: const Text('Guardar'),
        ),
      ],
    );
  }
}

/// El tema da a los botones rellenos el ancho completo, pensado para el login.
/// Dentro de un diálogo eso empuja «Cancelar» a otra línea.
final _botonDialogo = FilledButton.styleFrom(minimumSize: const Size(96, 44));

/// Pestañas como selector segmentado de vidrio: una cápsula con la opción
/// activa iluminada, en vez de la línea subrayada de Material.
class _PestanasVidrio extends StatelessWidget {
  const _PestanasVidrio();

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
          tabs: const [
            Tab(height: 36, text: 'Ficha'),
            Tab(height: 36, text: 'Odontograma'),
            Tab(height: 36, text: 'Cuenta'),
          ],
        ),
      ),
    );
  }
}
