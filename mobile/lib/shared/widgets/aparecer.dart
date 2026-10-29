import 'package:flutter/material.dart';

/// Entrada escalonada: el hijo sube 14 px y se funde al aparecer, un poco
/// después que el anterior ([orden]). Solo la primera vez que se construye;
/// al volver a la pantalla no se repite. Con «reducir movimiento» aparece
/// sin animar.
class Aparecer extends StatefulWidget {
  const Aparecer({super.key, required this.child, this.orden = 0});

  final Widget child;
  final int orden;

  @override
  State<Aparecer> createState() => _AparecerState();
}

class _AparecerState extends State<Aparecer> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: Duration(milliseconds: 520 + widget.orden.clamp(0, 8) * 60),
  );
  late final Animation<double> _t = CurvedAnimation(
    parent: _c,
    curve: Interval(
      (widget.orden.clamp(0, 8) * 60) / (520 + widget.orden.clamp(0, 8) * 60),
      1,
      curve: Curves.easeOutCubic,
    ),
  );
  bool _iniciado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_iniciado) return;
    _iniciado = true;
    if (MediaQuery.of(context).disableAnimations) {
      _c.value = 1;
    } else {
      _c.forward();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _t,
      builder: (context, hijo) => Opacity(
        opacity: _t.value,
        child: Transform.translate(offset: Offset(0, 14 * (1 - _t.value)), child: hijo),
      ),
      child: widget.child,
    );
  }
}
