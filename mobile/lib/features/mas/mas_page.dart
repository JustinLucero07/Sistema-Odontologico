import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/marca/marca.dart';
import '../bienvenida/bienvenida_page.dart';
import '../caja/caja_page.dart';
import '../cartera/cartera_page.dart';
import '../configuracion/configuracion_pages.dart';
import '../configuracion/roles_plantillas.dart';
import '../creditos/creditos_page.dart';
import '../cuenta/cambiar_clave_page.dart';
import '../finanzas/finanzas_page.dart';
import '../inventario/inventario_page.dart';
import '../laboratorio/laboratorio_page.dart';
import '../legal/cumplimiento_page.dart';
import '../oportunidades/oportunidades_page.dart';
import '../agenda/huecos_page.dart';
import '../reportes/reportes_page.dart';
import '../../shared/widgets/formulario.dart';
import '../../shared/widgets/glass.dart';
import '../../shared/widgets/ui.dart';

class _Modulo {
  const _Modulo(
    this.titulo,
    this.icono,
    this.color,
    this.permiso,
    this.pagina, [
    this.modulo,
  ]);
  final String titulo;
  final IconData icono;
  // Se conserva por si se quiere volver a distinguir módulos por color;
  // hoy todos usan el de la marca, que es más sobrio.
  final Color color;
  final String? permiso;
  final Widget Function() pagina;

  /// Código del módulo que la consulta puede ocultar en Personalización.
  final String? modulo;
}

final _grupos = <(String, List<_Modulo>)>[
  (
    'Consulta',
    [
      _Modulo(
        'Oportunidades',
        Icons.tips_and_updates_outlined,
        Color(0xFFD81B60),
        'patients:read',
        () => const OportunidadesPage(),
        'opportunities',
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
        'cash',
      ),
      _Modulo(
        'Cartera',
        Icons.account_balance_wallet_outlined,
        Tonos.rojo,
        'payments:read',
        () => const CarteraPage(),
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
        'credits',
      ),
      _Modulo(
        'Reportes',
        Icons.insights,
        Tonos.ambar,
        'reports:read',
        () => const ReportesPage(),
        'reports',
      ),
      _Modulo(
        'Inventario',
        Icons.inventory_2_outlined,
        Tonos.rojo,
        'inventory:read',
        () => const InventarioPage(),
        'inventory',
      ),
      _Modulo(
        'Laboratorio',
        Icons.precision_manufacturing_outlined,
        Color(0xFF0D7F76),
        'laboratory:read',
        () => const LaboratorioPage(),
        'laboratory',
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
        'Roles y permisos',
        Icons.admin_panel_settings_outlined,
        Tonos.violeta,
        'roles:manage',
        () => const RolesPage(),
      ),
      _Modulo(
        'Mensajes',
        Icons.chat_outlined,
        Tonos.verde,
        'settings:manage',
        () => const PlantillasMensajePage(),
      ),
      _Modulo(
        'Consentimientos',
        Icons.draw_outlined,
        Tonos.azul,
        'consents:write',
        () => const PlantillasConsentimientoPage(),
      ),
      _Modulo(
        'Personalización',
        Icons.palette_outlined,
        Tonos.violeta,
        'settings:manage',
        () => const BienvenidaPage(editar: true),
      ),
      _Modulo(
        'Legal y cumplimiento',
        Icons.gavel,
        Tonos.rojo,
        'settings:manage',
        () => const CumplimientoPage(),
      ),
      _Modulo(
        'Datos de la consulta',
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
    final marca = ref.watch(marcaProvider);
    bool ve(_Modulo m) =>
        (m.permiso == null || (usuario?.puede(m.permiso!) ?? false)) &&
        (m.modulo == null || marca.visible(m.modulo!));
    final scheme = Theme.of(context).colorScheme;

    return ListView(
      padding: EdgeInsets.fromLTRB(
        20,
        8,
        20,
        110 + MediaQuery.paddingOf(context).bottom,
      ),
      children: [
        for (final (titulo, modulos) in _grupos)
          if (modulos.any(ve)) ...[
            Seccion(titulo),
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              // Sin esto hereda el relleno inferior de la barra flotante y
              // deja un hueco entre grupos.
              padding: EdgeInsets.zero,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 0.95,
              children: [
                for (final m in modulos)
                  if (ve(m))
                    GlassCard(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => m.pagina()),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                color: scheme.primary.withValues(alpha: 0.08),
                              ),
                              child: Icon(
                                m.icono,
                                color: scheme.primary,
                                size: 22,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              m.titulo,
                              textAlign: TextAlign.center,
                              maxLines: 2,
                              style: const TextStyle(
                                fontSize: 12,
                                height: 1.25,
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
