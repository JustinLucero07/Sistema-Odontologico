import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odonto_movil/shared/odontograma/boca_3d.dart';

const _hallazgos = [
  {'fdi_number': '11', 'surface': 'whole', 'condition': 'corona'},
  {'fdi_number': '16', 'surface': 'oclusal', 'condition': 'caries'},
  {'fdi_number': '26', 'surface': 'oclusal', 'condition': 'restauracion'},
  {'fdi_number': '36', 'surface': 'whole', 'condition': 'implante'},
  {'fdi_number': '46', 'surface': 'mesial', 'condition': 'caries'},
  {'fdi_number': '18', 'surface': 'whole', 'condition': 'ausente'},
];

Future<void> _abrir(WidgetTester tester, {ValueChanged<String?>? alTocar, void Function(String, String)? alTocarCara}) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 2.75;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(
      body: Center(child: Boca3D(hallazgos: _hallazgos, alto: 460, alTocar: alTocar, alTocarCara: alTocarCara)),
    ),
  ));
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  testWidgets('La boca 3D se dibuja y cambia de vista sin errores', (tester) async {
    await _abrir(tester);
    expect(find.byType(Boca3D), findsOneWidget);
    for (final v in ['Oclusal superior', 'Oclusal inferior', 'Lado derecho', 'Lado izquierdo', 'Frente', 'Raíces', 'Números']) {
      await tester.tap(find.byTooltip(v));
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 16));
      }
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('Tocar una pieza muestra su detalle', (tester) async {
    String? elegida;
    await _abrir(tester, alTocar: (f) => elegida = f);
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 16));
    }
    final caja = tester.getRect(find.byType(Boca3D));
    await tester.tapAt(Offset(caja.center.dx - 14, caja.top + caja.height * 0.32));
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.textContaining('Pieza '), findsOneWidget);
    await tester.tap(find.byKey(const Key('registrar-pieza')));
    await tester.pump(const Duration(milliseconds: 50));
    expect(elegida, isNotNull);
    expect(find.text('Pieza $elegida'), findsOneWidget);
    await tester.tap(find.byKey(const Key('mapa-21')));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 16));
    }
    expect(find.text('Pieza 21'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Tocar la cara de un diente permite registrar en esa cara', (tester) async {
    (String, String)? registro;
    await _abrir(tester, alTocar: (_) {}, alTocarCara: (f, c) => registro = (f, c));
    for (var i = 0; i < 30; i++) {
      await tester.pump(const Duration(milliseconds: 16));
    }
    final caja = tester.getRect(find.byType(Boca3D));
    await tester.tapAt(Offset(caja.center.dx - 14, caja.top + caja.height * 0.32));
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.byKey(const Key('registrar-cara')), findsOneWidget);
    expect(find.textContaining('Cara: '), findsOneWidget);
    final esquema = tester.getRect(find.byKey(const Key('esquema-caras')));
    await tester.tapAt(esquema.center);
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Cara: Oclusal/Incisal'), findsOneWidget);
    await tester.tap(find.byKey(const Key('registrar-cara')));
    await tester.pump(const Duration(milliseconds: 50));
    expect(registro?.$2, 'oclusal');
    expect(tester.takeException(), isNull);
  });
}
