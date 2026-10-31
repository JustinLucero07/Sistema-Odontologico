import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Avisos de citas en el propio teléfono.
///
/// Se programan en el dispositivo con los datos de la agenda: aparecen
/// aunque la app esté cerrada o sin internet, y se rehacen cada vez que la
/// agenda se actualiza (al abrir la app, al volver a ella, tras sincronizar).
///
/// - Un aviso antes de cada cita (30 minutos por defecto).
/// - Un resumen cada mañana: cuántas citas hay y a qué hora es la primera.
/// - Un aviso cuando aparece una cita nueva que agendó otra persona.
class AjustesAvisos {
  const AjustesAvisos({
    this.activos = true,
    this.minutosAntes = 30,
    this.resumenDiario = true,
    this.horaResumen = 7,
    this.minutoResumen = 30,
    this.nuevasCitas = true,
  });

  final bool activos;
  final int minutosAntes;
  final bool resumenDiario;
  final int horaResumen;
  final int minutoResumen;
  final bool nuevasCitas;

  AjustesAvisos copyWith({bool? activos, int? minutosAntes, bool? resumenDiario, int? horaResumen, int? minutoResumen, bool? nuevasCitas}) =>
      AjustesAvisos(
        activos: activos ?? this.activos,
        minutosAntes: minutosAntes ?? this.minutosAntes,
        resumenDiario: resumenDiario ?? this.resumenDiario,
        horaResumen: horaResumen ?? this.horaResumen,
        minutoResumen: minutoResumen ?? this.minutoResumen,
        nuevasCitas: nuevasCitas ?? this.nuevasCitas,
      );

  Map<String, dynamic> toJson() => {
    'activos': activos,
    'minutosAntes': minutosAntes,
    'resumenDiario': resumenDiario,
    'horaResumen': horaResumen,
    'minutoResumen': minutoResumen,
    'nuevasCitas': nuevasCitas,
  };

  factory AjustesAvisos.fromJson(Map<String, dynamic> j) => AjustesAvisos(
    activos: j['activos'] as bool? ?? true,
    minutosAntes: j['minutosAntes'] as int? ?? 30,
    resumenDiario: j['resumenDiario'] as bool? ?? true,
    horaResumen: j['horaResumen'] as int? ?? 7,
    minutoResumen: j['minutoResumen'] as int? ?? 30,
    nuevasCitas: j['nuevasCitas'] as bool? ?? true,
  );
}

class AvisosCitas {
  AvisosCitas._();
  static final AvisosCitas instancia = AvisosCitas._();

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _listo = false;
  AjustesAvisos ajustes = const AjustesAvisos();

  static const _canalCitas = AndroidNotificationDetails(
    'citas',
    'Citas',
    channelDescription: 'Aviso antes de cada cita y citas nuevas',
    importance: Importance.high,
    priority: Priority.high,
    category: AndroidNotificationCategory.reminder,
  );
  static const _canalResumen = AndroidNotificationDetails(
    'resumen',
    'Resumen del día',
    channelDescription: 'Cuántas citas hay cada mañana',
    importance: Importance.defaultImportance,
  );

  /// Programar a futuro solo existe en Android e iOS; en el escritorio se
  /// muestran únicamente los avisos inmediatos.
  bool get _programable => !kIsWeb && (Platform.isAndroid || Platform.isIOS);

  Future<void> iniciar() async {
    if (_listo || kIsWeb) return;
    try {
      tzdata.initializeTimeZones();
      await _plugin.initialize(
        settings: const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
          iOS: DarwinInitializationSettings(requestAlertPermission: false, requestBadgePermission: false, requestSoundPermission: false),
          linux: LinuxInitializationSettings(defaultActionName: 'Abrir'),
        ),
      );
      final prefs = await SharedPreferences.getInstance();
      final guardados = prefs.getString('avisos_ajustes');
      if (guardados != null) ajustes = AjustesAvisos.fromJson((jsonDecode(guardados) as Map).cast<String, dynamic>());
      _listo = true;
    } catch (e) {
      debugPrint('Avisos no disponibles: $e');
    }
  }

  /// Android 13+ y iOS piden permiso para mostrar avisos.
  Future<bool> pedirPermiso() async {
    await iniciar();
    if (!_listo) return false;
    try {
      if (!kIsWeb && Platform.isAndroid) {
        return await _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()?.requestNotificationsPermission() ?? false;
      }
      if (!kIsWeb && Platform.isIOS) {
        return await _plugin.resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>()?.requestPermissions(alert: true, sound: true) ?? false;
      }
    } catch (_) {}
    return true;
  }

  Future<void> guardarAjustes(AjustesAvisos nuevos) async {
    ajustes = nuevos;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('avisos_ajustes', jsonEncode(nuevos.toJson()));
  }

  Future<void> probar() async {
    await iniciar();
    if (!_listo) return;
    await _plugin.show(
      id: 1,
      title: 'Así se verán sus avisos',
      body: 'Cita con María Gómez en ${ajustes.minutosAntes} minutos · Limpieza dental',
      notificationDetails: const NotificationDetails(android: _canalCitas, linux: LinuxNotificationDetails()),
    );
  }

  /// Rehace todos los avisos con la agenda de los próximos 7 días.
  Future<void> actualizar(Dio dio) async {
    await iniciar();
    if (!_listo) return;
    final hoy = DateTime.now();
    final desde = DateTime(hoy.year, hoy.month, hoy.day);
    List<Map<String, dynamic>> citas;
    try {
      final r = await dio.get('/appointments', queryParameters: {
        'from': desde.toUtc().toIso8601String(),
        'to': desde.add(const Duration(days: 7)).toUtc().toIso8601String(),
      });
      if (r.statusCode != 200 || r.data is! List) return;
      citas = (r.data as List).cast<Map<String, dynamic>>();
    } catch (_) {
      return; // sin agenda nueva se conservan los avisos ya programados
    }
    final vigentes = citas.where((c) => !{'cancelada', 'no_asistio', 'atendida'}.contains(c['status'])).toList();
    await _avisarNuevas(vigentes);
    await programar(vigentes);
  }

  Future<void> programar(List<Map<String, dynamic>> citas) async {
    if (!_listo || !_programable) return;
    try {
      await _plugin.cancelAllPendingNotifications();
    } catch (_) {}
    if (!ajustes.activos) return;
    final ahora = DateTime.now();
    final hora = DateFormat('HH:mm');
    var n = 0;
    final porDia = <String, List<DateTime>>{};
    for (final c in citas) {
      final inicio = DateTime.parse('${c['starts_at']}').toLocal();
      porDia.putIfAbsent(DateFormat('yyyy-MM-dd').format(inicio), () => []).add(inicio);
      final cuando = inicio.subtract(Duration(minutes: ajustes.minutosAntes));
      // Android limita las alarmas por app: 60 avisos de cita sobran para una semana.
      if (cuando.isBefore(ahora) || n >= 60) continue;
      final tratamiento = c['treatment_name'] != null ? ' · ${c['treatment_name']}' : '';
      await _programarUno(
        100 + n,
        cuando,
        'Cita a las ${hora.format(inicio)}',
        '${c['patient_name'] ?? 'Paciente'} con ${c['professional_name'] ?? 'el profesional'}$tratamiento',
        _canalCitas,
      );
      n++;
    }
    if (ajustes.resumenDiario) {
      for (var d = 0; d < 7; d++) {
        final dia = DateTime(ahora.year, ahora.month, ahora.day).add(Duration(days: d));
        final cuando = DateTime(dia.year, dia.month, dia.day, ajustes.horaResumen, ajustes.minutoResumen);
        if (cuando.isBefore(ahora)) continue;
        final delDia = (porDia[DateFormat('yyyy-MM-dd').format(dia)] ?? [])..sort();
        await _programarUno(
          10 + d,
          cuando,
          delDia.isEmpty ? 'Hoy no hay citas' : 'Hoy tiene ${delDia.length} ${delDia.length == 1 ? 'cita' : 'citas'}',
          delDia.isEmpty ? 'Buen día para ponerse al día con pendientes.' : 'La primera a las ${hora.format(delDia.first)}.',
          _canalResumen,
        );
      }
    }
  }

  Future<void> _programarUno(int id, DateTime cuando, String titulo, String cuerpo, AndroidNotificationDetails canal) async {
    try {
      await _plugin.zonedSchedule(
        id: id,
        scheduledDate: tz.TZDateTime.from(cuando.toUtc(), tz.UTC),
        notificationDetails: NotificationDetails(android: canal, iOS: const DarwinNotificationDetails()),
        // Inexacta: puede llegar con un par de minutos de margen, pero no
        // necesita el permiso de alarmas exactas.
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        title: titulo,
        body: cuerpo,
      );
    } catch (e) {
      debugPrint('No se pudo programar el aviso: $e');
    }
  }

  /// Citas que no estaban la última vez: las agendó otra persona.
  Future<void> _avisarNuevas(List<Map<String, dynamic>> citas) async {
    final prefs = await SharedPreferences.getInstance();
    final conocidas = prefs.getStringList('avisos_citas_conocidas');
    final ids = [for (final c in citas) '${c['id']}'];
    await prefs.setStringList('avisos_citas_conocidas', ids);
    // La primera vez solo se aprende la agenda: no se avisa de todo.
    if (conocidas == null || !ajustes.activos || !ajustes.nuevasCitas) return;
    final nuevas = citas.where((c) => !conocidas.contains('${c['id']}')).toList();
    if (nuevas.isEmpty) return;
    final f = DateFormat("EEE d 'a las' HH:mm", 'es');
    final primera = nuevas.first;
    try {
      await _plugin.show(
        id: 2,
        title: nuevas.length == 1 ? 'Nueva cita agendada' : '${nuevas.length} citas nuevas',
        body: nuevas.length == 1
            ? '${primera['patient_name']} · ${f.format(DateTime.parse('${primera['starts_at']}').toLocal())}'
            : nuevas.take(3).map((c) => '${c['patient_name']} (${f.format(DateTime.parse('${c['starts_at']}').toLocal())})').join(', '),
        notificationDetails: const NotificationDetails(android: _canalCitas, linux: LinuxNotificationDetails()),
      );
    } catch (_) {}
  }

  /// Al cerrar sesión no deben quedar avisos con datos de pacientes.
  Future<void> borrarTodo() async {
    try {
      await _plugin.cancelAll();
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('avisos_citas_conocidas');
    } catch (_) {}
  }
}
