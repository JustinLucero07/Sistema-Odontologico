import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
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
      loading: () => const Center(child: CircularProgressIndicator()),
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

class _Odontograma extends ConsumerWidget {
  const _Odontograma({required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final odontograma = ref.watch(_odontogramaProvider(pacienteId));

    return odontograma.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => EstadoError(
        mensaje: e is ErrorApi
            ? e.mensaje
            : 'No se pudo cargar el odontograma.',
        onReintentar: () => ref.invalidate(_odontogramaProvider(pacienteId)),
      ),
      data: (datos) {
        final condiciones = (datos?['conditions'] as List? ?? [])
            .cast<Map<String, dynamic>>();
        final dientes = <String, Diente>{};
        for (final fdi in [...filaArcada('upper'), ...filaArcada('lower')]) {
          final arcada = fdi.startsWith('1') || fdi.startsWith('2')
              ? 'upper'
              : 'lower';
          final delDiente = condiciones
              .where((c) => c['fdi_number'] == fdi)
              .toList();
          final completa = delDiente
              .where((c) => c['surface'] == 'whole')
              .firstOrNull;
          final codigo = completa?['condition'] as String?;
          dientes[fdi] = Diente(
            fdi: fdi,
            arcada: arcada,
            ausente: codigo == 'ausente' || codigo == 'extraccion_realizada',
            relleno: codigo != null ? _colorCondicion(codigo) : null,
          );
        }

        return ListView(
          padding: const EdgeInsets.all(12),
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
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(
                  'Versión del ${DateFormat('dd/MM/yyyy').format(DateTime.parse(datos['created_at']).toLocal())}',
                  style: TextStyle(
                    fontSize: 12.5,
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurface.withValues(alpha: 0.55),
                  ),
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
                    onTocarDiente: (fdi) {
                      final delDiente = condiciones
                          .where((c) => c['fdi_number'] == fdi)
                          .toList();
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          duration: const Duration(seconds: 3),
                          content: Text(
                            delDiente.isEmpty
                                ? 'Pieza $fdi · sana'
                                : 'Pieza $fdi · ${delDiente.map((c) => c['condition']).join(', ')}',
                          ),
                        ),
                      );
                    },
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
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
            ),
            const SizedBox(height: 14),
            // El color nunca va solo: cada uno se nombra en la leyenda.
            Wrap(
              spacing: 14,
              runSpacing: 8,
              children: [
                for (final (codigo, etiqueta) in _leyenda)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 11,
                        height: 11,
                        decoration: BoxDecoration(
                          color: codigo == 'sano'
                              ? Colors.transparent
                              : (codigo == 'ausente'
                                    ? Colors.grey
                                    : _colorCondicion(codigo)),
                          borderRadius: BorderRadius.circular(3),
                          border: Border.all(
                            color: Theme.of(
                              context,
                            ).colorScheme.onSurface.withValues(alpha: 0.3),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(etiqueta, style: const TextStyle(fontSize: 12.5)),
                    ],
                  ),
              ],
            ),
          ],
        );
      },
    );
  }

  static const _leyenda = [
    ('sano', 'Sano'),
    ('caries', 'Caries'),
    ('restauracion', 'Restauración'),
    ('corona', 'Corona'),
    ('endodoncia', 'Endodoncia'),
    ('implante', 'Implante'),
    ('sellante', 'Sellante'),
    ('ausente', 'Ausente'),
  ];

  /// Mismos colores que el catálogo de condiciones de la web.
  Color? _colorCondicion(String codigo) => switch (codigo) {
    'caries' => const Color(0xFFE53935),
    'restauracion' => const Color(0xFF1E88E5),
    'corona' => const Color(0xFFFDD835),
    'endodoncia' => const Color(0xFF6D4C41),
    'implante' => const Color(0xFF00897B),
    'sellante' => const Color(0xFF7CB342),
    'protesis' => const Color(0xFF3949AB),
    _ => null,
  };
}

class _Cuenta extends ConsumerWidget {
  const _Cuenta({required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cuenta = ref.watch(_cuentaProvider(pacienteId));

    return cuenta.when(
      loading: () => const Center(child: CircularProgressIndicator()),
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
