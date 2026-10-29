import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/odontograma/odontograma_widget.dart' show filaArcada;
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Periodontograma: seis sitios por pieza. Igual que en la web, un examen
/// nunca se edita: cada registro es una versión nueva y las anteriores quedan
/// intactas para comparar.

const _vestibular = ['vestibular_distal', 'vestibular_central', 'vestibular_mesial'];
const _lingual = ['lingual_distal', 'lingual_central', 'lingual_mesial'];
const _sitios = [..._vestibular, ..._lingual];
const _nombreSitio = {
  'vestibular_distal': 'Distal',
  'vestibular_central': 'Central',
  'vestibular_mesial': 'Mesial',
  'lingual_distal': 'Distal',
  'lingual_central': 'Central',
  'lingual_mesial': 'Mesial',
};

final _arriba = filaArcada('upper');
final _abajo = filaArcada('lower');

/// Hasta 3 mm es surco sano, 4–5 mm bolsa que vigilar, 6 mm o más avanzada.
Color colorBolsa(int? mm) => switch (mm) {
  null => Tonos.gris,
  <= 3 => Tonos.verde,
  <= 5 => Tonos.ambar,
  _ => Tonos.rojo,
};

final perioVersionesProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, id) => ref.watch(apiProvider).lista('/patients/$id/periodontogram/versions'),
);

/// Examen a mostrar: (paciente, versión) — versión vacía = el último.
final perioExamenProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>?, (String, String)>((ref, k) async {
      final api = ref.watch(apiProvider);
      final r = k.$2.isEmpty
          ? await api.get('/patients/${k.$1}/periodontogram')
          : await api.get('/patients/${k.$1}/periodontogram/${k.$2}');
      return r == null ? null : (r as Map).cast<String, dynamic>();
    });

// ------------------------------------------------------------------ Estado

class _Sitio {
  int? sondaje;
  int? recesion;
  bool sangrado = false;
  bool placa = false;
  bool supuracion = false;

  bool get tocado => sondaje != null || recesion != null || sangrado || placa || supuracion;
}

class _Pieza {
  _Pieza(this.fdi);
  final String fdi;
  bool ausente = false;
  bool implante = false;
  int? movilidad;
  int? furca;
  final sitios = {for (final s in _sitios) s: _Sitio()};

  bool get tocada =>
      ausente || implante || movilidad != null || furca != null || sitios.values.any((s) => s.tocado);

  int? get maxSondaje {
    final v = sitios.values.map((s) => s.sondaje).whereType<int>();
    return v.isEmpty ? null : v.reduce((a, b) => a > b ? a : b);
  }
}

Map<String, _Pieza> _desdeExamen(Map<String, dynamic>? examen) {
  final piezas = {for (final f in [..._arriba, ..._abajo]) f: _Pieza(f)};
  if (examen == null) return piezas;
  for (final t in (examen['teeth'] as List? ?? []).cast<Map<String, dynamic>>()) {
    final p = piezas['${t['fdi_number']}'];
    if (p == null) continue;
    p.ausente = t['absent'] == true;
    p.implante = t['implant'] == true;
    p.movilidad = t['mobility'] as int?;
    p.furca = t['furcation'] as int?;
  }
  for (final m in (examen['measurements'] as List? ?? []).cast<Map<String, dynamic>>()) {
    final s = piezas['${m['fdi_number']}']?.sitios['${m['site']}'];
    if (s == null) continue;
    s.sondaje = m['probing_depth'] as int?;
    s.recesion = m['recession'] as int?;
    s.sangrado = m['bleeding'] == true;
    s.placa = m['plaque'] == true;
    s.supuracion = m['suppuration'] == true;
  }
  return piezas;
}

// ------------------------------------------------------------------ Pestaña

class PestanaPeriodontograma extends ConsumerStatefulWidget {
  const PestanaPeriodontograma({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  ConsumerState<PestanaPeriodontograma> createState() => _PestanaPeriodontogramaState();
}

class _PestanaPeriodontogramaState extends ConsumerState<PestanaPeriodontograma> {
  String _version = '';

  @override
  Widget build(BuildContext context) {
    final id = widget.pacienteId;
    final versiones = ref.watch(perioVersionesProvider(id)).valueOrNull ?? const [];
    final examen = ref.watch(perioExamenProvider((id, _version)));
    final historico = _version.isNotEmpty && versiones.isNotEmpty && versiones.first['id'] != _version;

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(perioVersionesProvider(id));
        ref.invalidate(perioExamenProvider((id, _version)));
      },
      child: Asincrono(
        valor: examen,
        alReintentar: () => ref.invalidate(perioExamenProvider((id, _version))),
        listo: (e) {
          if (e == null) {
            return ListView(
              children: const [
                EstadoVacio(
                  icono: Icons.stacked_line_chart,
                  titulo: 'Sin periodontograma',
                  detalle: 'Registre el primer examen con el botón «Nuevo examen».',
                ),
              ],
            );
          }
          final ind = (e['indices'] as Map? ?? {}).cast<String, dynamic>();
          final piezas = _desdeExamen(e);
          int n(String k) => (ind[k] as num? ?? 0).toInt();
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
            children: [
              if (versiones.length > 1)
                SizedBox(
                  height: 40,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      for (var i = 0; i < versiones.length; i++)
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            label: Text(
                              '${fechaCorta(versiones[i]['created_at'])}${i == 0 ? ' · Actual' : ''}'
                              '${versiones[i]['type'] == 'initial' ? ' · Inicial' : ''}',
                            ),
                            selected: (_version.isEmpty ? versiones.first['id'] : _version) == versiones[i]['id'],
                            onSelected: (_) => setState(() => _version = i == 0 ? '' : '${versiones[i]['id']}'),
                          ),
                        ),
                    ],
                  ),
                ),
              if (historico)
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Text(
                    'Examen anterior, en solo lectura.',
                    style: TextStyle(fontSize: 12.5, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6)),
                  ),
                ),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 3,
                shrinkWrap: true,
                padding: EdgeInsets.zero,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 1.25,
                children: [
                  _Indice('Sangrado', '${n('bleeding_index')} %', n('bleeding_index') > 25 ? Tonos.rojo : Tonos.verde),
                  _Indice('Placa', '${n('plaque_index')} %', n('plaque_index') > 25 ? Tonos.rojo : Tonos.verde),
                  _Indice('Sondaje medio', '${ind['mean_probing_depth'] ?? '—'} mm', null),
                  _Indice('Sitios 4–5 mm', '${n('sites_over_3mm') - n('sites_over_5mm')}', Tonos.ambar),
                  _Indice('Sitios ≥ 6 mm', '${n('sites_over_5mm')}', n('sites_over_5mm') > 0 ? Tonos.rojo : Tonos.verde),
                  _Indice('Registrados', '${n('sites_recorded')}', null),
                ],
              ),
              const Seccion('Bolsas por pieza'),
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(10, 14, 10, 12),
                  child: Column(
                    children: [
                      _Arcada(fila: _arriba, piezas: piezas, arriba: true, alTocar: (p) => _detalle(context, p)),
                      const SizedBox(height: 10),
                      _Arcada(fila: _abajo, piezas: piezas, arriba: false, alTocar: (p) => _detalle(context, p)),
                      const SizedBox(height: 12),
                      const _Leyenda(),
                    ],
                  ),
                ),
              ),
              if ('${e['notes'] ?? ''}'.trim().isNotEmpty) ...[
                const Seccion('Notas'),
                GlassCard(
                  child: Padding(padding: const EdgeInsets.all(16), child: Text('${e['notes']}')),
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  void _detalle(BuildContext context, _Pieza p) {
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Pieza ${p.fdi}', style: estiloTitulo(20)),
              const SizedBox(height: 4),
              Text(
                [
                  if (p.ausente) 'Ausente',
                  if (p.implante) 'Implante',
                  if (p.movilidad != null) 'Movilidad ${p.movilidad}',
                  if (p.furca != null) 'Furca ${p.furca}',
                ].join(' · ').ifEmpty('Sin observaciones de la pieza'),
              ),
              if (!p.ausente) ...[
                const SizedBox(height: 14),
                for (final (titulo, sitios) in [('Vestibular', _vestibular), ('Lingual / palatino', _lingual)]) ...[
                  Text(titulo.toUpperCase(), style: Theme.of(context).textTheme.labelSmall),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      for (final s in sitios)
                        Expanded(
                          child: Column(
                            children: [
                              Text(_nombreSitio[s]!, style: Theme.of(context).textTheme.bodySmall),
                              Text(
                                p.sitios[s]!.sondaje == null ? '—' : '${p.sitios[s]!.sondaje} mm',
                                style: estiloTitulo(18, color: colorBolsa(p.sitios[s]!.sondaje)),
                              ),
                              Text(
                                [
                                  if (p.sitios[s]!.recesion != null) 'Rec ${p.sitios[s]!.recesion}',
                                  if (p.sitios[s]!.sangrado) 'Sangra',
                                  if (p.sitios[s]!.placa) 'Placa',
                                  if (p.sitios[s]!.supuracion) 'Pus',
                                ].join(' · '),
                                textAlign: TextAlign.center,
                                style: const TextStyle(fontSize: 11),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}

extension on String {
  String ifEmpty(String otro) => isEmpty ? otro : this;
}

class _Indice extends StatelessWidget {
  const _Indice(this.etiqueta, this.valor, this.color);

  final String etiqueta;
  final String valor;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    return GlassCard(
      radius: 18,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                if (color != null) ...[
                  Container(width: 7, height: 7, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
                  const SizedBox(width: 6),
                ],
                Expanded(
                  child: Text(
                    etiqueta,
                    maxLines: 2,
                    style: TextStyle(fontSize: 11.5, height: 1.2, color: tinta.withValues(alpha: 0.6)),
                  ),
                ),
              ],
            ),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(valor, style: estiloTitulo(20, color: tinta, peso: FontWeight.w800)),
            ),
          ],
        ),
      ),
    );
  }
}

/// Una arcada: por pieza, tres barras vestibulares y tres linguales cuya
/// altura es la profundidad de bolsa, con el color de su gravedad.
class _Arcada extends StatelessWidget {
  const _Arcada({required this.fila, required this.piezas, required this.arriba, required this.alTocar});

  final List<String> fila;
  final Map<String, _Pieza> piezas;
  final bool arriba;
  final ValueChanged<_Pieza> alTocar;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    return Row(
      children: [
        for (var i = 0; i < fila.length; i++) ...[
          if (i == 8) Container(width: 1, height: 70, color: tinta.withValues(alpha: 0.12)),
          Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => alTocar(piezas[fila[i]]!),
              child: _ColumnaPieza(pieza: piezas[fila[i]]!, arriba: arriba),
            ),
          ),
        ],
      ],
    );
  }
}

class _ColumnaPieza extends StatelessWidget {
  const _ColumnaPieza({required this.pieza, required this.arriba});

  final _Pieza pieza;
  final bool arriba;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    Widget barras(List<String> sitios, bool haciaAbajo) => SizedBox(
      height: 26,
      child: Row(
        crossAxisAlignment: haciaAbajo ? CrossAxisAlignment.start : CrossAxisAlignment.end,
        children: [
          for (final s in sitios)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 0.6),
                child: Column(
                  mainAxisAlignment: haciaAbajo ? MainAxisAlignment.start : MainAxisAlignment.end,
                  children: [
                    if (!haciaAbajo && pieza.sitios[s]!.sangrado) _punto(),
                    Container(
                      height: pieza.ausente ? 0 : (((pieza.sitios[s]!.sondaje ?? 0) * 2.2).clamp(0, 20)).toDouble(),
                      decoration: BoxDecoration(
                        color: colorBolsa(pieza.sitios[s]!.sondaje),
                        borderRadius: BorderRadius.circular(1.5),
                      ),
                    ),
                    if (haciaAbajo && pieza.sitios[s]!.sangrado) _punto(),
                  ],
                ),
              ),
            ),
        ],
      ),
    );

    final numero = Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Text(
        pieza.fdi,
        style: TextStyle(
          fontSize: 9.5,
          fontWeight: FontWeight.w600,
          color: tinta.withValues(alpha: pieza.ausente ? 0.25 : 0.55),
          decoration: pieza.ausente ? TextDecoration.lineThrough : null,
        ),
      ),
    );

    // Vestibular hacia fuera de la boca, lingual hacia dentro.
    return Column(
      children: arriba
          ? [barras(_vestibular, false), numero, barras(_lingual, true)]
          : [barras(_lingual, false), numero, barras(_vestibular, true)],
    );
  }

  Widget _punto() => Container(
    width: 3,
    height: 3,
    margin: const EdgeInsets.symmetric(vertical: 1),
    decoration: const BoxDecoration(color: Tonos.rojo, shape: BoxShape.circle),
  );
}

class _Leyenda extends StatelessWidget {
  const _Leyenda();

  @override
  Widget build(BuildContext context) {
    Widget item(Color c, String t) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 5),
        Text(t, style: const TextStyle(fontSize: 11)),
      ],
    );
    return Wrap(
      spacing: 12,
      runSpacing: 6,
      alignment: WrapAlignment.center,
      children: [
        item(Tonos.verde, '≤ 3 mm'),
        item(Tonos.ambar, '4–5 mm'),
        item(Tonos.rojo, '≥ 6 mm'),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 6, height: 6, decoration: const BoxDecoration(color: Tonos.rojo, shape: BoxShape.circle)),
            const SizedBox(width: 5),
            const Text('Sangrado', style: TextStyle(fontSize: 11)),
          ],
        ),
      ],
    );
  }
}

// ------------------------------------------------------------------ Nuevo examen

/// Pregunta si partir del último examen (lo habitual en un control: se
/// vuelve a sondear la misma boca) o empezar en blanco, y abre el editor.
Future<void> nuevoPeriodontograma(BuildContext context, WidgetRef ref, String pacienteId) async {
  final ultimo = await cargarOAvisar(context, ref.read(perioExamenProvider((pacienteId, '')).future));
  if (!context.mounted) return;
  Map<String, dynamic>? base;
  if (ultimo != null) {
    final eleccion = await showModalBottomSheet<String>(
      context: context,
      builder: (hoja) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.content_copy_outlined),
              title: const Text('Partir del último examen'),
              subtitle: const Text('Se corrigen solo los sitios que cambiaron'),
              onTap: () => Navigator.pop(hoja, 'copia'),
            ),
            ListTile(
              leading: const Icon(Icons.note_add_outlined),
              title: const Text('Empezar en blanco'),
              onTap: () => Navigator.pop(hoja, 'blanco'),
            ),
          ],
        ),
      ),
    );
    if (eleccion == null) return;
    if (eleccion == 'copia') base = ultimo;
  }
  if (!context.mounted) return;
  final guardado = await Navigator.of(context).push<bool>(
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (_) => EditorPeriodontograma(pacienteId: pacienteId, base: base),
    ),
  );
  if (guardado == true) {
    ref.invalidate(perioVersionesProvider(pacienteId));
    ref.invalidate(perioExamenProvider((pacienteId, '')));
  }
}

class EditorPeriodontograma extends ConsumerStatefulWidget {
  const EditorPeriodontograma({super.key, required this.pacienteId, this.base});

  final String pacienteId;
  final Map<String, dynamic>? base;

  @override
  ConsumerState<EditorPeriodontograma> createState() => _EditorPeriodontogramaState();
}

class _EditorPeriodontogramaState extends ConsumerState<EditorPeriodontograma> {
  late final Map<String, _Pieza> _piezas = _desdeExamen(widget.base);
  final _orden = [..._arriba, ..._abajo];
  final _notas = TextEditingController();
  int _actual = 0;
  bool _guardando = false;

  _Pieza get _p => _piezas[_orden[_actual]]!;

  @override
  void dispose() {
    _notas.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    final dientes = <Map<String, dynamic>>[];
    final medidas = <Map<String, dynamic>>[];
    for (final p in _piezas.values) {
      if (!p.tocada) continue;
      dientes.add({
        'fdi_number': p.fdi,
        'absent': p.ausente,
        'implant': p.implante,
        'mobility': p.movilidad,
        'furcation': p.furca,
        'notes': null,
      });
      if (p.ausente) continue;
      // Solo lo sondeado: «no medido» y «0 mm» son hallazgos distintos.
      for (final e in p.sitios.entries) {
        final s = e.value;
        if (!s.tocado) continue;
        medidas.add({
          'fdi_number': p.fdi,
          'site': e.key,
          'probing_depth': s.sondaje,
          'recession': s.recesion,
          'bleeding': s.sangrado,
          'suppuration': s.supuracion,
          'plaque': s.placa,
        });
      }
    }
    if (medidas.isEmpty) {
      avisar(context, 'Registre al menos una medición antes de guardar.');
      return;
    }
    setState(() => _guardando = true);
    final ok = await intentar(
      context,
      () => ref.read(apiProvider).post('/patients/${widget.pacienteId}/periodontogram', {
        'notes': _notas.text.trim().isEmpty ? null : _notas.text.trim(),
        'teeth': dientes,
        'measurements': medidas,
      }),
      exito: 'Periodontograma guardado',
    );
    if (!mounted) return;
    setState(() => _guardando = false);
    if (ok) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final tinta = scheme.onSurface;
    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          flexibleSpace: const GlassAppBarBackground(),
          title: const Text('Nuevo examen'),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size(96, 40)),
                onPressed: _guardando ? null : _guardar,
                child: Text(_guardando ? 'Guardando…' : 'Guardar'),
              ),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Text(
              'Al guardar se crea una versión nueva; el examen anterior queda intacto.',
              style: TextStyle(fontSize: 12.5, color: tinta.withValues(alpha: 0.6)),
            ),
            const SizedBox(height: 12),
            // Selector de pieza: las dos arcadas en miniatura.
            GlassCard(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  children: [
                    for (final fila in [_arriba, _abajo])
                      Row(
                        children: [
                          for (final f in fila)
                            Expanded(
                              child: GestureDetector(
                                onTap: () => setState(() => _actual = _orden.indexOf(f)),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 180),
                                  margin: const EdgeInsets.all(1.2),
                                  height: 30,
                                  alignment: Alignment.center,
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(7),
                                    color: _orden[_actual] == f
                                        ? scheme.primary
                                        : (_piezas[f]!.tocada
                                              ? colorBolsa(_piezas[f]!.maxSondaje).withValues(alpha: 0.18)
                                              : tinta.withValues(alpha: 0.04)),
                                  ),
                                  child: Text(
                                    f,
                                    style: TextStyle(
                                      fontSize: 9.5,
                                      fontWeight: FontWeight.w700,
                                      color: _orden[_actual] == f ? scheme.onPrimary : tinta.withValues(alpha: 0.7),
                                      decoration: _piezas[f]!.ausente ? TextDecoration.lineThrough : null,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                IconButton.outlined(
                  onPressed: _actual == 0 ? null : () => setState(() => _actual--),
                  icon: const Icon(Icons.chevron_left),
                  tooltip: 'Pieza anterior',
                ),
                Expanded(
                  child: Column(
                    children: [
                      Text('Pieza ${_p.fdi}', style: estiloTitulo(22, color: tinta, peso: FontWeight.w800)),
                      Text(
                        _arriba.contains(_p.fdi) ? 'Arcada superior' : 'Arcada inferior',
                        style: TextStyle(fontSize: 12, color: tinta.withValues(alpha: 0.55)),
                      ),
                    ],
                  ),
                ),
                IconButton.outlined(
                  onPressed: _actual == _orden.length - 1 ? null : () => setState(() => _actual++),
                  icon: const Icon(Icons.chevron_right),
                  tooltip: 'Pieza siguiente',
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  label: const Text('Ausente'),
                  selected: _p.ausente,
                  onSelected: (v) => setState(() => _p.ausente = v),
                ),
                FilterChip(
                  label: const Text('Implante'),
                  selected: _p.implante,
                  onSelected: (v) => setState(() => _p.implante = v),
                ),
              ],
            ),
            if (!_p.ausente) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: _Grado('Movilidad', _p.movilidad, (v) => setState(() => _p.movilidad = v))),
                  const SizedBox(width: 10),
                  Expanded(child: _Grado('Furca', _p.furca, (v) => setState(() => _p.furca = v))),
                ],
              ),
              for (final (titulo, sitios) in [('Vestibular', _vestibular), ('Lingual / palatino', _lingual)]) ...[
                Seccion(titulo),
                GlassCard(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(8, 12, 8, 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (final s in sitios)
                          Expanded(child: _EditorSitio(nombre: _nombreSitio[s]!, sitio: _p.sitios[s]!, alCambiar: () => setState(() {}))),
                      ],
                    ),
                  ),
                ),
              ],
            ],
            const SizedBox(height: 16),
            if (_actual < _orden.length - 1)
              OutlinedButton.icon(
                onPressed: () => setState(() => _actual++),
                icon: const Icon(Icons.arrow_forward),
                label: Text('Siguiente: pieza ${_orden[_actual + 1]}'),
              ),
            const Seccion('Notas del examen'),
            TextField(
              controller: _notas,
              maxLines: 3,
              minLines: 2,
              decoration: const InputDecoration(hintText: 'Observaciones generales (opcional)'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Grado 0–3 (movilidad, furca); tocar el elegido lo quita.
class _Grado extends StatelessWidget {
  const _Grado(this.titulo, this.valor, this.alCambiar);

  final String titulo;
  final int? valor;
  final ValueChanged<int?> alCambiar;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(titulo, style: Theme.of(context).textTheme.labelMedium),
        const SizedBox(height: 6),
        Row(
          children: [
            for (var g = 0; g <= 3; g++)
              Expanded(
                child: GestureDetector(
                  onTap: () => alCambiar(valor == g ? null : g),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 160),
                    height: 36,
                    margin: const EdgeInsets.only(right: 4),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: valor == g ? scheme.primary : scheme.surface,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: valor == g ? scheme.primary : scheme.outline),
                    ),
                    child: Text(
                      '$g',
                      style: TextStyle(fontWeight: FontWeight.w700, color: valor == g ? scheme.onPrimary : null),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _EditorSitio extends StatelessWidget {
  const _EditorSitio({required this.nombre, required this.sitio, required this.alCambiar});

  final String nombre;
  final _Sitio sitio;
  final VoidCallback alCambiar;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    Widget marca(String t, bool v, Color c, ValueChanged<bool> f) => GestureDetector(
      onTap: () {
        f(!v);
        alCambiar();
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: 26,
        height: 26,
        margin: const EdgeInsets.symmetric(horizontal: 1.5),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: v ? c : Colors.transparent,
          shape: BoxShape.circle,
          border: Border.all(color: v ? c : tinta.withValues(alpha: 0.2)),
        ),
        child: Text(t, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: v ? Colors.white : tinta.withValues(alpha: 0.55))),
      ),
    );

    return Column(
      children: [
        Text(nombre, style: Theme.of(context).textTheme.labelMedium),
        const SizedBox(height: 4),
        _Paso(
          etiqueta: 'Sondaje',
          valor: sitio.sondaje,
          min: 0,
          max: 15,
          color: colorBolsa(sitio.sondaje),
          alCambiar: (v) {
            sitio.sondaje = v;
            alCambiar();
          },
        ),
        const SizedBox(height: 6),
        _Paso(
          etiqueta: 'Recesión',
          valor: sitio.recesion,
          min: -10,
          max: 20,
          alCambiar: (v) {
            sitio.recesion = v;
            alCambiar();
          },
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            marca('S', sitio.sangrado, Tonos.rojo, (v) => sitio.sangrado = v),
            marca('P', sitio.placa, Tonos.azul, (v) => sitio.placa = v),
            marca('Su', sitio.supuracion, Tonos.ambar, (v) => sitio.supuracion = v),
          ],
        ),
      ],
    );
  }
}

/// Número con − y +. Vacío = no medido; el primer toque lo pone en 0… o en
/// 2 mm para el sondaje, que es la lectura más común.
class _Paso extends StatelessWidget {
  const _Paso({
    required this.etiqueta,
    required this.valor,
    required this.min,
    required this.max,
    required this.alCambiar,
    this.color,
  });

  final String etiqueta;
  final int? valor;
  final int min;
  final int max;
  final ValueChanged<int?> alCambiar;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final tinta = Theme.of(context).colorScheme.onSurface;
    final inicio = etiqueta == 'Sondaje' ? 2 : 0;
    Widget boton(IconData i, VoidCallback? f) => SizedBox(
      width: 28,
      height: 28,
      child: IconButton(
        padding: EdgeInsets.zero,
        iconSize: 16,
        onPressed: f,
        icon: Icon(i),
      ),
    );
    return Column(
      children: [
        Text(etiqueta, style: TextStyle(fontSize: 10, color: tinta.withValues(alpha: 0.5))),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            boton(Icons.remove, valor == null ? null : () => alCambiar(valor! <= min ? null : valor! - 1)),
            GestureDetector(
              onLongPress: () => alCambiar(null),
              child: SizedBox(
                width: 26,
                child: Text(
                  valor == null ? '—' : '$valor',
                  textAlign: TextAlign.center,
                  style: estiloTitulo(17, color: valor == null ? tinta.withValues(alpha: 0.35) : (color ?? tinta), peso: FontWeight.w800),
                ),
              ),
            ),
            boton(Icons.add, () => alCambiar(valor == null ? inicio : (valor! >= max ? max : valor! + 1))),
          ],
        ),
      ],
    );
  }
}

/// Permiso para registrar exámenes (para el botón flotante de la ficha).
bool puedeRegistrarPerio(WidgetRef ref) =>
    ref.read(authProvider).usuario?.puede('periodontogram:write') ?? false;
