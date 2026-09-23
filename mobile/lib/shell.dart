import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/auth/auth_controller.dart';
import 'features/agenda/agenda_page.dart';
import 'features/pacientes/pacientes_page.dart';
import 'features/panel/panel_page.dart';
import 'shared/widgets/glass.dart';
import 'shared/widgets/tooth_mark.dart';

/// Navegación inferior en lugar del menú lateral de la web.
///
/// Un cajón lateral esconde la navegación detrás de un gesto; en un móvil que
/// se usa con una mano entre paciente y paciente, los cuatro destinos que de
/// verdad se usan tienen que estar a un pulgar de distancia.
class Shell extends ConsumerStatefulWidget {
  const Shell({super.key});

  @override
  ConsumerState<Shell> createState() => _ShellState();
}

class _ShellState extends ConsumerState<Shell> {
  int _indice = 0;

  static const _paginas = [PanelPage(), AgendaPage(), PacientesPage()];

  @override
  Widget build(BuildContext context) {
    final usuario = ref.watch(authProvider).usuario;

    return AmbientBackground(
      child: Scaffold(
      backgroundColor: Colors.transparent,
      // El contenido pasa por debajo de la barra de navegación flotante: por
      // eso se extiende detrás de ella. Las listas reservan ese espacio al
      // final (MediaQuery.paddingOf(context).bottom) para no taparse.
      extendBody: true,
      appBar: AppBar(
        flexibleSpace: const GlassAppBarBackground(),
        titleSpacing: 16,
        title: Row(
          children: [
            const ToothMark(size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text(switch (_indice) {
                0 => 'Panel',
                1 => 'Agenda',
                _ => 'Pacientes',
              }),
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Cuenta',
            offset: const Offset(0, 46),
            icon: CircleAvatar(
              radius: 16,
              backgroundColor: Theme.of(
                context,
              ).colorScheme.primary.withValues(alpha: 0.16),
              child: Text(
                usuario?.iniciales ?? '?',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
            ),
            itemBuilder: (context) => [
              PopupMenuItem(
                enabled: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      usuario?.nombreCompleto ?? '',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    Text(
                      usuario?.roles.join(' · ') ?? '',
                      style: TextStyle(
                        fontSize: 12,
                        color: Theme.of(
                          context,
                        ).colorScheme.onSurface.withValues(alpha: 0.6),
                      ),
                    ),
                  ],
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'salir',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.logout),
                  title: Text('Cerrar sesión'),
                ),
              ),
            ],
            onSelected: (value) {
              if (value == 'salir') {
                ref.read(authProvider.notifier).cerrarSesion();
              }
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: IndexedStack(index: _indice, children: _paginas),
      bottomNavigationBar: GlassNavBar(
        selectedIndex: _indice,
        onSelected: (i) => setState(() => _indice = i),
        items: const [
          GlassNavItem(
            icon: Icons.space_dashboard_outlined,
            selectedIcon: Icons.space_dashboard,
            label: 'Panel',
          ),
          GlassNavItem(
            icon: Icons.event_outlined,
            selectedIcon: Icons.event,
            label: 'Agenda',
          ),
          GlassNavItem(
            icon: Icons.groups_outlined,
            selectedIcon: Icons.groups,
            label: 'Pacientes',
          ),
        ],
      ),
      ),
    );
  }
}
