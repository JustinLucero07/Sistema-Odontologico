import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../caja/caja_page.dart';
import '../configuracion/configuracion_pages.dart';
import '../creditos/creditos_page.dart';
import '../cuenta/cambiar_clave_page.dart';
import '../finanzas/finanzas_page.dart';
import '../inventario/inventario_page.dart';
import '../laboratorio/laboratorio_page.dart';
import '../oportunidades/oportunidades_page.dart';
import '../agenda/huecos_page.dart';
import '../reportes/reportes_page.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

class _Modulo {
  const _Modulo(this.titulo, this.icono, this.color, this.permiso, this.pagina);
  final String titulo;
  final IconData icono;
  final Color color;
  final String? permiso;
  final Widget Function() pagina;
}

final _grupos = <(String, List<_Modulo>)>[
  (
    'Clínica',
    [
      _Modulo(
        'Oportunidades',
        Icons.tips_and_updates_outlined,
        Color(0xFFD81B60),
        'patients:read',
        () => const OportunidadesPage(),
      ),
      _Modulo(
        'Huecos libres',
        Icons.event_available,
        Tonos.azul,
        'appointments:read',
        () => const HuecosPage(),
      ),
    ],
  ),
  (
    'Administración',
    [
      _Modulo(
        'Caja del día',
        Icons.point_of_sale,
        Tonos.verde,
        'payments:read',
        () => const CajaPage(),
      ),
      _Modulo(
        'Finanzas',
        Icons.account_balance,
        Tonos.azul,
        'payments:read',
        () => const FinanzasPage(),
      ),
      _Modulo(
        'Créditos',
        Icons.credit_score,
        Tonos.violeta,
        'payments:read',
        () => const CreditosPage(),
      ),
      _Modulo(
        'Reportes',
        Icons.insights,
        Tonos.ambar,
        'reports:read',
        () => const ReportesPage(),
      ),
      _Modulo(
        'Inventario',
        Icons.inventory_2_outlined,
        Tonos.rojo,
        'inventory:read',
        () => const InventarioPage(),
      ),
      _Modulo(
        'Laboratorio',
        Icons.precision_manufacturing_outlined,
        Color(0xFF0D7F76),
        'laboratory:read',
        () => const LaboratorioPage(),
      ),
    ],
  ),
  (
    'Configuración',
    [
      _Modulo(
        'Tratamientos',
        Icons.medical_services_outlined,
        Color(0xFF0D7F76),
        'treatments:write',
        () => const TratamientosPage(),
      ),
      _Modulo(
        'Profesionales',
        Icons.badge_outlined,
        Tonos.azul,
        'settings:manage',
        () => const ProfesionalesPage(),
      ),
      _Modulo(
        'Usuarios',
        Icons.group_outlined,
        Tonos.violeta,
        'users:manage',
        () => const UsuariosPage(),
      ),
      _Modulo(
        'Clínica',
        Icons.store_outlined,
        Tonos.ambar,
        'settings:manage',
        () => const ClinicaPage(),
      ),
    ],
  ),
];

/// Todo lo que la web tiene en su menú lateral, en una rejilla a un toque.
class MasPage extends ConsumerWidget {
  const MasPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usuario = ref.watch(authProvider).usuario;
    final scheme = Theme.of(context).colorScheme;

    return ListView(
      padding: EdgeInsets.fromLTRB(
        16,
        8,
        16,
        110 + MediaQuery.paddingOf(context).bottom,
      ),
      children: [
        for (final (titulo, modulos) in _grupos)
          if (modulos.any(
            (m) => m.permiso == null || (usuario?.puede(m.permiso!) ?? false),
          )) ...[
            Seccion(titulo),
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 0.95,
              children: [
                for (final m in modulos)
                  if (m.permiso == null ||
                      (usuario?.puede(m.permiso!) ?? false))
                    GlassCard(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => m.pagina()),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(10),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              width: 46,
                              height: 46,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(15),
                                gradient: LinearGradient(
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                  colors: [
                                    m.color.withValues(alpha: 0.85),
                                    m.color,
                                  ],
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: m.color.withValues(alpha: 0.35),
                                    blurRadius: 12,
                                    offset: const Offset(0, 6),
                                    spreadRadius: -4,
                                  ),
                                ],
                              ),
                              child: Icon(
                                m.icono,
                                color: Colors.white,
                                size: 23,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              m.titulo,
                              textAlign: TextAlign.center,
                              maxLines: 2,
                              style: const TextStyle(
                                fontSize: 12.5,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
              ],
            ),
          ],
        const Seccion('Mi cuenta'),
        GlassCard(
          child: Column(
            children: [
              ListTile(
                leading: CircleAvatar(
                  backgroundColor: scheme.primary.withValues(alpha: 0.15),
                  child: Text(
                    usuario?.iniciales ?? '?',
                    style: TextStyle(
                      color: scheme.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                title: Text(usuario?.nombreCompleto ?? ''),
                subtitle: Text(usuario?.email ?? ''),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.lock_reset),
                title: const Text('Cambiar contraseña'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const CambiarClavePage(),
                  ),
                ),
              ),
              ListTile(
                leading: Icon(Icons.logout, color: scheme.error),
                title: Text(
                  'Cerrar sesión',
                  style: TextStyle(color: scheme.error),
                ),
                onTap: () async {
                  if (await confirmar(
                    context,
                    titulo: '¿Cerrar sesión?',
                    textoConfirmar: 'Salir',
                  )) {
                    ref.read(authProvider.notifier).cerrarSesion();
                  }
                },
              ),
            ],
          ),
        ),
      ],
    );
  }
}
