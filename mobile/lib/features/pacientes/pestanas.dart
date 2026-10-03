import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/models/cita.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';
import '../agenda/cita_form.dart';
import '../creditos/creditos_page.dart';

// ------------------------------------------------------------------ Proveedores

final historiaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>?, String>((ref, id) async {
      final r = await ref
          .watch(apiProvider)
          .get('/patients/$id/medical-history');
      return r is Map ? r.cast<String, dynamic>() : null;
    });

final _versionesHistoriaProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>(
      (ref, id) => ref
          .watch(apiProvider)
          .lista('/patients/$id/medical-history/versions'),
    );

final planesProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>(
      (ref, id) =>
          ref.watch(apiProvider).lista('/patients/$id/treatment-plans'),
    );

class _Clinico {
  const _Clinico(this.evoluciones, this.recetas, this.diagnosticos);
  final List<Map<String, dynamic>> evoluciones;
  final List<Map<String, dynamic>> recetas;
  final List<Map<String, dynamic>> diagnosticos;
}

final clinicoProvider = FutureProvider.autoDispose.family<_Clinico, String>((
  ref,
  id,
) async {
  final api = ref.watch(apiProvider);
  final r = await Future.wait([
    api.lista('/patients/$id/evolutions'),
    api.lista('/patients/$id/prescriptions'),
    api.lista('/patients/$id/diagnoses'),
  ]);
  return _Clinico(r[0], r[1], r[2]);
});

final imagenesProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>(
      (ref, id) => ref.watch(apiProvider).lista('/patients/$id/images'),
    );

final citasPacienteProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>(
      (ref, id) => ref.watch(apiProvider).lista('/patients/$id/appointments'),
    );

class _Cuenta {
  const _Cuenta(this.cuenta, this.creditos);
  final Map<String, dynamic> cuenta;
  final List<Map<String, dynamic>> creditos;
}

final cuentaProvider = FutureProvider.autoDispose.family<_Cuenta, String>((
  ref,
  id,
) async {
  final api = ref.watch(apiProvider);
  final cuenta = await api.mapa('/patients/$id/account');
  List<Map<String, dynamic>> creditos = [];
  try {
    creditos = await api.lista('/patients/$id/credits');
  } catch (_) {
    // Sin permiso de créditos se ve la cuenta igual.
  }
  return _Cuenta(cuenta, creditos);
});

// -------------------------------------------------------------- Datos paciente

/// Alta o edición del paciente. Devuelve el id (nuevo o el mismo).
Future<String?> editarPaciente(
  BuildContext context,
  WidgetRef ref, {
  Map<String, dynamic>? paciente,
}) async {
  final api = ref.read(apiProvider);
  final p = paciente;
  String? id;
  await mostrarFormulario(
    context,
    titulo: p == null ? 'Nuevo paciente' : 'Editar datos',
    subtitulo: p == null
        ? 'Solo nombres y apellidos son obligatorios.'
        : 'Los cambios quedan registrados en la auditoría.',
    icono: p == null ? Icons.person_add_alt : Icons.edit_outlined,
    textoGuardar: p == null ? 'Crear paciente' : 'Guardar cambios',
    campos: [
      Campo(
        'first_name',
        'Nombres',
        requerido: true,
        inicial: p?['first_name'],
        mitad: true,
        seccion: 'Datos personales',
      ),
      Campo(
        'last_name',
        'Apellidos',
        requerido: true,
        inicial: p?['last_name'],
        mitad: true,
      ),
      Campo('national_id', 'Cédula', inicial: p?['national_id'], mitad: true),
      Campo(
        'birth_date',
        'Nacimiento',
        tipo: TipoCampo.fecha,
        inicial: p?['birth_date'],
        mitad: true,
      ),
      Campo(
        'sex',
        'Sexo',
        tipo: TipoCampo.seleccion,
        opciones: sexos,
        inicial: p?['sex'],
        mitad: true,
      ),
      Campo('occupation', 'Ocupación', inicial: p?['occupation'], mitad: true),
      Campo(
        'phone',
        'Teléfono',
        tipo: TipoCampo.telefono,
        icono: Icons.call_outlined,
        inicial: p?['phone'],
        seccion: 'Contacto',
      ),
      Campo(
        'whatsapp',
        'WhatsApp',
        tipo: TipoCampo.telefono,
        icono: Icons.chat_outlined,
        inicial: p?['whatsapp'],
        ayuda: 'Vacío = el mismo teléfono',
      ),
      Campo(
        'email',
        'Correo',
        tipo: TipoCampo.correo,
        icono: Icons.mail_outline,
        inicial: p?['email'],
      ),
      Campo('address', 'Dirección', inicial: p?['address']),
      Campo('city', 'Ciudad', inicial: p?['city']),
      Campo(
        'emergency_contact_name',
        'Contacto de emergencia',
        inicial: p?['emergency_contact_name'],
        seccion: 'Emergencia',
      ),
      Campo(
        'emergency_contact_phone',
        'Teléfono de emergencia',
        tipo: TipoCampo.telefono,
        inicial: p?['emergency_contact_phone'],
      ),
      Campo(
        'notes',
        'Observaciones',
        tipo: TipoCampo.multilinea,
        inicial: p?['notes'],
      ),
    ],
    alGuardar: (v) async {
      if (v['whatsapp'] == null && v['phone'] != null) {
        v['whatsapp'] = v['phone'];
      }
      if (p == null) {
        final r = await api.post('/patients', v);
        id = '${(r as Map)['id']}';
      } else {
        await api.put('/patients/${p['id']}', v);
        id = '${p['id']}';
      }
    },
  );
  return id;
}

// ------------------------------------------------------------ Historia clínica

const _camposHistoria = <(String, String, String)>[
  ('Datos médicos', 'allergies', 'Alergias'),
  ('Datos médicos', 'medications', 'Medicamentos'),
  ('Datos médicos', 'medical_conditions', 'Enfermedades'),
  ('Datos médicos', 'surgeries', 'Cirugías'),
  ('Datos médicos', 'habits', 'Hábitos'),
  ('Datos médicos', 'vital_signs', 'Signos vitales'),
  ('Datos odontológicos', 'chief_complaint', 'Motivo de consulta'),
  ('Datos odontológicos', 'present_illness_history', 'Historia del problema'),
  ('Datos odontológicos', 'oral_hygiene', 'Higiene oral'),
  ('Datos odontológicos', 'dental_habits', 'Hábitos orales'),
  ('Datos odontológicos', 'dental_history', 'Antecedentes odontológicos'),
  ('Evaluación', 'extraoral_exam', 'Examen extraoral'),
  ('Evaluación', 'intraoral_exam', 'Examen intraoral'),
  ('Evaluación', 'soft_tissues', 'Tejidos blandos'),
  ('Evaluación', 'gums', 'Encías'),
  ('Evaluación', 'periodontium', 'Periodonto'),
  ('Evaluación', 'tmj', 'ATM'),
  ('Evaluación', 'occlusion', 'Oclusión'),
  ('Evaluación', 'observations', 'Observaciones'),
];

Future<void> nuevaVersionHistoria(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
  Map<String, dynamic>? actual,
) {
  String? seccionAnterior;
  return mostrarFormulario(
    context,
    titulo: actual == null ? 'Crear historia clínica' : 'Nueva versión',
    subtitulo: 'La versión anterior se conserva; nunca se sobrescribe.',
    icono: Icons.note_add_outlined,
    textoGuardar: 'Guardar versión',
    campos: [
      for (final (seccion, clave, etiqueta) in _camposHistoria)
        Campo(
          clave,
          etiqueta,
          tipo: clave == 'observations' || clave == 'present_illness_history'
              ? TipoCampo.multilinea
              : TipoCampo.texto,
          inicial: actual?[clave],
          seccion: seccion == seccionAnterior
              ? null
              : (seccionAnterior = seccion),
        ),
    ],
    alGuardar: (v) async {
      await ref
          .read(apiProvider)
          .post('/patients/$pacienteId/medical-history', v);
      ref.invalidate(historiaProvider(pacienteId));
      ref.invalidate(_versionesHistoriaProvider(pacienteId));
    },
  );
}

class PestanaHistoria extends ConsumerWidget {
  const PestanaHistoria({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final puede =
        ref.watch(authProvider).usuario?.puede('medical_history:write') ??
        false;
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(historiaProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(historiaProvider(pacienteId)),
        alReintentar: () => ref.invalidate(historiaProvider(pacienteId)),
        listo: (h) {
          if (h == null) {
            return ListView(
              children: [
                EstadoVacio(
                  icono: Icons.history_edu,
                  titulo: 'Sin historia clínica',
                  detalle: 'Registre la anamnesis y el examen del paciente.',
                  accion: puede
                      ? FilledButton.icon(
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(0, 46),
                          ),
                          onPressed: () => nuevaVersionHistoria(
                            context,
                            ref,
                            pacienteId,
                            null,
                          ),
                          icon: const Icon(Icons.note_add_outlined),
                          label: const Text('Crear historia clínica'),
                        )
                      : null,
                ),
              ],
            );
          }
          final secciones = <String, List<(String, dynamic)>>{};
          for (final (s, clave, etiqueta) in _camposHistoria) {
            secciones.putIfAbsent(s, () => []).add((etiqueta, h[clave]));
          }
          final alergias = '${h['allergies'] ?? ''}'.trim();
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (alergias.isNotEmpty &&
                  !RegExp(
                    r'^(ninguna?|no)$',
                    caseSensitive: false,
                  ).hasMatch(alergias))
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: GlassPanel(
                    tint: Tonos.rojo,
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const Icon(Icons.warning_amber, color: Colors.white),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Alergias: $alergias',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              for (final e in secciones.entries) ...[
                Seccion(e.key),
                GlassCard(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      children: [
                        for (final (etiqueta, valor) in e.value)
                          _Dato(etiqueta: etiqueta, valor: valor),
                      ],
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 10),
              Text(
                'Última actualización: ${fechaHora(h['created_at'])}',
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () => showModalBottomSheet<void>(
                  context: context,
                  showDragHandle: true,
                  builder: (_) => _Versiones(pacienteId: pacienteId),
                ),
                icon: const Icon(Icons.history),
                label: const Text('Ver historial de versiones'),
              ),
              finDeLista,
            ],
          );
        },
      ),
    );
  }
}

class _Versiones extends ConsumerWidget {
  const _Versiones({required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.6,
        child: Asincrono(
          valor: ref.watch(_versionesHistoriaProvider(pacienteId)),
          alReintentar: () =>
              ref.invalidate(_versionesHistoriaProvider(pacienteId)),
          listo: (l) => ListView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              for (final (i, v) in l.indexed)
                ListTile(
                  leading: Icon(
                    i == 0 ? Icons.check_circle : Icons.history,
                    color: i == 0 ? Tonos.verde : null,
                  ),
                  title: Text(fechaHora(v['created_at'])),
                  subtitle: Text(
                    '${v['chief_complaint'] ?? v['allergies'] ?? 'Sin motivo registrado'}',
                  ),
                  trailing: i == 0 ? const Pastilla('Vigente') : null,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato({required this.etiqueta, required this.valor});

  final String etiqueta;
  final dynamic valor;

  @override
  Widget build(BuildContext context) {
    final texto = valor == null || '$valor'.trim().isEmpty ? '—' : '$valor';
    final tenue = Theme.of(context).colorScheme.onSurface;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              etiqueta,
              style: TextStyle(
                fontSize: 12.5,
                color: tenue.withValues(alpha: 0.55),
              ),
            ),
          ),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(
                fontSize: 14,
                color: texto == '—' ? tenue.withValues(alpha: 0.35) : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- Tratamientos

Color _colorItem(String? s) => switch (s) {
  'completado' => Tonos.verde,
  'en_progreso' => Tonos.azul,
  'aprobado' => const Color(0xFF0D7F76),
  'cancelado' || 'rechazado' => Tonos.gris,
  _ => Tonos.ambar,
};

Future<void> editarPlan(
  BuildContext context,
  WidgetRef ref,
  String pacienteId, {
  Map<String, dynamic>? plan,
}) => mostrarFormulario(
  context,
  titulo: plan == null ? 'Nuevo plan de tratamiento' : 'Editar plan',
  icono: Icons.assignment_outlined,
  campos: [
    Campo(
      'title',
      'Título',
      requerido: true,
      inicial: plan?['title'] ?? 'Plan de tratamiento',
    ),
    Campo(
      'notes',
      'Notas',
      tipo: TipoCampo.multilinea,
      inicial: plan?['notes'],
    ),
  ],
  alGuardar: (v) async {
    final api = ref.read(apiProvider);
    if (plan == null) {
      await api.post('/patients/$pacienteId/treatment-plans', {
        ...v,
        'items': <dynamic>[],
      });
    } else {
      await api.put('/treatment-plans/${plan['id']}', v);
    }
    ref.invalidate(planesProvider(pacienteId));
  },
);

Future<void> _editarItem(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
  String planId, {
  Map<String, dynamic>? item,
}) async {
  final tratamientos = await cargarOAvisar(
    context,
    ref.read(tratamientosCatalogoProvider.future),
  );
  if (tratamientos == null) return;
  if (!context.mounted) return;
  final profesionales = await cargarOAvisar(
    context,
    ref.read(profesionalesProvider.future),
  );
  if (profesionales == null) return;
  if (!context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: item == null ? 'Agregar tratamiento' : '${item['treatment_name']}',
    subtitulo: item == null
        ? 'Si deja el precio vacío se usa el del catálogo.'
        : null,
    icono: Icons.medical_services_outlined,
    campos: [
      if (item == null)
        Campo(
          'treatment_id',
          'Tratamiento',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: opcionesTratamientos(tratamientos),
        ),
      Campo(
        'fdi_number',
        'Pieza (FDI)',
        inicial: item?['fdi_number'],
        mitad: true,
      ),
      Campo('surface', 'Superficie', inicial: item?['surface'], mitad: true),
      Campo(
        'price',
        'Precio',
        tipo: TipoCampo.dinero,
        inicial: item?['price'],
        mitad: true,
      ),
      Campo(
        'discount',
        'Descuento',
        tipo: TipoCampo.dinero,
        inicial: item?['discount'] ?? '0',
        mitad: true,
      ),
      Campo(
        'status',
        'Estado',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: estadosItemPlan,
        inicial: item?['status'] ?? 'propuesto',
      ),
      Campo(
        'professional_id',
        'Profesional',
        tipo: TipoCampo.seleccion,
        opciones: opcionesProfesionales(profesionales),
        inicial: item?['professional_id'],
      ),
      Campo(
        'estimated_date',
        'Fecha estimada',
        tipo: TipoCampo.fecha,
        inicial: item?['estimated_date'],
      ),
      Campo(
        'notes',
        'Notas',
        tipo: TipoCampo.multilinea,
        inicial: item?['notes'],
      ),
    ],
    alGuardar: (v) async {
      final api = ref.read(apiProvider);
      if (item == null) {
        if (v['price'] == null) {
          v['price'] = tratamientos.firstWhere(
            (t) => t['id'] == v['treatment_id'],
          )['default_price'];
        }
        v['discount'] ??= 0;
        await api.post('/treatment-plans/$planId/items', v);
      } else {
        await api.put('/treatment-plans/$planId/items/${item['id']}', v);
      }
      ref.invalidate(planesProvider(pacienteId));
    },
  );
}

class PestanaTratamientos extends ConsumerWidget {
  const PestanaTratamientos({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(planesProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(planesProvider(pacienteId)),
        alReintentar: () => ref.invalidate(planesProvider(pacienteId)),
        listo: (planes) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (planes.isEmpty)
              const EstadoVacio(
                icono: Icons.assignment_outlined,
                titulo: 'Sin planes de tratamiento',
                detalle: 'Cree un plan con el botón de abajo.',
              ),
            for (final plan in planes) ...[
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${plan['title']}',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          IconButton(
                            tooltip: 'Editar plan',
                            icon: const Icon(Icons.edit_outlined, size: 20),
                            onPressed: () => editarPlan(
                              context,
                              ref,
                              pacienteId,
                              plan: plan,
                            ),
                          ),
                        ],
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: LinearProgressIndicator(
                            value: numero(plan['progress_percent']) / 100,
                            minHeight: 7,
                          ),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${numero(plan['progress_percent']).toStringAsFixed(0)} % completado · total ${dinero(numero(plan['total_price']))}',
                        style: const TextStyle(fontSize: 12.5),
                      ),
                      const SizedBox(height: 8),
                      for (final item
                          in (plan['items'] as List? ?? [])
                              .cast<Map<String, dynamic>>())
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          dense: true,
                          onTap: () => _editarItem(
                            context,
                            ref,
                            pacienteId,
                            '${plan['id']}',
                            item: item,
                          ),
                          leading: Icon(
                            item['status'] == 'completado'
                                ? Icons.check_circle
                                : Icons.radio_button_unchecked,
                            color: _colorItem(item['status']),
                          ),
                          title: Text(
                            '${item['treatment_name']}'
                            '${item['fdi_number'] != null ? ' · ${item['fdi_number']}' : ''}',
                          ),
                          subtitle: Text(
                            etiquetaDe(estadosItemPlan, item['status']),
                          ),
                          trailing: Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: Text(
                              dinero(numero(item['net_price'])),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ),
                      TextButton.icon(
                        onPressed: () => _editarItem(
                          context,
                          ref,
                          pacienteId,
                          '${plan['id']}',
                        ),
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Agregar tratamiento'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
            finDeLista,
          ],
        ),
      ),
    );
  }
}

// ------------------------------------------------------------------- Clínico

Future<void> registrarEvolucion(
  BuildContext context,
  WidgetRef ref,
  String pacienteId, {
  Map<String, dynamic>? evolucion,
}) async {
  final profesionales = await cargarOAvisar(
    context,
    ref.read(profesionalesProvider.future),
  );
  if (profesionales == null) return;
  if (!context.mounted) return;
  final e = evolucion;
  await mostrarFormulario(
    context,
    titulo: e == null ? 'Registrar evolución' : 'Editar evolución',
    icono: Icons.edit_note,
    campos: [
      Campo(
        'procedure',
        'Procedimiento realizado',
        tipo: TipoCampo.multilinea,
        requerido: true,
        inicial: e?['procedure'],
      ),
      Campo(
        'fdi_numbers',
        'Piezas (FDI)',
        inicial: e?['fdi_numbers'],
        mitad: true,
      ),
      if (e == null)
        Campo(
          'professional_id',
          'Profesional',
          tipo: TipoCampo.seleccion,
          opciones: opcionesProfesionales(profesionales),
          mitad: true,
        ),
      Campo('diagnosis', 'Diagnóstico', inicial: e?['diagnosis']),
      Campo('anesthesia', 'Anestesia', inicial: e?['anesthesia'], mitad: true),
      Campo('materials', 'Materiales', inicial: e?['materials'], mitad: true),
      Campo(
        'evolution',
        'Evolución',
        tipo: TipoCampo.multilinea,
        inicial: e?['evolution'],
      ),
      Campo(
        'instructions',
        'Indicaciones al paciente',
        tipo: TipoCampo.multilinea,
        inicial: e?['instructions'],
      ),
      Campo(
        'next_appointment_notes',
        'Próxima cita',
        inicial: e?['next_appointment_notes'],
      ),
    ],
    alGuardar: (v) async {
      final api = ref.read(apiProvider);
      if (e == null) {
        await api.post('/patients/$pacienteId/evolutions', v);
      } else {
        await api.put('/evolutions/${e['id']}', v);
      }
      ref.invalidate(clinicoProvider(pacienteId));
    },
  );
}

Future<void> nuevaReceta(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
) async {
  final profesionales = await cargarOAvisar(
    context,
    ref.read(profesionalesProvider.future),
  );
  if (profesionales == null) return;
  if (!context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: 'Nueva receta',
    icono: Icons.medication_outlined,
    campos: [
      Campo(
        'professional_id',
        'Profesional que prescribe',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: opcionesProfesionales(profesionales),
      ),
      for (var i = 1; i <= 3; i++) ...[
        Campo(
          'm$i',
          'Medicamento $i',
          requerido: i == 1,
          seccion: 'Medicamento $i${i > 1 ? ' (opcional)' : ''}',
        ),
        Campo('d$i', 'Dosis', mitad: true),
        Campo('f$i', 'Frecuencia', mitad: true),
        Campo('t$i', 'Duración', mitad: true),
        Campo('i$i', 'Indicaciones', mitad: true),
      ],
      const Campo(
        'notes',
        'Notas',
        tipo: TipoCampo.multilinea,
        seccion: 'Notas',
      ),
    ],
    alGuardar: (v) async {
      final items = [
        for (var i = 1; i <= 3; i++)
          if (v['m$i'] != null)
            {
              'medication': v['m$i'],
              'dosage': v['d$i'],
              'frequency': v['f$i'],
              'duration': v['t$i'],
              'instructions': v['i$i'],
            },
      ];
      await ref.read(apiProvider).post('/patients/$pacienteId/prescriptions', {
        'professional_id': v['professional_id'],
        'notes': v['notes'],
        'items': items,
      });
      ref.invalidate(clinicoProvider(pacienteId));
    },
  );
}

Future<void> nuevoDiagnostico(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
) => mostrarFormulario(
  context,
  titulo: 'Nuevo diagnóstico',
  icono: Icons.medical_information_outlined,
  campos: const [
    Campo('description', 'Diagnóstico', requerido: true),
    Campo('fdi_number', 'Pieza (FDI)'),
    Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
  ],
  alGuardar: (v) async {
    await ref.read(apiProvider).post('/patients/$pacienteId/diagnoses', v);
    ref.invalidate(clinicoProvider(pacienteId));
  },
);

void menuClinico(BuildContext context, WidgetRef ref, String pacienteId) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (hoja) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.edit_note),
            title: const Text('Evolución'),
            subtitle: const Text('Lo que se hizo en la consulta'),
            onTap: () {
              Navigator.pop(hoja);
              registrarEvolucion(context, ref, pacienteId);
            },
          ),
          ListTile(
            leading: const Icon(Icons.medication_outlined),
            title: const Text('Receta'),
            onTap: () {
              Navigator.pop(hoja);
              nuevaReceta(context, ref, pacienteId);
            },
          ),
          ListTile(
            leading: const Icon(Icons.medical_information_outlined),
            title: const Text('Diagnóstico'),
            onTap: () {
              Navigator.pop(hoja);
              nuevoDiagnostico(context, ref, pacienteId);
            },
          ),
        ],
      ),
    ),
  );
}

class PestanaClinica extends ConsumerWidget {
  const PestanaClinica({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(clinicoProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(clinicoProvider(pacienteId)),
        alReintentar: () => ref.invalidate(clinicoProvider(pacienteId)),
        listo: (c) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Seccion('Diagnósticos (${c.diagnosticos.length})'),
            if (c.diagnosticos.isEmpty) const _Vacio('Sin diagnósticos'),
            for (final d in c.diagnosticos)
              FilaTarjeta(
                icono: Icons.medical_information_outlined,
                colorIcono: Tonos.violeta,
                titulo: '${d['description']}',
                subtitulo: [
                  fechaCorta(d['created_at']),
                  if (d['fdi_number'] != null) 'Pieza ${d['fdi_number']}',
                  if (d['voided_at'] != null) 'Anulado: ${d['void_reason']}',
                ].join(' · '),
                tachado: d['voided_at'] != null,
                alTocar: d['voided_at'] != null
                    ? null
                    : () => anularConMotivo(
                        context,
                        que: 'diagnóstico',
                        alAnular: (m) async {
                          await api.post(
                            '/patients/$pacienteId/diagnoses/${d['id']}/void',
                            {'reason': m},
                          );
                          ref.invalidate(clinicoProvider(pacienteId));
                        },
                      ),
              ),
            Seccion('Evoluciones (${c.evoluciones.length})'),
            if (c.evoluciones.isEmpty) const _Vacio('Sin evoluciones'),
            for (final e in c.evoluciones)
              FilaTarjeta(
                icono: Icons.edit_note,
                titulo: '${e['procedure']}',
                subtitulo: [
                  fechaHora(e['created_at']),
                  if (e['fdi_numbers'] != null) 'Piezas ${e['fdi_numbers']}',
                  if (e['diagnosis'] != null) '${e['diagnosis']}',
                  if (e['instructions'] != null)
                    'Indicaciones: ${e['instructions']}',
                ].join('\n'),
                derecha: const Icon(Icons.edit_outlined, size: 18),
                alTocar: () =>
                    registrarEvolucion(context, ref, pacienteId, evolucion: e),
              ),
            Seccion('Recetas (${c.recetas.length})'),
            if (c.recetas.isEmpty) const _Vacio('Sin recetas'),
            for (final r in c.recetas)
              FilaTarjeta(
                icono: Icons.medication_outlined,
                colorIcono: Tonos.azul,
                titulo: (r['items'] as List? ?? [])
                    .map((i) => '${i['medication']}')
                    .join(', '),
                subtitulo: [
                  fechaCorta(r['created_at']),
                  for (final i in (r['items'] as List? ?? []))
                    [
                      i['dosage'],
                      i['frequency'],
                      i['duration'],
                    ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                  if (r['voided_at'] != null) 'Anulada: ${r['void_reason']}',
                ].where((x) => x.isNotEmpty).join('\n'),
                tachado: r['voided_at'] != null,
                alTocar: r['voided_at'] != null
                    ? null
                    : () => anularConMotivo(
                        context,
                        que: 'receta',
                        alAnular: (m) async {
                          await api.post(
                            '/patients/$pacienteId/prescriptions/${r['id']}/void',
                            {'reason': m},
                          );
                          ref.invalidate(clinicoProvider(pacienteId));
                        },
                      ),
              ),
            finDeLista,
          ],
        ),
      ),
    );
  }
}

class _Vacio extends StatelessWidget {
  const _Vacio(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
    child: Text(
      texto,
      style: TextStyle(
        color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.45),
      ),
    ),
  );
}

// ------------------------------------------------------------------ Imágenes

Future<void> subirImagen(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
  ImageSource origen,
) async {
  final archivo = await ImagePicker().pickImage(
    source: origen,
    // 2000 px de lado bastan para mirar una radiografía en pantalla y no
    // mandan 6 MB por la red móvil.
    maxWidth: 2000,
    imageQuality: 88,
  );
  if (archivo == null || !context.mounted) return;
  final tipos = await cargarOAvisar(
    context,
    ref.read(tiposImagenProvider.future),
  );
  if (tipos == null) return;
  if (!context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: 'Datos de la imagen',
    icono: Icons.add_photo_alternate_outlined,
    textoGuardar: 'Subir',
    campos: [
      const Campo('title', 'Título', requerido: true),
      Campo(
        'image_type',
        'Tipo de estudio',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: tipos,
        inicial: 'foto_intraoral',
      ),
      const Campo('fdi_numbers', 'Piezas (FDI)', ayuda: 'Ej.: 16, 17'),
      Campo('taken_on', 'Fecha', tipo: TipoCampo.fecha, inicial: hoyIso()),
      const Campo('description', 'Descripción', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      final form = await formDataDesde(archivo.path, {
        ...v,
        if (v['fdi_numbers'] != null)
          'fdi_numbers': '${v['fdi_numbers']}'.replaceAll(' ', ''),
      });
      await ref.read(apiProvider).post('/patients/$pacienteId/images', form);
      ref.invalidate(imagenesProvider(pacienteId));
    },
  );
}

void menuImagen(BuildContext context, WidgetRef ref, String pacienteId) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (hoja) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.photo_camera),
            title: const Text('Tomar foto o radiografía'),
            onTap: () {
              Navigator.pop(hoja);
              subirImagen(context, ref, pacienteId, ImageSource.camera);
            },
          ),
          ListTile(
            leading: const Icon(Icons.photo_library),
            title: const Text('Elegir de la galería'),
            onTap: () {
              Navigator.pop(hoja);
              subirImagen(context, ref, pacienteId, ImageSource.gallery);
            },
          ),
        ],
      ),
    ),
  );
}

class PestanaImagenes extends ConsumerWidget {
  const PestanaImagenes({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final token = ref.watch(tokenStoreProvider).accessToken;
    final base = ref.watch(apiClientProvider).dio.options.baseUrl;
    final tipos = ref.watch(tiposImagenProvider).value ?? const <Opcion>[];
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(imagenesProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(imagenesProvider(pacienteId)),
        alReintentar: () => ref.invalidate(imagenesProvider(pacienteId)),
        listo: (lista) {
          final activas = lista.where((i) => i['archived_at'] == null).toList();
          if (activas.isEmpty) {
            return ListView(
              children: const [
                EstadoVacio(
                  icono: Icons.image_outlined,
                  titulo: 'Sin radiografías ni fotos',
                  detalle: 'Súbalas con la cámara o desde la galería.',
                ),
              ],
            );
          }
          return GridView.builder(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 0.82,
            ),
            itemCount: activas.length,
            itemBuilder: (context, i) {
              final img = activas[i];
              final url = '$base/images/${img['id']}/file';
              final cabeceras = {
                if (token != null) 'Authorization': 'Bearer $token',
              };
              return GlassCard(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => _VisorImagen(
                      url: url,
                      cabeceras: cabeceras,
                      imagen: img,
                      pacienteId: pacienteId,
                    ),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: Image.network(
                        url,
                        headers: cabeceras,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => const Center(
                          child: Icon(Icons.broken_image_outlined, size: 36),
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${img['title']}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          Text(
                            '${etiquetaDe(tipos, img['image_type'])} · ${fechaCorta(img['taken_on'] ?? img['created_at'])}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 11.5),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _VisorImagen extends ConsumerWidget {
  const _VisorImagen({
    required this.url,
    required this.cabeceras,
    required this.imagen,
    required this.pacienteId,
  });

  final String url;
  final Map<String, String> cabeceras;
  final Map<String, dynamic> imagen;
  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text('${imagen['title']}'),
        actions: [
          IconButton(
            tooltip: 'Editar datos',
            icon: const Icon(Icons.edit_outlined),
            onPressed: () async {
              final tipos = await cargarOAvisar(
                context,
                ref.read(tiposImagenProvider.future),
              );
              if (tipos == null) return;
              if (!context.mounted) return;
              await mostrarFormulario(
                context,
                titulo: 'Editar imagen',
                icono: Icons.edit_outlined,
                campos: [
                  Campo(
                    'title',
                    'Título',
                    requerido: true,
                    inicial: imagen['title'],
                  ),
                  Campo(
                    'image_type',
                    'Tipo',
                    tipo: TipoCampo.seleccion,
                    requerido: true,
                    opciones: tipos,
                    inicial: imagen['image_type'],
                  ),
                  Campo(
                    'fdi',
                    'Piezas (FDI)',
                    inicial: (imagen['fdi_numbers'] as List?)?.join(', '),
                  ),
                  Campo(
                    'taken_on',
                    'Fecha',
                    tipo: TipoCampo.fecha,
                    inicial: imagen['taken_on'],
                  ),
                  Campo(
                    'description',
                    'Descripción',
                    tipo: TipoCampo.multilinea,
                    inicial: imagen['description'],
                  ),
                ],
                alGuardar: (v) async {
                  final fdi = '${v.remove('fdi') ?? ''}'
                      .split(RegExp(r'[,\s]+'))
                      .where((e) => e.isNotEmpty)
                      .toList();
                  await api.put('/images/${imagen['id']}', {
                    ...v,
                    'fdi_numbers': fdi,
                  });
                  ref.invalidate(imagenesProvider(pacienteId));
                },
              );
            },
          ),
          IconButton(
            tooltip: 'Archivar',
            icon: const Icon(Icons.archive_outlined),
            onPressed: () => mostrarFormulario(
              context,
              titulo: 'Archivar imagen',
              subtitulo: 'No se borra: deja de mostrarse y queda el motivo.',
              icono: Icons.archive_outlined,
              peligro: true,
              textoGuardar: 'Archivar',
              campos: const [
                Campo(
                  'reason',
                  'Motivo',
                  tipo: TipoCampo.multilinea,
                  requerido: true,
                ),
              ],
              alGuardar: (v) async {
                await api.post('/images/${imagen['id']}/archive', v);
                ref.invalidate(imagenesProvider(pacienteId));
                if (context.mounted) Navigator.of(context).pop();
              },
            ),
          ),
        ],
      ),
      body: InteractiveViewer(
        maxScale: 6,
        child: Center(child: Image.network(url, headers: cabeceras)),
      ),
    );
  }
}

// --------------------------------------------------------------------- Citas

class PestanaCitas extends ConsumerWidget {
  const PestanaCitas({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(citasPacienteProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(citasPacienteProvider(pacienteId)),
        alReintentar: () => ref.invalidate(citasPacienteProvider(pacienteId)),
        listo: (lista) {
          final ahora = DateTime.now();
          final citas = lista.map(Cita.fromJson).toList()
            ..sort((a, b) => b.inicio.compareTo(a.inicio));
          final proximas = citas.where((c) => c.inicio.isAfter(ahora)).toList()
            ..sort((a, b) => a.inicio.compareTo(b.inicio));
          final pasadas = citas.where((c) => !c.inicio.isAfter(ahora)).toList();
          Widget fila(Cita c) {
            final color = StatusColors.of(context, c.estado);
            return FilaTarjeta(
              icono: Icons.event,
              colorIcono: color,
              titulo: fechaHora(c.inicio.toIso8601String()),
              subtitulo: [
                c.profesionalNombre,
                ?c.tratamientoNombre,
                '${c.duracionMinutos} min',
              ].join(' · '),
              derecha: Pastilla(
                etiquetaDe(estadosCita, c.estado),
                color: color,
              ),
              alTocar: () => showModalBottomSheet<void>(
                context: context,
                showDragHandle: true,
                builder: (hoja) => SafeArea(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ListTile(
                        leading: const Icon(Icons.edit_calendar),
                        title: const Text('Reprogramar'),
                        onTap: () async {
                          Navigator.pop(hoja);
                          if (await editarCita(context, ref, citaId: c.id)) {
                            ref.invalidate(citasPacienteProvider(pacienteId));
                          }
                        },
                      ),
                      ListTile(
                        leading: const Icon(Icons.flag_outlined),
                        title: const Text('Cambiar estado'),
                        onTap: () async {
                          Navigator.pop(hoja);
                          if (await cambiarEstadoCita(
                            context,
                            ref,
                            c.id,
                            c.estado,
                          )) {
                            ref.invalidate(citasPacienteProvider(pacienteId));
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
            );
          }

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Seccion('Próximas (${proximas.length})'),
              if (proximas.isEmpty) const _Vacio('Sin citas próximas'),
              for (final c in proximas) fila(c),
              Seccion('Anteriores (${pasadas.length})'),
              if (pasadas.isEmpty) const _Vacio('Sin citas anteriores'),
              for (final c in pasadas) fila(c),
              finDeLista,
            ],
          );
        },
      ),
    );
  }
}

// --------------------------------------------------------------------- Cuenta

Future<void> registrarCobro(
  BuildContext context,
  WidgetRef ref,
  String pacienteId, {
  List<Map<String, dynamic>> cargos = const [],
  String? cargoId,
}) async {
  final formas = await cargarOAvisar(
    context,
    ref.read(formasPagoProvider.future),
  );
  if (formas == null) return;
  if (!context.mounted) return;
  final pendientes = cargos
      .where((c) => c['voided_at'] == null && numero(c['pending']) > 0)
      .toList();
  final elegido = pendientes.where((c) => c['id'] == cargoId).firstOrNull;
  await mostrarFormulario(
    context,
    titulo: 'Registrar cobro',
    icono: Icons.payments_outlined,
    textoGuardar: 'Cobrar',
    campos: [
      Campo(
        'amount',
        'Importe',
        tipo: TipoCampo.dinero,
        requerido: true,
        inicial: elegido?['pending'],
        mitad: true,
      ),
      Campo(
        'method',
        'Forma de pago',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: formas,
        inicial: 'efectivo',
        mitad: true,
      ),
      Campo(
        'charge_id',
        'Aplicar a',
        tipo: TipoCampo.seleccion,
        opciones: [
          for (final c in pendientes)
            (
              '${c['id']}',
              '${c['description']} · debe ${dinero(numero(c['pending']))}',
            ),
        ],
        inicial: cargoId,
        ayuda: 'Vacío = a cuenta (se aplica al cargo más antiguo).',
      ),
      const Campo('reference', 'Referencia (tarjeta / transferencia)'),
      Campo('received_on', 'Fecha', tipo: TipoCampo.fecha, inicial: hoyIso()),
      const Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      await ref.read(apiProvider).post('/patients/$pacienteId/payments', v);
      ref.invalidate(cuentaProvider(pacienteId));
    },
  );
}

Future<void> nuevoCargo(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
) => mostrarFormulario(
  context,
  titulo: 'Nuevo cargo',
  subtitulo: 'Lo que el paciente debe por un tratamiento o servicio.',
  icono: Icons.receipt_long,
  campos: [
    const Campo('description', 'Concepto', requerido: true),
    const Campo(
      'amount',
      'Importe',
      tipo: TipoCampo.dinero,
      requerido: true,
      mitad: true,
    ),
    Campo(
      'issued_on',
      'Fecha',
      tipo: TipoCampo.fecha,
      inicial: hoyIso(),
      mitad: true,
    ),
    const Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
  ],
  alGuardar: (v) async {
    await ref.read(apiProvider).post('/patients/$pacienteId/charges', v);
    ref.invalidate(cuentaProvider(pacienteId));
  },
);

Future<void> financiarCargo(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
  Map<String, dynamic> cargo,
) async {
  final api = ref.read(apiProvider);
  final opciones = await cargarOAvisar(context, api.mapa('/credits/options'));
  if (opciones == null) return;
  if (!context.mounted) return;
  final formas = await cargarOAvisar(
    context,
    ref.read(formasPagoProvider.future),
  );
  if (formas == null) return;
  if (!context.mounted) return;
  final frecuencias = [
    for (final f in (opciones['frequencies'] as List? ?? []))
      ('${f['code']}', '${f['label']}'),
  ];
  final enUnMes = DateTime.now().add(const Duration(days: 30));
  await mostrarFormulario(
    context,
    titulo: 'Financiar en cuotas',
    subtitulo:
        '${cargo['description']} · pendiente ${dinero(numero(cargo['pending']))}',
    icono: Icons.credit_score,
    textoGuardar: 'Crear crédito',
    campos: [
      Campo(
        'installment_count',
        'Número de cuotas',
        tipo: TipoCampo.entero,
        requerido: true,
        inicial: 3,
        mitad: true,
        ayuda: 'Máximo ${opciones['max_installments']}',
      ),
      Campo(
        'frequency',
        'Frecuencia',
        tipo: TipoCampo.seleccion,
        requerido: true,
        opciones: frecuencias,
        inicial: 'mensual',
        mitad: true,
      ),
      Campo(
        'first_due_on',
        'Primera cuota',
        tipo: TipoCampo.fecha,
        requerido: true,
        inicial: enUnMes.toIso8601String().substring(0, 10),
      ),
      Campo(
        'monthly_rate',
        'Interés mensual (%)',
        tipo: TipoCampo.numero,
        inicial: '0',
        mitad: true,
        ayuda: 'Máximo ${opciones['max_monthly_rate']} %',
      ),
      const Campo(
        'down_payment',
        'Entrada',
        tipo: TipoCampo.dinero,
        inicial: '0',
        mitad: true,
      ),
      Campo(
        'down_payment_method',
        'Forma de pago de la entrada',
        tipo: TipoCampo.seleccion,
        opciones: formas,
        inicial: 'efectivo',
      ),
      const Campo('guarantor_name', 'Garante', seccion: 'Garante (opcional)'),
      const Campo('guarantor_id_number', 'Cédula del garante', mitad: true),
      const Campo(
        'guarantor_phone',
        'Teléfono',
        tipo: TipoCampo.telefono,
        mitad: true,
      ),
      const Campo('notes', 'Notas', tipo: TipoCampo.multilinea),
    ],
    alGuardar: (v) async {
      v['charge_id'] = cargo['id'];
      v['monthly_rate'] ??= '0';
      v['down_payment'] ??= '0';
      v['down_payment_method'] ??= 'efectivo';
      await api.post('/patients/$pacienteId/credits', v);
      ref.invalidate(cuentaProvider(pacienteId));
    },
  );
}

void menuCuenta(
  BuildContext context,
  WidgetRef ref,
  String pacienteId,
  List<Map<String, dynamic>> cargos,
) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (hoja) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.payments_outlined),
            title: const Text('Registrar cobro'),
            onTap: () {
              Navigator.pop(hoja);
              registrarCobro(context, ref, pacienteId, cargos: cargos);
            },
          ),
          ListTile(
            leading: const Icon(Icons.receipt_long),
            title: const Text('Nuevo cargo'),
            onTap: () {
              Navigator.pop(hoja);
              nuevoCargo(context, ref, pacienteId);
            },
          ),
        ],
      ),
    ),
  );
}

class PestanaCuenta extends ConsumerWidget {
  const PestanaCuenta({super.key, required this.pacienteId});

  final String pacienteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    final usuario = ref.watch(authProvider).usuario;
    final puedeCobrar = usuario?.puede('payments:write') ?? false;
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(cuentaProvider(pacienteId)),
      child: Asincrono(
        valor: ref.watch(cuentaProvider(pacienteId)),
        alReintentar: () => ref.invalidate(cuentaProvider(pacienteId)),
        listo: (d) {
          final c = d.cuenta;
          final saldo = numero(c['balance']);
          final cargos = (c['charges'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          final pagos = (c['payments'] as List? ?? [])
              .cast<Map<String, dynamic>>();
          Map<String, dynamic>? creditoDe(dynamic cargoId) => d.creditos
              .where(
                (k) => k['charge_id'] == cargoId && k['status'] != 'anulado',
              )
              .firstOrNull;
          final scheme = Theme.of(context).colorScheme;

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              GlassPanel(
                tint: saldo > 0 ? null : scheme.primary,
                padding: const EdgeInsets.all(18),
                child: DefaultTextStyle.merge(
                  style: TextStyle(color: saldo > 0 ? null : Colors.white),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Saldo',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      Text(
                        dinero(saldo),
                        style: TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -1,
                          color: saldo > 0 ? Tonos.rojo : Colors.white,
                        ),
                      ),
                      Text(
                        saldo > 0
                            ? 'El paciente debe'
                            : (saldo < 0
                                  ? 'Saldo a favor del paciente'
                                  : 'Cuenta saldada'),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Cargado ${dinero(numero(c['total_charged']))} · '
                        'pagado ${dinero(numero(c['total_paid']))}'
                        '${numero(c['overdue_amount']) > 0 ? ' · vencido ${dinero(numero(c['overdue_amount']))}' : ''}',
                        style: const TextStyle(fontSize: 12.5),
                      ),
                    ],
                  ),
                ),
              ),
              Seccion('Cargos (${cargos.length})'),
              if (cargos.isEmpty) const _Vacio('Sin cargos registrados'),
              for (final cargo in cargos)
                Builder(
                  builder: (context) {
                    final anulado = cargo['voided_at'] != null;
                    final credito = creditoDe(cargo['id']);
                    final pendiente = numero(cargo['pending']);
                    return FilaTarjeta(
                      icono: Icons.receipt_long,
                      colorIcono: anulado
                          ? Tonos.gris
                          : (pendiente > 0 ? Tonos.ambar : Tonos.verde),
                      titulo: '${cargo['description']}',
                      subtitulo: [
                        fechaCorta(cargo['issued_on']),
                        'pagado ${dinero(numero(cargo['paid']))}',
                        if (credito != null) 'En crédito',
                        if (anulado) 'Anulado: ${cargo['void_reason']}',
                      ].join(' · '),
                      tachado: anulado,
                      derecha: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            dinero(numero(cargo['amount'])),
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          if (!anulado && pendiente > 0)
                            Text(
                              'debe ${dinero(pendiente)}',
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: Tonos.rojo,
                              ),
                            ),
                        ],
                      ),
                      alTocar: anulado || !puedeCobrar
                          ? null
                          : () => showModalBottomSheet<void>(
                              context: context,
                              showDragHandle: true,
                              builder: (hoja) => SafeArea(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (credito != null)
                                      ListTile(
                                        leading: const Icon(Icons.credit_score),
                                        title: const Text('Ver crédito'),
                                        onTap: () {
                                          Navigator.pop(hoja);
                                          abrirCredito(
                                            context,
                                            '${credito['id']}',
                                            alCambiar: () => ref.invalidate(
                                              cuentaProvider(pacienteId),
                                            ),
                                          );
                                        },
                                      )
                                    else if (pendiente > 0) ...[
                                      ListTile(
                                        leading: const Icon(
                                          Icons.payments_outlined,
                                        ),
                                        title: const Text('Cobrar este cargo'),
                                        onTap: () {
                                          Navigator.pop(hoja);
                                          registrarCobro(
                                            context,
                                            ref,
                                            pacienteId,
                                            cargos: cargos,
                                            cargoId: '${cargo['id']}',
                                          );
                                        },
                                      ),
                                      ListTile(
                                        leading: const Icon(Icons.credit_score),
                                        title: const Text(
                                          'Financiar en cuotas',
                                        ),
                                        onTap: () {
                                          Navigator.pop(hoja);
                                          financiarCargo(
                                            context,
                                            ref,
                                            pacienteId,
                                            cargo,
                                          );
                                        },
                                      ),
                                    ],
                                    ListTile(
                                      leading: Icon(
                                        Icons.block,
                                        color: scheme.error,
                                      ),
                                      title: const Text('Anular cargo'),
                                      onTap: () {
                                        Navigator.pop(hoja);
                                        anularConMotivo(
                                          context,
                                          que: 'cargo',
                                          alAnular: (m) async {
                                            await api.post(
                                              '/finance/charges/${cargo['id']}/void',
                                              {'reason': m},
                                            );
                                            ref.invalidate(
                                              cuentaProvider(pacienteId),
                                            );
                                          },
                                        );
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ),
                    );
                  },
                ),
              Seccion('Pagos (${pagos.length})'),
              if (pagos.isEmpty) const _Vacio('Sin pagos registrados'),
              for (final p in pagos)
                FilaTarjeta(
                  icono: Icons.payments_outlined,
                  colorIcono: p['voided_at'] != null ? Tonos.gris : Tonos.verde,
                  titulo: dinero(numero(p['amount'])),
                  subtitulo: [
                    fechaCorta(p['received_on']),
                    '${p['method']}',
                    if (p['reference'] != null) '${p['reference']}',
                    if (p['credit_id'] != null) 'Cuota de crédito',
                    if (p['voided_at'] != null) 'Anulado: ${p['void_reason']}',
                  ].join(' · '),
                  tachado: p['voided_at'] != null,
                  alTocar: p['voided_at'] != null || !puedeCobrar
                      ? null
                      : () => anularConMotivo(
                          context,
                          que: 'pago',
                          alAnular: (m) async {
                            await api.post(
                              '/finance/payments/${p['id']}/void',
                              {'reason': m},
                            );
                            ref.invalidate(cuentaProvider(pacienteId));
                          },
                        ),
                ),
              finDeLista,
            ],
          );
        },
      ),
    );
  }
}
