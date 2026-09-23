import 'dart:ui';

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

/// Liquid Glass para la app, con los mismos principios que la web.
///
/// El vidrio se lee como material por tres cosas a la vez: deja ver el color
/// de detrás, tiene un canto iluminado (borde claro y brillo arriba) y
/// proyecta una sombra suave. Sin las tres parece solo un panel translúcido.

/// Fondo con luz de color detrás de todas las pantallas: es lo que el vidrio
/// deja ver. Es estático, así que se pinta una vez y no cuesta al hacer scroll.
class AmbientBackground extends StatelessWidget {
  const AmbientBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final base = dark
        ? const [Color(0xFF0A191B), Color(0xFF050E10)]
        : const [Color(0xFFEDF3F3), Color(0xFFE2EAEA)];

    Widget blob(Alignment at, double size, Color color) => Align(
      alignment: at,
      child: IgnorePointer(
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [color, color.withValues(alpha: 0)]),
          ),
        ),
      ),
    );

    return Stack(
      fit: StackFit.expand,
      children: [
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: base,
            ),
          ),
        ),
        // RepaintBoundary: las manchas no cambian, no se repintan con el
        // contenido que pasa por encima.
        RepaintBoundary(
          child: Stack(
            fit: StackFit.expand,
            children: [
              blob(
                const Alignment(-1.2, -1.1),
                520,
                AppColors.mint.withValues(alpha: dark ? 0.22 : 0.34),
              ),
              blob(
                const Alignment(1.3, -0.7),
                460,
                AppColors.primary.withValues(alpha: dark ? 0.26 : 0.22),
              ),
              blob(
                const Alignment(1.1, 1.2),
                540,
                AppColors.accent.withValues(alpha: dark ? 0.10 : 0.22),
              ),
              blob(
                const Alignment(-1.2, 1.1),
                420,
                const Color(0xFF60A5FA).withValues(alpha: dark ? 0.10 : 0.14),
              ),
            ],
          ),
        ),
        child,
      ],
    );
  }
}

/// Colores del material según el tema.
class GlassTokens {
  const GlassTokens._(this.fill, this.rim, this.edge, this.shadow);

  final List<Color> fill;
  final Color rim;
  final Color edge;
  final Color shadow;

  static GlassTokens of(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return dark
        ? const GlassTokens._(
            [Color(0xA8223E42), Color(0x85122629)],
            Color(0x17FFFFFF),
            Color(0x2EFFFFFF),
            Color(0x99000000),
          )
        : const GlassTokens._(
            [Color(0xD1FFFFFF), Color(0x99FFFFFF)],
            Color(0xB3FFFFFF),
            Color(0xF2FFFFFF),
            Color(0x380A2325),
          );
  }
}

/// Superficie de vidrio. [blur] activa el desenfoque real del fondo; solo se
/// usa donde pasa contenido por detrás (barras flotantes). En tarjetas sobre
/// el fondo ambiental no hace falta: desenfocar algo ya difuso no cambia nada
/// y cuesta rendimiento en cada frame del scroll.
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

  /// Color que tiñe el vidrio (p. ej. el primario para un bloque destacado).
  final Color? tint;
  final bool elevated;

  @override
  Widget build(BuildContext context) {
    final t = GlassTokens.of(context);
    final shape = BorderRadius.circular(radius);
    final fill = tint == null
        ? t.fill
        : [tint!.withValues(alpha: 0.9), tint!.withValues(alpha: 0.72)];

    Widget surface = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: shape,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: fill,
        ),
        border: Border.all(color: t.rim),
      ),
      child: Stack(
        children: [
          Padding(padding: padding ?? EdgeInsets.zero, child: child),
          // Reflejo especular: una línea de luz en el canto superior, más
          // intensa en el centro, como el borde de un vidrio curvo.
          Positioned(
            left: radius * 0.6,
            right: radius * 0.6,
            top: 0,
            height: 1,
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [t.edge.withValues(alpha: 0), t.edge, t.edge.withValues(alpha: 0)],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
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
                BoxShadow(color: t.shadow, blurRadius: 30, spreadRadius: -12, offset: const Offset(0, 14)),
                BoxShadow(color: t.shadow.withValues(alpha: 0.08), blurRadius: 2, offset: const Offset(0, 1)),
              ]
            : null,
      ),
      child: ClipRRect(borderRadius: shape, child: surface),
    );
  }
}

/// Sustituto directo de [Card] con el material de vidrio. Acepta los mismos
/// parámetros que las pantallas ya usaban (child, margin, clipBehavior).
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
  // Se acepta por compatibilidad con Card: el vidrio siempre recorta.
  final Clip? clipBehavior;
  final VoidCallback? onTap;
  final double radius;

  @override
  Widget build(BuildContext context) {
    Widget content = child;
    if (onTap != null) {
      content = Material(
        type: MaterialType.transparency,
        child: InkWell(onTap: onTap, child: child),
      );
    }
    final card = GlassPanel(radius: radius, child: content);
    return margin == null ? card : Padding(padding: margin!, child: card);
  }
}

/// Barra de navegación flotante: una cápsula de vidrio separada del borde,
/// con desenfoque real porque el contenido pasa por debajo.
class GlassNavBar extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final ink = Theme.of(context).textTheme.bodyMedium?.color ?? scheme.onSurface;

    return SafeArea(
      top: false,
      minimum: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: GlassPanel(
        blur: true,
        radius: 30,
        padding: const EdgeInsets.all(6),
        child: Row(
          children: [
            for (var i = 0; i < items.length; i++)
              Expanded(
                child: _NavButton(
                  item: items[i],
                  selected: i == selectedIndex,
                  color: i == selectedIndex ? scheme.primary : ink.withValues(alpha: 0.6),
                  onTap: () => onSelected(i),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class GlassNavItem {
  const GlassNavItem({required this.icon, required this.selectedIcon, required this.label});

  final IconData icon;
  final IconData selectedIcon;
  final String label;
}

class _NavButton extends StatelessWidget {
  const _NavButton({required this.item, required this.selected, required this.color, required this.onTap});

  final GlassNavItem item;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Semantics(
      selected: selected,
      button: true,
      label: item.label,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        // La gota de vidrio claro se desliza al destino elegido: el cambio se
        // anima con una curva sin rebote, igual que en la web.
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 280),
          curve: const Cubic(0.32, 0.72, 0, 1),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            color: selected
                ? (dark ? Colors.white.withValues(alpha: 0.1) : Colors.white.withValues(alpha: 0.95))
                : Colors.transparent,
            boxShadow: selected && !dark
                ? const [BoxShadow(color: Color(0x220A2325), blurRadius: 14, offset: Offset(0, 6))]
                : null,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(selected ? item.selectedIcon : item.icon, color: color, size: 24),
              const SizedBox(height: 2),
              Text(
                item.label,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  color: color,
                ),
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
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: dark
                  ? const [Color(0xCC0A191B), Color(0x990A191B)]
                  : const [Color(0xD9EDF3F3), Color(0x99EDF3F3)],
            ),
          ),
        ),
      ),
    );
  }
}
