import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/ui.dart';
import '../auth/auth_controller.dart';
import '../theme/app_theme.dart';

/// Aviso flotante arriba: sin conexión, cambios por subir o rechazados.
/// Tocarlo abre la lista de cambios pendientes.
class BarraSinConexion extends ConsumerWidget {
  const BarraSinConexion({super.key, required this.navegador});

  final GlobalKey<NavigatorState> navegador;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(sinConexionProvider);
    final pendientes = s.pendientes.length;
    final conflictos = s.conflictos.length;
    final visible = !s.enLinea || pendientes > 0 || conflictos > 0 || s.sincronizando;
    final (icono, texto, color) = switch (true) {
      _ when conflictos > 0 => (Icons.error_outline, '$conflictos ${conflictos == 1 ? 'cambio rechazado' : 'cambios rechazados'} · tocar para revisar', Tonos.rojo),
      _ when s.sincronizando => (Icons.sync, 'Subiendo $pendientes ${pendientes == 1 ? 'cambio' : 'cambios'}…', Tonos.azul),
      _ when !s.enLinea => (
        Icons.cloud_off_outlined,
        pendientes > 0 ? 'Sin conexión · $pendientes ${pendientes == 1 ? 'cambio' : 'cambios'} por subir' : 'Sin conexión · usando datos guardados',
        Tonos.ambar,
      ),
      _ => (Icons.cloud_upload_outlined, '$pendientes ${pendientes == 1 ? 'cambio' : 'cambios'} por subir', Tonos.azul),
    };
    return IgnorePointer(
      ignoring: !visible,
      child: AnimatedSlide(
        offset: visible ? Offset.zero : const Offset(0, -1.5),
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeOutCubic,
        child: SafeArea(
          bottom: false,
          child: Align(
            alignment: Alignment.topCenter,
            child: Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(999),
                  onTap: () => navegador.currentState?.push(MaterialPageRoute<void>(builder: (_) => const CambiosPendientesPage())),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: Color.lerp(color, Colors.black, 0.25),
                      borderRadius: BorderRadius.circular(999),
                      boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 14, offset: Offset(0, 6))],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        s.sincronizando
                            ? const SizedBox(width: 15, height: 15, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : Icon(icono, size: 17, color: Colors.white),
                        const SizedBox(width: 8),
                        Text(texto, style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600)),
                      ],
                    ),
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

class CambiosPendientesPage extends ConsumerWidget {
  const CambiosPendientesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(sinConexionProvider);
    final tinta = Theme.of(context).colorScheme.onSurface;
    return PaginaModulo(
      titulo: 'Cambios por subir',
      cuerpo: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            s.enLinea
                ? 'Hay conexión: los cambios se suben solos, en el orden en que se hicieron.'
                : 'Sin conexión. Los cambios quedan guardados en este teléfono y se subirán solos al volver la red.',
            style: TextStyle(color: tinta.withValues(alpha: 0.65)),
          ),
          const SizedBox(height: 12),
          if (s.pendientes.isNotEmpty)
            FilledButton.icon(
              onPressed: s.sincronizando ? null : s.sincronizar,
              icon: const Icon(Icons.sync),
              label: Text(s.sincronizando ? 'Subiendo…' : 'Subir ahora'),
            ),
          if (s.conflictos.isNotEmpty) ...[
            const Seccion('Rechazados por el servidor'),
            for (final p in s.conflictos)
              FilaTarjeta(
                icono: Icons.error_outline,
                colorIcono: Tonos.rojo,
                titulo: p.descripcion,
                subtitulo: '${p.error}\n${fechaHora(p.creado.toIso8601String())}',
                derecha: PopupMenuButton<String>(
                  onSelected: (o) async {
                    if (o == 'reintentar') {
                      await s.reintentar(p);
                    } else if (await confirmar(context, titulo: '¿Descartar este cambio?', mensaje: 'No se subirá al servidor.', textoConfirmar: 'Descartar', peligro: true)) {
                      await s.descartar(p);
                    }
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'reintentar', child: Text('Reintentar')),
                    PopupMenuItem(value: 'descartar', child: Text('Descartar')),
                  ],
                ),
              ),
          ],
          if (s.pendientes.isNotEmpty) ...[
            const Seccion('Esperando conexión'),
            for (final p in s.pendientes)
              FilaTarjeta(
                icono: Icons.cloud_upload_outlined,
                colorIcono: Tonos.azul,
                titulo: p.descripcion,
                subtitulo: 'Hecho el ${fechaHora(p.creado.toIso8601String())}',
              ),
          ],
          if (s.pendientes.isEmpty && s.conflictos.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 40),
              child: Column(
                children: [
                  Icon(Icons.cloud_done_outlined, size: 48, color: AppColors.primary),
                  const SizedBox(height: 10),
                  Text('Todo está subido', style: estiloTitulo(18, color: tinta)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
