import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:odonto_movil/core/api/api.dart';
import 'package:odonto_movil/core/api/repositorios.dart';
import 'package:odonto_movil/core/theme/app_theme.dart';
import 'package:odonto_movil/features/caja/caja_page.dart';
import 'package:odonto_movil/features/configuracion/configuracion_pages.dart';
import 'package:odonto_movil/features/creditos/creditos_page.dart';
import 'package:odonto_movil/features/finanzas/finanzas_page.dart';
import 'package:odonto_movil/features/inventario/inventario_page.dart';
import 'package:odonto_movil/features/laboratorio/laboratorio_page.dart';
import 'package:odonto_movil/features/mas/mas_page.dart';
import 'package:odonto_movil/features/oportunidades/oportunidades_page.dart';
import 'package:odonto_movil/features/agenda/huecos_page.dart';
import 'package:odonto_movil/shared/contacto.dart';
import 'package:odonto_movil/core/api/api_config.dart';
import 'package:odonto_movil/features/pacientes/paciente_detalle_page.dart';
import 'package:odonto_movil/features/reportes/reportes_page.dart';

const _pid = 'p1';

/// Respuestas de ejemplo con la misma forma que el servidor real.
final Map<String, Object?> _datos = {
  '/finance/cash-session': {
    'id': 's1',
    'opened_at': '2026-10-03T13:00:00Z',
    'opening_float': '20.00',
    'is_open': true,
    'cash_in': '100.00',
    'cash_out': '10.00',
    'expected_now': '110.00',
  },
  '/finance/daily-report': {
    'day': '2026-10-03',
    'total': '150.00',
    'payment_count': 2,
    'by_method': [
      {
        'method': 'efectivo',
        'label': 'Efectivo',
        'total': '100.00',
        'count': 1,
      },
    ],
    'expenses_total': '10.00',
    'expenses_count': 1,
  },
  '/finance/payments': [
    {
      'id': 'pay1',
      'received_on': '2026-10-03',
      'patient_name': 'Ana Mora',
      'concept': 'Resina',
      'amount': '50.00',
      'method_label': 'Efectivo',
      'voided_at': null,
    },
  ],
  '/finance/summary': {
    'date_from': '2026-09-04',
    'date_to': '2026-10-03',
    'sales': '1030.00',
    'income': '750.00',
    'expenses': '120.00',
    'net': '630.00',
    'receivables': '530.00',
    'income_by_method': [
      {'code': 'efectivo', 'label': 'Efectivo', 'total': '700.00', 'count': 5},
    ],
    'expenses_by_category': [
      {'code': 'insumos', 'label': 'Insumos', 'total': '120.00', 'count': 2},
    ],
    'monthly': [
      {
        'month': '2026-09',
        'income': '500.00',
        'expenses': '80.00',
        'net': '420.00',
      },
      {
        'month': '2026-10',
        'income': '250.00',
        'expenses': '40.00',
        'net': '210.00',
      },
    ],
  },
  '/finance/expenses': [
    {
      'id': 'e1',
      'spent_on': '2026-10-02',
      'category': 'insumos',
      'category_label': 'Insumos',
      'description': 'Guantes',
      'amount': '12.30',
      'method_label': 'Efectivo',
      'voided_at': null,
    },
  ],
  '/credits/summary': {
    'active_count': 1,
    'overdue_count': 0,
    'outstanding': '450.00',
    'overdue_amount': '0.00',
    'collected_this_month': '150.00',
  },
  '/credits': [_credito],
  '/credits/c1': {
    ..._credito,
    'installments': [
      {
        'number': 1,
        'due_on': '2026-11-03',
        'principal': '150.00',
        'interest': '0.00',
        'amount': '150.00',
        'paid': '150.00',
        'pending': '0.00',
        'status': 'pagada',
        'days_late': 0,
      },
    ],
    'payments': [
      {
        'group_id': 'g1',
        'received_on': '2026-10-03',
        'amount': '150.00',
        'method_label': 'Efectivo',
        'voided_at': null,
      },
    ],
  },
  '/inventory/items': [
    {
      'id': 'i1',
      'name': 'Anestesia',
      'unit': 'caja',
      'minimum_stock': '10.000',
      'unit_cost': null,
      'is_active': true,
      'on_hand': '6.000',
      'below_minimum': true,
      'next_expiry': '2026-10-15',
      'supplier_name': null,
    },
  ],
  '/inventory/suppliers': [
    {'id': 'sup1', 'name': 'Dental Sur', 'is_active': true},
  ],
  '/inventory/catalog': {
    'units': [
      {'code': 'caja', 'label': 'Caja'},
    ],
    'reasons': [
      {'code': 'compra', 'label': 'Compra', 'sign': 1},
    ],
  },
  '/laboratory/orders': [
    {
      'id': 'o1',
      'patient_name': 'Carlos Pérez',
      'laboratory_name': 'Lab Andes',
      'work_type': 'corona',
      'description': 'Corona 16',
      'status': 'enviado',
      'due_on': '2026-09-01',
      'cost': '420.00',
      'days_overdue': 32,
      'events': [
        {'status': 'enviado', 'created_at': '2026-09-01T10:00:00Z'},
      ],
    },
  ],
  '/laboratory/laboratories': [
    {
      'id': 'l1',
      'name': 'Lab Andes',
      'is_active': true,
      'default_turnaround_days': 8,
    },
  ],
  '/laboratory/catalog': {
    'statuses': [
      {'code': 'enviado', 'label': 'Enviado'},
    ],
    'work_types': [
      {'code': 'corona', 'label': 'Corona'},
    ],
  },
  '/reports/summary': {
    'collected': '750.00',
    'outstanding': '530.00',
    'appointments': 6,
    'no_show_rate': 0.1,
    'new_patients': 3,
    'treatments_completed': 2,
  },
  '/reports/financial': {
    'by_method': [
      {'key': 'efectivo', 'label': 'Efectivo', 'amount': '700.00', 'count': 5},
    ],
    'by_professional': <Object>[],
    'aging': [
      {'label': '0-30 días', 'amount': '200.00', 'count': 2},
    ],
  },
  '/reports/clinical': {
    'by_treatment': [
      {'key': 't', 'label': 'Resina', 'amount': '90.00', 'count': 2},
    ],
    'top_diagnoses': <Object>[],
    'budgets': {'conversion_rate': 0.5},
  },
  '/reports/appointments': {
    'by_status': [
      {'key': 'atendida', 'label': 'Atendida', 'amount': '0', 'count': 4},
    ],
  },
  '/reports/patients': {
    'by_age_band': [
      {'key': '18-30', 'label': '18-30', 'amount': '0', 'count': 3},
    ],
  },
  '/treatments': [
    {'id': 't1', 'name': 'Resina', 'default_price': 45.5, 'is_active': true},
  ],
  '/professionals': [
    {
      'id': 'pr1',
      'first_name': 'Luis',
      'last_name': 'Paz',
      'specialty_id': 'sp1',
      'color_hex': '#0F6FFF',
      'is_active': true,
    },
  ],
  '/specialties': [
    {'id': 'sp1', 'name': 'Odontología general'},
  ],
  '/users': [
    {
      'id': 'u1',
      'first_name': 'Ana',
      'last_name': 'Admin',
      'email': 'a@b.io',
      'is_active': true,
      'roles': [
        {'id': 'r1', 'name': 'Administrador'},
      ],
    },
  ],
  '/roles': [
    {'id': 'r1', 'name': 'Administrador'},
  ],
  '/clinics/me': {'name': 'Clínica Demo', 'currency': 'USD'},
  '/patients/$_pid': {
    'id': _pid,
    'first_name': 'María',
    'last_name': 'Gómez',
    'age': 36,
    'sex': 'F',
    'national_id': '0102030405',
    'phone': '0999',
    'notes': 'Nerviosa',
  },
  '/patients/$_pid/medical-history': {
    'allergies': 'Penicilina',
    'chief_complaint': 'Dolor',
    'created_at': '2026-09-17T17:03:29Z',
  },
  '/patients/$_pid/odontogram': {
    'created_at': '2026-09-17T17:03:29Z',
    'conditions': [
      {'fdi_number': '16', 'surface': 'whole', 'condition': 'corona'},
      {'fdi_number': '36', 'surface': 'oclusal', 'condition': 'caries'},
    ],
  },
  '/patients/$_pid/treatment-plans': [
    {
      'id': 'pl1',
      'title': 'Plan inicial',
      'progress_percent': 33.3,
      'total_price': 255.0,
      'items': [
        {
          'id': 'it1',
          'treatment_name': 'Resina',
          'fdi_number': '36',
          'status': 'propuesto',
          'net_price': 45.0,
        },
      ],
    },
  ],
  '/patients/$_pid/evolutions': [
    {
      'id': 'ev1',
      'created_at': '2026-09-18T20:10:26Z',
      'procedure': 'Resina',
      'fdi_numbers': '46',
    },
  ],
  '/patients/$_pid/prescriptions': [
    {
      'id': 'rx1',
      'created_at': '2026-09-18T20:10:26Z',
      'items': [
        {'medication': 'Ibuprofeno', 'dosage': '400 mg', 'frequency': 'c/8h'},
      ],
      'voided_at': null,
    },
  ],
  '/patients/$_pid/diagnoses': <Object>[],
  '/patients/$_pid/images': <Object>[],
  '/images/types': [
    {'code': 'foto_intraoral', 'label': 'Fotografía intraoral'},
  ],
  '/patients/$_pid/appointments': [
    {
      'id': 'a1',
      'patient_id': _pid,
      'patient_name': 'María Gómez',
      'professional_name': 'Luis Paz',
      'starts_at': '2030-09-19T22:00:00Z',
      'ends_at': '2030-09-19T22:45:00Z',
      'status': 'programada',
    },
  ],
  '/patients/$_pid/account': {
    'total_charged': '850.00',
    'total_paid': '650.00',
    'balance': '200.00',
    'overdue_amount': '0.00',
    'charges': [
      {
        'id': 'ch1',
        'description': 'Corona',
        'amount': '850.00',
        'issued_on': '2026-09-20',
        'paid': '650.00',
        'pending': '200.00',
        'voided_at': null,
      },
    ],
    'payments': [
      {
        'id': 'pay1',
        'amount': '250.00',
        'method': 'efectivo',
        'received_on': '2026-09-20',
        'voided_at': null,
      },
    ],
  },
  '/patients/$_pid/credits': <Object>[],
  '/insights/opportunities': {
    'clinic_name': 'Clínica Demo',
    'recall': [
      {
        'patient_id': 'p2',
        'patient_name': 'Luis Vera',
        'phone': '0999111222',
        'whatsapp': null,
        'contact_allowed': true,
        'last_visit': '2026-01-10',
        'months_since': 9,
      },
    ],
    'pending_treatments': <Object>[],
    'debtors': [
      {
        'patient_id': 'p3',
        'patient_name': 'Carlos Pérez',
        'phone': '0999',
        'whatsapp': '0999333444',
        'contact_allowed': false,
        'pending': '450.00',
        'oldest_charge_on': '2026-09-20',
      },
    ],
    'birthdays': <Object>[],
    'unconfirmed': <Object>[],
  },
  '/insights/free-slots': [
    {'starts_at': '2030-10-07T13:00:00Z', 'ends_at': '2030-10-07T13:30:00Z'},
    {'starts_at': '2030-10-07T14:00:00Z', 'ends_at': '2030-10-07T14:30:00Z'},
  ],
  '/finance/expense-categories': [
    {'code': 'insumos', 'label': 'Insumos y materiales'},
  ],
  '/finance/payment-methods': [
    {'code': 'efectivo', 'label': 'Efectivo'},
  ],
};

const _credito = {
  'id': 'c1',
  'patient_name': 'Ana Mora',
  'charge_id': 'ch9',
  'charge_description': 'Ortodoncia',
  'down_payment': '0.00',
  'monthly_rate': '0',
  'frequency': 'mensual',
  'frequency_label': 'Mensual',
  'installment_count': 3,
  'total': '600.00',
  'paid': '150.00',
  'pending': '450.00',
  'overdue': '0.00',
  'days_late': 0,
  'next_due_on': '2026-12-03',
  'next_amount': '150.00',
  'status': 'al_dia',
};

class _Adaptador implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final ruta = options.uri.path.replaceFirst('/api/v1', '');
    final existe = _datos.containsKey(ruta);
    return ResponseBody.fromString(
      jsonEncode(
        existe ? _datos[ruta] : {'detail': 'sin datos de prueba: $ruta'},
      ),
      existe ? 200 : 404,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Widget _app(Widget pagina) {
  final dio = Dio(
    BaseOptions(baseUrl: 'http://x/api/v1', validateStatus: (_) => true),
  )..httpClientAdapter = _Adaptador();
  return ProviderScope(
    overrides: [
      apiProvider.overrideWithValue(Api(dio)),
      pacientesRepoProvider.overrideWithValue(PacientesRepo(dio)),
    ],
    child: MaterialApp(
      theme: lightTheme(),
      locale: const Locale('es'),
      supportedLocales: const [Locale('es')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: pagina,
    ),
  );
}

Future<void> _abrir(WidgetTester tester, Widget pagina) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 2.75;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(_app(pagina));
  for (var i = 0; i < 6; i++) {
    await tester.pump(const Duration(milliseconds: 200));
  }
  expect(tester.takeException(), isNull);
}

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  final paginas = <String, Widget>{
    'Caja': const CajaPage(),
    'Finanzas': const FinanzasPage(),
    'Créditos': const CreditosPage(),
    'Detalle de crédito': const CreditoDetallePage(id: 'c1'),
    'Inventario': const InventarioPage(),
    'Laboratorio': const LaboratorioPage(),
    'Reportes': const ReportesPage(),
    'Tratamientos': const TratamientosPage(),
    'Profesionales': const ProfesionalesPage(),
    'Usuarios': const UsuariosPage(),
    'Clínica': const ClinicaPage(),
    'Más': const Scaffold(body: MasPage()),
    'Oportunidades': const OportunidadesPage(),
    'Huecos libres': const HuecosPage(),
  };

  for (final e in paginas.entries) {
    testWidgets('${e.key} se dibuja con datos', (tester) async {
      await _abrir(tester, e.value);
    });
  }

  testWidgets('Finanzas: pestañas de cobros y egresos', (tester) async {
    await _abrir(tester, const FinanzasPage());
    await tester.tap(find.text('Cobros'));
    await tester.pumpAndSettle();
    expect(find.text('Ana Mora'), findsOneWidget);
    await tester.tap(find.text('Egresos'));
    await tester.pumpAndSettle();
    expect(find.text('Guantes'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Ficha del paciente: las 8 pestañas', (tester) async {
    await _abrir(
      tester,
      const PacienteDetallePage(pacienteId: _pid, nombre: 'María Gómez'),
    );
    expect(find.text('María Gómez'), findsWidgets);
    for (final pestana in [
      'Historia',
      'Odontograma',
      'Tratamientos',
      'Clínico',
      'Imágenes',
      'Citas',
      'Cuenta',
    ]) {
      await tester.tap(find.widgetWithText(Tab, pestana));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: pestana);
    }
    expect(find.text('Corona'), findsWidgets); // cargo en la cuenta
  });

  testWidgets('Formulario emergente: valida y muestra campos', (tester) async {
    await _abrir(tester, const TratamientosPage());
    await tester.tap(find.text('Tratamiento'));
    await tester.pumpAndSettle();
    expect(find.text('Nuevo tratamiento'), findsOneWidget);
    await tester.tap(find.text('Guardar'));
    await tester.pumpAndSettle();
    expect(find.text('Obligatorio'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  test('números de WhatsApp en formato internacional', () {
    expect(numeroWhatsapp('0999 123 456'), '593999123456');
    expect(numeroWhatsapp('+593 99 912 3456'), '593999123456');
    expect(numeroWhatsapp('123'), isNull);
    expect(numeroWhatsapp(null), isNull);
  });

  testWidgets('Oportunidades: lista y respeta la autorización', (tester) async {
    await _abrir(tester, const OportunidadesPage());
    expect(find.text('Luis Vera'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Saldos pendientes'),
      200,
      scrollable: find.byWidgetPredicate(
        (w) => w is Scrollable && w.axisDirection == AxisDirection.right,
      ),
    );
    await tester.tap(find.text('Saldos pendientes').first);
    await tester.pumpAndSettle();
    expect(find.text('Carlos Pérez'), findsOneWidget);
    // Sin autorización de comunicaciones: no hay botón de WhatsApp.
    expect(find.byTooltip('WhatsApp'), findsNothing);
  });

  test('dirección del servidor normalizada', () {
    expect(
      ApiConfig.normalizar('clinica.ejemplo.com/'),
      'https://clinica.ejemplo.com',
    );
    expect(ApiConfig.normalizar('https://x.ec/api/v1'), 'https://x.ec');
    expect(
      ApiConfig.normalizar('192.168.1.50:8000'),
      'http://192.168.1.50:8000',
    );
  });
}
