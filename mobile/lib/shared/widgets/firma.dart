import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// Guarda los trazos de una firma y la exporta como PNG (data URL), que es
/// lo que recibe el servidor.
class ControladorFirma extends ChangeNotifier {
  final List<List<Offset>> _trazos = [];
  Size _tamano = Size.zero;

  bool get vacia => _trazos.every((t) => t.isEmpty);
  List<List<Offset>> get trazos => _trazos;

  void _empezar(Offset p) {
    _trazos.add([p]);
    notifyListeners();
  }

  void _seguir(Offset p) {
    if (_trazos.isEmpty) return;
    _trazos.last.add(p);
    notifyListeners();
  }

  void borrar() {
    _trazos.clear();
    notifyListeners();
  }

  /// PNG con fondo transparente al doble de resolución, para que se vea
  /// nítida en el PDF.
  Future<String?> comoDataUrl() async {
    if (vacia || _tamano == Size.zero) return null;
    const escala = 2.0;
    final grabadora = ui.PictureRecorder();
    final lienzo = Canvas(grabadora)..scale(escala);
    PintorFirma(_trazos, const Color(0xFF14242B)).paint(lienzo, _tamano);
    final imagen = await grabadora.endRecording().toImage((_tamano.width * escala).round(), (_tamano.height * escala).round());
    final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
    if (datos == null) return null;
    return 'data:image/png;base64,${base64Encode(datos.buffer.asUint8List())}';
  }
}

class PanelFirma extends StatelessWidget {
  const PanelFirma({super.key, required this.controlador, this.etiqueta = 'Firma', this.alto = 190});

  final ControladorFirma controlador;
  final String etiqueta;
  final double alto;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          height: alto,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: tinta.withValues(alpha: 0.18), width: 1.4),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(15),
            child: LayoutBuilder(
              builder: (context, c) {
                controlador._tamano = Size(c.maxWidth, c.maxHeight);
                return GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onPanStart: (d) => controlador._empezar(d.localPosition),
                  onPanUpdate: (d) => controlador._seguir(d.localPosition),
                  child: ListenableBuilder(
                    listenable: controlador,
                    builder: (context, _) => Stack(
                      children: [
                        Positioned(
                          left: 24,
                          right: 24,
                          bottom: 38,
                          child: Container(height: 1, color: const Color(0xFFD9D4CA)),
                        ),
                        if (controlador.vacia)
                          const Center(child: Text('Firme aquí con el dedo', style: TextStyle(color: Color(0xFF9AA5A8)))),
                        Positioned.fill(child: CustomPaint(painter: PintorFirma(controlador.trazos, const Color(0xFF14242B)))),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        Row(
          children: [
            Expanded(child: Text(etiqueta, style: TextStyle(fontSize: 12.5, color: tinta.withValues(alpha: 0.55)))),
            ListenableBuilder(
              listenable: controlador,
              builder: (context, _) => TextButton.icon(
                onPressed: controlador.vacia ? null : controlador.borrar,
                icon: const Icon(Icons.backspace_outlined, size: 17),
                label: const Text('Borrar'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class PintorFirma extends CustomPainter {
  PintorFirma(this.trazos, this.color);

  final List<List<Offset>> trazos;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final lapiz = Paint()
      ..color = color
      ..strokeWidth = 2.6
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;
    for (final t in trazos) {
      if (t.length == 1) {
        canvas.drawCircle(t.first, 1.4, Paint()..color = color);
        continue;
      }
      // Curvas suaves entre puntos medios: trazo natural, sin quiebres.
      final camino = Path()..moveTo(t.first.dx, t.first.dy);
      for (var i = 1; i < t.length - 1; i++) {
        final medio = Offset((t[i].dx + t[i + 1].dx) / 2, (t[i].dy + t[i + 1].dy) / 2);
        camino.quadraticBezierTo(t[i].dx, t[i].dy, medio.dx, medio.dy);
      }
      camino.lineTo(t.last.dx, t.last.dy);
      canvas.drawPath(camino, lapiz);
    }
  }

  @override
  bool shouldRepaint(PintorFirma old) => true;
}
