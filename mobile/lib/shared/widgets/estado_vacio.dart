import 'package:flutter/material.dart';

/// Pantalla vacía con una explicación, no solo un icono triste.
class EstadoVacio extends StatelessWidget {
  const EstadoVacio({
    super.key,
    required this.icono,
    required this.titulo,
    this.detalle,
    this.accion,
  });

  final IconData icono;
  final String titulo;
  final String? detalle;
  final Widget? accion;

  @override
  Widget build(BuildContext context) {
    final tenue = Theme.of(
      context,
    ).colorScheme.onSurface.withValues(alpha: 0.45);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 48),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icono, size: 44, color: tenue),
            const SizedBox(height: 14),
            Text(
              titulo,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (detalle != null) ...[
              const SizedBox(height: 6),
              Text(
                detalle!,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13.5, height: 1.45, color: tenue),
              ),
            ],
            if (accion != null) ...[const SizedBox(height: 20), accion!],
          ],
        ),
      ),
    );
  }
}

/// Un error con su mensaje real y un botón de reintento. El mensaje del
/// servidor es mucho más útil que «algo salió mal».
class EstadoError extends StatelessWidget {
  const EstadoError({super.key, required this.mensaje, this.onReintentar});

  final String mensaje;
  final VoidCallback? onReintentar;

  @override
  Widget build(BuildContext context) {
    return EstadoVacio(
      icono: Icons.cloud_off,
      titulo: 'No se pudo cargar',
      detalle: mensaje,
      accion: onReintentar == null
          ? null
          : OutlinedButton.icon(
              onPressed: onReintentar,
              icon: const Icon(Icons.refresh),
              label: const Text('Reintentar'),
            ),
    );
  }
}
