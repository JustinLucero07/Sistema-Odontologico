import 'package:flutter/material.dart';

import 'tooth_anatomy.dart';
import 'svg_path.dart';

/// Orden FDI de una arcada: 18→11 | 21→28 arriba, 48→41 | 31→38 abajo.
List<String> filaArcada(String arcada, {bool temporal = false}) {
  final cuadrantes = temporal
      ? (arcada == 'upper' ? [5, 6] : [8, 7])
      : (arcada == 'upper' ? [1, 2] : [4, 3]);
  final porCuadrante = temporal ? 5 : 8;
  final fila = <String>[];
  for (var q = 0; q < 2; q++) {
    // El primer cuadrante se dibuja descendiendo hacia la línea media; el
    // segundo ascendiendo desde ella.
    final numeros = q == 0
        ? List.generate(porCuadrante, (i) => porCuadrante - i)
        : List.generate(porCuadrante, (i) => i + 1);
    for (final n in numeros) {
      fila.add('${cuadrantes[q]}$n');
    }
  }
  return fila;
}

/// Geometría vertical del odontograma, compartida por el dibujo y por la
/// detección de toques. Antes cada uno calculaba la suya y el hueco entre
/// arcadas (12 px) no dejaba sitio a las dos filas de números: se pintaban
/// encimados en la línea media.
class _Metrica {
  _Metrica(this.escala);

  final double escala;
  static const margen = 6.0;
  static const altoNumero = 14.0;
  static const separacion = 4.0;

  double get altoDiente => 64 * escala;

  /// Diagrama de caras bajo cada pieza, como en la web.
  double get altoCaras => 24 * escala;
  double get ySuperior => margen;
  double get yCarasSuperior => ySuperior + altoDiente + separacion;
  double get yNumerosSuperior => yCarasSuperior + altoCaras + separacion;
  double get lineaMedia => yNumerosSuperior + altoNumero + separacion;
  double get yNumerosInferior => lineaMedia + separacion;
  double get yCarasInferior => yNumerosInferior + altoNumero + separacion;
  double get yInferior => yCarasInferior + altoCaras + separacion;
  double get altoTotal => yInferior + altoDiente + margen;
}

class Diente {
  const Diente({
    required this.fdi,
    required this.arcada,
    this.relleno,
    this.ausente = false,
    this.aspa,
    this.caras = const {},
  });

  final String fdi;
  final String arcada;

  /// Color de la corona cuando hay una condición registrada; nulo = sano.
  final Color? relleno;
  final bool ausente;

  /// Aspa de color sobre la pieza sin atenuarla: extracción indicada.
  final Color? aspa;

  /// Color por cara (mesial, distal, vestibular, lingual, oclusal).
  final Map<String, Color> caras;
}

/// El odontograma.
///
/// Se dibuja con `CustomPaint` en vez de con imágenes: son trazados vectoriales
/// y tienen que verse nítidos tanto en un móvil de 5" como en una tablet, y
/// además cada pieza responde al toque.
class OdontogramaWidget extends StatelessWidget {
  const OdontogramaWidget({
    super.key,
    required this.dientes,
    this.onTocarDiente,
    this.temporal = false,
    this.seleccionado,
  });

  /// Pieza resaltada (la que se acaba de tocar).
  final String? seleccionado;

  final Map<String, Diente> dientes;
  final void Function(String fdi)? onTocarDiente;
  final bool temporal;

  @override
  Widget build(BuildContext context) {
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    final paleta = _Paleta(
      esmalte: oscuro ? const Color(0xFFE3EAE8) : const Color(0xFFFCFCFA),
      raiz: oscuro ? const Color(0xFFCDBB92) : const Color(0xFFECDFC4),
      contorno: oscuro
          ? const Color(0xFF061214).withValues(alpha: 0.8)
          : const Color(0xFF0F2427).withValues(alpha: 0.46),
      detalle: oscuro
          ? const Color(0xFF061214).withValues(alpha: 0.45)
          : const Color(0xFF0F2427).withValues(alpha: 0.3),
      brillo: Colors.white.withValues(alpha: oscuro ? 0.55 : 0.9),
      sombra: oscuro
          ? const Color(0xFF061214).withValues(alpha: 0.22)
          : const Color(0xFF0F2427).withValues(alpha: 0.15),
      numero: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7),
      lineaMedia: Theme.of(
        context,
      ).colorScheme.onSurface.withValues(alpha: 0.2),
      caraVacia: oscuro
          ? Colors.white.withValues(alpha: 0.08)
          : Colors.white.withValues(alpha: 0.85),
      acento: Theme.of(context).colorScheme.primary,
    );

    final superior = filaArcada('upper', temporal: temporal);
    final inferior = filaArcada('lower', temporal: temporal);

    return LayoutBuilder(
      builder: (context, constraints) {
        final anchos = superior
            .map((fdi) => anatomiaDe(fdi, 'upper').width.toDouble() + 2)
            .toList();
        final anchoTotal = anchos.fold<double>(0, (a, b) => a + b);
        // Se escala para que la arcada entera quepa: un odontograma que exige
        // desplazamiento lateral se lee a trozos, y el punto es verlo de golpe.
        final escala = (constraints.maxWidth - 8) / anchoTotal;
        final metrica = _Metrica(escala);

        return GestureDetector(
          onTapUp: onTocarDiente == null
              ? null
              : (detalle) {
                  final fdi = _dienteEn(
                    detalle.localPosition,
                    superior,
                    inferior,
                    metrica,
                  );
                  if (fdi != null) onTocarDiente!(fdi);
                },
          child: CustomPaint(
            size: Size(constraints.maxWidth, metrica.altoTotal),
            painter: _OdontogramaPainter(
              superior: superior,
              inferior: inferior,
              dientes: dientes,
              paleta: paleta,
              metrica: metrica,
              seleccionado: seleccionado,
            ),
          ),
        );
      },
    );
  }

  /// Qué pieza cae bajo el dedo. El alto de un diente es 64 unidades de la
  /// caja canónica; el resto de la celda es el número.
  String? _dienteEn(
    Offset punto,
    List<String> superior,
    List<String> inferior,
    _Metrica m,
  ) {
    final arriba = punto.dy < m.lineaMedia;
    final fila = arriba ? superior : inferior;
    final arcada = arriba ? 'upper' : 'lower';
    var x = 4.0;
    for (final fdi in fila) {
      final ancho = (anatomiaDe(fdi, arcada).width + 2) * m.escala;
      if (punto.dx >= x && punto.dx < x + ancho) return fdi;
      x += ancho;
    }
    return null;
  }
}

class _Paleta {
  const _Paleta({
    required this.esmalte,
    required this.raiz,
    required this.contorno,
    required this.detalle,
    required this.brillo,
    required this.sombra,
    required this.numero,
    required this.lineaMedia,
    required this.caraVacia,
    required this.acento,
  });

  final Color esmalte,
      raiz,
      contorno,
      detalle,
      brillo,
      sombra,
      numero,
      lineaMedia,
      caraVacia,
      acento;
}

class _OdontogramaPainter extends CustomPainter {
  _OdontogramaPainter({
    required this.superior,
    required this.inferior,
    required this.dientes,
    required this.paleta,
    required this.metrica,
    this.seleccionado,
  });

  final String? seleccionado;
  final List<String> superior;
  final List<String> inferior;
  final Map<String, Diente> dientes;
  final _Paleta paleta;
  final _Metrica metrica;

  double get escala => metrica.escala;

  @override
  void paint(Canvas canvas, Size size) {
    final medio = metrica.lineaMedia;

    _pintarFila(
      canvas,
      superior,
      'upper',
      metrica.ySuperior,
      metrica.yCarasSuperior,
      metrica.yNumerosSuperior,
      invertir: false,
    );
    _pintarFila(
      canvas,
      inferior,
      'lower',
      metrica.yInferior,
      metrica.yCarasInferior,
      metrica.yNumerosInferior,
      invertir: true,
    );

    // Línea media: dónde se refleja la boca.
    final guion = Paint()
      ..color = paleta.lineaMedia
      ..strokeWidth = 1;
    for (var x = 6.0; x < size.width - 6; x += 10) {
      canvas.drawLine(Offset(x, medio), Offset(x + 5, medio), guion);
    }
  }

  void _pintarFila(
    Canvas canvas,
    List<String> fila,
    String arcada,
    double y,
    double yCaras,
    double yNumeros, {
    required bool invertir,
  }) {
    var x = 4.0;
    for (final fdi in fila) {
      final a = anatomiaDe(fdi, arcada);
      final ancho = (a.width + 2) * escala;
      final diente = dientes[fdi];

      if (fdi == seleccionado) {
        final arriba = y < yNumeros ? y : yNumeros;
        final abajo = y < yNumeros
            ? yNumeros + _Metrica.altoNumero
            : y + metrica.altoDiente;
        final marco = RRect.fromRectAndRadius(
          Rect.fromLTRB(x, arriba - 3, x + ancho, abajo + 3),
          Radius.circular(5 * escala + 2),
        );
        canvas.drawRRect(
          marco,
          Paint()..color = paleta.acento.withValues(alpha: 0.12),
        );
        canvas.drawRRect(
          marco,
          Paint()
            ..color = paleta.acento
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.2,
        );
      }

      canvas.save();
      canvas.translate(x, y);
      if (invertir) {
        // La arcada inferior es la misma forma reflejada, igual que en un
        // odontograma impreso.
        canvas.translate(0, 64 * escala);
        canvas.scale(1, -1);
      }
      // Centra el trazado (caja de 40) dentro de su celda.
      canvas.translate((ancho - 40 * escala) / 2, 0);
      _pintarDiente(canvas, a, diente);
      canvas.restore();

      _pintarCaras(
        canvas,
        fdi,
        diente,
        Offset(x + ancho / 2, yCaras + metrica.altoCaras / 2),
        (ancho < metrica.altoCaras ? ancho : metrica.altoCaras) / 2 - 1,
      );
      _pintarNumero(canvas, fdi, x + ancho / 2, yNumeros);
      x += ancho;
    }
  }

  void _pintarDiente(Canvas canvas, ToothAnatomy a, Diente? diente) {
    final ausente = diente?.ausente ?? false;

    final pincelRaiz = Paint()
      ..color = ausente ? paleta.raiz.withValues(alpha: 0.25) : paleta.raiz;
    final pincelCorona = Paint()
      ..color = ausente
          ? paleta.esmalte.withValues(alpha: 0.25)
          : (diente?.relleno ?? paleta.esmalte);
    final contorno = Paint()
      ..color = paleta.contorno
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1 * escala
      ..strokeJoin = StrokeJoin.round;

    for (final r in a.roots) {
      final p = parseSvgPath(r, scale: escala);
      canvas.drawPath(p, pincelRaiz);
      canvas.drawPath(p, contorno);
    }

    final corona = parseSvgPath(a.crown, scale: escala);
    canvas.drawPath(corona, pincelCorona);
    canvas.drawPath(corona, contorno..strokeWidth = 1.2 * escala);

    if (ausente) {
      // Una pieza ausente se tacha, no se oculta: el hueco en la arcada es en
      // sí mismo un hallazgo, y la columna tiene que quedarse para que los
      // números sigan alineados.
      final aspa = Paint()
        ..color = const Color(0xFF8D8D8D)
        ..strokeWidth = 2.6 * escala
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(
        Offset(8 * escala, 14 * escala),
        Offset(32 * escala, 56 * escala),
        aspa,
      );
      canvas.drawLine(
        Offset(32 * escala, 14 * escala),
        Offset(8 * escala, 56 * escala),
        aspa,
      );
      return;
    }

    final marca = diente?.aspa;
    if (marca != null) {
      final aspa = Paint()
        ..color = marca
        ..strokeWidth = 2.4 * escala
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(
        Offset(9 * escala, 16 * escala),
        Offset(31 * escala, 54 * escala),
        aspa,
      );
      canvas.drawLine(
        Offset(31 * escala, 16 * escala),
        Offset(9 * escala, 54 * escala),
        aspa,
      );
    }

    final trazoDetalle = Paint()
      ..color = paleta.detalle
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.9 * escala
      ..strokeCap = StrokeCap.round;
    for (final d in a.detail) {
      canvas.drawPath(parseSvgPath(d, scale: escala), trazoDetalle);
    }

    canvas.drawPath(
      parseSvgPath(a.shade, scale: escala),
      Paint()
        ..color = paleta.sombra
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.8 * escala
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawPath(
      parseSvgPath(a.gloss, scale: escala),
      Paint()
        ..color = paleta.brillo
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6 * escala
        ..strokeCap = StrokeCap.round,
    );
  }

  /// Diagrama de cinco caras: vestibular arriba, lingual abajo, mesial hacia
  /// la línea media, distal hacia fuera y oclusal en el centro.
  void _pintarCaras(
    Canvas canvas,
    String fdi,
    Diente? diente,
    Offset centro,
    double radio,
  ) {
    final caras = diente?.caras ?? const <String, Color>{};
    final atenuar = diente?.ausente ?? false;
    final borde = Paint()
      ..color = paleta.contorno.withValues(alpha: atenuar ? 0.25 : 0.7)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8;
    // Cuadrantes 1, 4, 5 y 8 se dibujan a la izquierda: su mesial mira a la
    // derecha, hacia la línea media.
    final mesialDerecha = '1458'.contains(fdi[0]);
    final caja = Rect.fromCircle(center: centro, radius: radio);
    const cuarto = 3.141592653589793 / 2;
    final porLado = <(double, String)>[
      (-3 * cuarto / 2, 'vestibular'),
      (-cuarto / 2, mesialDerecha ? 'mesial' : 'distal'),
      (cuarto / 2, 'lingual'),
      (3 * cuarto / 2, mesialDerecha ? 'distal' : 'mesial'),
    ];
    for (final (inicio, cara) in porLado) {
      final sector = Path()
        ..moveTo(centro.dx, centro.dy)
        ..arcTo(caja, inicio, cuarto, false)
        ..close();
      canvas.drawPath(sector, Paint()..color = caras[cara] ?? paleta.caraVacia);
      canvas.drawPath(sector, borde);
    }
    canvas.drawCircle(
      centro,
      radio * 0.45,
      Paint()..color = caras['oclusal'] ?? paleta.caraVacia,
    );
    // Sobre un color, el centro necesita fondo opaco para no mezclarse con
    // los sectores que tiene debajo.
    canvas.drawCircle(centro, radio * 0.45, borde);
  }

  void _pintarNumero(Canvas canvas, String fdi, double cx, double y) {
    final pintor = TextPainter(
      text: TextSpan(
        text: fdi,
        style: TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w700,
          color: fdi == seleccionado || _tieneHallazgo(fdi)
              ? paleta.acento
              : paleta.numero,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    pintor.paint(canvas, Offset(cx - pintor.width / 2, y));
  }

  bool _tieneHallazgo(String fdi) {
    final d = dientes[fdi];
    return d != null &&
        (d.relleno != null ||
            d.ausente ||
            d.aspa != null ||
            d.caras.isNotEmpty);
  }

  @override
  bool shouldRepaint(_OdontogramaPainter old) =>
      old.dientes != dientes ||
      old.seleccionado != seleccionado ||
      old.metrica.escala != metrica.escala;
}
