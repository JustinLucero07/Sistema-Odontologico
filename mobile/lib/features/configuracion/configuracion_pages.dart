import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api.dart';
import '../../core/api/catalogos.dart';
import '../../shared/formato.dart';
import '../../shared/widgets/estado_vacio.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

// ---------------------------------------------------------------- Tratamientos

class TratamientosPage extends ConsumerWidget {
  const TratamientosPage({super.key});

  Future<void> _editar(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic>? t,
  ) => mostrarFormulario(
    context,
    titulo: t == null ? 'Nuevo tratamiento' : 'Editar tratamiento',
    subtitulo: 'Catálogo de procedimientos y su precio base.',
    icono: Icons.medical_services_outlined,
    campos: [
      Campo('name', 'Nombre', requerido: true, inicial: t?['name']),
      Campo(
        'default_price',
        'Precio base',
        tipo: TipoCampo.dinero,
        requerido: true,
        inicial: t?['default_price'] ?? '0',
      ),
      Campo(
        'description',
        'Descripción',
        tipo: TipoCampo.multilinea,
        inicial: t?['description'],
      ),
      if (t != null)
        Campo(
          'is_active',
          'Activo',
          tipo: TipoCampo.interruptor,
          inicial: t['is_active'] ?? true,
        ),
    ],
    alGuardar: (v) async {
      final api = ref.read(apiProvider);
      if (t == null) {
        await api.post('/treatments', v);
      } else {
        await api.put('/treatments/${t['id']}', v);
      }
      ref.invalidate(tratamientosCatalogoProvider);
    },
  );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PaginaModulo(
      titulo: 'Tratamientos',
      accion: FloatingActionButton.extended(
        onPressed: () => _editar(context, ref, null),
        icon: const Icon(Icons.add),
        label: const Text('Tratamiento'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(tratamientosCatalogoProvider),
        child: Asincrono(
          valor: ref.watch(tratamientosCatalogoProvider),
          alReintentar: () => ref.invalidate(tratamientosCatalogoProvider),
          listo: (lista) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (lista.isEmpty)
                const EstadoVacio(
                  icono: Icons.medical_services_outlined,
                  titulo: 'Sin tratamientos en el catálogo',
                ),
              for (final t in lista)
                FilaTarjeta(
                  icono: Icons.medical_services_outlined,
                  titulo: '${t['name']}',
                  subtitulo: t['description'] as String?,
                  tachado: t['is_active'] == false,
                  derecha: Text(
                    dinero(numero(t['default_price'])),
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  alTocar: () => _editar(context, ref, t),
                ),
              finDeLista,
            ],
          ),
        ),
      ),
    );
  }
}

// --------------------------------------------------------------- Profesionales

final _especialidadesProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref.watch(apiProvider).lista('/specialties'),
    );

const _coloresAgenda = <Opcion>[
  ('#0F6FFF', 'Azul'),
  ('#0D7F76', 'Verde azulado'),
  ('#7B5BD6', 'Violeta'),
  ('#D0453A', 'Rojo'),
  ('#C98A1E', 'Ámbar'),
  ('#2B9A5B', 'Verde'),
  ('#D81B60', 'Rosa'),
  ('#455A64', 'Gris azulado'),
];

Color _hex(String? h) {
  final v = int.tryParse((h ?? '#0F6FFF').replaceFirst('#', ''), radix: 16);
  return Color(0xFF000000 | (v ?? 0x0F6FFF));
}

class ProfesionalesPage extends ConsumerWidget {
  const ProfesionalesPage({super.key});

  Future<void> _editar(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic>? p,
  ) async {
    final especialidades = await cargarOAvisar(
      context,
      ref.read(_especialidadesProvider.future),
    );
    if (especialidades == null) return;
    if (!context.mounted) return;
    await mostrarFormulario(
      context,
      titulo: p == null ? 'Nuevo profesional' : 'Editar profesional',
      icono: Icons.badge_outlined,
      campos: [
        Campo(
          'first_name',
          'Nombres',
          requerido: true,
          inicial: p?['first_name'],
          mitad: true,
        ),
        Campo(
          'last_name',
          'Apellidos',
          requerido: true,
          inicial: p?['last_name'],
          mitad: true,
        ),
        Campo(
          'specialty_id',
          'Especialidad',
          tipo: TipoCampo.seleccion,
          opciones: [
            for (final e in especialidades) ('${e['id']}', '${e['name']}'),
          ],
          inicial: p?['specialty_id'],
        ),
        Campo(
          'license_number',
          'Registro profesional',
          inicial: p?['license_number'],
          mitad: true,
        ),
        Campo(
          'color_hex',
          'Color en la agenda',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: _coloresAgenda,
          inicial: p?['color_hex'] ?? '#0F6FFF',
          mitad: true,
        ),
        if (p != null)
          Campo(
            'is_active',
            'Activo',
            tipo: TipoCampo.interruptor,
            inicial: p['is_active'] ?? true,
          ),
      ],
      alGuardar: (v) async {
        final api = ref.read(apiProvider);
        if (p == null) {
          await api.post('/professionals', v);
        } else {
          await api.put('/professionals/${p['id']}', v);
        }
        ref.invalidate(profesionalesProvider);
      },
    );
  }

  Future<void> _nuevaEspecialidad(BuildContext context, WidgetRef ref) =>
      mostrarFormulario(
        context,
        titulo: 'Nueva especialidad',
        icono: Icons.category_outlined,
        campos: const [Campo('name', 'Nombre', requerido: true)],
        alGuardar: (v) async {
          await ref.read(apiProvider).post('/specialties', v);
          ref.invalidate(_especialidadesProvider);
        },
      );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final especialidades = ref.watch(_especialidadesProvider).value ?? [];
    String especialidad(dynamic id) =>
        especialidades
            .where((e) => e['id'] == id)
            .map((e) => '${e['name']}')
            .firstOrNull ??
        'Sin especialidad';

    return PaginaModulo(
      titulo: 'Profesionales',
      accion: FloatingActionButton.extended(
        onPressed: () => _editar(context, ref, null),
        icon: const Icon(Icons.add),
        label: const Text('Profesional'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(profesionalesProvider),
        child: Asincrono(
          valor: ref.watch(profesionalesProvider),
          alReintentar: () => ref.invalidate(profesionalesProvider),
          listo: (lista) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final p in lista)
                FilaTarjeta(
                  icono: Icons.badge_outlined,
                  colorIcono: _hex(p['color_hex'] as String?),
                  titulo: '${p['first_name']} ${p['last_name']}',
                  subtitulo: [
                    especialidad(p['specialty_id']),
                    if (p['license_number'] != null)
                      'Reg. ${p['license_number']}',
                  ].join(' · '),
                  tachado: p['is_active'] == false,
                  derecha: const Icon(Icons.edit_outlined, size: 20),
                  alTocar: () => _editar(context, ref, p),
                ),
              Seccion(
                'Especialidades',
                accion: TextButton.icon(
                  onPressed: () => _nuevaEspecialidad(context, ref),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Nueva'),
                ),
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final e in especialidades)
                    ActionChip(
                      label: Text('${e['name']}'),
                      onPressed: () => mostrarFormulario(
                        context,
                        titulo: 'Renombrar especialidad',
                        icono: Icons.category_outlined,
                        campos: [
                          Campo(
                            'name',
                            'Nombre',
                            requerido: true,
                            inicial: e['name'],
                          ),
                        ],
                        alGuardar: (v) async {
                          await ref
                              .read(apiProvider)
                              .put('/specialties/${e['id']}', v);
                          ref.invalidate(_especialidadesProvider);
                        },
                      ),
                    ),
                ],
              ),
              finDeLista,
            ],
          ),
        ),
      ),
    );
  }
}

// -------------------------------------------------------------------- Usuarios

final _usuariosProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>(
      (ref) => ref.watch(apiProvider).lista('/users'),
    );
final _rolesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(apiProvider).lista('/roles'),
);

class UsuariosPage extends ConsumerWidget {
  const UsuariosPage({super.key});

  Future<void> _editar(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic>? u,
  ) async {
    final roles = await cargarOAvisar(context, ref.read(_rolesProvider.future));
    if (roles == null) return;
    if (!context.mounted) return;
    final rolActual = u == null
        ? null
        : (u['roles'] as List? ?? [])
              .map((r) => '${(r as Map)['id']}')
              .firstOrNull;
    await mostrarFormulario(
      context,
      titulo: u == null ? 'Nuevo usuario' : 'Editar usuario',
      subtitulo: u == null
          ? 'Deberá cambiar la contraseña temporal al entrar.'
          : 'Deje la contraseña vacía para no cambiarla.',
      icono: Icons.person_add_alt,
      campos: [
        Campo(
          'first_name',
          'Nombres',
          requerido: true,
          inicial: u?['first_name'],
          mitad: true,
        ),
        Campo(
          'last_name',
          'Apellidos',
          requerido: true,
          inicial: u?['last_name'],
          mitad: true,
        ),
        if (u == null)
          const Campo(
            'email',
            'Correo',
            tipo: TipoCampo.correo,
            requerido: true,
          ),
        Campo(
          'password',
          u == null ? 'Contraseña temporal' : 'Nueva contraseña',
          requerido: u == null,
          ayuda: 'Mínimo 8 caracteres, con letras y números.',
        ),
        Campo(
          'rol',
          'Rol',
          tipo: TipoCampo.seleccion,
          requerido: true,
          opciones: [for (final r in roles) ('${r['id']}', '${r['name']}')],
          inicial: rolActual,
        ),
        if (u != null)
          Campo(
            'is_active',
            'Activo',
            tipo: TipoCampo.interruptor,
            inicial: u['is_active'] ?? true,
          ),
      ],
      alGuardar: (v) async {
        final api = ref.read(apiProvider);
        final datos = {
          ...v,
          'role_ids': [v.remove('rol')],
        };
        if (datos['password'] == null) datos.remove('password');
        if (u == null) {
          await api.post('/users', datos);
        } else {
          await api.put('/users/${u['id']}', datos);
        }
        ref.invalidate(_usuariosProvider);
      },
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PaginaModulo(
      titulo: 'Usuarios',
      accion: FloatingActionButton.extended(
        onPressed: () => _editar(context, ref, null),
        icon: const Icon(Icons.add),
        label: const Text('Usuario'),
      ),
      cuerpo: RefreshIndicator(
        onRefresh: () async => ref.invalidate(_usuariosProvider),
        child: Asincrono(
          valor: ref.watch(_usuariosProvider),
          alReintentar: () => ref.invalidate(_usuariosProvider),
          listo: (lista) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final u in lista)
                FilaTarjeta(
                  icono: Icons.person_outline,
                  titulo: '${u['first_name']} ${u['last_name']}',
                  subtitulo:
                      '${u['email']} · ${(u['roles'] as List? ?? []).map((r) => (r as Map)['name']).join(', ')}',
                  tachado: u['is_active'] == false,
                  derecha: u['is_active'] == false
                      ? const Pastilla('Inactivo', color: Tonos.gris)
                      : const Icon(Icons.edit_outlined, size: 20),
                  alTocar: () => _editar(context, ref, u),
                ),
              finDeLista,
            ],
          ),
        ),
      ),
    );
  }
}

// ------------------------------------------------------------- Datos clínica

final _clinicaProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) => ref.watch(apiProvider).mapa('/clinics/me'),
);

class ClinicaPage extends ConsumerWidget {
  const ClinicaPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    Future<void> editar(Map<String, dynamic> c) => mostrarFormulario(
      context,
      titulo: 'Datos de la clínica',
      subtitulo: 'Aparecen en recetas, presupuestos y avisos legales.',
      icono: Icons.store_outlined,
      campos: [
        Campo('name', 'Nombre comercial', requerido: true, inicial: c['name']),
        Campo('legal_name', 'Razón social', inicial: c['legal_name']),
        Campo('tax_id', 'RUC', inicial: c['tax_id'], mitad: true),
        Campo(
          'phone',
          'Teléfono',
          tipo: TipoCampo.telefono,
          inicial: c['phone'],
          mitad: true,
        ),
        Campo('email', 'Correo', tipo: TipoCampo.correo, inicial: c['email']),
        Campo('address', 'Dirección', inicial: c['address']),
      ],
      alGuardar: (v) async {
        await ref.read(apiProvider).put('/clinics/me', v);
        ref.invalidate(_clinicaProvider);
      },
    );

    return PaginaModulo(
      titulo: 'Datos de la clínica',
      cuerpo: Asincrono(
        valor: ref.watch(_clinicaProvider),
        alReintentar: () => ref.invalidate(_clinicaProvider),
        listo: (c) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            GlassCard(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${c['name']}',
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 10),
                    for (final (etiqueta, clave) in const [
                      ('Razón social', 'legal_name'),
                      ('RUC', 'tax_id'),
                      ('Teléfono', 'phone'),
                      ('Correo', 'email'),
                      ('Dirección', 'address'),
                      ('Zona horaria', 'timezone'),
                      ('Moneda', 'currency'),
                    ])
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 5),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 110,
                              child: Text(
                                etiqueta,
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: Theme.of(context).colorScheme.onSurface
                                      .withValues(alpha: 0.55),
                                ),
                              ),
                            ),
                            Expanded(child: Text('${c[clave] ?? '—'}')),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: () => editar(c),
              icon: const Icon(Icons.edit_outlined),
              label: const Text('Editar datos'),
            ),
          ],
        ),
      ),
    );
  }
}
