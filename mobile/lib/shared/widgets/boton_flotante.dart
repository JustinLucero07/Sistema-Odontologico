import 'package:flutter/material.dart';

class BotonFlotante extends StatelessWidget {
  const BotonFlotante({
    super.key,
    required this.child,
    required this.icono,
    required this.texto,
    required this.alTocar,
    this.visible = true,
  });

  final Widget child;
  final IconData icono;
  final String texto;
  final VoidCallback alTocar;
  final bool visible;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(child: child),
        if (visible)
          Positioned(
            right: 16,
            bottom: 96 + MediaQuery.paddingOf(context).bottom,
            child: FloatingActionButton.extended(
              heroTag: texto,
              onPressed: alTocar,
              icon: Icon(icono),
              label: Text(texto),
            ),
          ),
      ],
    );
  }
}
