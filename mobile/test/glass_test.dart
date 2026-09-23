import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odonto_movil/core/theme/app_theme.dart';
import 'package:odonto_movil/shared/widgets/glass.dart';

Widget _app(ThemeData theme, Widget child) => MaterialApp(
  theme: theme,
  home: AmbientBackground(
    child: Scaffold(
      backgroundColor: Colors.transparent,
      extendBody: true,
      body: child,
    ),
  ),
);

void main() {
  for (final entry in {'claro': lightTheme(), 'oscuro': darkTheme()}.entries) {
    testWidgets('tarjeta con InkWell responde al toque (${entry.key})', (
      tester,
    ) async {
      var tocada = 0;
      await tester.pumpWidget(
        _app(
          entry.value,
          Center(
            child: GlassCard(
              child: InkWell(
                onTap: () => tocada++,
                child: const Padding(
                  padding: EdgeInsets.all(20),
                  child: Text('Cita'),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Cita'));
      await tester.pumpAndSettle();
      expect(tocada, 1);
      expect(tester.takeException(), isNull);
    });

    testWidgets(
      'barra de navegación flotante cambia de destino (${entry.key})',
      (tester) async {
        var elegido = 0;
        await tester.pumpWidget(
          MaterialApp(
            theme: entry.value,
            home: StatefulBuilder(
              builder: (context, setState) => AmbientBackground(
                child: Scaffold(
                  backgroundColor: Colors.transparent,
                  extendBody: true,
                  body: const SizedBox.expand(),
                  bottomNavigationBar: GlassNavBar(
                    selectedIndex: elegido,
                    onSelected: (i) => setState(() => elegido = i),
                    items: const [
                      GlassNavItem(
                        icon: Icons.home_outlined,
                        selectedIcon: Icons.home,
                        label: 'Panel',
                      ),
                      GlassNavItem(
                        icon: Icons.event_outlined,
                        selectedIcon: Icons.event,
                        label: 'Agenda',
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.tap(find.text('Agenda'));
        await tester.pumpAndSettle();
        expect(elegido, 1);
        expect(find.byIcon(Icons.event), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('panel con desenfoque se dibuja', (tester) async {
    await tester.pumpWidget(
      _app(
        lightTheme(),
        const Center(
          child: GlassPanel(
            blur: true,
            padding: EdgeInsets.all(16),
            child: Text('Vidrio'),
          ),
        ),
      ),
    );
    expect(find.text('Vidrio'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
