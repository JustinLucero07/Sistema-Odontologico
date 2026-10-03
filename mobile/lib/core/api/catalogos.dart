import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/widgets/formulario.dart';
import 'api.dart';

/// Catálogos que usan muchos formularios. Se piden una vez por sesión de
/// pantalla y se reutilizan.

List<Opcion> _codigos(List<Map<String, dynamic>> l) => [
  for (final e in l) ('${e['code']}', '${e['label']}'),
];

final formasPagoProvider = FutureProvider.autoDispose<List<Opcion>>(
  (ref) async =>
      _codigos(await ref.watch(apiProvider).lista('/finance/payment-methods')),
);

final categoriasEgresoProvider = FutureProvider.autoDispose<List<Opcion>>(
  (ref) async => _codigos(
    await ref.watch(apiProvider).lista('/finance/expense-categories'),
  ),
);

final tiposImagenProvider = FutureProvider.autoDispose<List<Opcion>>(
  (ref) async => _codigos(await ref.watch(apiProvider).lista('/images/types')),
);

final profesionalesProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref.watch(apiProvider).lista('/professionals'),
    );

final tratamientosCatalogoProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref.watch(apiProvider).lista('/treatments'),
    );

List<Opcion> opcionesProfesionales(List<Map<String, dynamic>> l) => [
  for (final p in l)
    if (p['is_active'] != false)
      ('${p['id']}', '${p['first_name']} ${p['last_name']}'),
];

List<Opcion> opcionesTratamientos(List<Map<String, dynamic>> l) => [
  for (final t in l)
    if (t['is_active'] != false) ('${t['id']}', '${t['name']}'),
];

/// Buscador de pacientes para los formularios.
Future<List<Opcion>> Function(String) buscadorPacientes(Api api) =>
    (texto) async {
      final l = await api.lista('/patients', query: {'search': texto});
      return [
        for (final p in l)
          (
            '${p['id']}',
            '${p['first_name']} ${p['last_name']}'
                '${p['national_id'] != null ? ' · ${p['national_id']}' : ''}',
          ),
      ];
    };

const estadosCita = <Opcion>[
  ('programada', 'Programada'),
  ('confirmada', 'Confirmada'),
  ('en_espera', 'En espera'),
  ('en_atencion', 'En atención'),
  ('atendida', 'Atendida'),
  ('cancelada', 'Cancelada'),
  ('no_asistio', 'No asistió'),
];

const estadosItemPlan = <Opcion>[
  ('propuesto', 'Propuesto'),
  ('aprobado', 'Aprobado'),
  ('en_progreso', 'En progreso'),
  ('completado', 'Completado'),
  ('cancelado', 'Cancelado'),
  ('rechazado', 'Rechazado'),
];

const sexos = <Opcion>[('F', 'Femenino'), ('M', 'Masculino'), ('O', 'Otro')];

String etiquetaDe(List<Opcion> opciones, dynamic codigo) =>
    opciones.where((o) => o.$1 == '$codigo').map((o) => o.$2).firstOrNull ??
    '${codigo ?? '—'}';
