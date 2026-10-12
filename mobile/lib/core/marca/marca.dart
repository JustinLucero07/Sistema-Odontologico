import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api.dart';
import '../auth/auth_controller.dart';

/// Identidad de la consulta: nombre, logo, color y módulos visibles.
///
/// Se guarda en el teléfono para que el login y el arranque ya salgan con la
/// marca de la consulta, aunque todavía no haya conexión.
class Marca {
  const Marca({
    required this.nombre,
    required this.tipo,
    this.logo,
    this.eslogan,
    required this.color,
    this.ocultos = const {},
    this.configurada = true,
    this.abre = '08:00',
    this.cierra = '18:00',
    this.dias = '123456',
    this.sesionMinutos = 30,
    this.terminosPendientes = false,
    this.permisoVence,
  });

  final String nombre;
  final String tipo; // independiente | consultorio | clinica
  final String? logo; // data URL
  final String? eslogan;
  final Color color;
  final Set<String> ocultos;
  final bool configurada;
  final String abre;
  final String cierra;
  final String dias;

  /// Minutos sin uso tras los que se cierra la sesión (0 = nunca).
  final int sesionMinutos;
  final bool terminosPendientes;

  /// Vencimiento del permiso de funcionamiento (yyyy-MM-dd).
  final String? permisoVence;

  static const porDefecto = Marca(
    nombre: 'Sistema Odontológico',
    tipo: 'clinica',
    color: Color(0xFF0D7F76),
  );

  /// El color vigente, para los colores que dependen de él (AppColors).
  static Color actual = porDefecto.color;
  static Uint8List? logoBytes;

  bool visible(String modulo) => !ocultos.contains(modulo);

  factory Marca.fromJson(Map<String, dynamic> j) => Marca(
    nombre: '${j['name'] ?? 'Sistema Odontológico'}',
    tipo: '${j['practice_type'] ?? 'clinica'}',
    logo: j['logo_data'] as String?,
    eslogan: j['slogan'] as String?,
    color: colorDeHex(j['primary_color'] as String?) ?? porDefecto.color,
    ocultos: {...((j['hidden_modules'] as List?) ?? []).map((e) => '$e')},
    configurada: j['setup_completed'] as bool? ?? true,
    abre: '${j['opens_at'] ?? '08:00'}',
    cierra: '${j['closes_at'] ?? '18:00'}',
    dias: '${j['work_days'] ?? '123456'}',
    sesionMinutos: (j['session_timeout_minutes'] as num?)?.toInt() ?? 30,
    terminosPendientes: j['terms_pending'] as bool? ?? false,
    permisoVence: j['health_permit_expires_on'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'name': nombre,
    'practice_type': tipo,
    'logo_data': logo,
    'slogan': eslogan,
    'primary_color': hexDeColor(color),
    'hidden_modules': ocultos.toList(),
    'setup_completed': configurada,
    'opens_at': abre,
    'closes_at': cierra,
    'work_days': dias,
    'session_timeout_minutes': sesionMinutos,
    'terms_pending': terminosPendientes,
    'health_permit_expires_on': permisoVence,
  };

  void aplicar() {
    actual = color;
    logoBytes = bytesDeLogo(logo);
  }
}

Color? colorDeHex(String? hex) {
  if (hex == null || !RegExp(r'^#[0-9a-fA-F]{6}$').hasMatch(hex)) return null;
  return Color(0xFF000000 | int.parse(hex.substring(1), radix: 16));
}

String hexDeColor(Color c) =>
    '#${(c.toARGB32() & 0xFFFFFF).toRadixString(16).padLeft(6, '0').toUpperCase()}';

Uint8List? bytesDeLogo(String? dataUrl) {
  if (dataUrl == null || !dataUrl.startsWith('data:image/')) return null;
  if (dataUrl.startsWith('data:image/svg')) return null; // la app no dibuja SVG
  final i = dataUrl.indexOf('base64,');
  if (i < 0) return null;
  try {
    return base64Decode(dataUrl.substring(i + 7));
  } catch (_) {
    return null;
  }
}

/// Mezcla un color hacia blanco (t>0) o negro (t<0).
Color tono(Color c, double t) {
  final destino = t >= 0 ? Colors.white : Colors.black;
  return Color.lerp(c, destino, t.abs())!;
}

const _clave = 'marca_consulta';

class MarcaController extends StateNotifier<Marca> {
  MarcaController(this._ref) : super(Marca.porDefecto);

  final Ref _ref;

  Future<void> cargarGuardada() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_clave);
      if (raw != null) _poner(Marca.fromJson(jsonDecode(raw) as Map<String, dynamic>));
    } catch (_) {}
  }

  Future<Marca> actualizar() async {
    try {
      final j = await _ref.read(apiProvider).mapa('/clinics/branding');
      final m = Marca.fromJson(j);
      _poner(m);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_clave, jsonEncode(m.toJson()));
    } catch (_) {
      // Sin conexión se queda la guardada.
    }
    return state;
  }

  void vistaPrevia(Color c) {
    Marca.actual = c;
    state = Marca(
      nombre: state.nombre, tipo: state.tipo, logo: state.logo, eslogan: state.eslogan, color: c,
      ocultos: state.ocultos, configurada: state.configurada, abre: state.abre, cierra: state.cierra, dias: state.dias,
      sesionMinutos: state.sesionMinutos, terminosPendientes: state.terminosPendientes, permisoVence: state.permisoVence,
    );
  }

  void _poner(Marca m) {
    m.aplicar();
    state = m;
  }
}

final marcaProvider = StateNotifierProvider<MarcaController, Marca>((ref) {
  final c = MarcaController(ref);
  // Al iniciar sesión se pide la marca vigente al servidor.
  ref.listen(authProvider, (antes, ahora) {
    if (ahora.estado == EstadoSesion.autenticado && antes?.estado != EstadoSesion.autenticado) {
      c.actualizar();
    }
  });
  return c;
});
