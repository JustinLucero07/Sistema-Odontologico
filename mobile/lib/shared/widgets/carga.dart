import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import 'tooth_mark.dart';

/// Brillo que recorre los esqueletos: un solo controlador para toda la
/// pantalla, así todas las formas brillan a la vez, como en la web.
class Destello extends StatefulWidget {
  const Destello({super.key, required this.child});

  final Widget child;

  @override
  State<Destello> createState() => _DestelloState();
}

class _DestelloState extends State<Destello>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  )..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) return widget.child;
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    final brillo = oscuro
        ? AppColors.primaryOnDark.withValues(alpha: 0.22)
        : Colors.white.withValues(alpha: 0.9);
    return AnimatedBuilder(
      animation: _c,
      child: widget.child,
      builder: (context, child) {
        final t = Curves.easeInOut.transform(_c.value);
        return ShaderMask(
          blendMode: BlendMode.srcATop,
          shaderCallback: (rect) => LinearGradient(
            begin: Alignment(-1.6 + 3.2 * t - 0.5, -0.3),
            end: Alignment(-1.6 + 3.2 * t + 0.5, 0.3),
            colors: [Colors.transparent, brillo, Colors.transparent],
          ).createShader(rect),
          child: child,
        );
      },
    );
  }
}

/// Una forma del esqueleto.
class Hueso extends StatelessWidget {
  const Hueso({super.key, this.ancho, this.alto = 12, this.radio = 8});

  final double? ancho;
  final double alto;
  final double radio;

  @override
  Widget build(BuildContext context) {
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: ancho,
      height: alto,
      decoration: BoxDecoration(
        color: oscuro
            ? Colors.white.withValues(alpha: 0.08)
            : const Color(0xFF0F2427).withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(radio),
      ),
    );
  }
}

/// Lista en carga: avatar, dos líneas y una cápsula, como las filas reales.
class EsqueletoLista extends StatelessWidget {
  const EsqueletoLista({
    super.key,
    this.filas = 6,
    this.conTarjetas = false,
    this.dentroDeLista = false,
  });

  final int filas;

  /// Va dentro de otra lista: se dibuja como columna, sin desplazamiento ni
  /// márgenes propios.
  final bool dentroDeLista;

  /// Antepone una fila de tarjetas de cifras (para el panel).
  final bool conTarjetas;

  @override
  Widget build(BuildContext context) {
    final hijos = <Widget>[
      if (conTarjetas) ...[
        Row(
          children: [
            for (var i = 0; i < 2; i++) ...[
              if (i > 0) const SizedBox(width: 12),
              Expanded(
                child: _Panel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Hueso(ancho: 70),
                      SizedBox(height: 12),
                      Hueso(ancho: 56, alto: 24, radio: 10),
                      SizedBox(height: 10),
                      Hueso(ancho: 90, alto: 9),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 16),
      ],
      for (var i = 0; i < filas; i++)
        _Aparece(
          retraso: i * 60,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _Panel(
              child: Row(
                children: [
                  const Hueso(ancho: 42, alto: 42, radio: 21),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        FractionallySizedBox(
                          widthFactor: 0.75 - (i % 3) * 0.12,
                          child: const Hueso(),
                        ),
                        const SizedBox(height: 8),
                        FractionallySizedBox(
                          widthFactor: 0.45 + (i % 2) * 0.1,
                          child: const Hueso(alto: 9),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Hueso(ancho: 56, alto: 24, radio: 12),
                ],
              ),
            ),
          ),
        ),
    ];
    return Destello(
      child: dentroDeLista
          ? Column(children: hijos)
          : ListView(
              physics: const NeverScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
              children: hijos,
            ),
    );
  }
}

/// Bloque grande en carga (odontograma, estado de cuenta).
class EsqueletoBloque extends StatelessWidget {
  const EsqueletoBloque({super.key, this.alto = 260});

  final double alto;

  @override
  Widget build(BuildContext context) {
    return Destello(
      child: ListView(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const Hueso(ancho: 140),
          const SizedBox(height: 14),
          _Panel(child: SizedBox(height: alto)),
          const SizedBox(height: 14),
          const Row(
            children: [
              Hueso(ancho: 80, alto: 26, radio: 13),
              SizedBox(width: 8),
              Hueso(ancho: 80, alto: 26, radio: 13),
              SizedBox(width: 8),
              Hueso(ancho: 80, alto: 26, radio: 13),
            ],
          ),
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: oscuro
            ? Colors.white.withValues(alpha: 0.04)
            : Colors.white.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: oscuro
              ? Colors.white.withValues(alpha: 0.07)
              : Colors.white.withValues(alpha: 0.8),
        ),
      ),
      child: child,
    );
  }
}

/// Entrada escalonada: cada fila aparece un poco después de la anterior.
class _Aparece extends StatelessWidget {
  const _Aparece({required this.retraso, required this.child});

  final int retraso;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final total = 360 + retraso;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: total),
      curve: Interval(retraso / total, 1, curve: Curves.easeOutCubic),
      builder: (context, v, child) => Opacity(
        opacity: v,
        child: Transform.translate(
          offset: Offset(0, 8 * (1 - v)),
          child: child,
        ),
      ),
      child: child,
    );
  }
}

/// Pantalla de arranque: el logo con un aro que gira, un resplandor que
/// respira y una barra que avanza. La misma que la web.
class PantallaArranque extends StatefulWidget {
  const PantallaArranque({super.key, this.mensaje = 'Preparando su clínica…'});

  final String mensaje;

  @override
  State<PantallaArranque> createState() => _PantallaArranqueState();
}

class _PantallaArranqueState extends State<PantallaArranque>
    with TickerProviderStateMixin {
  late final AnimationController _giro = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat();
  late final AnimationController _respira = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  )..repeat(reverse: true);
  late final AnimationController _barra = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat();

  @override
  void dispose() {
    _giro.dispose();
    _respira.dispose();
    _barra.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final oscuro = Theme.of(context).brightness == Brightness.dark;
    final tinta = oscuro ? AppColors.inkDark : AppColors.inkLight;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: const Alignment(-0.7, -0.8),
            radius: 1.3,
            colors: oscuro
                ? const [Color(0xFF103A38), AppColors.baseDark]
                : const [Color(0xFFCBEDE7), AppColors.baseLight],
          ),
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 132,
                height: 132,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Resplandor.
                    AnimatedBuilder(
                      animation: _respira,
                      builder: (context, _) {
                        final v = Curves.easeInOut.transform(_respira.value);
                        return Container(
                          width: 92 + 10 * v,
                          height: 92 + 10 * v,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(32),
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.mint.withValues(
                                  alpha: 0.35 + 0.25 * v,
                                ),
                                blurRadius: 36,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                    // Aro que gira.
                    AnimatedBuilder(
                      animation: _giro,
                      builder: (context, _) => CustomPaint(
                        size: const Size(118, 118),
                        painter: _Aro(_giro.value),
                      ),
                    ),
                    const LogoApp(tamano: 96),
                  ],
                ),
              ),
              const SizedBox(height: 22),
              Text(
                'Sistema Odontológico',
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  color: tinta,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                widget.mensaje,
                style: TextStyle(
                  fontSize: 13,
                  color: tinta.withValues(alpha: 0.55),
                ),
              ),
              const SizedBox(height: 20),
              ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: SizedBox(
                  width: 160,
                  height: 4,
                  child: AnimatedBuilder(
                    animation: _barra,
                    builder: (context, _) {
                      final t = Curves.easeInOutCubic.transform(_barra.value);
                      return Stack(
                        children: [
                          Container(
                            color: AppColors.primary.withValues(alpha: 0.15),
                          ),
                          Positioned(
                            left: -64 + 224 * t,
                            width: 64,
                            top: 0,
                            bottom: 0,
                            child: const DecoratedBox(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [AppColors.mint, AppColors.primary],
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
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

/// Borde redondeado fijo; lo que gira es el destello que lo recorre.
class _Aro extends CustomPainter {
  _Aro(this.vuelta);

  final double vuelta;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(36),
    );
    final pincel = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        colors: const [
          Colors.transparent,
          Colors.transparent,
          AppColors.mint,
          AppColors.primary,
        ],
        stops: const [0, 0.55, 0.85, 1],
        transform: GradientRotation(-math.pi / 2 + vuelta * 2 * math.pi),
      ).createShader(Offset.zero & size);
    canvas.drawRRect(rect, pincel);
  }

  @override
  bool shouldRepaint(_Aro oldDelegate) => oldDelegate.vuelta != vuelta;
}

/// El logo de la app: el diente sobre su gota de vidrio verde azulado, igual
/// que el icono del teléfono y el de la web.
class LogoApp extends StatelessWidget {
  const LogoApp({super.key, this.tamano = 64});

  final double tamano;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: tamano,
      height: tamano,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(tamano * 0.27),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1FB3A4), AppColors.primary, Color(0xFF074A45)],
          stops: [0, 0.55, 1],
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF074A45).withValues(alpha: 0.45),
            blurRadius: 24,
            offset: const Offset(0, 12),
            spreadRadius: -8,
          ),
        ],
      ),
      foregroundDecoration: BoxDecoration(
        borderRadius: BorderRadius.circular(tamano * 0.27),
        gradient: RadialGradient(
          center: const Alignment(-0.45, -0.65),
          radius: 0.9,
          colors: [
            Colors.white.withValues(alpha: 0.32),
            Colors.white.withValues(alpha: 0),
          ],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
      ),
      child: Center(
        child: ToothMark(
          size: tamano * 0.55,
          color: Colors.white,
          filled: true,
        ),
      ),
    );
  }
}
