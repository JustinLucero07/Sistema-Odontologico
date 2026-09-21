import 'dart:ui';

/// Convierte una cadena de trazado SVG en un `Path` de Flutter.
///
/// Solo entiende los comandos que usan las formas dentales —M, L, C, A y Z, en
/// mayúsculas— en lugar de traer una librería entera de SVG. Si algún día una
/// forma usa otro comando, esto lanza en vez de dibujar algo raro en silencio.
Path parseSvgPath(String d, {double scale = 1}) {
  final path = Path();
  final tokens = RegExp(
    r'[MLCAZmlcaz]|-?\d*\.?\d+',
  ).allMatches(d).map((m) => m.group(0)!).toList();

  var i = 0;
  double next() => double.parse(tokens[i++]) * scale;

  var startX = 0.0, startY = 0.0, curX = 0.0, curY = 0.0;

  while (i < tokens.length) {
    final cmd = tokens[i];
    if (RegExp(r'[A-Za-z]').hasMatch(cmd)) {
      i++;
      switch (cmd.toUpperCase()) {
        case 'M':
          curX = next();
          curY = next();
          startX = curX;
          startY = curY;
          path.moveTo(curX, curY);
        case 'L':
          curX = next();
          curY = next();
          path.lineTo(curX, curY);
        case 'C':
          final c1x = next(), c1y = next();
          final c2x = next(), c2y = next();
          curX = next();
          curY = next();
          path.cubicTo(c1x, c1y, c2x, c2y, curX, curY);
        case 'A':
          // Arco: se usa solo en la rueda de superficies, siempre como medio
          // círculo. Se aproxima con el arco del rectángulo que lo contiene.
          final rx = next(), ry = next();
          next(); // rotación del eje x, siempre 0 aquí
          final largeArc = next() != 0;
          final sweep = next() != 0;
          final endX = next(), endY = next();
          _arcTo(path, curX, curY, rx, ry, largeArc, sweep, endX, endY);
          curX = endX;
          curY = endY;
        case 'Z':
          path.close();
          curX = startX;
          curY = startY;
        default:
          throw UnsupportedError('Comando SVG no soportado: $cmd en «$d»');
      }
    } else {
      // Un número suelto tras un comando significa repetirlo; ninguna de las
      // formas dentales lo hace, así que es más útil fallar que adivinar.
      throw FormatException('Número sin comando en el trazado: «$d»');
    }
  }
  return path;
}

void _arcTo(
  Path path,
  double x0,
  double y0,
  double rx,
  double ry,
  bool largeArc,
  bool sweep,
  double x1,
  double y1,
) {
  path.arcToPoint(
    Offset(x1, y1),
    radius: Radius.elliptical(rx, ry),
    largeArc: largeArc,
    clockwise: sweep,
  );
}
