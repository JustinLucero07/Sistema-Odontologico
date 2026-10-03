import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../shared/widgets/formulario.dart';

const _duraciones = <Opcion>[
  ('15', '15 min'),
  ('30', '30 min'),
  ('45', '45 min'),
  ('60', '1 hora'),
  ('90', '1 h 30 min'),
  ('120', '2 horas'),
];

/// Nueva cita o reprogramación. Con [citaId] se edita (se lee del servidor);
/// con [pacienteId] no se pregunta el paciente.
Future<bool> editarCita(
  BuildContext context,
  WidgetRef ref, {
  String? citaId,
  String? pacienteId,
  String? pacienteNombre,
  DateTime? dia,
  String? hora,
  String? profesionalId,
  int? duracion,
}) async {
  final api = ref.read(apiProvider);
  Map<String, dynamic>? cita;
  List<Map<String, dynamic>> profesionales;
  List<Map<String, dynamic>> tratamientos;
  try {
    if (citaId != null) cita = await api.mapa('/appointments/$citaId');
    profesionales = await ref.read(profesionalesProvider.future);
    tratamientos = await ref.read(tratamientosCatalogoProvider.future);
  } catch (_) {
    if (context.mounted) avisar(context, 'No se pudieron cargar los datos.');
    return false;
  }
  if (!context.mounted) return false;

  final inicio = cita == null
      ? null
      : DateTime.parse('${cita['starts_at']}').toLocal();
  final base = dia ?? DateTime.now();
  final minutos = cita == null
      ? '${duracion ?? 30}'
      : '${cita['duration_minutes'] ?? 30}';
  var guardado = false;

  await mostrarFormulario(
    context,
    titulo: cita == null ? 'Nueva cita' : 'Reprogramar cita',
    subtitulo: cita == null
        ? (pacienteNombre ?? 'Agendar a un paciente')
        : '${cita['patient_name']}',
    icono: Icons.event_available,
    textoGuardar: cita == null ? 'Agendar' : 'Guardar cambios',
    campos: [
      if (cita == null && pacienteId == null)
        Campo(
          'patient_id',
          'Paciente',
          tipo: TipoCampo.buscar,
          requerido: true,
          buscar: buscadorPacientes(api),
        ),
      Campo(
        'professional_id',
        'Profesional',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: opcionesProfesionales(profesionales),
        inicial: cita?['professional_id'] ?? profesionalId,
      ),
      Campo(
        'treatment_id',
        'Tratamiento',
        tipo: TipoCampo.seleccion,
        opciones: opcionesTratamientos(tratamientos),
        inicial: cita?['treatment_id'],
      ),
      Campo(
        'fecha',
        'Fecha',
        tipo: TipoCampo.fecha,
        requerido: true,
        inicial: DateFormat('yyyy-MM-dd').format(inicio ?? base),
        mitad: true,
      ),
      Campo(
        'hora',
        'Hora',
        tipo: TipoCampo.hora,
        requerido: true,
        inicial: inicio == null
            ? (hora ?? '09:00')
            : DateFormat('HH:mm').format(inicio),
        mitad: true,
      ),
      Campo(
        'duracion',
        'Duración',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: _duraciones.any((d) => d.$1 == minutos)
            ? _duraciones
            : [..._duraciones, (minutos, '$minutos min')],
        inicial: minutos,
      ),
      Campo(
        'notes',
        'Notas',
        tipo: TipoCampo.multilinea,
        inicial: cita?['notes'],
      ),
    ],
    alGuardar: (v) async {
      final h = '${v['hora']}'.split(':');
      final f = DateTime.parse('${v['fecha']}');
      final empieza = DateTime(
        f.year,
        f.month,
        f.day,
        int.parse(h[0]),
        int.parse(h[1]),
      );
      final termina = empieza.add(
        Duration(minutes: int.parse('${v['duracion']}')),
      );
      final datos = {
        'professional_id': v['professional_id'],
        'treatment_id': v['treatment_id'],
        'starts_at': empieza.toUtc().toIso8601String(),
        'ends_at': termina.toUtc().toIso8601String(),
        'notes': v['notes'],
      };
      if (cita == null) {
        await api.post('/appointments', {
          ...datos,
          'patient_id': pacienteId ?? v['patient_id'],
        });
      } else {
        await api.put('/appointments/${cita['id']}', datos);
      }
      guardado = true;
    },
  );
  return guardado;
}

/// Cambiar el estado de una cita a cualquiera de los posibles (con motivo si
/// se cancela).
Future<bool> cambiarEstadoCita(
  BuildContext context,
  WidgetRef ref,
  String citaId,
  String estadoActual,
) async {
  var hecho = false;
  await mostrarFormulario(
    context,
    titulo: 'Estado de la cita',
    icono: Icons.flag_outlined,
    campos: [
      Campo(
        'status',
        'Estado',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: estadosCita,
        inicial: estadoActual,
      ),
      const Campo(
        'cancellation_reason',
        'Motivo (si se cancela)',
        tipo: TipoCampo.multilinea,
      ),
    ],
    alGuardar: (v) async {
      await ref.read(apiProvider).put('/appointments/$citaId/status', v);
      hecho = true;
    },
  );
  return hecho;
}
