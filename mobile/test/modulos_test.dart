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
import 'package:odonto_movil/features/pacientes/pestanas.dart' show EditorPresupuesto;
import 'package:odonto_movil/features/reportes/reportes_page.dart';
import 'package:odonto_movil/features/bienvenida/bienvenida_page.dart';
import 'package:odonto_movil/features/cartera/cartera_page.dart';
import 'package:odonto_movil/features/legal/cumplimiento_page.dart';

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
  '/finance/portfolio': {
    'summary': {
      'total_charged': '900.00',
      'total_paid': '450.00',
      'receivable': '450.00',
      'credit_balance': '0.00',
      'patients_owing': 1,
      'patients_settled': 1,
      'patients_credit': 0,
      'open_charges': 1,
      'treatments_in_progress': 1,
      'treatments_in_progress_value': '120.00',
      'treatments_planned': 0,
      'treatments_planned_value': '0.00',
      'collection_rate': 0.5,
    },
    'patients': [
      {
        'patient_id': 'p1',
        'patient_name': 'Ana Mora',
        'national_id': null,
        'phone': '0991234567',
        'total_charged': '600.00',
        'total_paid': '150.00',
        'balance': '450.00',
        'status': 'debe',
        'open_charges': 1,
        'oldest_pending_on': '2026-09-01',
        'days_pending': 40,
        'last_payment_on': '2026-09-20',
        'in_credit': true,
      },
      {
        'patient_id': 'p2',
        'patient_name': 'Luis Vera',
        'national_id': null,
        'phone': null,
        'total_charged': '300.00',
        'total_paid': '300.00',
        'balance': '0.00',
        'status': 'saldado',
        'open_charges': 0,
        'oldest_pending_on': null,
        'days_pending': null,
        'last_payment_on': '2026-10-01',
        'in_credit': false,
      },
    ],
    'charges': [
      {
        'charge_id': 'ch9',
        'patient_id': 'p1',
        'patient_name': 'Ana Mora',
        'description': 'Ortodoncia',
        'issued_on': '2026-09-01',
        'amount': '600.00',
        'paid': '150.00',
        'pending': '450.00',
        'status': 'parcial',
        'in_credit': true,
        'days_open': 40,
      },
    ],
    'treatments': [
      {
        'item_id': 't1',
        'patient_id': 'p1',
        'patient_name': 'Ana Mora',
        'plan_title': 'Plan 1',
        'treatment': 'Endodoncia',
        'fdi_number': '36',
        'status': 'en_progreso',
        'net_price': '120.00',
        'professional_name': 'Dra. Paz',
        'estimated_date': '2026-10-20',
        'completed_date': null,
      },
    ],
  },
  '/finance/recurring-expenses': [
    {
      'id': 'r1',
      'description': 'Arriendo del consultorio',
      'category': 'insumos',
      'category_label': 'Insumos y materiales',
      'amount': '400.00',
      'method': 'efectivo',
      'method_label': 'Efectivo',
      'day_of_month': 5,
      'supplier_name': null,
      'is_active': true,
      'last_registered_month': null,
      'due_this_month': true,
      'due_on': '2026-10-05',
    },
  ],
  '/finance/projection': {
    'days': 30,
    'expected_in': '150.00',
    'expected_out': '400.00',
    'net': '-250.00',
    'overdue_in': '0.00',
    'items': [
      {'on': '2026-11-03', 'kind': 'cuota_credito', 'label': 'Cuota 2 · Ortodoncia', 'patient_name': 'Ana Mora', 'amount': '150.00'},
      {'on': '2026-11-05', 'kind': 'gasto_fijo', 'label': 'Arriendo del consultorio', 'patient_name': null, 'amount': '-400.00'},
    ],
  },
  '/clinics/me': {
    'id': 'c1',
    'name': 'Consultorio Dra. Paz',
    'currency': 'USD',
    'practice_type': 'independiente',
    'primary_color': '#7B5BD6',
    'logo_data': null,
    'work_days': '12345',
    'opens_at': '09:00',
    'closes_at': '17:00',
    'hidden_modules': ['inventory'],
    'setup_completed_at': null,
    'legal_name': 'Ana Paz',
    'tax_id': '1712345678001',
    'address': 'Av. Amazonas',
    'legal_rep_name': null,
    'dpo_name': 'Ana Paz',
    'dpo_email': 'datos@paz.ec',
    'health_permit_number': 'ACESS-1',
    'health_permit_expires_on': '2027-01-01',
    'tax_regime': 'general',
    'keeps_accounting': false,
    'sri_establishment': '001',
    'sri_emission_point': '001',
    'vat_rate': '0.00',
    'record_retention_years': 15,
    'privacy_extra': null,
    'session_timeout_minutes': 30,
    'terms_version': null,
    'terms_accepted_at': null,
    'terms_accepted_by': null,
    'terms_current_version': '2026-10',
  },
  '/patients/p1/documents': [
    {'id': 'd1', 'title': 'Informe radiológico', 'document_type': 'informe', 'mime_type': 'application/pdf', 'created_at': '2026-10-01T10:00:00Z', 'archived_at': null},
  ],
  '/patients/p1/consents': [
    {'id': 'k1', 'title': 'Consentimiento de endodoncia', 'body': 'Texto', 'status': 'pendiente', 'created_at': '2026-10-01T10:00:00Z', 'signed_at': null, 'voided_at': null},
  ],
  '/patients/p1/budgets': [
    {'id': 'b1', 'treatment_plan_id': 'pl1', 'status': 'borrador', 'total': '80.00', 'tax_rate': 0, 'notes': null, 'created_at': '2026-10-01T10:00:00Z',
     'items': [{'description': 'Resina 16', 'price': 40, 'discount': 0, 'quantity': 2, 'treatment_plan_item_id': null}]},
  ],
  '/legal/catalogs': {
    'rights_kinds': [
      {'code': 'acceso', 'label': 'Acceso'},
    ],
    'rights_statuses': [
      {'code': 'pendiente', 'label': 'Pendiente'},
    ],
    'tax_regimes': [
      {'code': 'general', 'label': 'Régimen general'},
    ],
  },
  '/legal/requests': [
    {
      'id': 'q1',
      'patient_id': null,
      'patient_name': null,
      'requester_name': 'Rosa Vela',
      'requester_id_number': null,
      'contact': null,
      'kind': 'acceso',
      'kind_label': 'Acceso',
      'details': null,
      'received_on': '2026-09-01',
      'due_on': '2026-09-16',
      'status': 'pendiente',
      'status_label': 'Pendiente',
      'response': null,
      'resolved_on': null,
      'overdue': true,
      'days_left': -25,
    },
  ],
  '/legal/documents/terminos': {
    'code': 'terminos',
    'title': 'Términos de uso del sistema',
    'version': '2026-10',
    'sections': [
      {
        'title': 'Objeto',
        'paragraphs': ['Estos términos regulan el uso del sistema.'],
      },
    ],
  },
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
    'Cartera': const CarteraPage(),
    'Personalización': const BienvenidaPage(editar: true),
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

  testWidgets('Cartera: deudores, cargos con abonos y tratamientos', (tester) async {
    await _abrir(tester, const CarteraPage());
    expect(find.text('Ana Mora'), findsOneWidget);
    expect(find.text('Luis Vera'), findsNothing); // filtro «Deben»
    await tester.tap(find.text('Cargos'));
    await tester.pumpAndSettle();
    expect(find.text('Debe \$ 450,00'), findsOneWidget);
    expect(tester.takeException(), isNull, reason: 'cargos');
    await tester.tap(find.text('Tratamientos'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Endodoncia'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Finanzas: gastos fijos y proyección', (tester) async {
    await _abrir(tester, const FinanzasPage());
    await tester.ensureVisible(find.text('Gastos fijos'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Gastos fijos'));
    await tester.pumpAndSettle();
    expect(find.text('Arriendo del consultorio'), findsOneWidget);
    await tester.ensureVisible(find.text('Proyección'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Proyección'));
    await tester.pumpAndSettle();
    expect(find.text('Cuota 2 · Ortodoncia'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Asistente de bienvenida: recorre los 5 pasos', (tester) async {
    await _abrir(tester, const BienvenidaPage());
    expect(find.text('Trabajo solo'), findsOneWidget);
    for (final titulo in ['Datos de tu consulta', 'Tu marca', 'Horario de atención', '¿Qué quieres ver?']) {
      await tester.tap(find.text('Continuar'));
      await tester.pumpAndSettle();
      expect(find.text(titulo), findsOneWidget);
    }
    expect(find.text('Empezar a usar el sistema'), findsOneWidget);
    // Sin aceptar los términos no se puede terminar.
    final boton = tester.widget<FilledButton>(find.ancestor(of: find.text('Empezar a usar el sistema'), matching: find.byType(FilledButton)));
    expect(boton.onPressed, isNull);
    await tester.ensureVisible(find.byType(CheckboxListTile));
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    final listo = tester.widget<FilledButton>(find.ancestor(of: find.text('Empezar a usar el sistema'), matching: find.byType(FilledButton)));
    expect(listo.onPressed, isNotNull);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Legal y cumplimiento: estado, términos y solicitudes', (tester) async {
    await _abrir(tester, const CumplimientoPage());
    expect(find.text('Representante legal'), findsOneWidget);
    await tester.scrollUntilVisible(find.textContaining('Leí y acepto'), 300, scrollable: find.descendant(of: find.byType(ListView).first, matching: find.byType(Scrollable)).first);
    expect(find.textContaining('Leí y acepto'), findsOneWidget);
    await tester.tap(find.text('Solicitudes'));
    await tester.pumpAndSettle();
    expect(find.text('Rosa Vela'), findsOneWidget);
    expect(find.textContaining('Vencida hace 25'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Documento legal servido por el servidor', (tester) async {
    await _abrir(tester, const DocumentoLegalPage(codigo: 'terminos'));
    expect(find.text('Términos de uso del sistema'), findsOneWidget);
    expect(find.text('Objeto'), findsOneWidget);
  });

  testWidgets('Editor de presupuesto: líneas y total', (tester) async {
    await _abrir(tester, EditorPresupuesto(presupuesto: const {
      'id': 'b1', 'tax_rate': 12, 'notes': null,
      'items': [{'description': 'Resina 16', 'price': 40, 'discount': 0, 'quantity': 2}],
    }, alGuardar: () async {}));
    expect(find.text('Resina 16'), findsOneWidget);
    expect(find.textContaining('89,60'), findsOneWidget); // 80 + 12 %
    await tester.tap(find.byTooltip('Quitar'));
    await tester.pumpAndSettle();
    expect(find.text('Resina 16'), findsNothing);
  });

  testWidgets('Ficha del paciente: las 10 pestañas', (tester) async {
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
      'Documentos',
      'Consentimientos',
    ]) {
      await tester.ensureVisible(find.widgetWithText(Tab, pestana));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(Tab, pestana));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: pestana);
    }
    expect(find.text('Consentimiento de endodoncia'), findsOneWidget);
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
