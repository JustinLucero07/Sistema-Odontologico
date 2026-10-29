import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/carga.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

/// Roles y permisos, plantillas de mensajes y plantillas de consentimiento:
/// las mismas pantallas de configuración que la web.

// ------------------------------------------------------------------- Roles

const _modulos = {
  'appointments': 'Agenda',
  'audit': 'Auditoría',
  'budgets': 'Presupuestos',
  'consents': 'Consentimientos',
  'diagnoses': 'Diagnósticos',
  'documents': 'Documentos',
  'evolutions': 'Evoluciones',
  'imaging': 'Imágenes',
  'inventory': 'Inventario',
  'laboratory': 'Laboratorio',
  'medical_history': 'Historia médica',
  'odontogram': 'Odontograma',
  'patients': 'Pacientes',
  'payments': 'Caja y pagos',
  'periodontogram': 'Periodontograma',
  'prescriptions': 'Recetas',
  'reports': 'Reportes',
  'roles': 'Roles',
  'settings': 'Configuración',
  'treatments': 'Tratamientos',
  'users': 'Usuarios',
};

final rolesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/roles'),
);
final _permisosProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/permissions'),
);

class RolesPage extends ConsumerWidget {
  const RolesPage({super.key});

  /// Nuevo rol (opcionalmente copia de otro) o edición de nombre y descripción.
  Future<void> _editar(BuildContext context, WidgetRef ref, {Map<String, dynamic>? rol, Map<String, dynamic>? copiaDe}) async {
    final roles = await cargarOAvisar(context, ref.read(rolesProvider.future));
    if (roles == null || !context.mounted) return;
    await mostrarFormulario(
      context,
      titulo: rol == null ? 'Nuevo rol' : 'Editar rol',
      subtitulo: rol == null ? 'Después ajuste sus permisos y guarde.' : null,
      icono: Icons.admin_panel_settings_outlined,
      campos: [
        Campo('name', 'Nombre', requerido: true, inicial: rol?['name'] ?? (copiaDe == null ? null : '${copiaDe['name']} (copia)')),
        Campo('description', 'Descripción', tipo: TipoCampo.multilinea, inicial: rol?['description']),
        if (rol == null)
          Campo(
            'copy_from',
            'Copiar permisos de',
            tipo: TipoCampo.seleccion,
            opciones: [('', 'Ninguno (empezar vacío)'), for (final r in roles) ('${r['id']}', '${r['name']}')],
            inicial: copiaDe?['id'] ?? '',
          ),
      ],
      alGuardar: (v) async {
        final api = ref.read(apiProvider);
        final datos = {
          'name': '${v['name']}'.trim(),
          'description': '${v['description'] ?? ''}'.trim().isEmpty ? null : '${v['description']}'.trim(),
        };
        if (rol != null) {
          await api.put('/roles/${rol['id']}', datos);
        } else {
          final fuente = roles.where((r) => r['id'] == v['copy_from']).firstOrNull;
          await api.post('/roles', {
            ...datos,
            'permission_codes': [for (final p in (fuente?['permissions'] as List? ?? [])) '${(p as Map)['code']}'],
          });
        }
        ref.invalidate(rolesProvider);
      },
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PaginaModulo(
      titulo: 'Roles y permisos',
      accion: FloatingActionButton.extended(
        onPressed: () => _editar(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('Rol'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(rolesProvider),
        child: Asincrono(
          valor: ref.watch(rolesProvider),
          alReintentar: () => ref.invalidate(rolesProvider),
          listo: (lista) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final r in lista)
                FilaTarjeta(
                  icono: r['is_system'] == true ? Icons.verified_user_outlined : Icons.admin_panel_settings_outlined,
                  titulo: '${r['name']}',
                  subtitulo: [
                    '${(r['permissions'] as List? ?? []).length} permisos',
                    if (r['is_system'] == true) 'del sistema',
                    if ('${r['description'] ?? ''}'.isNotEmpty) '${r['description']}',
                  ].join(' · '),
                  alTocar: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => RolPermisosPage(rolId: '${r['id']}')),
                  ),
                  derecha: PopupMenuButton<String>(
                    onSelected: (o) async {
                      switch (o) {
                        case 'editar':
                          await _editar(context, ref, rol: r);
                        case 'duplicar':
                          await _editar(context, ref, copiaDe: r);
                        case 'eliminar':
                          if (!await confirmar(
                            context,
                            titulo: '¿Eliminar el rol «${r['name']}»?',
                            mensaje: 'Solo se puede si ningún usuario lo tiene asignado.',
                            textoConfirmar: 'Eliminar',
                            peligro: true,
                          )) {
                            return;
                          }
                          if (!context.mounted) return;
                          if (await intentar(context, () => ref.read(apiProvider).delete('/roles/${r['id']}'), exito: 'Rol eliminado')) {
                            ref.invalidate(rolesProvider);
                          }
                      }
                    },
                    itemBuilder: (_) => [
                      if (r['is_system'] != true) const PopupMenuItem(value: 'editar', child: Text('Editar nombre')),
                      const PopupMenuItem(value: 'duplicar', child: Text('Duplicar')),
                      if (r['is_system'] != true) const PopupMenuItem(value: 'eliminar', child: Text('Eliminar')),
                    ],
                  ),
                ),
              finDeLista,
            ],
          ),
        ),
      ),
    );
  }
}

/// Permisos de un rol, agrupados por módulo. Los roles del sistema se ven
/// pero no se cambian: para personalizarlos se duplican.
class RolPermisosPage extends ConsumerStatefulWidget {
  const RolPermisosPage({super.key, required this.rolId});

  final String rolId;

  @override
  ConsumerState<RolPermisosPage> createState() => _RolPermisosPageState();
}

class _RolPermisosPageState extends ConsumerState<RolPermisosPage> {
  Set<String>? _marcados;
  bool _guardando = false;

  @override
  Widget build(BuildContext context) {
    final roles = ref.watch(rolesProvider);
    final permisos = ref.watch(_permisosProvider);
    final rol = roles.valueOrNull?.where((r) => r['id'] == widget.rolId).firstOrNull;
    final sistema = rol?['is_system'] == true;
    _marcados ??= rol == null ? null : {for (final p in (rol['permissions'] as List? ?? [])) '${(p as Map)['code']}'};
    final original = {for (final p in (rol?['permissions'] as List? ?? [])) '${(p as Map)['code']}'};
    final cambiado = _marcados != null && (_marcados!.length != original.length || !_marcados!.containsAll(original));

    return PaginaModulo(
      titulo: '${rol?['name'] ?? 'Rol'}',
      acciones: [
        if (!sistema && cambiado)
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: FilledButton(
              style: FilledButton.styleFrom(minimumSize: const Size(96, 40)),
              onPressed: _guardando
                  ? null
                  : () async {
                      setState(() => _guardando = true);
                      final ok = await intentar(
                        context,
                        () => ref.read(apiProvider).put('/roles/${widget.rolId}', {'permission_codes': _marcados!.toList()}),
                        exito: 'Permisos actualizados',
                      );
                      if (!mounted) return;
                      setState(() => _guardando = false);
                      if (ok) {
                        ref.invalidate(rolesProvider);
                        _marcados = null;
                      }
                    },
              child: Text(_guardando ? 'Guardando…' : 'Guardar'),
            ),
          ),
      ],
      cuerpo: Asincrono(
        valor: permisos,
        alReintentar: () => ref.invalidate(_permisosProvider),
        listo: (lista) {
          if (rol == null || _marcados == null) return const EsqueletoLista();
          final grupos = <String, List<Map<String, dynamic>>>{};
          for (final p in lista) {
            grupos.putIfAbsent('${p['module']}', () => []).add(p);
          }
          final orden = grupos.keys.toList()
            ..sort((a, b) => (_modulos[a] ?? a).compareTo(_modulos[b] ?? b));
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              if (sistema)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    'Rol del sistema: sus permisos no se cambian. Duplíquelo desde la lista para personalizarlo.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              for (final m in orden) ...[
                Seccion(_modulos[m] ?? m),
                GlassCard(
                  child: Column(
                    children: [
                      for (final p in grupos[m]!)
                        CheckboxListTile(
                          dense: true,
                          value: _marcados!.contains(p['code']),
                          onChanged: sistema
                              ? null
                              : (v) => setState(() => v == true ? _marcados!.add('${p['code']}') : _marcados!.remove(p['code'])),
                          title: Text('${p['description']}', style: const TextStyle(fontSize: 14)),
                          subtitle: Text('${p['code']}', style: const TextStyle(fontSize: 11.5)),
                        ),
                    ],
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

// ------------------------------------------------------ Plantillas de mensaje

const _variables = {
  '{paciente}': 'Lucía',
  '{nombre_completo}': 'Lucía Arce',
  '{clinica}': 'su clínica',
  '{fecha}': '27/09/2026',
  '{hora}': '11:00',
};

String _vistaPrevia(String cuerpo) => _variables.entries.fold(cuerpo, (t, e) => t.replaceAll(e.key, e.value));

final _plantillasProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/messaging/templates'),
);

class PlantillasMensajePage extends ConsumerWidget {
  const PlantillasMensajePage({super.key});

  /// El servidor guarda la plantilla por código; uno nuevo sale del nombre.
  String _codigo(String nombre, Set<String> usados) {
    const acentos = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n'};
    var base = nombre.toLowerCase().split('').map((c) => acentos[c] ?? c).join();
    base = base.replaceAll(RegExp(r'[^a-z0-9]+'), '_').replaceAll(RegExp(r'^_|_$'), '');
    if (base.isEmpty) base = 'plantilla';
    var codigo = base;
    var n = 2;
    while (usados.contains(codigo)) {
      codigo = '${base}_${n++}';
    }
    return codigo;
  }

  Future<void> _editar(BuildContext context, WidgetRef ref, List<Map<String, dynamic>> todas, Map<String, dynamic>? t) =>
      mostrarFormulario(
        context,
        titulo: t == null ? 'Nueva plantilla' : 'Editar plantilla',
        subtitulo: 'Variables: ${_variables.keys.join('  ')}',
        icono: Icons.chat_outlined,
        campos: [
          Campo('name', 'Nombre', requerido: true, inicial: t?['name']),
          Campo(
            'channel',
            'Canal',
            tipo: TipoCampo.seleccion,
            requerido: true,
            opciones: const [('whatsapp', 'WhatsApp'), ('email', 'Correo')],
            inicial: t?['channel'] ?? 'whatsapp',
          ),
          Campo('body', 'Texto', tipo: TipoCampo.multilinea, requerido: true, inicial: t?['body'], ayuda: 'Ej.: Hola {paciente}, le recordamos su cita el {fecha} a las {hora}.'),
        ],
        alGuardar: (v) async {
          await ref.read(apiProvider).put('/messaging/templates', {
            'code': t?['code'] ?? _codigo('${v['name']}', {for (final x in todas) '${x['code']}'}),
            'name': '${v['name']}'.trim(),
            'channel': v['channel'],
            'body': v['body'],
            'is_active': t?['is_active'] ?? true,
          });
          ref.invalidate(_plantillasProvider);
        },
      );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final valor = ref.watch(_plantillasProvider);
    return PaginaModulo(
      titulo: 'Plantillas de mensajes',
      accion: FloatingActionButton.extended(
        onPressed: () => _editar(context, ref, valor.valueOrNull ?? const [], null),
        icon: const Icon(Icons.add),
        label: const Text('Plantilla'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_plantillasProvider),
        child: Asincrono(
          valor: valor,
          alReintentar: () => ref.invalidate(_plantillasProvider),
          listo: (lista) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (lista.isEmpty) const EstadoVacio(icono: Icons.chat_outlined, titulo: 'Sin plantillas'),
              for (final t in lista)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Opacity(
                    opacity: t['is_active'] == false ? 0.55 : 1,
                    child: GlassCard(
                      onTap: () => _editar(context, ref, lista, t),
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(16, 14, 6, 14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('${t['name']}', style: estiloTitulo(15.5)),
                                      Text(
                                        '${t['channel'] == 'email' ? 'Correo' : 'WhatsApp'} · ${t['code']}',
                                        style: Theme.of(context).textTheme.bodySmall,
                                      ),
                                    ],
                                  ),
                                ),
                                Pastilla(t['is_active'] == false ? 'Inactiva' : 'Activa', color: t['is_active'] == false ? Tonos.gris : Tonos.verde),
                                PopupMenuButton<String>(
                                  onSelected: (_) async {
                                    final copia = {
                                      for (final k in ['code', 'name', 'channel', 'body']) k: t[k],
                                      'is_active': t['is_active'] == false,
                                    };
                                    if (await intentar(context, () => ref.read(apiProvider).put('/messaging/templates', copia))) {
                                      ref.invalidate(_plantillasProvider);
                                    }
                                  },
                                  itemBuilder: (_) => [
                                    PopupMenuItem(value: 'estado', child: Text(t['is_active'] == false ? 'Activar' : 'Desactivar')),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            Container(
                              margin: const EdgeInsets.only(right: 10),
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                              decoration: BoxDecoration(
                                color: const Color(0xFF25D366).withValues(alpha: 0.12),
                                borderRadius: const BorderRadius.only(
                                  topLeft: Radius.circular(16),
                                  topRight: Radius.circular(16),
                                  bottomRight: Radius.circular(16),
                                  bottomLeft: Radius.circular(4),
                                ),
                              ),
                              child: Text(_vistaPrevia('${t['body']}'), style: const TextStyle(fontSize: 13.5, height: 1.45)),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              finDeLista,
            ],
          ),
        ),
      ),
    );
  }
}

// ------------------------------------------------ Plantillas de consentimiento

final _consentimientosProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/consents/templates', query: {'include_inactive': true}),
);

class PlantillasConsentimientoPage extends ConsumerStatefulWidget {
  const PlantillasConsentimientoPage({super.key});

  @override
  ConsumerState<PlantillasConsentimientoPage> createState() => _PlantillasConsentimientoPageState();
}

class _PlantillasConsentimientoPageState extends ConsumerState<PlantillasConsentimientoPage> {
  bool _retiradas = false;

  Future<void> _editar(Map<String, dynamic>? t) => mostrarFormulario(
    context,
    titulo: t == null ? 'Nueva plantilla' : 'Editar plantilla',
    subtitulo: 'Lo ya firmado conserva el texto con el que se firmó.',
    icono: Icons.draw_outlined,
    campos: [
      Campo('name', 'Nombre', requerido: true, inicial: t?['name']),
      Campo('procedure_type', 'Procedimiento', inicial: t?['procedure_type'], ayuda: 'Ej.: endodoncia, exodoncia, implante'),
      Campo('body', 'Texto del consentimiento', tipo: TipoCampo.multilinea, requerido: true, inicial: t?['body']),
    ],
    alGuardar: (v) async {
      final datos = {
        'name': '${v['name']}'.trim(),
        'procedure_type': '${v['procedure_type'] ?? ''}'.trim().isEmpty ? null : '${v['procedure_type']}'.trim(),
        'body': v['body'],
      };
      final api = ref.read(apiProvider);
      if (t == null) {
        await api.post('/consents/templates', datos);
      } else {
        await api.put('/consents/templates/${t['id']}', {...datos, 'is_active': t['is_active']});
      }
      ref.invalidate(_consentimientosProvider);
    },
  );

  @override
  Widget build(BuildContext context) {
    final valor = ref.watch(_consentimientosProvider);
    return PaginaModulo(
      titulo: 'Plantillas de consentimiento',
      accion: FloatingActionButton.extended(
        onPressed: () => _editar(null),
        icon: const Icon(Icons.add),
        label: const Text('Plantilla'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_consentimientosProvider),
        child: Asincrono(
          valor: valor,
          alReintentar: () => ref.invalidate(_consentimientosProvider),
          listo: (lista) {
            final retiradas = lista.where((t) => t['is_active'] == false).length;
            final visibles = lista.where((t) => _retiradas || t['is_active'] != false).toList();
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (retiradas > 0)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: FilterChip(
                      label: Text('Mostrar retiradas ($retiradas)'),
                      selected: _retiradas,
                      onSelected: (v) => setState(() => _retiradas = v),
                    ),
                  ),
                const SizedBox(height: 8),
                if (visibles.isEmpty) const EstadoVacio(icono: Icons.draw_outlined, titulo: 'Sin plantillas'),
                for (final t in visibles)
                  FilaTarjeta(
                    icono: Icons.description_outlined,
                    colorIcono: t['is_active'] == false ? Tonos.gris : null,
                    titulo: '${t['name']}',
                    subtitulo: [
                      if ('${t['procedure_type'] ?? ''}'.isNotEmpty) '${t['procedure_type']}',
                      _resumen('${t['body'] ?? ''}'),
                    ].join(' · '),
                    tachado: t['is_active'] == false,
                    alTocar: () => _editar(t),
                    derecha: PopupMenuButton<String>(
                      onSelected: (_) async {
                        final datos = {
                          for (final k in ['name', 'procedure_type', 'body']) k: t[k],
                          'is_active': t['is_active'] == false,
                        };
                        if (await intentar(
                          context,
                          () => ref.read(apiProvider).put('/consents/templates/${t['id']}', datos),
                          exito: t['is_active'] == false ? 'Plantilla restaurada' : 'Plantilla retirada',
                        )) {
                          ref.invalidate(_consentimientosProvider);
                        }
                      },
                      itemBuilder: (_) => [
                        PopupMenuItem(value: 'estado', child: Text(t['is_active'] == false ? 'Restaurar' : 'Retirar')),
                      ],
                    ),
                  ),
                finDeLista,
              ],
            );
          },
        ),
      ),
    );
  }

  String _resumen(String texto) => texto.length > 90 ? '${texto.substring(0, 90).trimRight()}…' : texto;
}
