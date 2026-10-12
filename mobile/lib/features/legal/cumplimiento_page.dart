import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../core/marca/marca.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

final _clinicaProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/clinics/me'),
);
final _solicitudesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/legal/requests'),
);
final _catalogosLegalesProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/legal/catalogs'),
);
final documentoLegalProvider = FutureProvider.autoDispose.family<Map<String, dynamic>, String>(
  (ref, codigo) => ref.watch(apiProvider).mapa('/legal/documents/$codigo'),
);

List<Opcion> _opciones(Map<String, dynamic> cat, String clave) => [
  for (final o in ((cat[clave] as List?) ?? []).cast<Map<String, dynamic>>()) ('${o['code']}', '${o['label']}'),
];

int? _diasHasta(dynamic iso) {
  final d = DateTime.tryParse('${iso ?? ''}');
  if (d == null) return null;
  final hoy = DateTime.now();
  return DateTime(d.year, d.month, d.day).difference(DateTime(hoy.year, hoy.month, hoy.day)).inDays;
}

/// Términos de uso o contrato de encargo: el mismo texto que la web, servido
/// por el servidor.
class DocumentoLegalPage extends ConsumerWidget {
  const DocumentoLegalPage({super.key, required this.codigo});

  final String codigo;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final doc = ref.watch(documentoLegalProvider(codigo));
    return PaginaModulo(
      titulo: codigo == 'terminos' ? 'Términos de uso' : 'Contrato de encargo',
      cuerpo: Asincrono(
        valor: doc,
        alReintentar: () => ref.invalidate(documentoLegalProvider(codigo)),
        listo: (d) => ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
          children: [
            Text('${d['title']}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: -0.5)),
            Text('Versión ${d['version']}', style: TextStyle(color: scheme.onSurface.withValues(alpha: 0.55))),
            for (final s in ((d['sections'] as List?) ?? []).cast<Map<String, dynamic>>()) ...[
              const SizedBox(height: 16),
              Text('${s['title']}', style: TextStyle(fontWeight: FontWeight.w700, color: scheme.primary)),
              for (final p in (s['paragraphs'] as List? ?? []))
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('$p', style: const TextStyle(height: 1.5)),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Configuración › Legal y cumplimiento, igual que en la web.
class CumplimientoPage extends ConsumerWidget {
  const CumplimientoPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 2,
      child: PaginaModulo(
        titulo: 'Legal y cumplimiento',
        inferior: const TabBar(tabs: [Tab(text: 'Configuración'), Tab(text: 'Solicitudes')]),
        cuerpo: const TabBarView(children: [_Configuracion(), _Solicitudes()]),
      ),
    );
  }
}

class _Configuracion extends ConsumerWidget {
  const _Configuracion();

  Future<void> _guardar(WidgetRef ref, Map<String, dynamic> v) async {
    await ref.read(apiProvider).put('/clinics/me', v);
    ref.invalidate(_clinicaProvider);
    await ref.read(marcaProvider.notifier).actualizar();
  }

  void _editarResponsable(BuildContext context, WidgetRef ref, Map<String, dynamic> c) => mostrarFormulario(
    context,
    titulo: 'Responsable y permiso',
    icono: Icons.badge_outlined,
    campos: [
      Campo('legal_name', 'Razón social / nombres', inicial: c['legal_name'], seccion: 'Responsable'),
      Campo('tax_id', 'RUC', inicial: c['tax_id'], mitad: true),
      Campo('phone', 'Teléfono', tipo: TipoCampo.telefono, inicial: c['phone'], mitad: true),
      Campo('address', 'Dirección matriz', inicial: c['address']),
      Campo('email', 'Correo', tipo: TipoCampo.correo, inicial: c['email']),
      Campo('legal_rep_name', 'Nombre', inicial: c['legal_rep_name'], seccion: 'Representante legal', mitad: true),
      Campo('legal_rep_id', 'Cédula', inicial: c['legal_rep_id'], mitad: true),
      Campo('health_permit_number', 'Número de permiso', inicial: c['health_permit_number'], seccion: 'Permiso de funcionamiento (ACESS)', mitad: true),
      Campo('health_permit_expires_on', 'Vence el', tipo: TipoCampo.fecha, inicial: c['health_permit_expires_on'], mitad: true),
    ],
    alGuardar: (v) => _guardar(ref, v),
  );

  Future<void> _editarTributario(BuildContext context, WidgetRef ref, Map<String, dynamic> c) async {
    final cat = await cargarOAvisar(context, ref.read(_catalogosLegalesProvider.future));
    if (cat == null || !context.mounted) return;
    await mostrarFormulario(
      context,
      titulo: 'Datos tributarios (SRI)',
      subtitulo: 'Salen en tus comprobantes. Confírmalos con tu contador.',
      icono: Icons.receipt_long_outlined,
      campos: [
        Campo('tax_regime', 'Régimen', tipo: TipoCampo.seleccion, requerido: true, opciones: _opciones(cat, 'tax_regimes'), inicial: c['tax_regime']),
        Campo('sri_establishment', 'Establecimiento', inicial: c['sri_establishment'], mitad: true, ayuda: 'Tres dígitos, ej. 001'),
        Campo('sri_emission_point', 'Punto de emisión', inicial: c['sri_emission_point'], mitad: true),
        Campo('vat_rate', 'IVA de servicios (%)', tipo: TipoCampo.numero, inicial: c['vat_rate'], mitad: true, ayuda: 'Salud suele ser 0 %'),
        Campo('special_taxpayer', 'Contribuyente especial', inicial: c['special_taxpayer'], mitad: true),
        Campo('keeps_accounting', 'Obligado a llevar contabilidad', tipo: TipoCampo.interruptor, inicial: c['keeps_accounting']),
      ],
      alGuardar: (v) => _guardar(ref, v),
    );
  }

  void _editarDatos(BuildContext context, WidgetRef ref, Map<String, dynamic> c) => mostrarFormulario(
    context,
    titulo: 'Protección de datos',
    subtitulo: 'Lo que se informa al paciente en el aviso de privacidad.',
    icono: Icons.shield_outlined,
    campos: [
      Campo('dpo_name', 'Nombre', inicial: c['dpo_name'], seccion: 'Delegado de protección de datos', mitad: true),
      Campo('dpo_email', 'Correo', tipo: TipoCampo.correo, inicial: c['dpo_email'], mitad: true),
      Campo('record_retention_years', 'Años de conservación de la historia', tipo: TipoCampo.entero, inicial: c['record_retention_years'], seccion: 'Historia clínica'),
      Campo('privacy_extra', 'Cláusulas propias (opcional)', tipo: TipoCampo.multilinea, inicial: c['privacy_extra']),
    ],
    alGuardar: (v) => _guardar(ref, v),
  );

  void _editarSeguridad(BuildContext context, WidgetRef ref, Map<String, dynamic> c) => mostrarFormulario(
    context,
    titulo: 'Seguridad',
    subtitulo: 'Si nadie usa el sistema este tiempo, se cierra la sesión en la web y en el celular.',
    icono: Icons.lock_clock,
    campos: [
      Campo(
        'session_timeout_minutes',
        'Cerrar sesión tras',
        tipo: TipoCampo.seleccion,
        requerido: true,
        inicial: '${c['session_timeout_minutes']}',
        opciones: const [
          ('0', 'Nunca (no recomendado)'),
          ('10', '10 minutos'),
          ('15', '15 minutos'),
          ('30', '30 minutos'),
          ('60', '1 hora'),
          ('120', '2 horas'),
          ('480', '8 horas'),
        ],
      ),
    ],
    alGuardar: (v) => _guardar(ref, {'session_timeout_minutes': int.parse('${v['session_timeout_minutes']}')}),
  );

  Future<void> _aceptarTerminos(BuildContext context, WidgetRef ref) async {
    if (!await confirmar(
      context,
      titulo: 'Aceptar Términos de uso y contrato de encargo',
      mensaje: 'Quedará registrado con tu nombre, la versión y la fecha. ¿Leíste ambos documentos?',
      textoConfirmar: 'Acepto',
    )) {
      return;
    }
    if (!context.mounted) return;
    if (await intentar(context, () => ref.read(apiProvider).post('/clinics/me/accept-terms'), exito: 'Términos aceptados')) {
      ref.invalidate(_clinicaProvider);
      await ref.read(marcaProvider.notifier).actualizar();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(_clinicaProvider),
      child: Asincrono(
        valor: ref.watch(_clinicaProvider),
        alReintentar: () => ref.invalidate(_clinicaProvider),
        esqueleto: const EsqueletoLista(filas: 6, conTarjetas: true),
        listo: (c) {
          final vencidas = (ref.watch(_solicitudesProvider).valueOrNull ?? []).where((s) => s['overdue'] == true).length;
          final dias = _diasHasta(c['health_permit_expires_on']);
          final terminosOk = c['terms_version'] == c['terms_current_version'];
          final puntos = <(bool, String, String, VoidCallback?)>[
            (c['legal_name'] != null && c['tax_id'] != null && c['address'] != null, 'Razón social, RUC y dirección',
                'Salen en recibos, recetas y en el aviso de privacidad.', () => _editarResponsable(context, ref, c)),
            (c['legal_rep_name'] != null, 'Representante legal', 'Quién firma por la consulta.', () => _editarResponsable(context, ref, c)),
            (dias != null && dias >= 0, 'Permiso de funcionamiento vigente',
                dias == null ? 'Registra el número y la fecha de vencimiento.' : dias < 0 ? 'Venció hace ${-dias} días.' : 'Vence en $dias días.',
                () => _editarResponsable(context, ref, c)),
            (c['tax_regime'] != null, 'Datos tributarios', 'Régimen, establecimiento y punto de emisión.', () => _editarTributario(context, ref, c)),
            (c['dpo_name'] != null && c['dpo_email'] != null, 'Delegado de protección de datos',
                'A quién escriben los pacientes sobre sus datos.', () => _editarDatos(context, ref, c)),
            (numero(c['session_timeout_minutes']) > 0, 'Cierre de sesión por inactividad',
                'Hoy: ${numero(c['session_timeout_minutes']).toInt()} min.', () => _editarSeguridad(context, ref, c)),
            (terminosOk, 'Términos y contrato de encargo aceptados', 'Versión vigente ${c['terms_current_version']}.', null),
            (vencidas == 0, 'Solicitudes de pacientes al día', vencidas == 0 ? 'Ninguna fuera de plazo.' : '$vencidas fuera de plazo.',
                () => DefaultTabController.of(context).animateTo(1)),
          ];
          final hechos = puntos.where((p) => p.$1).length;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 62,
                        height: 62,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            SizedBox.expand(
                              child: CircularProgressIndicator(value: hechos / puntos.length, strokeWidth: 7, strokeCap: StrokeCap.round),
                            ),
                            Text('$hechos/${puntos.length}', style: const TextStyle(fontWeight: FontWeight.w800)),
                          ],
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Text(
                          hechos == puntos.length ? 'Todo en regla.' : 'Te faltan ${puntos.length - hechos} puntos. Toca cada uno para completarlo.',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const Seccion('Estado de cumplimiento'),
              for (final (ok, titulo, detalle, accion) in puntos)
                FilaTarjeta(
                  icono: ok ? Icons.check_circle : Icons.radio_button_unchecked,
                  colorIcono: ok ? Tonos.verde : Tonos.ambar,
                  titulo: titulo,
                  subtitulo: detalle,
                  alTocar: accion,
                  derecha: accion == null ? null : const Icon(Icons.chevron_right),
                ),
              const Seccion('Editar'),
              FilaTarjeta(icono: Icons.badge_outlined, titulo: 'Responsable y permiso', alTocar: () => _editarResponsable(context, ref, c)),
              FilaTarjeta(icono: Icons.receipt_long_outlined, titulo: 'Tributario (SRI)', alTocar: () => _editarTributario(context, ref, c)),
              FilaTarjeta(icono: Icons.shield_outlined, titulo: 'Protección de datos', alTocar: () => _editarDatos(context, ref, c)),
              FilaTarjeta(icono: Icons.lock_clock, titulo: 'Seguridad', alTocar: () => _editarSeguridad(context, ref, c)),
              const Seccion('Términos'),
              FilaTarjeta(
                icono: Icons.description_outlined,
                titulo: 'Términos de uso del sistema',
                derecha: const Icon(Icons.chevron_right),
                alTocar: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const DocumentoLegalPage(codigo: 'terminos'))),
              ),
              FilaTarjeta(
                icono: Icons.handshake_outlined,
                titulo: 'Contrato de encargo de tratamiento',
                derecha: const Icon(Icons.chevron_right),
                alTocar: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const DocumentoLegalPage(codigo: 'encargo'))),
              ),
              if (terminosOk)
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 4, 4, 0),
                  child: Text(
                    'Aceptados por ${c['terms_accepted_by']} el ${fechaHora(c['terms_accepted_at'])}.',
                    style: const TextStyle(fontSize: 12.5),
                  ),
                )
              else
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: FilledButton.icon(
                    onPressed: () => _aceptarTerminos(context, ref),
                    icon: const Icon(Icons.gavel),
                    label: Text('Leí y acepto la versión ${c['terms_current_version']}'),
                  ),
                ),
              const SizedBox(height: 14),
              Text(
                'Esta guía sigue la normativa del Ecuador (LOPDP, SRI y ACESS). No reemplaza la asesoría de un abogado o contador.',
                style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.55)),
              ),
              finDeLista,
            ],
          );
        },
      ),
    );
  }
}

Future<void> editarSolicitud(BuildContext context, WidgetRef ref, Map<String, dynamic>? s) async {
  final api = ref.read(apiProvider);
  final cat = await cargarOAvisar(context, ref.read(_catalogosLegalesProvider.future));
  if (cat == null || !context.mounted) return;
  await mostrarFormulario(
    context,
    titulo: s == null ? 'Nueva solicitud' : 'Solicitud de ${s['requester_name']}',
    subtitulo: 'Un paciente pide acceder, corregir o eliminar sus datos. Plazo: 15 días.',
    icono: Icons.inbox_outlined,
    campos: [
      Campo('patient_id', 'Paciente (opcional)', tipo: TipoCampo.buscar, buscar: buscadorPacientes(api),
          inicial: s?['patient_id'], inicialEtiqueta: s?['patient_name'] as String?),
      Campo('requester_name', 'Solicitante', requerido: true, inicial: s?['requester_name']),
      Campo('requester_id_number', 'Cédula', inicial: s?['requester_id_number'], mitad: true),
      Campo('contact', 'Contacto', inicial: s?['contact'], mitad: true),
      Campo('kind', 'Tipo', tipo: TipoCampo.seleccion, requerido: true, opciones: _opciones(cat, 'rights_kinds'), inicial: s?['kind'] ?? 'acceso', mitad: true),
      Campo('received_on', 'Recibida el', tipo: TipoCampo.fecha, requerido: true, inicial: s?['received_on'] ?? hoyIso(), mitad: true),
      Campo('status', 'Estado', tipo: TipoCampo.seleccion, requerido: true, opciones: _opciones(cat, 'rights_statuses'), inicial: s?['status'] ?? 'pendiente'),
      Campo('details', 'Qué pide', tipo: TipoCampo.multilinea, inicial: s?['details']),
      Campo('response', 'Respuesta dada', tipo: TipoCampo.multilinea, inicial: s?['response']),
    ],
    alGuardar: (v) async {
      if (s == null) {
        await api.post('/legal/requests', v);
      } else {
        await api.put('/legal/requests/${s['id']}', v);
      }
      ref.invalidate(_solicitudesProvider);
    },
  );
}

class _Solicitudes extends ConsumerWidget {
  const _Solicitudes();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.read(apiProvider);
    return Stack(
      children: [
        RefreshIndicator(
          onRefresh: () async => ref.invalidate(_solicitudesProvider),
          child: Asincrono(
            valor: ref.watch(_solicitudesProvider),
            alReintentar: () => ref.invalidate(_solicitudesProvider),
            listo: (lista) => lista.isEmpty
                ? ListView(
                    children: const [
                      EstadoVacio(
                        icono: Icons.inbox_outlined,
                        titulo: 'Sin solicitudes',
                        detalle: 'Cuando un paciente pida ver, corregir o eliminar sus datos, regístralo aquí.',
                      ),
                    ],
                  )
                : ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      for (final s in lista)
                        FilaTarjeta(
                          icono: Icons.inbox_outlined,
                          colorIcono: s['overdue'] == true
                              ? Tonos.rojo
                              : s['days_left'] == null
                              ? Tonos.verde
                              : Tonos.ambar,
                          titulo: '${s['requester_name']}',
                          subtitulo: [
                            '${s['kind_label']}',
                            fechaCorta(s['received_on']),
                            if (s['overdue'] == true)
                              'Vencida hace ${-(s['days_left'] as num)} días'
                            else if (s['days_left'] != null)
                              'Quedan ${s['days_left']} días',
                          ].join(' · '),
                          derecha: Pastilla('${s['status_label']}', color: s['days_left'] == null ? Tonos.verde : Tonos.ambar),
                          alTocar: () => showModalBottomSheet<void>(
                            context: context,
                            showDragHandle: true,
                            builder: (hoja) => SafeArea(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  ListTile(
                                    leading: const Icon(Icons.edit_outlined),
                                    title: const Text('Editar / responder'),
                                    onTap: () {
                                      Navigator.pop(hoja);
                                      editarSolicitud(context, ref, s);
                                    },
                                  ),
                                  ListTile(
                                    leading: Icon(Icons.delete_outline, color: Theme.of(context).colorScheme.error),
                                    title: const Text('Eliminar'),
                                    onTap: () async {
                                      Navigator.pop(hoja);
                                      if (await confirmar(context, titulo: '¿Eliminar la solicitud?', textoConfirmar: 'Eliminar', peligro: true) &&
                                          context.mounted &&
                                          await intentar(context, () => api.delete('/legal/requests/${s['id']}'))) {
                                        ref.invalidate(_solicitudesProvider);
                                      }
                                    },
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      finDeLista,
                    ],
                  ),
          ),
        ),
        Positioned(
          right: 16,
          bottom: 16 + MediaQuery.paddingOf(context).bottom,
          child: FloatingActionButton.extended(
            heroTag: 'nueva-solicitud',
            onPressed: () => editarSolicitud(context, ref, null),
            icon: const Icon(Icons.add),
            label: const Text('Solicitud'),
          ),
        ),
      ],
    );
  }
}
