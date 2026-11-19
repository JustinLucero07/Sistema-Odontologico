import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../core/api/repositorios.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../pacientes/paciente_detalle_page.dart';

// ---------------------------------------------------------------------------
// Catálogos (mismos códigos que la web y el servidor)
// ---------------------------------------------------------------------------

const estadosOrto = <Opcion>[
  ('activo', 'Activo'),
  ('retencion', 'En retención'),
  ('pausa', 'En pausa'),
  ('finalizado', 'Finalizado'),
  ('abandono', 'Abandonó'),
];
const tadsOrto = <Opcion>[('por_confirmar', 'Por confirmar'), ('si', 'Sí'), ('no', 'No')];
const docsEstados = <Opcion>[
  ('por_revisar', 'Por revisar'),
  ('pendiente', 'Pendiente'),
  ('listo', 'Listo'),
  ('no_requiere', 'No requiere'),
];
const docsCampos = <(String, String, IconData)>[
  ('doc_xrays', 'Radiografías', Icons.filter_b_and_w),
  ('doc_photos', 'Fotografías', Icons.photo_camera_outlined),
  ('doc_models', 'Modelos', Icons.view_in_ar_outlined),
  ('doc_folder', 'Carpeta clínica', Icons.folder_shared_outlined),
];
const _estadoCuota = <Opcion>[
  ('pendiente', 'Pendiente'),
  ('parcial', 'Parcial'),
  ('pagada', 'Pagada'),
  ('vencida', 'Vencida'),
  ('sin_valor', 'Sin valor'),
];
const _abiertos = {'activo', 'retencion', 'pausa'};

Color colorEstadoOrto(String? e) => switch (e) {
  'activo' => Tonos.verde,
  'retencion' || 'pausa' => Tonos.ambar,
  'abandono' => Tonos.rojo,
  _ => Tonos.gris,
};

Color _colorCuota(String? e) => switch (e) {
  'pagada' => Tonos.verde,
  'parcial' => Tonos.azul,
  'vencida' => Tonos.rojo,
  'pendiente' => Tonos.ambar,
  _ => Tonos.gris,
};

Color _colorDoc(String? e) => switch (e) {
  'listo' || 'no_requiere' => Tonos.verde,
  'pendiente' => Tonos.ambar,
  _ => Tonos.gris,
};

String _dos(dynamic n) => '${n ?? 0}'.padLeft(2, '0');

// ---------------------------------------------------------------------------
// Datos
// ---------------------------------------------------------------------------

/// Filtros de la lista: código → valor (null = todos).
final _filtrosProvider = StateProvider.autoDispose<Map<String, String?>>(
  (ref) => {'status': 'abiertos'},
);
final _buscarOrtoProvider = StateProvider.autoDispose<String>((ref) => '');

final _listaOrtoProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) {
  final f = ref.watch(_filtrosProvider);
  final q = ref.watch(_buscarOrtoProvider);
  return ref.watch(apiProvider).mapa('/orthodontics/cases', query: {...f, 'q': q});
});

final fichasOrtoPacienteProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
  (ref, pacienteId) => ref.watch(apiProvider).lista('/patients/$pacienteId/orthodontics'),
);

final fichaOrtoProvider = FutureProvider.autoDispose.family<Map<String, dynamic>, String>(
  (ref, id) => ref.watch(apiProvider).mapa('/orthodontics/cases/$id'),
);

/// Ficha elegida en la pestaña del paciente (si tiene varias).
final _fichaElegidaProvider = StateProvider.autoDispose.family<String?, String>((ref, _) => null);

void _refrescar(WidgetRef ref, {String? pacienteId, String? fichaId}) {
  if (pacienteId != null) ref.invalidate(fichasOrtoPacienteProvider(pacienteId));
  if (fichaId != null) ref.invalidate(fichaOrtoProvider(fichaId));
  ref.invalidate(_listaOrtoProvider);
}

// ---------------------------------------------------------------------------
// Lista: Pacientes de ortodoncia
// ---------------------------------------------------------------------------

class OrtodonciaPage extends ConsumerStatefulWidget {
  const OrtodonciaPage({super.key});

  @override
  ConsumerState<OrtodonciaPage> createState() => _OrtodonciaPageState();
}

class _OrtodonciaPageState extends ConsumerState<OrtodonciaPage> {
  final _buscar = TextEditingController();

  @override
  void dispose() {
    _buscar.dispose();
    super.dispose();
  }

  void _filtro(String clave, String? valor) {
    final f = {...ref.read(_filtrosProvider)};
    f[clave] = f[clave] == valor ? null : valor;
    ref.read(_filtrosProvider.notifier).state = f;
  }

  Widget _chip(String clave, String? valor, String texto) {
    final f = ref.watch(_filtrosProvider);
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(texto),
        selected: f[clave] == valor,
        onSelected: (_) => _filtro(clave, valor),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final puede = ref.watch(authProvider).usuario?.puede('orthodontics:write') ?? false;
    final lista = ref.watch(_listaOrtoProvider);
    return PaginaModulo(
      titulo: 'Ortodoncia',
      accion: puede
          ? FloatingActionButton.extended(
              heroTag: 'fab-orto',
              onPressed: () async {
                final id = await nuevaFichaOrto(context, ref);
                if (id != null) _refrescar(ref);
              },
              icon: const Icon(Icons.add),
              label: const Text('Nueva ficha'),
            )
          : null,
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_listaOrtoProvider),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: _buscar,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Nombre, cédula o ficha (ORT-0001)',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _buscar.text.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () {
                          _buscar.clear();
                          ref.read(_buscarOrtoProvider.notifier).state = '';
                          setState(() {});
                        },
                      ),
              ),
              onChanged: (_) => setState(() {}),
              onSubmitted: (t) => ref.read(_buscarOrtoProvider.notifier).state = t.trim(),
            ),
            const SizedBox(height: 10),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _chip('status', 'abiertos', 'En tratamiento'),
                  _chip('status', 'cerrados', 'Cerrados'),
                  _chip('next_control', 'vencido', 'Control atrasado'),
                  _chip('next_control', 'semana', 'Esta semana'),
                  _chip('next_control', 'sin_fecha', 'Sin fecha'),
                  _chip('next_control', 'con_saldo', 'Con saldo'),
                  _chip('docs', 'pendiente', 'Documentos pendientes'),
                  _chip('has_tad', 'si', 'Con TAD'),
                  _chip('special_attention', 'true', 'Atención especial'),
                  _chip('needs_review', 'true', 'Requieren revisión'),
                ],
              ),
            ),
            const SizedBox(height: 12),
            lista.when(
              loading: () => const EsqueletoLista(filas: 5, dentroDeLista: true),
              error: (e, _) => EstadoError(
                mensaje: e is ErrorApi ? e.mensaje : 'No se pudo cargar la lista.',
                onReintentar: () => ref.invalidate(_listaOrtoProvider),
              ),
              data: (d) {
                final items = (d['items'] as List? ?? []).cast<Map<String, dynamic>>();
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        Pastilla('${d['active']} en tratamiento', color: Tonos.verde),
                        Pastilla('${d['inactive']} cerrados', color: Tonos.gris),
                        Pastilla('${items.length} coincidencias'),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (items.isEmpty)
                      EstadoVacio(
                        icono: Icons.sentiment_very_satisfied_outlined,
                        titulo: (d['total'] ?? 0) == 0
                            ? 'Aún no hay fichas de ortodoncia'
                            : 'Nadie coincide con los filtros',
                        detalle: (d['total'] ?? 0) == 0
                            ? 'Crea la ficha desde aquí o desde la pestaña Ortodoncia del paciente.'
                            : null,
                      )
                    else
                      for (final c in items) _FilaOrto(c),
                  ],
                );
              },
            ),
            finDeLista,
          ],
        ),
      ),
    );
  }
}

class _FilaOrto extends ConsumerWidget {
  const _FilaOrto(this.c);
  final Map<String, dynamic> c;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final p = (c['patient'] as Map).cast<String, dynamic>();
    final nombre = '${p['first_name']} ${p['last_name']}';
    final proximo = c['next_control_on'] == null
        ? 'Sin fecha'
        : '${fechaCorta(c['next_control_on'])}${c['next_control_overdue'] == true ? ' · atrasado' : ''}';
    final saldo = numero(c['balance']);
    return FilaTarjeta(
      icono: Icons.sentiment_very_satisfied_outlined,
      colorIcono: colorEstadoOrto(c['status'] as String?),
      titulo: nombre,
      subtitulo: [
        '${c['code']} · ${etiquetaDe(estadosOrto, c['status'])}',
        if (c['stage'] != null) '${c['stage']}',
        'Próximo control: $proximo',
        if ((c['docs_pending'] ?? 0) > 0) '${c['docs_pending']} documento(s) por revisar',
      ].join('\n'),
      derecha: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            dinero(saldo),
            style: TextStyle(fontWeight: FontWeight.w700, color: saldo > 0 ? Tonos.rojo : null),
          ),
          const SizedBox(height: 4),
          if (c['next_control_overdue'] == true)
            const Pastilla('Atrasado', color: Tonos.rojo)
          else if (c['has_tad'] == 'si')
            const Pastilla('TAD', color: Tonos.azul),
        ],
      ),
      alTocar: () => Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => PacienteDetallePage(pacienteId: '${p['id']}', nombre: nombre, abrirOrtodoncia: true),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Pestaña Ortodoncia dentro de la ficha del paciente
// ---------------------------------------------------------------------------

class PestanaOrtodoncia extends ConsumerWidget {
  const PestanaOrtodoncia({super.key, required this.pacienteId, required this.nombre});

  final String pacienteId;
  final String nombre;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(authProvider).usuario;
    final puede = usuario?.puede('orthodontics:write') ?? false;
    return ref
        .watch(fichasOrtoPacienteProvider(pacienteId))
        .when(
          loading: () => const EsqueletoLista(filas: 4, conTarjetas: true),
          error: (e, _) => EstadoError(
            mensaje: e is ErrorApi ? e.mensaje : 'No se pudo cargar la ortodoncia.',
            onReintentar: () => ref.invalidate(fichasOrtoPacienteProvider(pacienteId)),
          ),
          data: (fichas) {
            if (fichas.isEmpty) {
              return EstadoVacio(
                icono: Icons.sentiment_very_satisfied_outlined,
                titulo: 'Sin ficha de ortodoncia',
                detalle: 'Crea la ficha para llevar el plan de controles, las cuotas y la documentación.',
                accion: puede
                    ? FilledButton.icon(
                        onPressed: () async {
                          final id = await nuevaFichaOrto(context, ref, pacienteId: pacienteId, nombre: nombre);
                          if (id != null) _refrescar(ref, pacienteId: pacienteId);
                        },
                        icon: const Icon(Icons.add),
                        label: const Text('Crear ficha'),
                      )
                    : null,
              );
            }
            final elegida = ref.watch(_fichaElegidaProvider(pacienteId));
            final id = (fichas.where((f) => f['id'] == elegida).firstOrNull ??
                    fichas.where((f) => _abiertos.contains(f['status'])).firstOrNull ??
                    fichas.last)['id']
                as String;
            return _DetalleFicha(pacienteId: pacienteId, nombre: nombre, fichaId: id, todas: fichas);
          },
        );
  }
}

class _DetalleFicha extends ConsumerStatefulWidget {
  const _DetalleFicha({required this.pacienteId, required this.nombre, required this.fichaId, required this.todas});

  final String pacienteId;
  final String nombre;
  final String fichaId;
  final List<Map<String, dynamic>> todas;

  @override
  ConsumerState<_DetalleFicha> createState() => _DetalleFichaState();
}

class _DetalleFichaState extends ConsumerState<_DetalleFicha> {
  String _filtro = 'todas';
  final _abiertas = <String>{};

  void _ref() => _refrescar(ref, pacienteId: widget.pacienteId, fichaId: widget.fichaId);

  @override
  Widget build(BuildContext context) {
    final u = ref.watch(authProvider).usuario;
    final puede = u?.puede('orthodontics:write') ?? false;
    final cobra = u?.puede('payments:write') ?? false;
    final scheme = Theme.of(context).colorScheme;

    return Asincrono(
      valor: ref.watch(fichaOrtoProvider(widget.fichaId)),
      alReintentar: () => ref.invalidate(fichaOrtoProvider(widget.fichaId)),
      esqueleto: const EsqueletoLista(filas: 5, conTarjetas: true),
      listo: (c) {
        final controles = (c['controls'] as List? ?? []).cast<Map<String, dynamic>>();
        final visibles = switch (_filtro) {
          'pagadas' => controles.where((x) => x['status'] == 'pagada').toList(),
          'pendientes' => controles.where((x) => x['status'] != 'pagada').toList(),
          _ => controles,
        };
        final diferencia = numero(c['difference']);
        final valor = numero(c['agreed_total']);
        final notas = (c['doc_notes'] as Map? ?? {}).cast<String, dynamic>();

        return RefreshIndicator(
          onRefresh: () async => _ref(),
          child: ListView(
            padding: EdgeInsets.fromLTRB(16, 8, 16, 110 + MediaQuery.paddingOf(context).bottom),
            children: [
              // ---- Cabecera ----
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${c['code']} · Ortodoncia',
                                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                                const SizedBox(height: 2),
                                Text(
                                  [
                                    c['stage'] ?? 'Etapa sin definir',
                                    if (c['appliance'] != null) c['appliance'],
                                    if (c['professional_name'] != null) c['professional_name'],
                                    if (c['started_on'] != null) 'desde ${fechaCorta(c['started_on'])}',
                                  ].join(' · '),
                                  style: TextStyle(fontSize: 12.5, color: scheme.onSurfaceVariant),
                                ),
                              ],
                            ),
                          ),
                          PopupMenuButton<String>(
                            onSelected: (v) async {
                              switch (v) {
                                case 'pdf':
                                  await _exportar(context, ref, c, 'pdf');
                                case 'csv':
                                  await _exportar(context, ref, c, 'csv');
                                case 'editar':
                                  if (await editarFichaOrto(context, ref, c)) _ref();
                                case 'nueva':
                                  final id = await nuevaFichaOrto(context, ref,
                                      pacienteId: widget.pacienteId, nombre: widget.nombre);
                                  if (id != null) {
                                    ref.read(_fichaElegidaProvider(widget.pacienteId).notifier).state = id;
                                    _ref();
                                  }
                                case 'eliminar':
                                  if (await _eliminarFicha(context, ref, c)) {
                                    ref.read(_fichaElegidaProvider(widget.pacienteId).notifier).state = null;
                                    _refrescar(ref, pacienteId: widget.pacienteId);
                                  }
                                default:
                                  if (v.startsWith('ver:')) {
                                    ref.read(_fichaElegidaProvider(widget.pacienteId).notifier).state = v.substring(4);
                                  }
                              }
                            },
                            itemBuilder: (_) => [
                              const PopupMenuItem(value: 'pdf', child: Text('Imprimir / PDF')),
                              const PopupMenuItem(value: 'csv', child: Text('Exportar a Excel')),
                              if (puede) const PopupMenuItem(value: 'editar', child: Text('Editar ficha')),
                              if (puede && !_abiertos.contains(c['status']))
                                const PopupMenuItem(value: 'nueva', child: Text('Nueva ficha (tratamiento nuevo)')),
                              for (final f in widget.todas.where((f) => f['id'] != c['id']))
                                PopupMenuItem(
                                  value: 'ver:${f['id']}',
                                  child: Text('Ver ${f['code']} · ${etiquetaDe(estadosOrto, f['status'])}'),
                                ),
                              if (puede) const PopupMenuItem(value: 'eliminar', child: Text('Eliminar ficha')),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          Pastilla(etiquetaDe(estadosOrto, c['status']), color: colorEstadoOrto(c['status'] as String?)),
                          Pastilla('TAD: ${etiquetaDe(tadsOrto, c['has_tad'])}',
                              color: c['has_tad'] == 'si' ? Tonos.azul : Tonos.gris),
                          if (c['needs_review'] == true) const Pastilla('Requiere revisión', color: Tonos.ambar),
                          if (c['special_attention'] == true)
                            Pastilla('Atención especial${c['special_attention_note'] != null ? ': ${c['special_attention_note']}' : ''}',
                                color: Tonos.rojo),
                          if ((c['docs_pending'] ?? 0) > 0)
                            Pastilla('${c['docs_pending']} documento(s) por revisar', color: Tonos.ambar),
                        ],
                      ),
                      if (puede) ...[
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          onPressed: () async {
                            if (await _seguimiento(context, ref, c)) _ref();
                          },
                          icon: const Icon(Icons.tune, size: 18),
                          label: const Text('Estado, TAD y revisión'),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // ---- Panel de pagos ----
              RejillaKpi(
                hijos: [
                  Kpi(etiqueta: 'Valor del tratamiento', valor: dinero(valor), icono: Icons.sell_outlined),
                  Kpi(etiqueta: 'Recibido', valor: dinero(numero(c['paid'])), icono: Icons.savings_outlined, color: Tonos.verde),
                  Kpi(
                    etiqueta: 'Saldo',
                    valor: dinero(numero(c['balance'])),
                    icono: Icons.account_balance_wallet_outlined,
                    color: numero(c['balance']) > 0 ? Tonos.rojo : Tonos.verde,
                  ),
                  Kpi(
                    etiqueta: 'Cuotas pagadas',
                    valor: '${c['controls_paid']} / ${c['controls_count']}',
                    icono: Icons.event_available,
                  ),
                ],
              ),
              if (valor == 0)
                _Aviso(
                  icono: Icons.info_outline,
                  texto: 'Defina el valor del tratamiento para poder registrar abonos.',
                  accion: puede ? 'Definir valor' : null,
                  alTocar: () async {
                    if (await editarFichaOrto(context, ref, c)) _ref();
                  },
                )
              else if (controles.isNotEmpty && diferencia != 0)
                _Aviso(
                  icono: diferencia > 0 ? Icons.trending_up : Icons.trending_down,
                  texto:
                      'Las cuotas suman ${dinero(diferencia.abs())} ${diferencia > 0 ? 'por encima' : 'por debajo'} del valor acordado.',
                  accion: puede ? 'Revisar valor' : null,
                  alTocar: () async {
                    if (await editarFichaOrto(context, ref, c)) _ref();
                  },
                ),

              // ---- Documentación ----
              Seccion(
                'Documentación',
                accion: puede
                    ? TextButton(
                        onPressed: () async {
                          if (await _documentacion(context, ref, c)) _ref();
                        },
                        child: const Text('Editar'),
                      )
                    : null,
              ),
              GlassCard(
                child: Column(
                  children: [
                    for (final (campo, etiqueta, icono) in docsCampos)
                      ListTile(
                        dense: true,
                        leading: Icon(icono, color: scheme.primary),
                        title: Text(etiqueta, style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: notas[campo] == null ? null : Text('${notas[campo]}'),
                        trailing: Pastilla(etiquetaDe(docsEstados, c[campo]), color: _colorDoc(c[campo] as String?)),
                      ),
                  ],
                ),
              ),

              // ---- Plan de controles y cuotas ----
              Seccion(
                'Plan de controles y cuotas',
                accion: puede
                    ? TextButton.icon(
                        onPressed: () async {
                          if (await agregarCuotasOrto(context, ref, c)) _ref();
                        },
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Agregar cuotas'),
                      )
                    : null,
              ),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  for (final (codigo, texto) in const [('todas', 'Todas'), ('pendientes', 'Pendientes'), ('pagadas', 'Pagadas')])
                    Padding(
                      padding: EdgeInsets.zero,
                      child: ChoiceChip(
                        label: Text(texto),
                        selected: _filtro == codigo,
                        onSelected: (_) => setState(() => _filtro = codigo),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              if (controles.isEmpty)
                const EstadoVacio(
                  icono: Icons.event_note_outlined,
                  titulo: 'Sin cuotas todavía',
                  detalle: 'Agrega el plan completo de una vez (por ejemplo 24 cuotas mensuales) y luego registra cada control.',
                )
              else
                for (final ctrl in visibles)
                  _TarjetaCuota(
                    ctrl: ctrl,
                    abierta: _abiertas.contains(ctrl['id']),
                    alAlternar: () => setState(() {
                      final id = '${ctrl['id']}';
                      _abiertas.contains(id) ? _abiertas.remove(id) : _abiertas.add(id);
                    }),
                    puede: puede,
                    cobra: cobra && c['charge_id'] != null,
                    alEditar: () async {
                      if (await _editarCuota(context, ref, ctrl)) _ref();
                    },
                    alAbonar: () async {
                      if (await _abonar(context, ref, c, ctrl)) _ref();
                    },
                    alEliminar: () async {
                      if (await _eliminarCuota(context, ref, ctrl)) _ref();
                    },
                    alAnular: (pagoId) async {
                      await anularConMotivo(
                        context,
                        que: 'abono',
                        alAnular: (motivo) async {
                          await ref.read(apiProvider).post('/finance/payments/$pagoId/void', {'reason': motivo});
                          _ref();
                        },
                      );
                    },
                  ),
              if ('${c['notes'] ?? ''}'.isNotEmpty) ...[
                const Seccion('Notas'),
                GlassCard(child: Padding(padding: const EdgeInsets.all(14), child: Text('${c['notes']}'))),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.icono, required this.texto, this.accion, this.alTocar});
  final IconData icono;
  final String texto;
  final String? accion;
  final VoidCallback? alTocar;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
        decoration: BoxDecoration(
          color: Tonos.ambar.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Icon(icono, color: Tonos.ambar, size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(texto, style: const TextStyle(fontSize: 13))),
            if (accion != null) TextButton(onPressed: alTocar, child: Text(accion!)),
          ],
        ),
      ),
    );
  }
}

class _TarjetaCuota extends StatelessWidget {
  const _TarjetaCuota({
    required this.ctrl,
    required this.abierta,
    required this.alAlternar,
    required this.puede,
    required this.cobra,
    required this.alEditar,
    required this.alAbonar,
    required this.alEliminar,
    required this.alAnular,
  });

  final Map<String, dynamic> ctrl;
  final bool abierta;
  final VoidCallback alAlternar;
  final bool puede;
  final bool cobra;
  final VoidCallback alEditar;
  final VoidCallback alAbonar;
  final VoidCallback alEliminar;
  final void Function(String pagoId) alAnular;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final pagos = (ctrl['payments'] as List? ?? []).cast<Map<String, dynamic>>();
    final saldo = numero(ctrl['balance']);
    final clinico = [
      ('Planificación', ctrl['planning']),
      ('Arcos', ctrl['arches']),
      ('Elásticos', ctrl['elastics']),
      ('TADs', ctrl['tads']),
    ].where((e) => e.$2 != null && '${e.$2}'.isNotEmpty);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GlassCard(
        onTap: puede ? alEditar : null,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 6, 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(_dos(ctrl['number']), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                  const SizedBox(width: 10),
                  Pastilla(etiquetaDe(_estadoCuota, ctrl['status']), color: _colorCuota(ctrl['status'] as String?)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(dinero(numero(ctrl['amount'])), style: const TextStyle(fontWeight: FontWeight.w700)),
                        Text(
                          saldo > 0 ? 'Saldo ${dinero(saldo)}' : 'Abonado ${dinero(numero(ctrl['paid']))}',
                          textAlign: TextAlign.end,
                          style: TextStyle(fontSize: 12, color: saldo > 0 ? Tonos.rojo : Tonos.verde),
                        ),
                      ],
                    ),
                  ),
                  if (puede)
                    PopupMenuButton<String>(
                      onSelected: (v) => v == 'editar' ? alEditar() : alEliminar(),
                      itemBuilder: (_) => const [
                        PopupMenuItem(value: 'editar', child: Text('Registrar control / editar')),
                        PopupMenuItem(value: 'eliminar', child: Text('Eliminar cuota')),
                      ],
                    )
                  else
                    const SizedBox(width: 8),
                ],
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 12,
                runSpacing: 4,
                children: [
                  _dato(Icons.event_outlined, 'Control ${ctrl['planned_on'] == null ? 'sin fecha' : fechaCorta(ctrl['planned_on'])}'),
                  _dato(
                    ctrl['attended_on'] == null ? Icons.radio_button_unchecked : Icons.check_circle,
                    ctrl['attended_on'] == null ? 'Sin asistencia' : 'Asistió ${fechaCorta(ctrl['attended_on'])}',
                    color: ctrl['attended_on'] == null ? null : Tonos.verde,
                  ),
                  if (ctrl['due_on'] != null) _dato(Icons.schedule, 'Vence ${fechaCorta(ctrl['due_on'])}'),
                ],
              ),
              if (clinico.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (final (et, v) in clinico)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 2, right: 8),
                    child: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(text: '$et: ', style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 12.5)),
                          TextSpan(text: '$v'.toUpperCase(), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
                        ],
                      ),
                    ),
                  ),
              ],
              if (cobra && saldo > 0 || pagos.isNotEmpty)
                Row(
                  children: [
                    if (pagos.isNotEmpty)
                      TextButton(
                        onPressed: alAlternar,
                        child: Text('${pagos.where((p) => p['voided_at'] == null).length} abono(s) ${abierta ? '▴' : '▾'}'),
                      ),
                    const Spacer(),
                    if (cobra && saldo > 0)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilledButton.tonalIcon(
                          onPressed: alAbonar,
                          icon: const Icon(Icons.payments_outlined, size: 18),
                          label: const Text('Abonar'),
                        ),
                      ),
                  ],
                ),
              if (abierta)
                for (final p in pagos)
                  Padding(
                    padding: const EdgeInsets.only(right: 8, bottom: 4),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${fechaCorta(p['received_on'])} · ${dinero(numero(p['amount']))} · ${p['method']}'
                            '${p['reference'] != null ? ' · ${p['reference']}' : ''}',
                            style: TextStyle(
                              fontSize: 12.5,
                              decoration: p['voided_at'] != null ? TextDecoration.lineThrough : null,
                            ),
                          ),
                        ),
                        if (p['voided_at'] != null)
                          const Pastilla('Anulado', color: Tonos.rojo)
                        else if (cobra)
                          TextButton(
                            onPressed: () => alAnular('${p['id']}'),
                            style: TextButton.styleFrom(foregroundColor: Tonos.rojo),
                            child: const Text('Anular'),
                          ),
                      ],
                    ),
                  ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _dato(IconData i, String t, {Color? color}) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(i, size: 15, color: color),
      const SizedBox(width: 4),
      Text(t, style: TextStyle(fontSize: 12.5, color: color)),
    ],
  );
}

// ---------------------------------------------------------------------------
// Acciones (todas en ventana emergente)
// ---------------------------------------------------------------------------

Future<List<Opcion>> _profesionales(WidgetRef ref) async {
  try {
    final l = await ref.read(apiProvider).lista('/clinics/professionals');
    return [
      for (final p in l)
        if (p['is_active'] != false) ('${p['id']}', '${p['first_name']} ${p['last_name']}'),
    ];
  } catch (_) {
    return [];
  }
}

List<Campo> _camposFicha(Map<String, dynamic>? c, List<Opcion> profesionales) => [
  if (c != null)
    Campo('status', 'Estado de ortodoncia', tipo: TipoCampo.seleccion, opciones: estadosOrto, inicial: c['status'], requerido: true),
  Campo('stage', 'Etapa del tratamiento', inicial: c?['stage'], ayuda: 'Ej.: Alineación y nivelación'),
  Campo('appliance', 'Aparatología', inicial: c?['appliance'], ayuda: 'Ej.: Brackets metálicos, alineadores…'),
  Campo('has_tad', '¿Tiene TAD actualmente?', tipo: TipoCampo.seleccion, opciones: tadsOrto,
      inicial: c?['has_tad'] ?? 'por_confirmar', requerido: true, mitad: true),
  Campo('professional_id', 'Ortodoncista', tipo: TipoCampo.seleccion, opciones: profesionales,
      inicial: c?['professional_id'], mitad: true),
  Campo('started_on', 'Fecha de inicio', tipo: TipoCampo.fecha, inicial: c?['started_on'] ?? (c == null ? hoyIso() : null), mitad: true),
  Campo('estimated_months', 'Duración (meses)', tipo: TipoCampo.entero, inicial: c?['estimated_months'], mitad: true),
  Campo('agreed_total', 'Valor del tratamiento', tipo: TipoCampo.dinero,
      inicial: c == null ? null : numero(c['agreed_total']).toStringAsFixed(2), ayuda: 'Se carga a la cuenta del paciente'),
  Campo('special_attention', 'Atención especial', tipo: TipoCampo.interruptor, inicial: c?['special_attention'] == true),
  Campo('special_attention_note', '¿Por qué? (si requiere atención especial)', inicial: c?['special_attention_note']),
  Campo('needs_review', 'Consultar / requiere revisión', tipo: TipoCampo.interruptor, inicial: c?['needs_review'] == true),
  Campo('notes', 'Notas', tipo: TipoCampo.multilinea, inicial: c?['notes']),
];

Map<String, dynamic> _limpiarFicha(Map<String, dynamic> v) => {
  ...v,
  'agreed_total': v['agreed_total'] ?? '0',
  'special_attention_note': v['special_attention'] == true ? v['special_attention_note'] : null,
};

/// Crea una ficha. Sin [pacienteId] primero pide elegir al paciente.
Future<String?> nuevaFichaOrto(BuildContext context, WidgetRef ref, {String? pacienteId, String? nombre}) async {
  var id = pacienteId;
  var quien = nombre;
  if (id == null) {
    final elegido = await elegirConBusqueda(
      context,
      titulo: 'Paciente',
      buscar: (t) async {
        final r = await ref.read(apiProvider).lista('/patients', query: {'search': t, 'limit': 20});
        return [for (final p in r) ('${p['id']}', '${p['first_name']} ${p['last_name']}')];
      },
    );
    if (elegido == null) return null;
    id = elegido.$1;
    quien = elegido.$2;
  }
  final profesionales = await _profesionales(ref);
  if (!context.mounted) return null;
  String? creada;
  await mostrarFormulario(
    context,
    titulo: 'Nueva ficha de ortodoncia',
    subtitulo: quien,
    icono: Icons.sentiment_very_satisfied_outlined,
    textoGuardar: 'Crear ficha',
    campos: _camposFicha(null, profesionales),
    alGuardar: (v) async {
      final r = await ref.read(apiProvider).post('/orthodontics/cases', {'patient_id': id, ..._limpiarFicha(v)});
      creada = '${(r as Map)['id']}';
    },
  );
  if (creada != null && context.mounted) avisar(context, 'Ficha creada.');
  return creada;
}

Future<bool> editarFichaOrto(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
  final profesionales = await _profesionales(ref);
  if (!context.mounted) return false;
  final r = await mostrarFormulario(
    context,
    titulo: 'Editar ${c['code']}',
    icono: Icons.edit_outlined,
    campos: _camposFicha(c, profesionales),
    alGuardar: (v) async => ref.read(apiProvider).patch('/orthodontics/cases/${c['id']}', _limpiarFicha(v)),
  );
  return r != null;
}

Future<bool> _seguimiento(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
  final r = await mostrarFormulario(
    context,
    titulo: 'Seguimiento',
    subtitulo: '${c['code']}',
    icono: Icons.tune,
    campos: [
      Campo('status', 'Estado de ortodoncia', tipo: TipoCampo.seleccion, opciones: estadosOrto, inicial: c['status'], requerido: true),
      Campo('has_tad', '¿Tiene TAD actualmente?', tipo: TipoCampo.seleccion, opciones: tadsOrto, inicial: c['has_tad'], requerido: true),
      Campo('needs_review', 'Consultar / requiere revisión', tipo: TipoCampo.interruptor, inicial: c['needs_review'] == true),
    ],
    alGuardar: (v) async => ref.read(apiProvider).patch('/orthodontics/cases/${c['id']}', v),
  );
  return r != null;
}

Future<bool> _documentacion(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
  final notas = (c['doc_notes'] as Map? ?? {}).cast<String, dynamic>();
  final r = await mostrarFormulario(
    context,
    titulo: 'Documentación',
    subtitulo: '«No requiere» se indica expresamente; lo no confirmado queda «Por revisar».',
    icono: Icons.assignment_outlined,
    campos: [
      for (final (campo, etiqueta, _) in docsCampos) ...[
        Campo(campo, etiqueta, tipo: TipoCampo.seleccion, opciones: docsEstados, inicial: c[campo], requerido: true, seccion: etiqueta),
        Campo('nota_$campo', 'Nota breve', inicial: notas[campo]),
      ],
    ],
    alGuardar: (v) async => ref.read(apiProvider).patch('/orthodontics/cases/${c['id']}', {
      for (final (campo, _, _) in docsCampos) campo: v[campo],
      'doc_notes': {
        for (final (campo, _, _) in docsCampos)
          if ('${v['nota_$campo'] ?? ''}'.trim().isNotEmpty) campo: '${v['nota_$campo']}'.trim(),
      },
    }),
  );
  return r != null;
}

Future<bool> agregarCuotasOrto(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
  final restante = numero(c['agreed_total']) - numero(c['controls_total']);
  final cuotas = (c['estimated_months'] as int?) ?? 12;
  final controles = (c['controls'] as List? ?? []).cast<Map<String, dynamic>>();
  final fechas = controles.map((x) => x['planned_on'] ?? x['due_on']).whereType<String>().toList()..sort();
  var desde = c['started_on'] as String? ?? hoyIso();
  if (fechas.isNotEmpty) {
    final d = DateTime.parse(fechas.last);
    final s = DateTime(d.year, d.month + 1, d.day);
    desde = '${s.year}-${'${s.month}'.padLeft(2, '0')}-${'${s.day}'.padLeft(2, '0')}';
  }
  final r = await mostrarFormulario(
    context,
    titulo: 'Agregar cuotas',
    subtitulo: restante > 0 ? 'Falta por planificar ${dinero(restante)} del valor acordado.' : null,
    icono: Icons.event_note_outlined,
    textoGuardar: 'Agregar',
    campos: [
      Campo('count', 'Número de cuotas', tipo: TipoCampo.entero, inicial: cuotas, requerido: true, mitad: true),
      Campo('amount', 'Valor de cada cuota', tipo: TipoCampo.dinero, requerido: true, mitad: true,
          inicial: restante > 0 ? (restante / cuotas).toStringAsFixed(2) : '0'),
      Campo('first_on', 'Primera fecha', tipo: TipoCampo.fecha, inicial: desde, requerido: true, mitad: true),
      Campo('every_days', 'Frecuencia', tipo: TipoCampo.seleccion, mitad: true, inicial: '0', requerido: true, opciones: const [
        ('0', 'Mensual'),
        ('14', 'Cada 2 semanas'),
        ('21', 'Cada 3 semanas'),
        ('28', 'Cada 4 semanas'),
        ('42', 'Cada 6 semanas'),
      ]),
    ],
    alGuardar: (v) async => ref.read(apiProvider).post('/orthodontics/cases/${c['id']}/controls/generate', {
      'count': v['count'],
      'amount': v['amount'],
      'first_on': v['first_on'],
      'every_days': v['every_days'] == '0' ? null : int.tryParse('${v['every_days']}'),
    }),
  );
  return r != null;
}

Future<bool> _editarCuota(BuildContext context, WidgetRef ref, Map<String, dynamic> ctrl) async {
  final r = await mostrarFormulario(
    context,
    titulo: 'Cuota ${_dos(ctrl['number'])}',
    subtitulo: 'Registro clínico del control y valor de la cuota.',
    icono: Icons.medical_services_outlined,
    campos: [
      Campo('planned_on', 'Fecha planificada', tipo: TipoCampo.fecha, inicial: ctrl['planned_on'], mitad: true),
      Campo('asistio', 'Asistió al control', tipo: TipoCampo.interruptor, inicial: ctrl['attended_on'] != null, mitad: true),
      Campo('planning', 'Planificación', tipo: TipoCampo.multilinea, inicial: ctrl['planning'], seccion: 'Clínico'),
      Campo('arches', 'Arcos', inicial: ctrl['arches'], mitad: true),
      Campo('elastics', 'Elásticos', inicial: ctrl['elastics'], mitad: true),
      Campo('tads', 'TADs', inicial: ctrl['tads']),
      Campo('due_on', 'Vencimiento', tipo: TipoCampo.fecha, inicial: ctrl['due_on'], mitad: true, seccion: 'Cuota'),
      Campo('amount', 'Valor', tipo: TipoCampo.dinero, inicial: numero(ctrl['amount']).toStringAsFixed(2), mitad: true),
    ],
    alGuardar: (v) async {
      final asistio = v.remove('asistio') == true;
      final hoy = hoyIso();
      final plan = v['planned_on'] as String?;
      v['attended_on'] = asistio
          ? (ctrl['attended_on'] ?? (plan != null && plan.compareTo(hoy) <= 0 ? plan : hoy))
          : null;
      v['amount'] = v['amount'] ?? '0';
      await ref.read(apiProvider).patch('/orthodontics/controls/${ctrl['id']}', v);
    },
  );
  return r != null;
}

Future<bool> _abonar(BuildContext context, WidgetRef ref, Map<String, dynamic> c, Map<String, dynamic> ctrl) async {
  final formas = await cargarOAvisar(context, ref.read(formasPagoProvider.future));
  if (formas == null || !context.mounted) return false;
  final p = (c['patient'] as Map).cast<String, dynamic>();
  final r = await mostrarFormulario(
    context,
    titulo: 'Abono a la cuota ${_dos(ctrl['number'])}',
    subtitulo: '${p['first_name']} ${p['last_name']} · saldo de la cuota ${dinero(numero(ctrl['balance']))}',
    icono: Icons.payments_outlined,
    textoGuardar: 'Registrar abono',
    campos: [
      Campo('amount', 'Monto', tipo: TipoCampo.dinero, requerido: true, mitad: true,
          inicial: numero(ctrl['balance']).toStringAsFixed(2)),
      Campo('method', 'Forma de pago', tipo: TipoCampo.seleccion, requerido: true, opciones: formas, inicial: 'efectivo', mitad: true),
      const Campo('reference', 'Referencia (transferencia o tarjeta)'),
      Campo('received_on', 'Fecha', tipo: TipoCampo.fecha, inicial: hoyIso()),
      const Campo('notes', 'Nota (opcional)'),
    ],
    alGuardar: (v) async => ref.read(apiProvider).post('/orthodontics/controls/${ctrl['id']}/payments', v),
  );
  if (r != null && context.mounted) avisar(context, 'Abono registrado.');
  return r != null;
}

Future<bool> _eliminarCuota(BuildContext context, WidgetRef ref, Map<String, dynamic> ctrl) async {
  if (!await confirmar(
    context,
    titulo: '¿Eliminar la cuota ${_dos(ctrl['number'])}?',
    mensaje: 'Las demás se renumeran. Una cuota con abonos no se puede eliminar.',
    textoConfirmar: 'Eliminar',
    peligro: true,
  )) {
    return false;
  }
  if (!context.mounted) return false;
  return intentar(context, () => ref.read(apiProvider).delete('/orthodontics/controls/${ctrl['id']}'));
}

Future<bool> _eliminarFicha(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
  if (!await confirmar(
    context,
    titulo: '¿Eliminar la ficha ${c['code']}?',
    mensaje: 'Se borran la ficha, su plan de cuotas y la documentación. Si ya tiene abonos no se puede: márquela como «Finalizado».',
    textoConfirmar: 'Eliminar',
    peligro: true,
  )) {
    return false;
  }
  if (!context.mounted) return false;
  return intentar(context, () => ref.read(apiProvider).delete('/orthodontics/cases/${c['id']}'), exito: 'Ficha eliminada.');
}

Future<void> _exportar(BuildContext context, WidgetRef ref, Map<String, dynamic> c, String tipo) async {
  final bytes = await cargarOAvisar(context, ref.read(apiProvider).bytes('/orthodontics/cases/${c['id']}/export.$tipo'));
  if (bytes == null) return;
  final dir = await getTemporaryDirectory();
  final archivo = File('${dir.path}/ortodoncia-${c['code']}.$tipo');
  await archivo.writeAsBytes(bytes, flush: true);
  final r = await OpenFilex.open(archivo.path, type: tipo == 'pdf' ? 'application/pdf' : 'text/csv');
  if (r.type != ResultType.done && context.mounted) {
    avisar(context, tipo == 'pdf' ? 'No hay una aplicación para abrir PDF.' : 'No hay una aplicación para abrir hojas de cálculo.');
  }
}

/// Atajo para el botón flotante de la pestaña: crea la ficha si no hay una
/// abierta; si la hay, agrega cuotas.
Future<void> accionOrtodoncia(BuildContext context, WidgetRef ref, String pacienteId, String nombre) async {
  final fichas = await cargarOAvisar(context, ref.read(fichasOrtoPacienteProvider(pacienteId).future));
  if (fichas == null || !context.mounted) return;
  final abierta = fichas.where((f) => _abiertos.contains(f['status'])).firstOrNull;
  if (abierta == null) {
    final id = await nuevaFichaOrto(context, ref, pacienteId: pacienteId, nombre: nombre);
    if (id != null) _refrescar(ref, pacienteId: pacienteId);
    return;
  }
  final c = await cargarOAvisar(context, ref.read(fichaOrtoProvider('${abierta['id']}').future));
  if (c == null || !context.mounted) return;
  if (await agregarCuotasOrto(context, ref, c)) _refrescar(ref, pacienteId: pacienteId, fichaId: '${c['id']}');
}

