import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import 'condiciones.dart';

typedef V3 = (double, double, double);

V3 _suma(V3 a, V3 b) => (a.$1 + b.$1, a.$2 + b.$2, a.$3 + b.$3);
V3 _esc(V3 a, double k) => (a.$1 * k, a.$2 * k, a.$3 * k);
V3 _resta(V3 a, V3 b) => (a.$1 - b.$1, a.$2 - b.$2, a.$3 - b.$3);
V3 _cruz(V3 a, V3 b) => (
  a.$2 * b.$3 - a.$3 * b.$2,
  a.$3 * b.$1 - a.$1 * b.$3,
  a.$1 * b.$2 - a.$2 * b.$1,
);
double _punto(V3 a, V3 b) => a.$1 * b.$1 + a.$2 * b.$2 + a.$3 * b.$3;
V3 _norm(V3 a) {
  final l = math.sqrt(_punto(a, a));
  return l == 0 ? (0, 1, 0) : (a.$1 / l, a.$2 / l, a.$3 / l);
}

V3 _rgb(Color c) => (c.r, c.g, c.b);
V3 _mezcla(V3 a, V3 b, double t) => (
  a.$1 + (b.$1 - a.$1) * t,
  a.$2 + (b.$2 - a.$2) * t,
  a.$3 + (b.$3 - a.$3) * t,
);
double _clamp(double x, [double a = 0, double b = 1]) =>
    x < a ? a : (x > b ? b : x);
double _suave(double a, double b, double x) {
  final t = _clamp((x - a) / (b - a));
  return t * t * (3 - 2 * t);
}

double _ruido(double x, double y, double z) {
  final s = math.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453;
  return s - s.floorToDouble();
}

enum _Tipo { incisivo, canino, premolar, molar }

class _Medida {
  const _Medida(
    this.ancho,
    this.fondo,
    this.alto,
    this.tipo,
    this.raices,
    this.largoRaiz,
  );
  final double ancho, fondo, alto, largoRaiz;
  final _Tipo tipo;
  final int raices;
}

const _superior = [
  _Medida(0.86, 0.7, 1.05, _Tipo.incisivo, 1, 1.35),
  _Medida(0.66, 0.62, 0.93, _Tipo.incisivo, 1, 1.3),
  _Medida(0.78, 0.8, 1.08, _Tipo.canino, 1, 1.7),
  _Medida(0.7, 0.9, 0.84, _Tipo.premolar, 2, 1.3),
  _Medida(0.68, 0.88, 0.8, _Tipo.premolar, 1, 1.3),
  _Medida(1.02, 1.1, 0.74, _Tipo.molar, 3, 1.25),
  _Medida(0.94, 1.06, 0.7, _Tipo.molar, 3, 1.2),
  _Medida(0.86, 1.0, 0.66, _Tipo.molar, 3, 1.05),
];
const _inferior = [
  _Medida(0.54, 0.6, 0.92, _Tipo.incisivo, 1, 1.25),
  _Medida(0.6, 0.62, 0.95, _Tipo.incisivo, 1, 1.3),
  _Medida(0.7, 0.76, 1.04, _Tipo.canino, 1, 1.6),
  _Medida(0.7, 0.8, 0.84, _Tipo.premolar, 1, 1.35),
  _Medida(0.72, 0.84, 0.8, _Tipo.premolar, 1, 1.35),
  _Medida(1.1, 1.02, 0.72, _Tipo.molar, 2, 1.3),
  _Medida(1.04, 1.0, 0.7, _Tipo.molar, 2, 1.25),
  _Medida(1.0, 0.96, 0.66, _Tipo.molar, 2, 1.1),
];
const _temporales = [
  _Medida(0.62, 0.56, 0.72, _Tipo.incisivo, 1, 0.95),
  _Medida(0.54, 0.52, 0.68, _Tipo.incisivo, 1, 0.9),
  _Medida(0.64, 0.64, 0.76, _Tipo.canino, 1, 1.1),
  _Medida(0.76, 0.8, 0.6, _Tipo.molar, 2, 0.85),
  _Medida(0.92, 0.92, 0.6, _Tipo.molar, 2, 0.9),
];

const _nombresPerm = [
  'Incisivo central',
  'Incisivo lateral',
  'Canino',
  'Primer premolar',
  'Segundo premolar',
  'Primer molar',
  'Segundo molar',
  'Tercer molar',
];
const _nombresTemp = [
  'Incisivo central temporal',
  'Incisivo lateral temporal',
  'Canino temporal',
  'Primer molar temporal',
  'Segundo molar temporal',
];
const _lados = {
  '1': 'superior derecho',
  '2': 'superior izquierdo',
  '3': 'inferior izquierdo',
  '4': 'inferior derecho',
  '5': 'superior derecho',
  '6': 'superior izquierdo',
  '7': 'inferior izquierdo',
  '8': 'inferior derecho',
};

String nombrePieza(String fdi) {
  final q = int.tryParse(fdi[0]) ?? 0;
  final i = (int.tryParse(fdi.substring(1)) ?? 1) - 1;
  final lista = q >= 5 ? _nombresTemp : _nombresPerm;
  if (i < 0 || i >= lista.length) return 'Pieza $fdi';
  return '${lista[i]} ${_lados[fdi[0]] ?? ''}'.trim();
}

const caras3D = ['mesial', 'distal', 'vestibular', 'lingual', 'oclusal'];
const _ordenCara = [
  'caries',
  'fractura',
  'restauracion_defectuosa',
  'tratamiento_pendiente',
  'restauracion',
  'sellante',
  'tratamiento_realizado',
];
const _completos = [
  'implante',
  'corona',
  'protesis',
  'puente',
  'extraccion_indicada',
  'endodoncia',
  'diente_retenido',
  'movilidad',
];

const V3 _esmalte = (0.95, 0.93, 0.87);
const V3 _cuello = (0.9, 0.82, 0.64);
const V3 _borde = (0.8, 0.85, 0.89);
const V3 _dentina = (0.91, 0.84, 0.66);
const V3 _titanio = (0.7, 0.74, 0.78);
const V3 _oro = (0.88, 0.71, 0.34);
const V3 _oscuro = (0.22, 0.12, 0.1);
const V3 _enciaFija = (0.93, 0.6, 0.61);
const V3 _mucosa = (0.8, 0.36, 0.42);
const V3 _paladar = (0.9, 0.56, 0.6);

const _matEsmalte = 0,
    _matEncia = 1,
    _matMetal = 2,
    _matRaiz = 3,
    _matBrillo = 4;

class _Marco {
  const _Marco(this.centro, this.distal, this.vestibular);
  final V3 centro, distal, vestibular;
}

_Marco _puntoArcada(double rx, double rz, double lado, double th) {
  final c = math.cos(th), s = math.sin(th);
  return _Marco(
    (lado * rx * s, 0, rz * c - rz),
    _norm((lado * rx * c, 0, -rz * s)),
    _norm((lado * s / rx, 0, c / rz)),
  );
}

List<(double, double)> _ubicar(List<_Medida> m, double rx, double rz) {
  const sep = 0.025, paso = 0.003;
  final out = <(double, double)>[];
  var th = 0.0, recorrido = 0.0, objetivo = m[0].ancho / 2 + sep / 2;
  double largo(double a, double b) {
    final p = _puntoArcada(rx, rz, 1, a).centro,
        q = _puntoArcada(rx, rz, 1, b).centro;
    return math.sqrt(math.pow(q.$1 - p.$1, 2) + math.pow(q.$3 - p.$3, 2));
  }

  for (var i = 0; i < m.length; i++) {
    while (recorrido < objetivo) {
      recorrido += largo(th, th + paso);
      th += paso;
    }
    final ant = out.isEmpty ? 0.0 : (out.last.$1 + th) / 2;
    out.add((th, th - ant));
    if (i + 1 < m.length) objetivo += m[i].ancho / 2 + sep + m[i + 1].ancho / 2;
  }
  return out;
}

const _lado = 10, _tapa = 7, _seg = 24;

(double, double) _superelipse(double th, double n) {
  final c = math.cos(th), s = math.sin(th);
  return (
    c.sign * math.pow(c.abs(), 2 / n).toDouble(),
    s.sign * math.pow(s.abs(), 2 / n).toDouble(),
  );
}

double _gauss(double x, double z, double cx, double cz, double s2) =>
    math.exp(-((x - cx) * (x - cx) + (z - cz) * (z - cz)) / s2);

double _relieve(_Tipo t, bool arriba, double xn, double zn) {
  if (t == _Tipo.molar) {
    final cusp = arriba
        ? _gauss(xn, zn, -0.45, 0.48, 0.09) +
              0.9 * _gauss(xn, zn, 0.48, 0.46, 0.08) +
              1.05 * _gauss(xn, zn, -0.38, -0.46, 0.11) +
              0.7 * _gauss(xn, zn, 0.5, -0.5, 0.07)
        : _gauss(xn, zn, -0.55, 0.46, 0.08) +
              0.92 * _gauss(xn, zn, 0.05, 0.5, 0.07) +
              0.75 * _gauss(xn, zn, 0.66, 0.3, 0.05) +
              1.05 * _gauss(xn, zn, -0.45, -0.46, 0.09) +
              0.95 * _gauss(xn, zn, 0.42, -0.46, 0.08);
    final surco =
        0.55 * math.exp(-(zn * zn) / 0.018) * (1 - xn * xn * 0.6) +
        0.35 * math.exp(-math.pow(xn + 0.05, 2) / 0.02) * (1 - zn * zn);
    return cusp - surco - 0.1;
  }
  if (t == _Tipo.premolar) {
    final cusp =
        _gauss(xn, zn, 0, 0.46, 0.12) +
        (arriba ? 0.85 : 0.45) * _gauss(xn, zn, 0, -0.46, 0.11);
    final surco =
        0.5 * math.exp(-math.pow(zn + 0.02, 2) / 0.02) * (1 - xn * xn * 0.7);
    return cusp - surco - 0.05;
  }
  return 0;
}

class _Corona {
  final p = <V3>[];
  final tri = <int>[];
  final altura = <double>[];
  final tapa = <double>[];
  final surco = <double>[];
}

_Corona _corona(_Medida md, bool arriba) {
  final c = _Corona();
  final a0 = md.ancho / 2, b0 = md.fondo / 2, t = md.tipo;
  final n = t == _Tipo.molar
      ? 2.9
      : t == _Tipo.premolar
      ? 2.5
      : t == _Tipo.canino
      ? 2.2
      : 2.35;
  final ySide =
      md.alto *
      (t == _Tipo.incisivo
          ? 0.86
          : t == _Tipo.canino
          ? 0.72
          : t == _Tipo.premolar
          ? 0.74
          : 0.72);
  final anterior = t == _Tipo.incisivo || t == _Tipo.canino;
  for (var i = 0; i <= _lado; i++) {
    final u = i / _lado;
    var s = 0.78 + 0.22 * math.sin(math.min(u / 0.42, 1) * math.pi / 2);
    s *= 1 - 0.05 * math.max(0, (u - 0.6) / 0.4);
    for (var j = 0; j < _seg; j++) {
      final (cx, cz) = _superelipse(j / _seg * math.pi * 2, n);
      var a = a0 * s, b = b0 * s;
      if (t == _Tipo.incisivo) {
        b *= 1 - 0.42 * u;
        if (cz < 0) b *= 1 - 0.18 * math.sin(u * math.pi);
      }
      if (t == _Tipo.canino) {
        a *= 1 - 0.18 * u * u;
        b *= 1 - 0.22 * u;
      }
      c.p.add((a * cx, ySide * u, b * cz + (anterior ? 0.03 * u * u : 0)));
      c.altura.add(u * ySide / md.alto);
      c.tapa.add(0);
      c.surco.add(0);
    }
  }
  for (var k = 1; k <= _tapa; k++) {
    final f = k / _tapa * math.pi / 2;
    final rho = math.cos(f);
    for (var j = 0; j < _seg; j++) {
      final (cx, cz) = _superelipse(j / _seg * math.pi * 2, n);
      const sTop = 0.95;
      double x, z, y, rel = 0;
      if (t == _Tipo.incisivo) {
        x = a0 * sTop * cx * (0.9 + 0.1 * rho);
        z = b0 * sTop * 0.58 * cz * rho;
        final xn = x / a0;
        y =
            ySide +
            md.alto * 0.14 * math.sin(f) -
            md.alto * 0.07 * math.pow(xn, 4) +
            0.012 * math.cos(xn * math.pi * 3) * math.sin(f);
      } else if (t == _Tipo.canino) {
        x = a0 * sTop * 0.82 * cx * rho;
        z = b0 * sTop * 0.78 * cz * rho;
        final xn = x / a0;
        y =
            ySide +
            md.alto * 0.3 * math.pow(math.sin(f), 1.25) -
            md.alto * 0.12 * xn.abs() * (1 - rho);
      } else {
        x = a0 * sTop * cx * rho;
        z = b0 * sTop * cz * rho;
        final w = _suave(0, 0.35, 1 - rho);
        rel = _relieve(t, arriba, x / a0, z / b0) * w;
        y = ySide + md.alto * 0.1 * math.sin(f) + rel * md.alto * 0.24;
      }
      c.p.add((x, y, z));
      c.altura.add(math.min(1, y / md.alto));
      c.tapa.add(k / _tapa);
      c.surco.add(rel < 0 ? -rel : 0);
    }
  }
  const filas = _lado + _tapa;
  for (var i = 0; i < filas; i++) {
    for (var j = 0; j < _seg; j++) {
      final a = i * _seg + j, b = i * _seg + (j + 1) % _seg;
      c.tri.addAll([a, a + _seg, b, b, a + _seg, b + _seg]);
    }
  }
  return c;
}

(List<V3>, List<int>) _raiz(_Medida md, bool implante) {
  final p = <V3>[];
  final tri = <int>[];
  final a0 = md.ancho / 2, b0 = md.fondo / 2;
  const r = 7, s = 10;
  final m = math.min(a0, b0);
  final List<(double, double, double, double, double)> raices = implante
      ? [(0, 0, m * 0.62, m * 0.62, md.largoRaiz * 0.85)]
      : md.raices == 1
      ? [(0, 0, a0 * 0.7, b0 * 0.78, md.largoRaiz)]
      : md.raices == 2 && md.tipo == _Tipo.premolar
      ? [
          (0, b0 * 0.36, a0 * 0.55, b0 * 0.42, md.largoRaiz),
          (0, -b0 * 0.36, a0 * 0.5, b0 * 0.4, md.largoRaiz * 0.95),
        ]
      : md.raices == 2
      ? [
          (-a0 * 0.42, 0, a0 * 0.38, b0 * 0.7, md.largoRaiz),
          (a0 * 0.42, 0, a0 * 0.34, b0 * 0.66, md.largoRaiz * 0.92),
        ]
      : [
          (-a0 * 0.4, b0 * 0.38, a0 * 0.34, b0 * 0.34, md.largoRaiz * 0.92),
          (a0 * 0.42, b0 * 0.38, a0 * 0.3, b0 * 0.32, md.largoRaiz * 0.86),
          (0, -b0 * 0.42, a0 * 0.42, b0 * 0.36, md.largoRaiz),
        ];
  for (final (ox, oz, ra, rb, largo) in raices) {
    final base = p.length;
    for (var i = 0; i <= r; i++) {
      final u = i / r;
      final y = 0.06 - largo * 0.86 * u;
      var k =
          math.pow(math.max(0, 1 - math.pow(u, 2.4)), 0.55) * (1 - 0.28 * u);
      if (implante) {
        k =
            (u < 0.85 ? 1 : 1 - (u - 0.85) / 0.15 * 0.6) *
            (1 + 0.09 * math.sin(u * largo * 42));
      }
      final f = implante ? 0.0 : 0.4 + 0.6 * math.min(1, u * 3);
      for (var j = 0; j < s; j++) {
        final th = j / s * math.pi * 2;
        p.add((
          ox * f + ra * k * math.cos(th),
          y,
          oz * f + rb * k * math.sin(th),
        ));
      }
    }
    for (var i = 0; i < r; i++) {
      for (var j = 0; j < s; j++) {
        final a = base + i * s + j, b = base + i * s + (j + 1) % s;
        tri.addAll([a, b, a + s, b, b + s, a + s]);
      }
    }
  }
  return (p, tri);
}

List<V3> _normales(List<V3> p, List<int> tri) {
  final acc = List<V3>.filled(p.length, (0, 0, 0));
  for (var k = 0; k < tri.length; k += 3) {
    final a = tri[k], b = tri[k + 1], c = tri[k + 2];
    final f = _cruz(_resta(p[b], p[a]), _resta(p[c], p[a]));
    acc[a] = _suma(acc[a], f);
    acc[b] = _suma(acc[b], f);
    acc[c] = _suma(acc[c], f);
  }
  return acc.map(_norm).toList();
}

List<V3> _haciaAfuera(List<V3> p, List<V3> nn, V3 centro) {
  var s = 0.0;
  for (var i = 0; i < p.length; i += 7) {
    s += _punto(nn[i], _resta(p[i], centro));
  }
  return s < 0 ? nn.map((v) => _esc(v, -1)).toList() : nn;
}

int _indiceCara(V3 nl, double tapa) {
  if ((tapa > 0.35 && nl.$2 > 0.35) || nl.$2 > 0.8) return 4;
  if (nl.$3.abs() >= nl.$1.abs() * 0.9) return nl.$3 > 0 ? 2 : 3;
  return nl.$1 > 0 ? 1 : 0;
}

double _pesoCara(String cara, V3 nl, double altura, double tapa) {
  if (cara == 'oclusal') {
    return _suave(0.3, 0.7, nl.$2) * _suave(0.55, 0.8, altura);
  }
  final l = math.max(1e-6, math.sqrt(nl.$1 * nl.$1 + nl.$3 * nl.$3));
  final (dx, dz) = switch (cara) {
    'mesial' => (-1.0, 0.0),
    'distal' => (1.0, 0.0),
    'vestibular' => (0.0, 1.0),
    _ => (0.0, -1.0),
  };
  final d = (nl.$1 * dx + nl.$3 * dz) / l;
  return _suave(0.45, 0.85, d) *
      _suave(0.1, 0.3, altura) *
      (1 - _suave(0.45, 0.85, nl.$2)) *
      (1 - _suave(0.5, 1, tapa));
}

V3 _centroCara(String c, _Medida md) {
  final a = md.ancho / 2, b = md.fondo / 2, h = md.alto;
  return switch (c) {
    'vestibular' => (
      0,
      h * 0.42,
      b * (md.tipo == _Tipo.incisivo ? 0.75 : 0.95),
    ),
    'lingual' => (0, h * 0.42, -b * 0.9),
    'mesial' => (-a * 0.95, h * 0.55, 0),
    'distal' => (a * 0.95, h * 0.55, 0),
    _ => (a * 0.08, h * 0.95, 0),
  };
}

class _Malla {
  _Malla(
    this.pos,
    this.nor,
    this.col,
    this.mat,
    this.ao,
    this.tri, {
    this.superior = true,
  });
  final List<V3> pos, nor, col;
  final List<int> mat;
  final List<double> ao;
  final List<int> tri;
  final bool superior;
}

class _Pieza {
  _Pieza({
    required this.fdi,
    required this.malla,
    required this.raiz,
    required this.superior,
    required this.ausente,
    required this.movilidad,
    required this.centro,
    required this.radio,
    required this.ancla,
    required this.afuera,
    required this.caras,
  });
  final List<int> caras;
  final String fdi;
  final _Malla malla;
  final _Malla? raiz;
  final bool superior, ausente, movilidad;
  final V3 centro, ancla, afuera;
  final double radio;
}

class _Boca {
  _Boca(this.piezas, this.encias);
  final List<_Pieza> piezas;
  final List<_Malla> encias;
}

const _distancia = 0.04;

_Pieza _armarPieza(
  String fdi,
  _Medida md,
  _Marco marco,
  bool arriba,
  List<Map<String, dynamic>> hallazgos,
) {
  final c = _corona(md, arriba);
  final codigos = hallazgos.map((h) => '${h['condition']}').toSet();
  final ausente =
      codigos.contains('ausente') || codigos.contains('extraccion_realizada');
  final completo = _completos.where(codigos.contains).firstOrNull;
  final implante = codigos.contains('implante');
  final retenido = codigos.contains('diente_retenido');

  final inclin = md.tipo == _Tipo.incisivo
      ? (arriba ? 0.24 : 0.12)
      : md.tipo == _Tipo.canino
      ? 0.1
      : md.tipo == _Tipo.premolar
      ? 0.02
      : (arriba ? -0.02 : -0.08);
  final sArco = arriba ? 1.0 : -1.0;
  final V3 u0 = (0, -sArco, 0);
  final o0 = marco.vestibular;
  final uu = _norm(
    _suma(_esc(u0, math.cos(inclin)), _esc(o0, math.sin(inclin))),
  );
  final oo = _norm(
    _suma(_esc(o0, math.cos(inclin)), _esc(u0, -math.sin(inclin))),
  );
  final tt = marco.distal;
  final hundido = retenido ? md.alto * 0.7 : 0.0;
  final V3 origen = (
    marco.centro.$1,
    sArco * (_distancia + md.alto + hundido),
    marco.centro.$3,
  );
  V3 mundo(V3 v) => _suma(
    _suma(_suma(origen, _esc(tt, v.$1)), _esc(uu, v.$2)),
    _esc(oo, v.$3),
  );
  V3 giro(V3 v) => _suma(_suma(_esc(tt, v.$1), _esc(uu, v.$2)), _esc(oo, v.$3));

  final nl = _haciaAfuera(c.p, _normales(c.p, c.tri), (0, md.alto * 0.45, 0));
  final porCara = <String, String?>{};
  for (final cara in caras3D) {
    final aqui = hallazgos.where(
      (h) =>
          h['surface'] == cara ||
          (h['surface'] == 'whole' && _ordenCara.contains(h['condition'])),
    );
    porCara[cara] = _ordenCara
        .where((k) => aqui.any((h) => h['condition'] == k))
        .firstOrNull;
  }
  final variacion = (_ruido(double.tryParse(fdi) ?? 0, 1.7, 3.1) - 0.5) * 0.03;
  final anterior = md.tipo == _Tipo.incisivo || md.tipo == _Tipo.canino;

  final caras = <int>[];
  final pos = <V3>[],
      nor = <V3>[],
      col = <V3>[],
      mat = <int>[],
      ao = <double>[];
  for (var i = 0; i < c.p.length; i++) {
    final v = c.p[i], nn = nl[i], h = c.altura[i];
    var color = _mezcla(_cuello, _esmalte, _suave(0.02, 0.4, h));
    if (anterior) color = _mezcla(color, _borde, _suave(0.8, 1, h) * 0.55);
    color = (
      color.$1 + variacion,
      color.$2 + variacion,
      color.$3 + variacion * 0.6,
    );
    var material = _matEsmalte;
    var oclusion = 0.7 + 0.3 * _suave(0, 0.32, h);
    if (nn.$1.abs() > 0.75) oclusion *= 0.9;
    oclusion *= 1 - math.min(0.35, c.surco[i] * 0.55);

    if (completo == 'corona') {
      color = _oro;
      material = _matMetal;
    } else if (implante) {
      color = (0.93, 0.94, 0.95);
      material = _matBrillo;
    } else if (completo == 'protesis' || completo == 'puente') {
      color = _mezcla(color, _rgb(condicionDe(completo!).color), 0.38);
      material = _matBrillo;
    } else if (completo == 'extraccion_indicada') {
      color = _mezcla(color, _rgb(const Color(0xFFFB8C00)), 0.42);
    } else if (completo == 'endodoncia') {
      color = _mezcla(color, (0.82, 0.78, 0.72), 0.4);
    } else if (completo == 'diente_retenido') {
      color = _mezcla(color, _rgb(const Color(0xFFA1887F)), 0.25);
    } else if (completo == 'movilidad') {
      color = _mezcla(color, _rgb(const Color(0xFFD81B60)), 0.18);
    }

    if (!ausente && completo != 'corona' && !implante) {
      for (final cf in caras3D) {
        final cod = porCara[cf];
        if (cod == null) continue;
        var w = _pesoCara(cf, nn, h, c.tapa[i]);
        if (w <= 0.01) continue;
        final cc = _rgb(condicionDe(cod).color);
        final lateral = cf == 'mesial' || cf == 'distal';
        if (cod == 'caries') {
          final cen = _centroCara(cf, md);
          final ang = math.atan2(
            v.$2 - cen.$2,
            (lateral ? v.$3 : v.$1) - (lateral ? cen.$3 : cen.$1),
          );
          final semilla =
              (double.tryParse(fdi) ?? 0) * 0.37 + caras3D.indexOf(cf);
          final radio =
              (lateral ? md.fondo : md.ancho) *
              (cf == 'oclusal' ? 0.34 : 0.3) *
              (0.82 +
                  0.18 * math.sin(ang * 3 + semilla) +
                  0.08 * math.sin(ang * 7 + semilla * 2));
          final dist =
              math.sqrt(
                math.pow(v.$1 - cen.$1, 2) +
                    math.pow(v.$2 - cen.$2, 2) +
                    math.pow(v.$3 - cen.$3, 2),
              ) /
              radio;
          w = _clamp(w * 1.4) * (1 - _suave(0.7, 1.05, dist));
          color = _mezcla(color, cc, w * 0.94);
          if (w > 0.5) {
            color = _mezcla(
              color,
              _oscuro,
              (w - 0.5) * (1 - _suave(0, 0.6, dist)) * 1.1,
            );
          }
        } else if (cod == 'fractura') {
          final eje = lateral ? v.$3 / (md.fondo / 2) : v.$1 / (md.ancho / 2);
          final linea =
              0.12 + 0.18 * math.sin(h * 13) + 0.08 * math.sin(h * 31);
          final grieta = 1 - _suave(0.04, 0.1, (eje - linea).abs());
          color = _mezcla(color, cc, grieta * w * 0.95);
        } else if (cod == 'sellante') {
          color = _mezcla(color, cc, _suave(0.2, 0.6, w) * 0.55);
          if (w > 0.4) material = _matBrillo;
        } else {
          final borde = _suave(0.25, 0.45, w);
          color = _mezcla(color, cc, borde * 0.88);
          if (borde > 0.5) material = _matBrillo;
        }
      }
    }
    caras.add(_indiceCara(nn, c.tapa[i]));
    pos.add(mundo(v));
    nor.add(giro(nn));
    col.add(ausente ? (0.82, 0.86, 0.88) : color);
    mat.add(material);
    ao.add(oclusion);
  }

  _Malla? raiz;
  if (!ausente) {
    final (rp, rt) = _raiz(md, implante);
    final rn = _haciaAfuera(rp, _normales(rp, rt), (0, -md.largoRaiz * 0.4, 0));
    final colorRaiz = implante
        ? _titanio
        : (completo == 'endodoncia'
              ? _mezcla(_dentina, (0.75, 0.31, 0.23), 0.55)
              : _dentina);
    raiz = _Malla(
      rp.map(mundo).toList(),
      rn.map(giro).toList(),
      List.filled(rp.length, colorRaiz),
      List.filled(rp.length, implante ? _matMetal : _matRaiz),
      List.filled(rp.length, 0.9),
      rt,
      superior: arriba,
    );
  }
  return _Pieza(
    fdi: fdi,
    malla: _Malla(pos, nor, col, mat, ao, c.tri, superior: arriba),
    raiz: raiz,
    superior: arriba,
    ausente: ausente,
    movilidad: codigos.contains('movilidad'),
    centro: mundo((0, md.alto * 0.55, 0)),
    radio: math.max(md.ancho, math.max(md.fondo, md.alto)) * 0.62,
    ancla: mundo((0, md.alto * 1.22, md.fondo * 0.35)),
    afuera: oo,
    caras: caras,
  );
}

List<double> _catmull(
  List<double> p0,
  List<double> p1,
  List<double> p2,
  List<double> p3,
  double t,
) {
  final t2 = t * t, t3 = t2 * t;
  return List.generate(
    p1.length,
    (k) =>
        0.5 *
        (2 * p1[k] +
            (-p0[k] + p2[k]) * t +
            (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 +
            (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3),
  );
}

List<List<double>> _curva(List<List<double>> ctrl, int muestras) {
  final out = <List<double>>[];
  final tramos = ctrl.length - 1;
  for (var i = 0; i <= muestras; i++) {
    final g = i / muestras * tramos;
    final s = math.min(tramos - 1, g.floor());
    out.add(
      _catmull(
        ctrl[math.max(0, s - 1)],
        ctrl[s],
        ctrl[s + 1],
        ctrl[math.min(tramos, s + 2)],
        g - s,
      ),
    );
  }
  return out;
}

class _Hueco {
  const _Hueco(this.th, this.medio, this.cej, this.fondo, this.papila);
  final double th, medio, cej, fondo, papila;
}

_Malla _encia(double rx, double rz, List<_Hueco> piezas, bool arriba) {
  final s = arriba ? 1.0 : -1.0;
  final ult = piezas.last;
  final thMax = ult.th + ult.medio;
  const extra = 0.16, n = 120, p = 26;
  final pos = <V3>[], col = <V3>[], ao = <double>[];

  (double, double, double) enDiente(double th) {
    final a = th.abs();
    for (var i = 0; i < piezas.length; i++) {
      final pz = piezas[i];
      final lo = pz.th - pz.medio;
      final hi = i + 1 < piezas.length
          ? (pz.th + piezas[i + 1].th) / 2
          : pz.th + pz.medio;
      if (a <= hi || i == piezas.length - 1) {
        final mitad = a < pz.th ? pz.th - lo : hi - pz.th;
        final v = _clamp((a - pz.th) / (mitad == 0 ? 1 : mitad), -1, 1);
        final vecino = v < 0
            ? piezas[math.max(0, i - 1)]
            : piezas[math.min(piezas.length - 1, i + 1)];
        final mez = v * v * 0.5;
        return (
          pz.cej + (vecino.cej - pz.cej) * mez,
          pz.fondo + (vecino.fondo - pz.fondo) * mez,
          pz.papila * math.pow(v.abs(), 2.4),
        );
      }
    }
    return (ult.cej, ult.fondo, 0);
  }

  for (var i = 0; i <= n; i++) {
    final th = -(thMax + extra) + 2 * (thMax + extra) * i / n;
    final a = th.abs();
    final mk = _puntoArcada(
      rx,
      rz,
      th < 0 ? -1 : 1,
      math.min(a, thMax + extra),
    );
    final (cej, fondo, papila) = enDiente(math.min(a, thMax));
    final e = a > thMax ? (a - thMax) / extra : 0.0;
    final cierre = math.sqrt(math.max(0, 1 - e * e));
    final hb = cej - 0.11 + e * 0.55;
    final hm = hb - papila * 0.34;
    final f = fondo / 2;
    final perfil = _curva([
      [0, hb + 1.1],
      [-(f + 0.26), hb + 1.0],
      [-(f + 0.32), hb + 0.6],
      [-(f + 0.08), hm + 0.2],
      [-f * 0.84, hm],
      [0, hm + 0.04],
      [f * 0.88, hm],
      [f + 0.12, hm + 0.2],
      [f + 0.28, hb + 0.6],
      [f + 0.24, hb + 1.0],
      [0, hb + 1.1],
    ], p);
    for (final q in perfil) {
      final o = q[0] * cierre;
      final d2 = hb + (q[1] - hb) * (0.35 + 0.65 * cierre);
      pos.add((
        mk.centro.$1 + mk.vestibular.$1 * o,
        s * d2,
        mk.centro.$3 + mk.vestibular.$3 * o,
      ));
      final prof = d2 - hm;
      col.add(_mezcla(_enciaFija, _mucosa, _suave(0.45, 1.6, prof)));
      ao.add(0.8 + 0.2 * _suave(0, 0.25, prof));
    }
  }
  const ancho = p + 1;
  final tri = <int>[];
  for (var i = 0; i < n; i++) {
    for (var j = 0; j < p; j++) {
      final a = i * ancho + j, b = a + ancho;
      tri.addAll([a, b, a + 1, a + 1, b, b + 1]);
    }
  }
  if (arriba) {
    final base = pos.length;
    const r = 7;
    final cz = -rz * 0.62;
    final muestras = <int>[];
    for (var i = 0; i <= n; i += 2) {
      final th = -(thMax + extra) + 2 * (thMax + extra) * i / n;
      if (th.abs() <= thMax) muestras.add(i);
    }
    final alto = piezas.map((x) => x.cej).reduce(math.max) + 0.9;
    for (final i in muestras) {
      final q = pos[i * ancho + 5];
      final d0 = q.$2.abs();
      for (var k = 0; k <= r; k++) {
        final u = k / r;
        final z = q.$3 + (cz - q.$3) * u * 0.12;
        final frente = _suave(-1.2, 0.2, z) * (1 - u);
        final d =
            d0 +
            (alto - d0) * math.sin(u * math.pi / 2) -
            0.05 * math.sin(u * 22) * frente;
        pos.add((q.$1 * (1 - u), d, z));
        col.add(_mezcla(_paladar, _mucosa, 0.15 * u));
        ao.add(0.85 + 0.15 * u);
      }
    }
    for (var k = 0; k + 1 < muestras.length; k++) {
      for (var j = 0; j < r; j++) {
        final a = base + k * (r + 1) + j, b = a + r + 1;
        tri.addAll([a, a + 1, b, a + 1, b + 1, b]);
      }
    }
  }
  return _Malla(
    pos,
    _normales(pos, tri),
    col,
    List.filled(pos.length, _matEncia),
    ao,
    tri,
    superior: arriba,
  );
}

_Boca _armarBoca(List<Map<String, dynamic>> hallazgos, bool temporal) {
  final porPieza = <String, List<Map<String, dynamic>>>{};
  for (final h in hallazgos) {
    porPieza.putIfAbsent('${h['fdi_number']}', () => []).add(h);
  }
  final piezas = <_Pieza>[];
  final encias = <_Malla>[];
  final arcos = temporal
      ? [
          ([5, 6], true, _temporales, 2.0, 2.25),
          ([8, 7], false, _temporales, 1.85, 2.05),
        ]
      : [
          ([1, 2], true, _superior, 2.62, 3.1),
          ([4, 3], false, _inferior, 2.4, 2.86),
        ];
  for (final (cuadrantes, arriba, medidas, rx, rz) in arcos) {
    final lugares = _ubicar(medidas, rx, rz);
    final huecos = [
      for (var i = 0; i < lugares.length; i++)
        _Hueco(
          lugares[i].$1,
          lugares[i].$2,
          _distancia + medidas[i].alto,
          medidas[i].fondo,
          medidas[i].tipo == _Tipo.molar
              ? 0.7
              : medidas[i].tipo == _Tipo.premolar
              ? 0.85
              : 1,
        ),
    ];
    for (var k = 0; k < 2; k++) {
      final lado = k == 0 ? -1.0 : 1.0;
      for (var i = 0; i < lugares.length; i++) {
        final fdi = '${cuadrantes[k]}${i + 1}';
        piezas.add(
          _armarPieza(
            fdi,
            medidas[i],
            _puntoArcada(rx, rz, lado, lugares[i].$1),
            arriba,
            porPieza[fdi] ?? const [],
          ),
        );
      }
    }
    encias.add(_encia(rx, rz, huecos, arriba));
  }
  return _Boca(piezas, encias);
}

const _ordenPerm = (
  [
    '18',
    '17',
    '16',
    '15',
    '14',
    '13',
    '12',
    '11',
    '21',
    '22',
    '23',
    '24',
    '25',
    '26',
    '27',
    '28',
  ],
  [
    '48',
    '47',
    '46',
    '45',
    '44',
    '43',
    '42',
    '41',
    '31',
    '32',
    '33',
    '34',
    '35',
    '36',
    '37',
    '38',
  ],
);
const _ordenTemp = (
  ['55', '54', '53', '52', '51', '61', '62', '63', '64', '65'],
  ['85', '84', '83', '82', '81', '71', '72', '73', '74', '75'],
);

Color? colorPrincipal(List<Map<String, dynamic>> hallazgos, String fdi) {
  final aqui = hallazgos
      .where((h) => h['fdi_number'] == fdi && h['condition'] != 'sano')
      .map((h) => '${h['condition']}')
      .toSet();
  for (final c in [
    'ausente',
    'extraccion_realizada',
    ..._completos,
    ..._ordenCara,
  ]) {
    if (aqui.contains(c)) return condicionDe(c).color;
  }
  return null;
}

enum Arcada3D { ambas, superior, inferior }

class Boca3D extends StatefulWidget {
  const Boca3D({
    super.key,
    required this.hallazgos,
    this.temporal = false,
    this.seleccionado,
    this.alTocar,
    this.alTocarCara,
    this.alto = 420,
  });

  final List<Map<String, dynamic>> hallazgos;
  final bool temporal;
  final String? seleccionado;
  final ValueChanged<String?>? alTocar;
  final void Function(String fdi, String cara)? alTocarCara;
  final double alto;

  @override
  State<Boca3D> createState() => _Boca3DState();
}

class _Camara {
  _Camara(this.yaw, this.pitch, this.dist, this.mira);
  double yaw, pitch, dist;
  V3 mira;
}

class _Boca3DState extends State<Boca3D> with SingleTickerProviderStateMixin {
  late _Boca _boca;
  double _apertura = 0.42, _aperturaObj = 0.42;
  Arcada3D _arcada = Arcada3D.ambas;
  bool _girando = false, _raices = false, _numeros = true;
  String? _elegida;
  String? _vista = 'frente';

  static const V3 _miraInicio = (0, 0, -1.45);
  final _cam = _Camara(-0.7, 0.4, 16, _miraInicio);
  final _dest = _Camara(0, 0.16, 12.4, _miraInicio);
  double _velYaw = 0, _velPitch = 0;
  late final Ticker _ticker;
  Duration _ultimo = Duration.zero;
  Size _tam = Size.zero;

  final _dedos = <int, Offset>{};
  double _pellizco = 0, _movido = 0;
  bool _arrastrando = false;

  @override
  void initState() {
    super.initState();
    _elegida = widget.seleccionado;
    _boca = _armarBoca(widget.hallazgos, widget.temporal);
    _ticker = createTicker(_paso)..start();
  }

  @override
  void didUpdateWidget(Boca3D old) {
    super.didUpdateWidget(old);
    if (old.hallazgos != widget.hallazgos || old.temporal != widget.temporal) {
      _boca = _armarBoca(widget.hallazgos, widget.temporal);
    }
    if (old.seleccionado != widget.seleccionado) _elegida = widget.seleccionado;
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  bool get _sinMovimiento =>
      MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  void _paso(Duration t) {
    final dt = _ultimo == Duration.zero
        ? 0.016
        : math.min(0.05, (t - _ultimo).inMicroseconds / 1e6);
    _ultimo = t;
    if (!_arrastrando) {
      _dest.yaw += _velYaw;
      _dest.pitch = (_dest.pitch + _velPitch).clamp(-1.38, 1.38);
      final roce = math.pow(0.0025, dt).toDouble();
      _velYaw *= roce;
      _velPitch *= roce;
    }
    if (_girando) _dest.yaw += dt * 0.35;
    final k = 1 - math.exp(-dt * (_sinMovimiento ? 40 : 9));
    final antes =
        _cam.yaw +
        _cam.pitch +
        _cam.dist +
        _cam.mira.$1 +
        _cam.mira.$2 +
        _cam.mira.$3 +
        _apertura;
    _cam.yaw += (_dest.yaw - _cam.yaw) * k;
    _cam.pitch += (_dest.pitch - _cam.pitch) * k;
    _cam.dist += (_dest.dist - _cam.dist) * k;
    _cam.mira = _suma(_cam.mira, _esc(_resta(_dest.mira, _cam.mira), k));
    _apertura += (_aperturaObj - _apertura) * (1 - math.exp(-dt * 10));
    final despues =
        _cam.yaw +
        _cam.pitch +
        _cam.dist +
        _cam.mira.$1 +
        _cam.mira.$2 +
        _cam.mira.$3 +
        _apertura;
    final animado = _boca.piezas.any((p) => p.movilidad) && !_sinMovimiento;
    if ((antes - despues).abs() > 1e-5 || _elegida != null || animado) {
      setState(() {});
    }
  }

  bool _visible(bool superior) =>
      _arcada == Arcada3D.ambas || (_arcada == Arcada3D.superior) == superior;

  double get _sep => 0.02 + 1.15 * _apertura;

  V3 _desplazo(bool superior, [_Pieza? p]) {
    var off = (0.0, _sep * (superior ? 1 : -1), 0.0);
    if (p != null && p.movilidad && !_sinMovimiento) {
      final w = math.sin(DateTime.now().millisecondsSinceEpoch / 95) * 0.022;
      off = _suma(off, _esc(p.afuera, w));
    }
    return off;
  }

  _Proyector _proyector() => _Proyector(_cam, _tam);

  void _cambiarVista(String v) {
    final base = (_dest.yaw / (2 * math.pi)).roundToDouble() * 2 * math.pi;
    final (y, p, d, a) = switch (v) {
      'arriba' => (0.0, -1.36, 11.5, Arcada3D.superior),
      'abajo' => (0.0, 1.36, 11.5, Arcada3D.inferior),
      'derecha' => (-1.3, 0.12, 11.5, Arcada3D.ambas),
      'izquierda' => (1.3, 0.12, 11.5, Arcada3D.ambas),
      _ => (0.0, 0.16, 12.4, Arcada3D.ambas),
    };
    setState(() {
      _girando = false;
      _velYaw = _velPitch = 0;
      _dest
        ..yaw = base + y
        ..pitch = p
        ..dist = d
        ..mira = _miraInicio;
      _arcada = a;
      _vista = v;
    });
  }

  void _enfocar(String fdi) {
    final p = _boca.piezas.where((x) => x.fdi == fdi).firstOrNull;
    if (p == null) return;
    final off = _desplazo(p.superior);
    final base = (_dest.yaw / (2 * math.pi)).roundToDouble() * 2 * math.pi;
    var yaw = math.atan2(p.afuera.$1, p.afuera.$3);
    while (yaw - (_dest.yaw - base) > math.pi) {
      yaw -= 2 * math.pi;
    }
    while (yaw - (_dest.yaw - base) < -math.pi) {
      yaw += 2 * math.pi;
    }
    setState(() {
      if (!_visible(p.superior)) _arcada = Arcada3D.ambas;
      _dest
        ..yaw = base + yaw
        ..pitch = p.superior ? -0.12 : 0.32
        ..dist = 6.2
        ..mira = _suma(p.centro, off);
      _velYaw = _velPitch = 0;
      _girando = false;
      _vista = null;
    });
  }

  String? _buscar(Offset punto) {
    final pr = _proyector();
    String? mejor;
    var mejorZ = double.infinity;
    for (final p in _boca.piezas) {
      if (!_visible(p.superior)) continue;
      final (sx, sy, z) = pr.proyectar(_suma(p.centro, _desplazo(p.superior)));
      if (z <= 0.5) continue;
      final radioPx = p.radio * pr.foco / z;
      if ((Offset(sx, sy) - punto).distance < radioPx * 1.05 && z < mejorZ) {
        mejorZ = z;
        mejor = p.fdi;
      }
    }
    return mejor;
  }

  int? _cara;

  void _elegir(String? fdi, [int? cara]) => setState(() {
    _elegida = fdi;
    _cara = fdi == null ? null : cara;
  });

  int? _buscarCara(Offset punto, String fdi) {
    final p = _boca.piezas.where((x) => x.fdi == fdi).firstOrNull;
    if (p == null || p.ausente) return null;
    final pr = _proyector();
    final off = _desplazo(p.superior);
    final m = p.malla;
    final proy = [for (final v in m.pos) pr.proyectar(_suma(v, off))];
    int? mejor;
    var mejorZ = double.infinity;
    for (var k = 0; k < m.tri.length; k += 3) {
      final ia = m.tri[k], ib = m.tri[k + 1], ic = m.tri[k + 2];
      final a = proy[ia], b = proy[ib], c = proy[ic];
      final d = (b.$2 - c.$2) * (a.$1 - c.$1) + (c.$1 - b.$1) * (a.$2 - c.$2);
      if (d.abs() < 1e-9) continue;
      final l1 =
          ((b.$2 - c.$2) * (punto.dx - c.$1) +
              (c.$1 - b.$1) * (punto.dy - c.$2)) /
          d;
      final l2 =
          ((c.$2 - a.$2) * (punto.dx - c.$1) +
              (a.$1 - c.$1) * (punto.dy - c.$2)) /
          d;
      final l3 = 1 - l1 - l2;
      if (l1 < 0 || l2 < 0 || l3 < 0) continue;
      final z = a.$3 * l1 + b.$3 * l2 + c.$3 * l3;
      if (z < mejorZ) {
        mejorZ = z;
        mejor = p.caras[l1 >= l2 && l1 >= l3 ? ia : (l2 >= l3 ? ib : ic)];
      }
    }
    return mejor;
  }

  @override
  Widget build(BuildContext context) {
    final detalle = _elegida == null
        ? const <Map<String, dynamic>>[]
        : widget.hallazgos
              .where(
                (h) => h['fdi_number'] == _elegida && h['condition'] != 'sano',
              )
              .toList();
    final orden = widget.temporal ? _ordenTemp : _ordenPerm;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: Container(
            height: widget.alto,
            decoration: const BoxDecoration(
              gradient: RadialGradient(
                center: Alignment(0, -0.2),
                radius: 1.1,
                colors: [
                  Color(0xFF2B3E42),
                  Color(0xFF172427),
                  Color(0xFF0E1719),
                ],
              ),
            ),
            child: LayoutBuilder(
              builder: (context, c) {
                _tam = Size(c.maxWidth, c.maxHeight);
                final pr = _proyector();
                return Stack(
                  children: [
                    Positioned.fill(
                      child: RawGestureDetector(
                        gestures: {
                          EagerGestureRecognizer:
                              GestureRecognizerFactoryWithHandlers<
                                EagerGestureRecognizer
                              >(EagerGestureRecognizer.new, (_) {}),
                        },
                        child: GestureDetector(
                          onDoubleTapDown: (d) {
                            final f = _buscar(d.localPosition);
                            if (f != null) {
                              _enfocar(f);
                            } else {
                              _cambiarVista('frente');
                            }
                          },
                          onDoubleTap: () {},
                          child: Listener(
                            onPointerDown: (e) {
                              _dedos[e.pointer] = e.localPosition;
                              _movido = 0;
                              _arrastrando = true;
                              _velYaw = _velPitch = 0;
                              if (_dedos.length == 2) {
                                _pellizco = _distanciaDedos();
                              }
                            },
                            onPointerMove: (e) {
                              final antes = _dedos[e.pointer];
                              if (antes == null) return;
                              _dedos[e.pointer] = e.localPosition;
                              if (_dedos.length >= 2) {
                                final d = _distanciaDedos();
                                if (_pellizco > 0) {
                                  _dest.dist = (_dest.dist * _pellizco / d)
                                      .clamp(4.5, 24.0);
                                }
                                _pellizco = d;
                                _movido += 10;
                                return;
                              }
                              final delta = e.localPosition - antes;
                              _movido += delta.distance;
                              if (_movido < 4) return;
                              const k = 0.0085;
                              _girando = false;
                              _vista = null;
                              _dest.yaw -= delta.dx * k;
                              _dest.pitch = (_dest.pitch + delta.dy * k).clamp(
                                -1.38,
                                1.38,
                              );
                              _velYaw = -delta.dx * k * 0.55;
                              _velPitch = delta.dy * k * 0.55;
                            },
                            onPointerUp: (e) {
                              _dedos.remove(e.pointer);
                              if (_dedos.length < 2) _pellizco = 0;
                              if (_dedos.isEmpty) _arrastrando = false;
                              if (_movido < 8) {
                                _velYaw = _velPitch = 0;
                                final f = _buscar(e.localPosition);
                                _elegir(
                                  f,
                                  f == null
                                      ? null
                                      : _buscarCara(e.localPosition, f),
                                );
                              }
                            },
                            onPointerCancel: (e) {
                              _dedos.remove(e.pointer);
                              if (_dedos.isEmpty) _arrastrando = false;
                            },
                            child: CustomPaint(
                              size: _tam,
                              painter: _Pintor(
                                boca: _boca,
                                proyector: pr,
                                elegida: _elegida,
                                raices: _raices,
                                visible: _visible,
                                desplazo: _desplazo,
                                cara: _cara,
                                pulso:
                                    0.75 +
                                    0.25 *
                                        math.sin(
                                          DateTime.now()
                                                  .millisecondsSinceEpoch /
                                              240,
                                        ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    for (final p in _boca.piezas)
                      if (_numeros || p.fdi == _elegida) _etiqueta(p, pr),
                    Positioned(
                      left: 8,
                      right: 8,
                      top: 8,
                      child: Row(
                        children: [
                          Flexible(
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              alignment: Alignment.centerLeft,
                              child: _Grupo([
                                for (final (a, t) in const [
                                  (Arcada3D.ambas, 'Ambas'),
                                  (Arcada3D.superior, 'Maxilar'),
                                  (Arcada3D.inferior, 'Mandíbula'),
                                ])
                                  _Segmento(
                                    t,
                                    _arcada == a,
                                    () => setState(() => _arcada = a),
                                  ),
                              ]),
                            ),
                          ),
                          const SizedBox(width: 6),
                          _Grupo([
                            _Icono(
                              Icons.pin_outlined,
                              'Números',
                              _numeros,
                              () => setState(() => _numeros = !_numeros),
                            ),
                            _Icono(
                              Icons.layers_outlined,
                              'Raíces',
                              _raices,
                              () => setState(() => _raices = !_raices),
                            ),
                          ]),
                        ],
                      ),
                    ),
                    Positioned(
                      left: 8,
                      right: 8,
                      top: 52,
                      child: Row(
                        children: [
                          Flexible(
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              alignment: Alignment.centerLeft,
                              child: _Grupo([
                                for (final (v, ic, tip) in const [
                                  ('frente', Icons.face_outlined, 'Frente'),
                                  (
                                    'derecha',
                                    Icons.switch_left,
                                    'Lado derecho',
                                  ),
                                  (
                                    'izquierda',
                                    Icons.switch_right,
                                    'Lado izquierdo',
                                  ),
                                  (
                                    'arriba',
                                    Icons.expand_less,
                                    'Oclusal superior',
                                  ),
                                  (
                                    'abajo',
                                    Icons.expand_more,
                                    'Oclusal inferior',
                                  ),
                                ])
                                  _Icono(
                                    ic,
                                    tip,
                                    _vista == v,
                                    () => _cambiarVista(v),
                                  ),
                              ]),
                            ),
                          ),
                          const SizedBox(width: 6),
                          _Grupo([
                            _Icono(
                              Icons.threesixty,
                              'Girar solo',
                              _girando,
                              () => setState(() => _girando = !_girando),
                            ),
                            _Icono(
                              _aperturaObj > 0.25
                                  ? Icons.unfold_less
                                  : Icons.unfold_more,
                              _aperturaObj > 0.25
                                  ? 'Cerrar boca'
                                  : 'Abrir boca',
                              false,
                              () => setState(
                                () => _aperturaObj = _aperturaObj > 0.25
                                    ? 0.04
                                    : 0.55,
                              ),
                            ),
                          ]),
                        ],
                      ),
                    ),
                    if (_elegida != null)
                      Positioned(
                        left: 10,
                        right: 10,
                        bottom: 10,
                        child: _Detalle(
                          fdi: _elegida!,
                          detalle: detalle,
                          hallazgos: widget.hallazgos,
                          alCerrar: () => _elegir(null),
                          alEnfocar: () => _enfocar(_elegida!),
                          alRegistrar: widget.alTocar == null
                              ? null
                              : () => widget.alTocar!(_elegida),
                          cara: _cara == null ? null : caras3D[_cara!],
                          alElegirCara: (c) =>
                              setState(() => _cara = caras3D.indexOf(c)),
                          alRegistrarCara:
                              widget.alTocarCara == null || _cara == null
                              ? null
                              : () => widget.alTocarCara!(
                                  _elegida!,
                                  caras3D[_cara!],
                                ),
                        ),
                      )
                    else
                      const Positioned(
                        left: 10,
                        right: 10,
                        bottom: 8,
                        child: Text(
                          'Arrastre para girar · pellizque para acercar · toque una pieza · doble toque para verla de cerca',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 11, color: Colors.white60),
                        ),
                      ),
                  ],
                );
              },
            ),
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
          decoration: BoxDecoration(
            color: Theme.of(
              context,
            ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(14),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Column(
              children: [
                for (final fila in [orden.$1, orden.$2])
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      children: [
                        for (var i = 0; i < fila.length; i++) ...[
                          if (i == fila.length ~/ 2)
                            Container(
                              width: 1,
                              height: 20,
                              margin: const EdgeInsets.symmetric(horizontal: 4),
                              color: Colors.black26,
                            ),
                          _PiezaMapa(
                            fdi: fila[i],
                            color: colorPrincipal(widget.hallazgos, fila[i]),
                            elegida: fila[i] == _elegida,
                            ausente: widget.hallazgos.any(
                              (h) =>
                                  h['fdi_number'] == fila[i] &&
                                  (h['condition'] == 'ausente' ||
                                      h['condition'] == 'extraccion_realizada'),
                            ),
                            alTocar: () {
                              _elegir(fila[i]);
                              _enfocar(fila[i]);
                            },
                          ),
                        ],
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _etiqueta(_Pieza p, _Proyector pr) {
    final off = _desplazo(p.superior);
    final a = _suma(p.ancla, off);
    final (x, y, z) = pr.proyectar(a);
    final frente = _punto(p.afuera, _norm(_resta(pr.ojo, a)));
    final op = _visible(p.superior) && z > 0.5
        ? _clamp((frente - 0.3) / 0.3)
        : 0.0;
    if (op <= 0.01) return const SizedBox.shrink();
    final color = colorPrincipal(widget.hallazgos, p.fdi);
    final sel = p.fdi == _elegida;
    return Positioned(
      left: x - 15,
      top: y - 9,
      child: IgnorePointer(
        child: Opacity(
          opacity: op,
          child: Container(
            width: 30,
            padding: const EdgeInsets.symmetric(vertical: 1),
            decoration: BoxDecoration(
              color: sel
                  ? const Color(0xFF8FF0DE)
                  : Colors.white.withValues(alpha: p.ausente ? 0.5 : 0.9),
              borderRadius: BorderRadius.circular(99),
              border: Border.all(color: color ?? Colors.transparent, width: 2),
            ),
            child: Text(
              p.fdi,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: const Color(0xFF14242B),
                decoration: p.ausente ? TextDecoration.lineThrough : null,
              ),
            ),
          ),
        ),
      ),
    );
  }

  double _distanciaDedos() {
    final v = _dedos.values.toList();
    return math.max(1, (v[0] - v[1]).distance);
  }
}

class _Detalle extends StatelessWidget {
  const _Detalle({
    required this.fdi,
    required this.detalle,
    required this.hallazgos,
    required this.alCerrar,
    required this.alEnfocar,
    this.alRegistrar,
    this.cara,
    this.alElegirCara,
    this.alRegistrarCara,
  });
  final String? cara;
  final ValueChanged<String>? alElegirCara;
  final VoidCallback? alRegistrarCara;
  final String fdi;
  final List<Map<String, dynamic>> detalle, hallazgos;
  final VoidCallback alCerrar, alEnfocar;
  final VoidCallback? alRegistrar;

  @override
  Widget build(BuildContext context) {
    const tinta = Color(0xFF14242B);
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.96),
        borderRadius: BorderRadius.circular(18),
        boxShadow: const [
          BoxShadow(
            color: Colors.black38,
            blurRadius: 24,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 64,
            height: 64,
            child: GestureDetector(
              key: const Key('esquema-caras'),
              onTapDown: alElegirCara == null
                  ? null
                  : (d) =>
                        alElegirCara!(_caraEnEsquema(fdi, d.localPosition, 64)),
              child: CustomPaint(painter: _Esquema(fdi, hallazgos, cara)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Pieza $fdi',
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    color: tinta,
                    fontSize: 15,
                  ),
                ),
                Text(
                  nombrePieza(fdi),
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: Color(0xFF5F6F72),
                  ),
                ),
                const SizedBox(height: 4),
                if (detalle.isEmpty)
                  const Text(
                    'Sin hallazgos registrados.',
                    style: TextStyle(fontSize: 12.5, color: Color(0xFF2B9A5B)),
                  )
                else
                  for (final h in detalle.take(2))
                    Row(
                      children: [
                        Container(
                          width: 9,
                          height: 9,
                          margin: const EdgeInsets.only(right: 6),
                          decoration: BoxDecoration(
                            color: condicionDe('${h['condition']}').color,
                            borderRadius: BorderRadius.circular(3),
                          ),
                        ),
                        Flexible(
                          child: Text(
                            '${condicionDe('${h['condition']}').etiqueta} · ${_caras[h['surface']] ?? h['surface']}',
                            style: const TextStyle(fontSize: 12, color: tinta),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                if (cara != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Cara: ${_caras[cara] ?? cara}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF0D7F76),
                      ),
                    ),
                  ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    if (alRegistrarCara != null)
                      FilledButton.icon(
                        key: const Key('registrar-cara'),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size(0, 34),
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                        ),
                        onPressed: alRegistrarCara,
                        icon: const Icon(Icons.add, size: 16),
                        label: Text(
                          'Registrar en ${(_caras[cara] ?? cara ?? '').toLowerCase()}',
                        ),
                      ),
                    if (alRegistrar != null)
                      TextButton(
                        key: const Key('registrar-pieza'),
                        style: TextButton.styleFrom(
                          minimumSize: const Size(0, 34),
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                        ),
                        onPressed: alRegistrar,
                        child: const Text('Ver todo'),
                      ),
                  ],
                ),
              ],
            ),
          ),
          Column(
            children: [
              IconButton(
                icon: const Icon(Icons.close, color: tinta),
                onPressed: alCerrar,
              ),
              IconButton(
                tooltip: 'Acercar',
                icon: const Icon(
                  Icons.center_focus_strong,
                  color: Color(0xFF0D7F76),
                ),
                onPressed: alEnfocar,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

String _caraEnEsquema(String fdi, Offset p, double lado) {
  final q = int.tryParse(fdi[0]) ?? 1;
  final derecha = q == 1 || q == 4 || q == 5 || q == 8;
  final superior = q == 1 || q == 2 || q == 5 || q == 6;
  final dx = p.dx / lado * 100 - 50, dy = p.dy / lado * 100 - 50;
  if (dx.abs() < 20 && dy.abs() < 20) return 'oclusal';
  if (dy.abs() >= dx.abs()) {
    return dy < 0
        ? (superior ? 'vestibular' : 'lingual')
        : (superior ? 'lingual' : 'vestibular');
  }
  return dx < 0
      ? (derecha ? 'distal' : 'mesial')
      : (derecha ? 'mesial' : 'distal');
}

class _Esquema extends CustomPainter {
  _Esquema(this.fdi, this.hallazgos, [this.elegida]);
  final String? elegida;
  final String fdi;
  final List<Map<String, dynamic>> hallazgos;

  @override
  void paint(Canvas canvas, Size size) {
    final q = int.tryParse(fdi[0]) ?? 1;
    final derecha = q == 1 || q == 4 || q == 5 || q == 8;
    final superior = q == 1 || q == 2 || q == 5 || q == 6;
    final hs = hallazgos
        .where((h) => h['fdi_number'] == fdi && h['condition'] != 'sano')
        .toList();
    Color colorDe(String cara) {
      final h =
          hs.where((x) => x['surface'] == cara).firstOrNull ??
          hs.where((x) => x['surface'] == 'whole').firstOrNull;
      return h == null
          ? const Color(0xFFF4F1EA)
          : condicionDe('${h['condition']}').color;
    }

    final s = size.width / 100;
    Path poly(List<double> p) {
      final path = Path()..moveTo(p[0] * s, p[1] * s);
      for (var i = 2; i < p.length; i += 2) {
        path.lineTo(p[i] * s, p[i + 1] * s);
      }
      return path..close();
    }

    final figuras = <(String, List<double>)>[
      (superior ? 'vestibular' : 'lingual', [4.0, 4, 96, 4, 70, 30, 30, 30]),
      (superior ? 'lingual' : 'vestibular', [30.0, 70, 70, 70, 96, 96, 4, 96]),
      (derecha ? 'distal' : 'mesial', [4.0, 4, 30, 30, 30, 70, 4, 96]),
      (derecha ? 'mesial' : 'distal', [70.0, 30, 96, 4, 96, 96, 70, 70]),
      ('oclusal', [30.0, 30, 70, 30, 70, 70, 30, 70]),
    ];
    final borde = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = const Color(0xFF9AA9AC);
    for (final (cara, p) in figuras) {
      final path = poly(p);
      canvas.drawPath(path, Paint()..color = colorDe(cara));
      canvas.drawPath(path, borde);
      if (cara == elegida) {
        canvas.drawPath(
          path,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 3
            ..color = const Color(0xFF0D7F76),
        );
      }
    }
  }

  @override
  bool shouldRepaint(_Esquema old) =>
      old.fdi != fdi || old.hallazgos != hallazgos || old.elegida != elegida;
}

const _caras = {
  'whole': 'Diente completo',
  'mesial': 'Mesial',
  'distal': 'Distal',
  'vestibular': 'Vestibular',
  'lingual': 'Lingual/Palatina',
  'oclusal': 'Oclusal/Incisal',
};

class _Grupo extends StatelessWidget {
  const _Grupo(this.hijos);
  final List<Widget> hijos;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(3),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(99),
      border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: hijos),
  );
}

class _Segmento extends StatelessWidget {
  const _Segmento(this.texto, this.activo, this.alTocar);
  final String texto;
  final bool activo;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: alTocar,
    child: AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: BoxDecoration(
        color: activo ? Colors.white : Colors.transparent,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        texto,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: activo ? const Color(0xFF14242B) : Colors.white70,
        ),
      ),
    ),
  );
}

class _Icono extends StatelessWidget {
  const _Icono(this.icono, this.ayuda, this.activo, this.alTocar);
  final IconData icono;
  final String ayuda;
  final bool activo;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) => Tooltip(
    message: ayuda,
    child: InkResponse(
      onTap: alTocar,
      radius: 20,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: activo ? const Color(0x388FF0DE) : Colors.transparent,
          shape: BoxShape.circle,
        ),
        child: Icon(
          icono,
          size: 19,
          color: activo
              ? const Color(0xFF8FF0DE)
              : Colors.white.withValues(alpha: 0.85),
        ),
      ),
    ),
  );
}

class _PiezaMapa extends StatelessWidget {
  const _PiezaMapa({
    required this.fdi,
    required this.color,
    required this.elegida,
    required this.ausente,
    required this.alTocar,
  });
  final String fdi;
  final Color? color;
  final bool elegida, ausente;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 1.5),
      child: Opacity(
        opacity: ausente ? 0.45 : 1,
        child: Material(
          color: elegida ? scheme.primary : scheme.surface,
          borderRadius: BorderRadius.circular(9),
          child: InkWell(
            key: Key('mapa-$fdi'),
            borderRadius: BorderRadius.circular(9),
            onTap: alTocar,
            child: Container(
              width: 34,
              padding: const EdgeInsets.only(top: 4, bottom: 6),
              child: Column(
                children: [
                  Text(
                    fdi,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                      color: elegida
                          ? scheme.onPrimary
                          : scheme.onSurface.withValues(alpha: 0.75),
                      decoration: ausente ? TextDecoration.lineThrough : null,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Container(
                    width: 14,
                    height: 3,
                    decoration: BoxDecoration(
                      color: color ?? Colors.transparent,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Proyector {
  _Proyector(_Camara c, Size size) {
    final cp = math.cos(c.pitch);
    final aspecto = size.height == 0 ? 1.6 : size.width / size.height;
    final d = c.dist * math.max(1, 1.15 / aspecto);
    ojo = (
      c.mira.$1 + d * cp * math.sin(c.yaw),
      c.mira.$2 + d * math.sin(c.pitch),
      c.mira.$3 + d * cp * math.cos(c.yaw),
    );
    z = _norm(_resta(ojo, c.mira));
    x = _norm(_cruz((0, 1, 0), z));
    y = _cruz(z, x);
    cx = size.width / 2;
    cy = size.height / 2;
    foco = size.height / 2 / math.tan(0.6 / 2);
  }

  late final V3 ojo, x, y, z;
  late final double cx, cy, foco;

  (double, double, double) proyectar(V3 p) {
    final d = _resta(p, ojo);
    final zz = -_punto(d, z);
    return (cx + _punto(d, x) * foco / zz, cy - _punto(d, y) * foco / zz, zz);
  }
}

class _Pintor extends CustomPainter {
  _Pintor({
    required this.boca,
    required this.proyector,
    required this.elegida,
    required this.raices,
    required this.visible,
    required this.desplazo,
    required this.pulso,
    this.cara,
  });

  final int? cara;
  final _Boca boca;
  final _Proyector proyector;
  final String? elegida;
  final bool raices;
  final bool Function(bool) visible;
  final V3 Function(bool, [_Pieza?]) desplazo;
  final double pulso;

  static final V3 _l1 = _norm((0.35, 0.85, 0.8));
  static final V3 _l2 = _norm((-0.85, 0.15, 0.45));
  static final V3 _l3 = _norm((0.1, -0.6, 0.6));

  static int _resaltar(bool si, int argb) {
    if (!si) return argb;
    int mez(int c, int t) => (c + (t - c) * 0.5).round();
    final a = argb & 0xFF000000;
    final r = mez((argb >> 16) & 0xFF, 0x6F),
        g = mez((argb >> 8) & 0xFF, 0xE8),
        b = mez(argb & 0xFF, 0xD2);
    return a | (r << 16) | (g << 8) | b;
  }

  static double _aces(double c) =>
      _clamp((c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14));

  int _sombrear(
    V3 pos,
    V3 n0,
    V3 color,
    int mat,
    double ao,
    double alfa,
    V3? rim,
    double rimFuerza,
  ) {
    final v = _norm(_resta(proyector.ojo, pos));
    var n = n0;
    if (_punto(n, v) < 0) n = _esc(n, -1);
    final encia = mat == _matEncia,
        metal = mat == _matMetal,
        raiz = mat == _matRaiz,
        brillo = mat == _matBrillo;
    final wrap = encia ? 0.55 : (metal ? 0.1 : 0.32);
    double dif(V3 l) => math.max(0, (_punto(n, l) + wrap) / (1 + wrap));
    final dv = math.max(0.0, _punto(n, v));
    final d1 = dif(_l1), d2 = dif(_l2), d3 = dif(_l3);
    final t = n.$2 * 0.5 + 0.5;
    final ambR = 0.16 + (0.3 - 0.16) * t,
        ambG = 0.14 + (0.33 - 0.14) * t,
        ambB = 0.14 + (0.37 - 0.14) * t;
    final luzR =
        d1 * 1.05 + 0.62 * d2 * 0.45 + 0.9 * d3 * 0.22 + dv * 0.3 + ambR;
    final luzG =
        0.96 * d1 * 1.05 + 0.72 * d2 * 0.45 + 0.8 * d3 * 0.22 + dv * 0.3 + ambG;
    final luzB =
        0.9 * d1 * 1.05 + 0.9 * d2 * 0.45 + 0.75 * d3 * 0.22 + dv * 0.3 + ambB;
    final gloss = encia
        ? 48.0
        : metal
        ? 120.0
        : raiz
        ? 16.0
        : brillo
        ? 180.0
        : 85.0;
    final fuerza = encia
        ? 0.35
        : metal
        ? 1.4
        : raiz
        ? 0.05
        : brillo
        ? 1.0
        : 0.6;
    final fres = 0.04 + 0.96 * math.pow(1 - dv, 5);
    final h1 = _norm(_suma(_l1, v)), h2 = _norm(_suma(_l2, v));
    final sp =
        (math.pow(math.max(0, _punto(n, h1)), gloss) +
            0.45 * math.pow(math.max(0, _punto(n, h2)), gloss) +
            0.25 * math.pow(dv, gloss * 1.5)) *
        fuerza *
        (0.55 + fres);
    final br = color.$1 * color.$1,
        bg = color.$2 * color.$2,
        bb = color.$3 * color.$3;
    double canal(double base, double luz) {
      var c = base * luz * ao + (metal ? base * 1.4 + 0.1 : 1.0) * sp;
      if (mat == _matEsmalte) c += base * math.pow(1 - dv, 2.5) * 0.14;
      if (metal) c += base * 0.45;
      return c;
    }

    var r = canal(br, luzR), g = canal(bg, luzG), b = canal(bb, luzB);
    if (rim != null) {
      final k = math.pow(1 - dv, 2) * rimFuerza;
      r += rim.$1 * rim.$1 * k;
      g += rim.$2 * rim.$2 * k;
      b += rim.$3 * rim.$3 * k;
    }
    int ch(double c) => (math.sqrt(_aces(c)) * 255).round();
    return ((alfa * 255).round() << 24) | (ch(r) << 16) | (ch(g) << 8) | ch(b);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final pr = proyector;
    final tris = <(double, int)>[];
    final puntos = <double>[];
    final colores = <int>[];
    var cuenta = 0;

    void agregar(
      _Malla m,
      V3 off,
      double alfa,
      double sesgo, {
      V3? rim,
      double rimFuerza = 0,
      bool culling = true,
      List<int>? caras,
    }) {
      final n = m.pos.length;
      final proy = List<(double, double, double)>.generate(
        n,
        (i) => pr.proyectar(_suma(m.pos[i], off)),
        growable: false,
      );
      final col = List<int?>.filled(n, null);
      int color(int i) => col[i] ??= _resaltar(
        caras != null && cara != null && caras[i] == cara,
        _sombrear(
          _suma(m.pos[i], off),
          m.nor[i],
          m.col[i],
          m.mat[i],
          m.ao[i],
          alfa,
          rim,
          rimFuerza,
        ),
      );
      for (var k = 0; k < m.tri.length; k += 3) {
        final ia = m.tri[k], ib = m.tri[k + 1], ic = m.tri[k + 2];
        final a = proy[ia], b = proy[ib], c = proy[ic];
        if (a.$3 < 0.5 || b.$3 < 0.5 || c.$3 < 0.5) continue;
        if (culling) {
          final area =
              (b.$1 - a.$1) * (c.$2 - a.$2) - (b.$2 - a.$2) * (c.$1 - a.$1);
          var nt = _cruz(
            _resta(m.pos[ib], m.pos[ia]),
            _resta(m.pos[ic], m.pos[ia]),
          );
          if (_punto(nt, m.nor[ia]) < 0) nt = _esc(nt, -1);
          if (_punto(nt, _resta(pr.ojo, _suma(m.pos[ia], off))) <= 0) continue;
          if (area.abs() < 0.02) continue;
        }
        tris.add(((a.$3 + b.$3 + c.$3) / 3 + sesgo, cuenta));
        puntos.addAll([a.$1, a.$2, b.$1, b.$2, c.$1, c.$2]);
        colores.addAll([color(ia), color(ib), color(ic)]);
        cuenta += 3;
      }
    }

    if (!raices) {
      for (final e in boca.encias) {
        if (visible(e.superior)) {
          agregar(e, desplazo(e.superior), 1, 0, culling: false);
        }
      }
    }
    for (final p in boca.piezas) {
      if (p.ausente || !visible(p.superior)) continue;
      final off = desplazo(p.superior, p);
      final sel = p.fdi == elegida;
      agregar(
        p.malla,
        off,
        1,
        0,
        rim: sel ? (0.45, 0.95, 0.85) : null,
        rimFuerza: sel ? 1.4 * pulso : 0,
        caras: sel ? p.caras : null,
      );
      if (raices && p.raiz != null) agregar(p.raiz!, off, 1, 0);
    }
    if (raices) {
      for (final e in boca.encias) {
        if (visible(e.superior)) {
          agregar(e, desplazo(e.superior), 0.3, -500, culling: false);
        }
      }
    }
    for (final p in boca.piezas) {
      if (!p.ausente || !visible(p.superior)) continue;
      final sel = p.fdi == elegida;
      agregar(
        p.malla,
        desplazo(p.superior),
        sel ? 0.32 : 0.14,
        -1000,
        rim: (0.6, 0.85, 0.95),
        rimFuerza: sel ? 1.2 : 0.6,
        culling: false,
      );
    }

    tris.sort((p, q) => q.$1.compareTo(p.$1));
    final orden = Float32List(tris.length * 6);
    final cols = Int32List(tris.length * 3);
    for (var i = 0; i < tris.length; i++) {
      final s = tris[i].$2;
      for (var j = 0; j < 3; j++) {
        orden[i * 6 + j * 2] = puntos[(s + j) * 2];
        orden[i * 6 + j * 2 + 1] = puntos[(s + j) * 2 + 1];
        cols[i * 3 + j] = colores[s + j];
      }
    }
    final v = ui.Vertices.raw(VertexMode.triangles, orden, colors: cols);
    canvas.drawVertices(v, BlendMode.dst, Paint());
  }

  @override
  bool shouldRepaint(_Pintor old) => true;
}
