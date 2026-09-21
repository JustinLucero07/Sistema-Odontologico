import 'package:flutter/material.dart';

/// La marca del producto: un molar dibujado desde su anatomía —corona ancha
/// con dos cúspides y dos raíces— en vez del maletín médico genérico.
///
/// Es el mismo trazado que el SVG de la web, portado a `Path` para que las dos
/// aplicaciones tengan literalmente el mismo logotipo.
class ToothMark extends StatelessWidget {
  const ToothMark({super.key, this.size = 28, this.color, this.filled = false});

  final double size;
  final Color? color;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _ToothMarkPainter(
          color: color ?? Theme.of(context).colorScheme.primary,
          filled: filled,
        ),
      ),
    );
  }
}

class _ToothMarkPainter extends CustomPainter {
  _ToothMarkPainter({required this.color, required this.filled});

  final Color color;
  final bool filled;

  @override
  void paint(Canvas canvas, Size size) {
    // El trazado está definido en una caja de 32×32, como el SVG original.
    final k = size.width / 32;
    final path = Path()
      ..moveTo(16 * k, 3.4 * k)
      ..cubicTo(9.9 * k, 3.4 * k, 5.4 * k, 6.7 * k, 5.4 * k, 12.3 * k)
      ..cubicTo(5.4 * k, 16.2 * k, 6.5 * k, 19.2 * k, 7.3 * k, 23.2 * k)
      ..cubicTo(7.9 * k, 26.2 * k, 8.3 * k, 29 * k, 10.3 * k, 29 * k)
      ..cubicTo(12.3 * k, 29 * k, 12.7 * k, 26.3 * k, 13.4 * k, 23.5 * k)
      ..cubicTo(13.9 * k, 21.5 * k, 14.7 * k, 20.4 * k, 16 * k, 20.4 * k)
      ..cubicTo(17.3 * k, 20.4 * k, 18.1 * k, 21.5 * k, 18.6 * k, 23.5 * k)
      ..cubicTo(19.3 * k, 26.3 * k, 19.7 * k, 29 * k, 21.7 * k, 29 * k)
      ..cubicTo(23.7 * k, 29 * k, 24.1 * k, 26.2 * k, 24.7 * k, 23.2 * k)
      ..cubicTo(25.5 * k, 19.2 * k, 26.6 * k, 16.2 * k, 26.6 * k, 12.3 * k)
      ..cubicTo(26.6 * k, 6.7 * k, 22.1 * k, 3.4 * k, 16 * k, 3.4 * k)
      ..close();

    if (filled) {
      canvas.drawPath(path, Paint()..color = color);
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.7 * k
        ..strokeJoin = StrokeJoin.round,
    );

    // El brillo del esmalte: un arco corto donde la luz daría en la corona.
    final brillo = Path()
      ..moveTo(10.4 * k, 9.1 * k)
      ..cubicTo(11.4 * k, 7.5 * k, 13.3 * k, 6.5 * k, 15.4 * k, 6.5 * k);
    canvas.drawPath(
      brillo,
      Paint()
        ..color = (filled ? const Color(0xFF06221F) : color).withValues(
          alpha: filled ? 0.45 : 0.75,
        )
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6 * k
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_ToothMarkPainter old) =>
      old.color != color || old.filled != filled;
}
