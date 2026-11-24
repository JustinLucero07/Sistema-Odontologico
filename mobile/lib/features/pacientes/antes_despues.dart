import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/api.dart';
import '../../core/api/api_config.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/marca/marca.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Comparaciones antes/después del paciente.
final comparacionesProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>(
      (ref, pacienteId) =>
          ref.watch(apiProvider).lista('/patients/$pacienteId/comparisons'),
    );

bool _esFoto(Map<String, dynamic> i) =>
    '${i['mime_type'] ?? ''}'.startsWith('image/') && i['archived_at'] == null;

/// Sección de la pestaña Imágenes: las comparaciones del paciente.
class SeccionAntesDespues extends ConsumerWidget {
  const SeccionAntesDespues({
    super.key,
    required this.pacienteId,
    required this.imagenes,
  });

  final String pacienteId;
  final List<Map<String, dynamic>> imagenes;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final puede =
        ref.watch(authProvider).usuario?.puede('imaging:write') ?? false;
    final fotos = imagenes.where(_esFoto).toList();
    final token = ref.watch(tokenStoreProvider).accessToken;
    final cab = {if (token != null) 'Authorization': 'Bearer $token'};
    final lista =
        ref.watch(comparacionesProvider(pacienteId)).value ?? const [];
    final scheme = Theme.of(context).colorScheme;
    if (fotos.length < 2 && lista.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'Antes y después',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
            ),
            if (puede && fotos.length >= 2)
              TextButton.icon(
                onPressed: () async {
                  final id = await editarComparacion(
                    context,
                    ref,
                    pacienteId,
                    fotos,
                  );
                  if (id != null) {
                    ref.invalidate(comparacionesProvider(pacienteId));
                  }
                },
                icon: const Icon(Icons.compare, size: 18),
                label: const Text('Nuevo'),
              ),
          ],
        ),
        if (lista.isEmpty)
          Text(
            'Compare dos fotos del paciente con un deslizador.',
            style: TextStyle(fontSize: 12.5, color: scheme.onSurfaceVariant),
          )
        else
          SizedBox(
            height: 168,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: lista.length,
              separatorBuilder: (_, _) => const SizedBox(width: 10),
              itemBuilder: (context, i) {
                final c = lista[i];
                return SizedBox(
                  width: 200,
                  child: GlassCard(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => VisorComparacion(
                          comparacion: c,
                          pacienteId: pacienteId,
                          fotos: fotos,
                        ),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              _foto(c['after']['id'], cab),
                              ClipRect(
                                child: Align(
                                  alignment: Alignment.centerLeft,
                                  widthFactor: 0.5,
                                  child: _foto(c['before']['id'], cab),
                                ),
                              ),
                              const Center(
                                child: SizedBox(
                                  width: 2,
                                  child: ColoredBox(color: Colors.white),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${c['title']}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                c['share_consent'] == true
                                    ? 'Autorizado para redes'
                                    : '${c['treatment'] ?? 'Comparación'}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: c['share_consent'] == true
                                      ? Tonos.verde
                                      : null,
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
            ),
          ),
        const SizedBox(height: 14),
      ],
    );
  }
}

Widget _foto(
  dynamic id,
  Map<String, String> cab, {
  BoxFit fit = BoxFit.cover,
}) => Image.network(
  '${ApiConfig.apiUrl}/images/$id/file',
  headers: cab,
  fit: fit,
  width: double.infinity,
  height: double.infinity,
  errorBuilder: (_, _, _) => const ColoredBox(
    color: Colors.black12,
    child: Center(child: Icon(Icons.broken_image_outlined)),
  ),
);

/// Elegir el antes, el después y los datos. Devuelve el id guardado.
Future<String?> editarComparacion(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
  List<Map<String, dynamic>> fotos, [
  Map<String, dynamic>? actual,
]) async {
  var antes = actual?['before']?['id'] as String?;
  var despues = actual?['after']?['id'] as String?;
  if (actual == null) {
    antes = await _elegirFoto(context, ref, fotos, 'Elija la foto del ANTES');
    if (antes == null || !context.mounted) return null;
    despues = await _elegirFoto(
      context,
      ref,
      fotos.where((f) => f['id'] != antes).toList(),
      'Ahora la del DESPUÉS',
    );
    if (despues == null || !context.mounted) return null;
  }
  String? guardado;
  await mostrarFormulario(
    context,
    titulo: actual == null ? 'Nuevo antes y después' : 'Editar comparación',
    icono: Icons.compare,
    campos: [
      Campo(
        'title',
        'Título',
        requerido: true,
        inicial: actual?['title'],
        ayuda: 'Ej.: Blanqueamiento dental',
      ),
      Campo(
        'treatment',
        'Tratamiento (opcional)',
        inicial: actual?['treatment'],
      ),
      Campo(
        'notes',
        'Notas (opcional)',
        tipo: TipoCampo.multilinea,
        inicial: actual?['notes'],
      ),
      Campo(
        'share_consent',
        'El paciente autorizó usar estas fotos en redes y publicidad',
        tipo: TipoCampo.interruptor,
        inicial: actual?['share_consent'] == true,
        ayuda: 'Sin autorización la comparación solo se ve dentro del sistema.',
      ),
    ],
    alGuardar: (v) async {
      final api = ref.read(apiProvider);
      final cuerpo = {
        ...v,
        'before_image_id': antes,
        'after_image_id': despues,
      };
      final r = actual == null
          ? await api.post('/patients/$pacienteId/comparisons', cuerpo)
          : await api.put('/comparisons/${actual['id']}', cuerpo);
      guardado = '${(r as Map)['id']}';
    },
  );
  return guardado;
}

Future<String?> _elegirFoto(
  BuildContext context,
  WidgetRef ref,
  List<Map<String, dynamic>> fotos,
  String titulo,
) {
  final token = ref.read(tokenStoreProvider).accessToken;
  final cab = {if (token != null) 'Authorization': 'Bearer $token'};
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    builder: (h) => DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.75,
      builder: (_, scroll) => Column(
        children: [
          Text(
            titulo,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: GridView.builder(
              controller: scroll,
              padding: const EdgeInsets.all(14),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
              ),
              itemCount: fotos.length,
              itemBuilder: (_, i) => GestureDetector(
                onTap: () => Navigator.pop(h, '${fotos[i]['id']}'),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      _foto(fotos[i]['id'], cab),
                      Positioned(
                        left: 0,
                        right: 0,
                        bottom: 0,
                        child: Container(
                          color: Colors.black54,
                          padding: const EdgeInsets.all(6),
                          child: Text(
                            '${fotos[i]['title']}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class VisorComparacion extends ConsumerStatefulWidget {
  const VisorComparacion({
    super.key,
    required this.comparacion,
    required this.pacienteId,
    required this.fotos,
  });

  final Map<String, dynamic> comparacion;
  final String pacienteId;
  final List<Map<String, dynamic>> fotos;

  @override
  ConsumerState<VisorComparacion> createState() => _VisorComparacionState();
}

class _VisorComparacionState extends ConsumerState<VisorComparacion> {
  late Map<String, dynamic> _c = widget.comparacion;
  double _pos = 0.5;
  bool _lado = false;
  bool _generando = false;

  Future<void> _paraRedes() async {
    setState(() => _generando = true);
    try {
      final api = ref.read(apiProvider);
      final antes = await api.bytes('/images/${_c['before']['id']}/file');
      final despues = await api.bytes('/images/${_c['after']['id']}/file');
      final marca = ref.read(marcaProvider);
      final png = await imagenParaRedes(
        Uint8List.fromList(antes),
        Uint8List.fromList(despues),
        marca: marca,
        titulo: '${_c['treatment'] ?? _c['title']}',
      );
      final dir = await getTemporaryDirectory();
      final f = File(
        '${dir.path}/antes-despues-${DateTime.now().millisecondsSinceEpoch}.png',
      );
      await f.writeAsBytes(png, flush: true);
      final r = await OpenFilex.open(f.path, type: 'image/png');
      if (r.type != ResultType.done && mounted) {
        avisar(context, 'No hay una aplicación para abrir imágenes.');
      }
    } on ErrorApi catch (e) {
      if (mounted) avisar(context, e.mensaje);
    } catch (_) {
      if (mounted) avisar(context, 'No se pudo generar la imagen.');
    } finally {
      if (mounted) setState(() => _generando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final token = ref.watch(tokenStoreProvider).accessToken;
    final cab = {if (token != null) 'Authorization': 'Bearer $token'};
    final puede =
        ref.watch(authProvider).usuario?.puede('imaging:write') ?? false;
    final autorizado = _c['share_consent'] == true;

    Widget etiqueta(String t, Alignment a) => Align(
      alignment: a,
      child: Container(
        margin: const EdgeInsets.all(10),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.black54,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(
          t,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1,
          ),
        ),
      ),
    );

    return Scaffold(
      backgroundColor: const Color(0xFF0F1A1C),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F1A1C),
        foregroundColor: Colors.white,
        title: Text('${_c['title']}'),
        actions: [
          if (puede)
            PopupMenuButton<String>(
              onSelected: (v) async {
                if (v == 'editar') {
                  final id = await editarComparacion(
                    context,
                    ref,
                    widget.pacienteId,
                    widget.fotos,
                    _c,
                  );
                  if (id != null) {
                    ref.invalidate(comparacionesProvider(widget.pacienteId));
                    final nueva = (await ref.read(
                      comparacionesProvider(widget.pacienteId).future,
                    )).where((x) => x['id'] == id).firstOrNull;
                    if (nueva != null && mounted) setState(() => _c = nueva);
                  }
                } else if (v == 'eliminar') {
                  if (await confirmar(
                        context,
                        titulo: '¿Eliminar «${_c['title']}»?',
                        mensaje:
                            'Solo se borra la comparación. Las fotos siguen en la historia clínica.',
                        textoConfirmar: 'Eliminar',
                        peligro: true,
                      ) &&
                      context.mounted &&
                      await intentar(
                        context,
                        () => ref
                            .read(apiProvider)
                            .delete('/comparisons/${_c['id']}'),
                      )) {
                    ref.invalidate(comparacionesProvider(widget.pacienteId));
                    if (context.mounted) Navigator.pop(context);
                  }
                }
              },
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: 'editar',
                  child: Text('Editar / autorización'),
                ),
                PopupMenuItem(value: 'eliminar', child: Text('Eliminar')),
              ],
            ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(12),
              child: SegmentedButton<bool>(
                showSelectedIcon: false,
                style: SegmentedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  selectedForegroundColor: const Color(0xFF14242B),
                  selectedBackgroundColor: Colors.white,
                ),
                segments: const [
                  ButtonSegment(value: false, label: Text('Deslizar')),
                  ButtonSegment(value: true, label: Text('Lado a lado')),
                ],
                selected: {_lado},
                onSelectionChanged: (v) => setState(() => _lado = v.first),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: _lado
                    ? Column(
                        children: [
                          for (final (t, k) in [
                            ('ANTES', 'before'),
                            ('DESPUÉS', 'after'),
                          ])
                            Expanded(
                              child: Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(16),
                                  child: Stack(
                                    fit: StackFit.expand,
                                    children: [
                                      _foto(
                                        _c[k]['id'],
                                        cab,
                                        fit: BoxFit.contain,
                                      ),
                                      etiqueta(t, Alignment.topLeft),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                        ],
                      )
                    : LayoutBuilder(
                        builder: (context, box) => GestureDetector(
                          onHorizontalDragUpdate: (d) => setState(
                            () => _pos = (d.localPosition.dx / box.maxWidth)
                                .clamp(0.0, 1.0),
                          ),
                          onTapDown: (d) => setState(
                            () => _pos = (d.localPosition.dx / box.maxWidth)
                                .clamp(0.0, 1.0),
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(16),
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                _foto(
                                  _c['after']['id'],
                                  cab,
                                  fit: BoxFit.contain,
                                ),
                                ClipRect(
                                  clipper: _Corte(_pos),
                                  child: _foto(
                                    _c['before']['id'],
                                    cab,
                                    fit: BoxFit.contain,
                                  ),
                                ),
                                etiqueta('ANTES', Alignment.topLeft),
                                etiqueta('DESPUÉS', Alignment.topRight),
                                Positioned(
                                  left: box.maxWidth * _pos - 1.5,
                                  top: 0,
                                  bottom: 0,
                                  child: const SizedBox(
                                    width: 3,
                                    child: ColoredBox(color: Colors.white),
                                  ),
                                ),
                                Positioned(
                                  left: box.maxWidth * _pos - 22,
                                  top: box.maxHeight / 2 - 22,
                                  child: Container(
                                    width: 44,
                                    height: 44,
                                    decoration: const BoxDecoration(
                                      color: Colors.white,
                                      shape: BoxShape.circle,
                                    ),
                                    child: const Icon(
                                      Icons.compare_arrows,
                                      color: Color(0xFF14242B),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(
                        autorizado ? Icons.verified_user : Icons.lock_outline,
                        size: 16,
                        color: autorizado ? Tonos.verde : Colors.white54,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          autorizado
                              ? 'Autorizado para redes'
                              : 'Sin autorización para redes (menú › Editar)',
                          style: TextStyle(
                            fontSize: 12.5,
                            color: autorizado ? Tonos.verde : Colors.white54,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: autorizado && !_generando ? _paraRedes : null,
                      icon: const Icon(Icons.ios_share),
                      label: Text(
                        _generando ? 'Generando…' : 'Imagen para redes',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Corte extends CustomClipper<Rect> {
  _Corte(this.pos);
  final double pos;
  @override
  Rect getClip(Size s) => Rect.fromLTWH(0, 0, s.width * pos, s.height);
  @override
  bool shouldReclip(_Corte o) => o.pos != pos;
}

Future<ui.Image> _decodificar(Uint8List b) async =>
    (await (await ui.instantiateImageCodec(b)).getNextFrame()).image;

void _cubrir(Canvas c, ui.Image img, Rect r) {
  final k = (r.width / img.width) > (r.height / img.height)
      ? r.width / img.width
      : r.height / img.height;
  final sw = r.width / k, sh = r.height / k;
  final src = Rect.fromLTWH(
    (img.width - sw) / 2,
    (img.height - sh) / 2,
    sw,
    sh,
  );
  c.save();
  c.clipRRect(RRect.fromRectAndRadius(r, const Radius.circular(26)));
  c.drawImageRect(img, src, r, Paint()..filterQuality = FilterQuality.high);
  c.restore();
}

void _texto(
  Canvas c,
  String t,
  Offset o,
  double tam,
  Color color, {
  FontWeight peso = FontWeight.w500,
  double ancho = 980,
  int lineas = 1,
}) {
  final p =
      ui.ParagraphBuilder(
          ui.ParagraphStyle(
            fontSize: tam,
            fontWeight: peso,
            maxLines: lineas,
            ellipsis: '…',
          ),
        )
        ..pushStyle(
          ui.TextStyle(
            color: color,
            fontSize: tam,
            fontWeight: peso,
            fontFamily: 'Jakarta',
          ),
        )
        ..addText(t);
  final par = p.build()..layout(ui.ParagraphConstraints(width: ancho));
  c.drawParagraph(par, o);
}

void _pastilla(Canvas c, String t, Offset o, Color fondo) {
  final p =
      ui.ParagraphBuilder(
          ui.ParagraphStyle(fontSize: 30, fontWeight: FontWeight.w700),
        )
        ..pushStyle(
          ui.TextStyle(
            color: Colors.white,
            fontSize: 30,
            fontWeight: FontWeight.w700,
            fontFamily: 'Inter',
          ),
        )
        ..addText(t);
  final par = p.build()..layout(const ui.ParagraphConstraints(width: 400));
  final w = par.longestLine + 44;
  c.drawRRect(
    RRect.fromRectAndRadius(
      Rect.fromLTWH(o.dx, o.dy, w, 54),
      const Radius.circular(27),
    ),
    Paint()..color = fondo,
  );
  c.drawParagraph(par, Offset(o.dx + 22, o.dy + 9));
}

Future<Uint8List> imagenParaRedes(
  Uint8List antes,
  Uint8List despues, {
  required Marca marca,
  required String titulo,
}) async {
  const w = 1080.0, h = 1350.0, m = 48.0;
  final a = await _decodificar(antes);
  final d = await _decodificar(despues);
  final rec = ui.PictureRecorder();
  final c = Canvas(rec, const Rect.fromLTWH(0, 0, w, h));
  c.drawRect(
    const Rect.fromLTWH(0, 0, w, h),
    Paint()..color = const Color(0xFFF6F4EF),
  );
  c.drawRect(const Rect.fromLTWH(0, 0, w, 8), Paint()..color = marca.color);
  var x = m;
  if (Marca.logoBytes != null) {
    try {
      final logo = await _decodificar(Marca.logoBytes!);
      final lw = logo.width / logo.height * 86;
      c.drawImageRect(
        logo,
        Rect.fromLTWH(0, 0, logo.width.toDouble(), logo.height.toDouble()),
        Rect.fromLTWH(m, 46, lw, 86),
        Paint(),
      );
      x = m + lw + 22;
    } catch (_) {}
  }
  _texto(
    c,
    marca.nombre,
    Offset(x, 52),
    40,
    const Color(0xFF14242B),
    peso: FontWeight.w800,
    ancho: w - x - m,
  );
  if (marca.eslogan != null) {
    _texto(
      c,
      marca.eslogan!,
      Offset(x, 102),
      26,
      const Color(0xFF5D6B6D),
      ancho: w - x - m,
    );
  }
  const y = 166.0, pie = 130.0;
  const alto = h - y - pie - m;
  const hh = (alto - 16) / 2;
  _cubrir(c, a, const Rect.fromLTWH(m, y, w - 2 * m, hh));
  _cubrir(c, d, const Rect.fromLTWH(m, y + hh + 16, w - 2 * m, hh));
  _pastilla(c, 'ANTES', const Offset(m + 20, y + 20), const Color(0xC70F1A1C));
  _pastilla(c, 'DESPUÉS', const Offset(m + 20, y + hh + 36), marca.color);
  _texto(
    c,
    titulo,
    const Offset(m, h - m - 104),
    46,
    const Color(0xFF14242B),
    peso: FontWeight.w800,
  );
  _texto(
    c,
    'Resultado real de un paciente, publicado con su autorización.',
    const Offset(m, h - m - 40),
    26,
    const Color(0xFF5D6B6D),
  );
  final img = await rec.endRecording().toImage(w.toInt(), h.toInt());
  final png = await img.toByteData(format: ui.ImageByteFormat.png);
  return png!.buffer.asUint8List();
}
