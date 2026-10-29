import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

/// Superficies de la app: porcelana y papel.
///
/// El fondo es un blanco cálido y las tarjetas blanco puro con un canto fino.
/// La jerarquía sale del contraste de temperatura y de una sombra amplia y
/// muy tenue, no de colores ni brillos: es lo que hace que se vea tranquila y
/// cara a la vez. Los nombres (Glass*) se conservan porque los usa toda la
/// app; el vidrio real queda solo donde pasa contenido por detrás (barras).

/// Fondo de todas las pantallas. Un único lavado muy tenue del color de la
/// consulta arriba, para que la marca se sienta sin teñir el contenido.
class AmbientBackground extends StatelessWidget {
  const AmbientBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final base = dark ? AppColors.baseDark : AppColors.baseLight;
    final marca = dark ? AppColors.primaryOnDark : AppColors.primary;

    return Stack(
      fit: StackFit.expand,
      children: [
        ColoredBox(color: base),
        RepaintBoundary(
          child: IgnorePointer(
            child: Align(
              alignment: Alignment.topCenter,
              child: FractionallySizedBox(
                heightFactor: 0.45,
                widthFactor: 1,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: const Alignment(0.9, -1.1),
                      radius: 1.25,
                      colors: [
                        marca.withValues(alpha: dark ? 0.16 : 0.07),
                        marca.withValues(alpha: 0),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
        child,
      ],
    );
  }
}

/// Colores del material según el tema.
class GlassTokens {
  const GlassTokens._(this.fill, this.rim, this.shadow);

  final Color fill;
  final Color rim;
  final Color shadow;

  static GlassTokens of(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return dark
        ? const GlassTokens._(
            AppColors.surfaceDark,
            AppColors.lineDark,
            Color(0x66000000),
          )
        : const GlassTokens._(
            AppColors.surfaceLight,
            Color(0xFFECE8E0),
            Color(0x1A3B3222),
          );
  }
}

/// Superficie base. [blur] la vuelve translúcida con desenfoque real del
/// fondo; solo se usa donde pasa contenido por detrás (barras flotantes).
class GlassPanel extends StatelessWidget {
  const GlassPanel({
    super.key,
    required this.child,
    this.radius = 20,
    this.blur = false,
    this.padding,
    this.tint,
    this.elevated = true,
  });

  final Widget child;
  final double radius;
  final bool blur;
  final EdgeInsetsGeometry? padding;

  /// Color sólido para un bloque destacado (p. ej. el primario).
  final Color? tint;
  final bool elevated;

  @override
  Widget build(BuildContext context) {
    final t = GlassTokens.of(context);
    final shape = BorderRadius.circular(radius);
    final fill = tint ?? (blur ? t.fill.withValues(alpha: 0.82) : t.fill);

    Widget surface = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: shape,
        color: fill,
        border: Border.all(
          color: tint == null ? t.rim : Colors.white.withValues(alpha: 0.12),
        ),
      ),
      child: Padding(padding: padding ?? EdgeInsets.zero, child: child),
    );

    if (blur) {
      surface = BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: surface,
      );
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: shape,
        boxShadow: elevated
            ? [
                // Sombra amplia y casi invisible: separa sin «flotar».
                BoxShadow(
                  color: t.shadow,
                  blurRadius: 28,
                  spreadRadius: -14,
                  offset: const Offset(0, 12),
                ),
                BoxShadow(
                  color: t.shadow.withValues(alpha: 0.05),
                  blurRadius: 2,
                  offset: const Offset(0, 1),
                ),
              ]
            : null,
      ),
      child: ClipRRect(borderRadius: shape, child: surface),
    );
  }
}

/// Sustituto directo de [Card]. Acepta los mismos parámetros que las
/// pantallas ya usaban (child, margin, clipBehavior) y, si se toca, se hunde
/// un poco al presionar, como un botón físico.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.margin,
    this.clipBehavior,
    this.onTap,
    this.radius = 20,
  });

  final Widget child;
  final EdgeInsetsGeometry? margin;
  // Se acepta por compatibilidad con Card: la tarjeta siempre recorta.
  final Clip? clipBehavior;
  final VoidCallback? onTap;
  final double radius;

  @override
  Widget build(BuildContext context) {
    // Siempre hay un Material transparente: los InkWell de dentro (que antes
    // encontraban el del Card) lo necesitan para dibujar la respuesta al toque.
    final Widget content = Material(
      type: MaterialType.transparency,
      child: onTap == null ? child : InkWell(onTap: onTap, child: child),
    );
    Widget card = GlassPanel(radius: radius, child: content);
    if (onTap != null) card = Presionable(child: card);
    return margin == null ? card : Padding(padding: margin!, child: card);
  }
}

/// Se encoge un 2 % mientras el dedo está apoyado: respuesta inmediata al
/// tocar, antes de soltar. No intercepta el toque; solo lo observa.
class Presionable extends StatefulWidget {
  const Presionable({super.key, required this.child, this.escala = 0.98});

  final Widget child;
  final double escala;

  @override
  State<Presionable> createState() => _PresionableState();
}

class _PresionableState extends State<Presionable> {
  bool _abajo = false;

  void _poner(bool v) {
    if (_abajo != v) setState(() => _abajo = v);
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerDown: (_) => _poner(true),
      onPointerUp: (_) => _poner(false),
      onPointerCancel: (_) => _poner(false),
      child: AnimatedScale(
        scale: _abajo ? widget.escala : 1,
        duration: Duration(milliseconds: _abajo ? 90 : 220),
        curve: Curves.easeOutCubic,
        child: widget.child,
      ),
    );
  }
}

/// Barra de navegación flotante en Liquid Glass.
///
/// La cápsula es vidrio de verdad: desenfoca y satura lo que pasa por detrás,
/// tiene un canto de luz que cambia de intensidad alrededor del borde y un
/// brillo arriba. El destino elegido se marca con una gota de vidrio más
/// clara que viaja de uno a otro con un leve rebote y se estira mientras se
/// mueve, como un líquido.
class GlassNavBar extends StatefulWidget {
  const GlassNavBar({
    super.key,
    required this.selectedIndex,
    required this.onSelected,
    required this.items,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<GlassNavItem> items;

  @override
  State<GlassNavBar> createState() => _GlassNavBarState();
}

class _GlassNavBarState extends State<GlassNavBar> with SingleTickerProviderStateMixin {
  late final AnimationController _viaje = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 560),
    value: 1,
  );
  late double _desde = widget.selectedIndex.toDouble();
  late double _hasta = widget.selectedIndex.toDouble();

  /// Sale rápido y se asienta con un rebote corto.
  static const _curva = Cubic(0.3, 1.32, 0.5, 1);

  @override
  void didUpdateWidget(GlassNavBar old) {
    super.didUpdateWidget(old);
    if (old.selectedIndex != widget.selectedIndex) {
      // Parte desde donde está la gota ahora, aunque esté a mitad de viaje.
      _desde = _posicion;
      _hasta = widget.selectedIndex.toDouble();
      if (MediaQuery.of(context).disableAnimations) {
        _viaje.value = 1;
      } else {
        _viaje.forward(from: 0);
      }
    }
  }

  double get _posicion => _desde + (_hasta - _desde) * _curva.transform(_viaje.value);

  @override
  void dispose() {
    _viaje.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final ink = dark ? AppColors.inkDark : AppColors.inkLight;
    final activo = dark ? AppColors.primaryOnDark : AppColors.primary;
    const radio = 30.0;

    return SafeArea(
      top: false,
      minimum: const EdgeInsets.fromLTRB(18, 0, 18, 10),
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(radio),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: dark ? 0.45 : 0.12),
              blurRadius: 34,
              spreadRadius: -6,
              offset: const Offset(0, 16),
            ),
            BoxShadow(
              color: Colors.black.withValues(alpha: dark ? 0.3 : 0.06),
              blurRadius: 4,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(radio),
          child: BackdropFilter(
            // Desenfoque más saturación: el color de lo que pasa por detrás
            // se intensifica en lugar de lavarse a gris.
            filter: ImageFilter.compose(
              outer: ImageFilter.blur(sigmaX: 26, sigmaY: 26),
              inner: const ColorFilter.matrix(_saturar),
            ),
            child: CustomPaint(
              painter: _VidrioPintor(dark: dark, radio: radio),
              child: Padding(
                padding: const EdgeInsets.all(6),
                child: SizedBox(
                  height: 56,
                  child: LayoutBuilder(
                    builder: (context, c) {
                      final ancho = c.maxWidth / widget.items.length;
                      return AnimatedBuilder(
                        animation: _viaje,
                        builder: (context, _) {
                          final t = _viaje.value;
                          // Se estira a mitad de camino y recupera su forma al llegar.
                          final estiron = (_hasta - _desde).abs() > 0 ? math.sin(math.pi * t) : 0.0;
                          final w = ancho * (1 + 0.28 * estiron);
                          final h = 56 * (1 - 0.1 * estiron);
                          final x = _posicion * ancho + (ancho - w) / 2;
                          return Stack(
                            clipBehavior: Clip.none,
                            children: [
                              Positioned(
                                left: x,
                                top: (56 - h) / 2,
                                width: w,
                                height: h,
                                child: _Gota(dark: dark, tinte: activo),
                              ),
                              Row(
                                children: [
                                  for (var i = 0; i < widget.items.length; i++)
                                    Expanded(
                                      child: _NavButton(
                                        item: widget.items[i],
                                        selected: i == widget.selectedIndex,
                                        color: i == widget.selectedIndex ? activo : ink.withValues(alpha: 0.58),
                                        onTap: () => widget.onSelected(i),
                                      ),
                                    ),
                                ],
                              ),
                            ],
                          );
                        },
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Matriz de saturación ×1,6 (luminancia Rec. 709).
const List<double> _saturar = [
  1.4724, -0.4288, -0.0436, 0, 0,
  -0.1276, 1.1712, -0.0436, 0, 0,
  -0.1276, -0.4288, 1.5564, 0, 0,
  0, 0, 0, 1, 0,
];

/// El cuerpo y el canto del vidrio: relleno translúcido más claro arriba,
/// borde de luz que brilla en la esquina superior izquierda y en la inferior
/// derecha (como un vidrio curvo iluminado desde arriba) y un brillo fino.
class _VidrioPintor extends CustomPainter {
  _VidrioPintor({required this.dark, required this.radio});

  final bool dark;
  final double radio;

  @override
  void paint(Canvas canvas, Size size) {
    final r = RRect.fromRectAndRadius(Offset.zero & size, Radius.circular(radio));
    canvas.drawRRect(
      r,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: dark
              ? [const Color(0x66263538), const Color(0x4D0E1A1C)]
              : [const Color(0x99FFFFFF), const Color(0x70FFFFFF)],
        ).createShader(Offset.zero & size),
    );
    canvas.drawRRect(
      r.deflate(0.5),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..shader = LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: dark
              ? [const Color(0x59FFFFFF), const Color(0x0FFFFFFF), const Color(0x0FFFFFFF), const Color(0x33FFFFFF)]
              : [const Color(0xFFFFFFFF), const Color(0x66FFFFFF), const Color(0x33FFFFFF), const Color(0xCCFFFFFF)],
          stops: const [0, 0.35, 0.65, 1],
        ).createShader(Offset.zero & size),
    );
    // Brillo especular: línea de luz en el canto superior.
    final brillo = Rect.fromLTWH(radio, 1, size.width - radio * 2, 1.2);
    canvas.drawRect(
      brillo,
      Paint()
        ..shader = LinearGradient(
          colors: [
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: dark ? 0.35 : 0.95),
            Colors.white.withValues(alpha: 0),
          ],
        ).createShader(brillo),
    );
  }

  @override
  bool shouldRepaint(_VidrioPintor old) => old.dark != dark;
}

/// La gota de vidrio que marca el destino elegido.
class _Gota extends StatelessWidget {
  const _Gota({required this.dark, required this.tinte});

  final bool dark;
  final Color tinte;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: dark
              ? [Colors.white.withValues(alpha: 0.16), Colors.white.withValues(alpha: 0.07)]
              : [Colors.white.withValues(alpha: 0.98), Color.lerp(Colors.white, tinte, 0.08)!.withValues(alpha: 0.88)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: dark ? 0.22 : 1), width: 1),
        boxShadow: [
          BoxShadow(
            color: (dark ? Colors.black : tinte).withValues(alpha: dark ? 0.35 : 0.16),
            blurRadius: 16,
            spreadRadius: -4,
            offset: const Offset(0, 6),
          ),
        ],
      ),
    );
  }
}

class GlassNavItem {
  const GlassNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.item,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  final GlassNavItem item;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      label: item.label,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Presionable(
          escala: 0.92,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                child: Icon(
                  selected ? item.selectedIcon : item.icon,
                  key: ValueKey(selected),
                  color: color,
                  size: 22,
                ),
              ),
              const SizedBox(height: 3),
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 220),
                style: TextStyle(
                  fontFamily: fuenteTexto,
                  fontSize: 11,
                  letterSpacing: 0.1,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                  color: color,
                ),
                child: Text(item.label),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Barra superior translúcida: el contenido se ve pasar por detrás, desenfocado.
class GlassAppBarBackground extends StatelessWidget {
  const GlassAppBarBackground({super.key});

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final base = dark ? AppColors.baseDark : AppColors.baseLight;
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
        child: ColoredBox(color: base.withValues(alpha: 0.82)),
      ),
    );
  }
}
