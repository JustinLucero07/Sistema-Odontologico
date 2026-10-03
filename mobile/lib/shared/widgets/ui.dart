import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/repositorios.dart';
import 'carga.dart';
import 'estado_vacio.dart';
import 'glass.dart';

/// Piezas visuales comunes de los módulos, para que todas las pantallas
/// hablen el mismo idioma que la web.

/// Cifra destacada (KPI) en tarjeta de vidrio.
class Kpi extends StatelessWidget {
  const Kpi({
    super.key,
    required this.etiqueta,
    required this.valor,
    this.icono,
    this.color,
    this.detalle,
  });

  final String etiqueta;
  final String valor;
  final IconData? icono;
  final Color? color;
  final String? detalle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final c = color ?? scheme.primary;
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    etiqueta,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: scheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ),
                if (icono != null)
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: c.withValues(alpha: 0.13),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(icono, size: 17, color: c),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                valor,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.6,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
              ),
            ),
            if (detalle != null)
              Text(
                detalle!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 11.5,
                  color: scheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Rejilla de KPIs de dos columnas.
class RejillaKpi extends StatelessWidget {
  const RejillaKpi({super.key, required this.hijos});

  final List<Widget> hijos;

  @override
  Widget build(BuildContext context) {
    final filas = <Widget>[];
    for (var i = 0; i < hijos.length; i += 2) {
      filas.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: hijos[i]),
                const SizedBox(width: 10),
                Expanded(
                  child: i + 1 < hijos.length
                      ? hijos[i + 1]
                      : const SizedBox.shrink(),
                ),
              ],
            ),
          ),
        ),
      );
    }
    return Column(children: filas);
  }
}

/// Estado en cápsula de color con su nombre (nunca solo color).
class Pastilla extends StatelessWidget {
  const Pastilla(this.texto, {super.key, this.color});

  final String texto;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        texto,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c),
      ),
    );
  }
}

/// Título de sección con acción opcional a la derecha.
class Seccion extends StatelessWidget {
  const Seccion(this.titulo, {super.key, this.accion});

  final String titulo;
  final Widget? accion;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 14, 0, 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              titulo,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
          ),
          ?accion,
        ],
      ),
    );
  }
}

/// Fila de lista dentro de una tarjeta de vidrio.
class FilaTarjeta extends StatelessWidget {
  const FilaTarjeta({
    super.key,
    required this.titulo,
    this.subtitulo,
    this.icono,
    this.colorIcono,
    this.derecha,
    this.alTocar,
    this.tachado = false,
  });

  final String titulo;
  final String? subtitulo;
  final IconData? icono;
  final Color? colorIcono;
  final Widget? derecha;
  final VoidCallback? alTocar;
  final bool tachado;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final c = colorIcono ?? scheme.primary;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GlassCard(
        onTap: alTocar,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            children: [
              if (icono != null) ...[
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: c.withValues(alpha: 0.13),
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: Icon(icono, color: c, size: 21),
                ),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      titulo,
                      style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600,
                        decoration: tachado ? TextDecoration.lineThrough : null,
                        color: tachado
                            ? scheme.onSurface.withValues(alpha: 0.5)
                            : null,
                      ),
                    ),
                    if (subtitulo != null && subtitulo!.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          subtitulo!,
                          style: TextStyle(
                            fontSize: 12.5,
                            color: scheme.onSurface.withValues(alpha: 0.55),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              if (derecha != null) ...[const SizedBox(width: 8), derecha!],
            ],
          ),
        ),
      ),
    );
  }
}

/// Dibuja un [AsyncValue] con esqueleto, error con reintento y vacío.
class Asincrono<T> extends StatelessWidget {
  const Asincrono({
    super.key,
    required this.valor,
    required this.alReintentar,
    required this.listo,
    this.esqueleto,
  });

  final AsyncValue<T> valor;
  final VoidCallback alReintentar;
  final Widget Function(T datos) listo;
  final Widget? esqueleto;

  @override
  Widget build(BuildContext context) {
    return valor.when(
      skipLoadingOnRefresh: true,
      loading: () => esqueleto ?? const EsqueletoLista(),
      error: (e, _) => ListView(
        children: [
          EstadoError(
            mensaje: e is ErrorApi ? e.mensaje : 'Revise la conexión.',
            onReintentar: alReintentar,
          ),
        ],
      ),
      data: listo,
    );
  }
}

/// Espacio al final de las listas para no quedar bajo el botón flotante.
const finDeLista = SizedBox(height: 96);

String fechaCorta(dynamic iso) {
  if (iso == null || '$iso'.isEmpty) return '—';
  final d = DateTime.tryParse('$iso');
  return d == null ? '$iso' : DateFormat('dd/MM/yyyy').format(d.toLocal());
}

String fechaHora(dynamic iso) {
  final d = DateTime.tryParse('${iso ?? ''}');
  return d == null ? '—' : DateFormat('dd/MM/yyyy HH:mm').format(d.toLocal());
}

String hoyIso() => DateFormat('yyyy-MM-dd').format(DateTime.now());

/// Colores semánticos para estados.
class Tonos {
  static const verde = Color(0xFF2B9A5B);
  static const ambar = Color(0xFFC98A1E);
  static const rojo = Color(0xFFD0453A);
  static const azul = Color(0xFF2F7FD1);
  static const gris = Color(0xFF8A9598);
  static const violeta = Color(0xFF7B5BD6);
}
