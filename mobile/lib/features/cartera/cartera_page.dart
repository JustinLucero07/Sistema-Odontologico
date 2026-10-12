import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/marca/marca.dart';
import '../../shared/contacto.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../pacientes/paciente_detalle_page.dart';

final carteraProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/finance/portfolio'),
);

List<Map<String, dynamic>> _filas(Map<String, dynamic> c, String clave) =>
    ((c[clave] as List?) ?? []).cast<Map<String, dynamic>>();

void _abrirPaciente(BuildContext context, Map<String, dynamic> x) =>
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => PacienteDetallePage(
          pacienteId: '${x['patient_id']}',
          nombre: '${x['patient_name']}',
        ),
      ),
    );

/// Cartera: de un vistazo, quién debe, quién está al día, qué cargos siguen
/// abiertos y qué tratamientos están en curso, de TODOS los pacientes.
class CarteraPage extends ConsumerWidget {
  const CarteraPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 3,
      child: PaginaModulo(
        titulo: 'Cartera',
        inferior: const TabBar(
          tabs: [
            Tab(text: 'Pacientes'),
            Tab(text: 'Cargos'),
            Tab(text: 'Tratamientos'),
          ],
        ),
        cuerpo: Asincrono(
          valor: ref.watch(carteraProvider),
          alReintentar: () => ref.invalidate(carteraProvider),
          esqueleto: const EsqueletoLista(filas: 5, conTarjetas: true),
          listo: (c) => TabBarView(
            children: [_Pacientes(c), _Cargos(c), _Tratamientos(c)],
          ),
        ),
      ),
    );
  }
}

class _Resumen extends StatelessWidget {
  const _Resumen(this.s);

  final Map<String, dynamic> s;

  @override
  Widget build(BuildContext context) {
    final tasa = s['collection_rate'] == null ? null : numero(s['collection_rate']);
    return RejillaKpi(
      hijos: [
        Kpi(
          etiqueta: 'Por cobrar',
          valor: dinero(numero(s['receivable'])),
          icono: Icons.hourglass_bottom,
          color: Tonos.ambar,
        ),
        Kpi(
          etiqueta: 'Cobrado',
          valor: dinero(numero(s['total_paid'])),
          icono: Icons.trending_up,
          color: Tonos.verde,
        ),
        Kpi(
          etiqueta: 'Pacientes que deben',
          valor: '${s['patients_owing']}',
          icono: Icons.person_search_outlined,
          color: Tonos.rojo,
        ),
        Kpi(
          etiqueta: 'Cobranza',
          valor: tasa == null ? '—' : '${(tasa * 100).round()} %',
          icono: Icons.percent,
        ),
      ],
    );
  }
}

/// Fichas de filtro en una fila desplazable.
class _Filtros extends StatelessWidget {
  const _Filtros({required this.opciones, required this.actual, required this.alElegir});

  final List<(String, String, int)> opciones;
  final String actual;
  final ValueChanged<String> alElegir;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 42,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          for (final (v, t, n) in opciones)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text('$t · $n'),
                selected: actual == v,
                onSelected: (_) => alElegir(v),
              ),
            ),
        ],
      ),
    );
  }
}

class _Buscador extends StatelessWidget {
  const _Buscador(this.alCambiar);

  final ValueChanged<String> alCambiar;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: TextField(
      onChanged: alCambiar,
      decoration: const InputDecoration(
        prefixIcon: Icon(Icons.search),
        hintText: 'Buscar paciente…',
        isDense: true,
      ),
    ),
  );
}

class _Pacientes extends ConsumerStatefulWidget {
  const _Pacientes(this.c);

  final Map<String, dynamic> c;

  @override
  ConsumerState<_Pacientes> createState() => _PacientesState();
}

class _PacientesState extends ConsumerState<_Pacientes> {
  String _filtro = 'debe';
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final todos = _filas(widget.c, 'patients');
    int cuenta(String s) => todos.where((p) => p['status'] == s).length;
    final lista = todos
        .where((p) => _filtro == 'todos' || p['status'] == _filtro)
        .where((p) => '${p['patient_name']}'.toLowerCase().contains(_q))
        .toList();
    final consulta = ref.watch(marcaProvider).nombre;
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(carteraProvider),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _Resumen((widget.c['summary'] as Map).cast<String, dynamic>()),
          const SizedBox(height: 12),
          _Filtros(
            opciones: [
              ('debe', 'Deben', cuenta('debe')),
              ('saldado', 'Al día', cuenta('saldado')),
              ('a_favor', 'A favor', cuenta('a_favor')),
              ('todos', 'Todos', todos.length),
            ],
            actual: _filtro,
            alElegir: (v) => setState(() => _filtro = v),
          ),
          const SizedBox(height: 8),
          _Buscador((v) => setState(() => _q = v.trim().toLowerCase())),
          if (lista.isEmpty)
            const EstadoVacio(icono: Icons.check_circle_outline, titulo: 'Nadie en esta lista'),
          for (final p in lista)
            FilaTarjeta(
              icono: p['status'] == 'debe'
                  ? Icons.error_outline
                  : p['status'] == 'a_favor'
                  ? Icons.savings_outlined
                  : Icons.check_circle_outline,
              colorIcono: p['status'] == 'debe'
                  ? Tonos.rojo
                  : p['status'] == 'a_favor'
                  ? Tonos.azul
                  : Tonos.verde,
              titulo: '${p['patient_name']}',
              subtitulo: [
                'Cargado ${dinero(numero(p['total_charged']))}',
                'Pagado ${dinero(numero(p['total_paid']))}',
                if (p['days_pending'] != null) 'hace ${p['days_pending']} días',
                if (p['in_credit'] == true) 'En crédito',
              ].join(' · '),
              alTocar: () => _abrirPaciente(context, p),
              derecha: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    dinero(numero(p['balance']).abs()),
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: p['status'] == 'debe' ? Tonos.rojo : null,
                    ),
                  ),
                  if (p['status'] == 'debe' && p['phone'] != null)
                    IconButton(
                      tooltip: 'Recordar por WhatsApp',
                      icon: const Icon(Icons.chat_outlined, color: Tonos.verde),
                      onPressed: () => abrirWhatsapp(
                        context,
                        '${p['phone']}',
                        'Hola ${'${p['patient_name']}'.split(' ').first}, le saludamos de $consulta. '
                            'Le recordamos que tiene un saldo pendiente de ${dinero(numero(p['balance']))}. '
                            'Puede acercarse cuando guste o escribirnos para coordinar. ¡Gracias!',
                      ),
                    ),
                ],
              ),
            ),
          finDeLista,
        ],
      ),
    );
  }
}

class _Cargos extends ConsumerStatefulWidget {
  const _Cargos(this.c);

  final Map<String, dynamic> c;

  @override
  ConsumerState<_Cargos> createState() => _CargosState();
}

class _CargosState extends ConsumerState<_Cargos> {
  String _filtro = 'abiertos';
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final todos = _filas(widget.c, 'charges');
    bool pasa(Map<String, dynamic> x) => switch (_filtro) {
      'abiertos' => x['status'] != 'pagada',
      'parcial' => x['status'] == 'parcial',
      'pagada' => x['status'] == 'pagada',
      _ => true,
    };
    final lista = todos.where(pasa).where((x) => '${x['patient_name']}'.toLowerCase().contains(_q)).toList();
    final pendiente = lista.fold<double>(0, (a, x) => a + numero(x['pending']));
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(carteraProvider),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _Filtros(
            opciones: [
              ('abiertos', 'Con saldo', todos.where((x) => x['status'] != 'pagada').length),
              ('parcial', 'Con abonos', todos.where((x) => x['status'] == 'parcial').length),
              ('pagada', 'Pagados', todos.where((x) => x['status'] == 'pagada').length),
              ('todos', 'Todos', todos.length),
            ],
            actual: _filtro,
            alElegir: (v) => setState(() => _filtro = v),
          ),
          const SizedBox(height: 8),
          _Buscador((v) => setState(() => _q = v.trim().toLowerCase())),
          if (lista.isNotEmpty && _filtro != 'pagada')
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                '${lista.length} cargos · ${dinero(pendiente)} pendientes',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          if (lista.isEmpty) const EstadoVacio(icono: Icons.receipt_long_outlined, titulo: 'Sin cargos en esta lista'),
          for (final x in lista) _TarjetaCargo(x),
          finDeLista,
        ],
      ),
    );
  }
}

class _TarjetaCargo extends StatelessWidget {
  const _TarjetaCargo(this.x);

  final Map<String, dynamic> x;

  @override
  Widget build(BuildContext context) {
    final monto = numero(x['amount']);
    final pagado = numero(x['paid']);
    final fraccion = monto <= 0 ? 1.0 : (pagado / monto).clamp(0.0, 1.0);
    final color = switch (x['status']) {
      'pagada' => Tonos.verde,
      'parcial' => Tonos.ambar,
      _ => Tonos.rojo,
    };
    final tenue = Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.55);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GlassCard(
        onTap: () => _abrirPaciente(context, x),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text('${x['patient_name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
                  ),
                  Pastilla(
                    switch (x['status']) {
                      'pagada' => 'Pagado',
                      'parcial' => 'Con abonos',
                      _ => 'Pendiente',
                    },
                    color: color,
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                '${x['description']} · ${fechaCorta(x['issued_on'])}${x['in_credit'] == true ? ' · En crédito' : ''}',
                style: TextStyle(fontSize: 12.5, color: tenue),
              ),
              const SizedBox(height: 10),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: fraccion,
                  minHeight: 7,
                  color: color,
                  backgroundColor: color.withValues(alpha: 0.15),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: Text('Abonado ${dinero(pagado)} de ${dinero(monto)}', style: TextStyle(fontSize: 12.5, color: tenue)),
                  ),
                  const SizedBox(width: 8),
                  if (numero(x['pending']) > 0)
                    Text('Debe ${dinero(numero(x['pending']))}',
                        style: const TextStyle(fontWeight: FontWeight.w800, color: Tonos.rojo)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

const _estadosTratamiento = {
  'en_progreso': ('En curso', Tonos.azul),
  'aprobado': ('Aprobado', Tonos.violeta),
  'propuesto': ('Propuesto', Tonos.ambar),
  'completado': ('Terminado', Tonos.verde),
  'cancelado': ('Cancelado', Tonos.gris),
};

class _Tratamientos extends ConsumerStatefulWidget {
  const _Tratamientos(this.c);

  final Map<String, dynamic> c;

  @override
  ConsumerState<_Tratamientos> createState() => _TratamientosState();
}

class _TratamientosState extends ConsumerState<_Tratamientos> {
  String _filtro = 'activos';
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final s = (widget.c['summary'] as Map).cast<String, dynamic>();
    final todos = _filas(widget.c, 'treatments');
    bool activo(Map<String, dynamic> t) => const {'en_progreso', 'aprobado', 'propuesto'}.contains(t['status']);
    final lista = todos
        .where((t) => switch (_filtro) {
          'activos' => activo(t),
          'todos' => true,
          _ => t['status'] == _filtro,
        })
        .where((t) => '${t['patient_name']}'.toLowerCase().contains(_q))
        .toList();
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(carteraProvider),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          RejillaKpi(
            hijos: [
              Kpi(
                etiqueta: 'En curso · ${s['treatments_in_progress']}',
                valor: dinero(numero(s['treatments_in_progress_value'])),
                icono: Icons.healing_outlined,
                color: Tonos.azul,
              ),
              Kpi(
                etiqueta: 'Por iniciar · ${s['treatments_planned']}',
                valor: dinero(numero(s['treatments_planned_value'])),
                icono: Icons.event_note_outlined,
                color: Tonos.violeta,
              ),
            ],
          ),
          const SizedBox(height: 12),
          _Filtros(
            opciones: [
              ('activos', 'Activos', todos.where(activo).length),
              ('en_progreso', 'En curso', todos.where((t) => t['status'] == 'en_progreso').length),
              ('completado', 'Terminados', todos.where((t) => t['status'] == 'completado').length),
              ('todos', 'Todos', todos.length),
            ],
            actual: _filtro,
            alElegir: (v) => setState(() => _filtro = v),
          ),
          const SizedBox(height: 8),
          _Buscador((v) => setState(() => _q = v.trim().toLowerCase())),
          if (lista.isEmpty) const EstadoVacio(icono: Icons.medical_services_outlined, titulo: 'Sin tratamientos en esta lista'),
          for (final t in lista)
            FilaTarjeta(
              icono: Icons.medical_services_outlined,
              colorIcono: (_estadosTratamiento[t['status']] ?? ('', Tonos.gris)).$2,
              titulo: '${t['treatment']}${t['fdi_number'] != null ? ' · pieza ${t['fdi_number']}' : ''}',
              subtitulo: [
                '${t['patient_name']}',
                (_estadosTratamiento[t['status']] ?? ('${t['status']}', Tonos.gris)).$1,
                if (t['professional_name'] != null) '${t['professional_name']}',
                if (t['estimated_date'] != null && t['completed_date'] == null) 'prev. ${fechaCorta(t['estimated_date'])}',
              ].join(' · '),
              alTocar: () => _abrirPaciente(context, t),
              derecha: Text(dinero(numero(t['net_price'])), style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
          finDeLista,
        ],
      ),
    );
  }
}
