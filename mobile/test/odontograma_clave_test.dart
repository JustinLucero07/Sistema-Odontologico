import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odonto_movil/core/models/usuario.dart';
import 'package:odonto_movil/core/theme/app_theme.dart';
import 'package:odonto_movil/features/cuenta/cambiar_clave_page.dart';
import 'package:odonto_movil/shared/odontograma/condiciones.dart';
import 'package:odonto_movil/shared/odontograma/odontograma_widget.dart';

void main() {
  test('reglas de contraseña', () {
    bool cumple(String clave) => reglasClave(
      clave,
      nombre: 'Lucía',
      apellido: 'Arce',
      email: 'lucia@clinica.io',
    ).every((r) => r.$2);

    expect(cumple('corta1'), isFalse);
    expect(cumple('sololetras'), isFalse);
    expect(cumple('12345678'), isFalse);
    expect(cumple('miArce2026'), isFalse); // contiene el apellido
    expect(cumple('Molar-Sano-48'), isTrue);
    expect(fortalezaClave(''), 0);
    expect(fortalezaClave('Molar-Sano-48'), 4);
  });

  test('el usuario lee must_change_password', () {
    final u = Usuario.fromJson({
      'id': '1',
      'clinic_id': '2',
      'email': 'a@b.io',
      'first_name': 'A',
      'last_name': 'B',
      'must_change_password': true,
    });
    expect(u.debeCambiarClave, isTrue);
  });

  test('una condición desconocida no se pierde', () {
    expect(condicionDe('caries').etiqueta, 'Caries');
    expect(condicionDe('nueva_cosa').etiqueta, 'nueva_cosa');
    expect(esPiezaAusente('extraccion_realizada'), isTrue);
  });

  for (final temporal in [false, true]) {
    testWidgets('odontograma con caras y toque (temporal: $temporal)', (
      tester,
    ) async {
      String? tocada;
      final fila = filaArcada('upper', temporal: temporal);
      await tester.pumpWidget(
        MaterialApp(
          theme: lightTheme(),
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 380,
                child: OdontogramaWidget(
                  temporal: temporal,
                  seleccionado: fila.first,
                  onTocarDiente: (fdi) => tocada = fdi,
                  dientes: {
                    fila.first: Diente(
                      fdi: fila.first,
                      arcada: 'upper',
                      caras: const {
                        'oclusal': Colors.red,
                        'mesial': Colors.blue,
                      },
                    ),
                    fila.last: Diente(
                      fdi: fila.last,
                      arcada: 'upper',
                      aspa: Colors.orange,
                    ),
                  },
                ),
              ),
            ),
          ),
        ),
      );
      expect(tester.takeException(), isNull);
      final caja = tester.getRect(find.byType(OdontogramaWidget));
      await tester.tapAt(caja.topLeft + const Offset(10, 20));
      expect(tocada, fila.first);
    });
  }
}
