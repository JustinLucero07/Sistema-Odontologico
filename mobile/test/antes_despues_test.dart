import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter_test/flutter_test.dart';
import 'package:odonto_movil/core/marca/marca.dart';
import 'package:odonto_movil/features/pacientes/antes_despues.dart';

void main() {
  testWidgets('La imagen para redes sale de 1080×1350 y en PNG', (tester) async {
    final antes = File('test/recursos/antes.jpg').readAsBytesSync();
    final despues = File('test/recursos/despues.jpg').readAsBytesSync();
    final png = await tester.runAsync(
      () => imagenParaRedes(antes, despues, marca: Marca.porDefecto, titulo: 'Blanqueamiento en consultorio'),
    );
    expect(png, isNotNull);
    expect(png!.sublist(1, 4), [0x50, 0x4E, 0x47]); // «PNG»
    final img = await tester.runAsync(() async => (await (await ui.instantiateImageCodec(png)).getNextFrame()).image);
    expect(img!.width, 1080);
    expect(img.height, 1350);
    if (Platform.environment['GUARDAR_IMAGEN'] != null) File(Platform.environment['GUARDAR_IMAGEN']!).writeAsBytesSync(png);
  });
}
