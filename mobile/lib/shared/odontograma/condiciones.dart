import 'package:flutter/material.dart';

/// Catálogo de condiciones del odontograma.
///
/// Mismos códigos, nombres y colores que la web
/// (frontend/src/app/shared/odontogram/tooth-conditions.ts): una caries no
/// puede ser roja en el escritorio y de otro color en el teléfono.
class Condicion {
  const Condicion(this.codigo, this.etiqueta, this.color);

  final String codigo;
  final String etiqueta;
  final Color color;
}

const condiciones = <Condicion>[
  Condicion('caries', 'Caries', Color(0xFFE53935)),
  Condicion('restauracion', 'Restauración', Color(0xFF1E88E5)),
  Condicion(
    'restauracion_defectuosa',
    'Restauración defectuosa',
    Color(0xFFFB8C00),
  ),
  Condicion('corona', 'Corona', Color(0xFFFDD835)),
  Condicion('puente', 'Puente', Color(0xFF8E24AA)),
  Condicion('implante', 'Implante', Color(0xFF00897B)),
  Condicion('ausente', 'Ausente', Color(0xFF9E9E9E)),
  Condicion('extraccion_indicada', 'Extracción indicada', Color(0xFFFB8C00)),
  Condicion('extraccion_realizada', 'Extracción realizada', Color(0xFF757575)),
  Condicion('endodoncia', 'Endodoncia', Color(0xFF6D4C41)),
  Condicion('fractura', 'Fractura', Color(0xFF212121)),
  Condicion('sellante', 'Sellante', Color(0xFF7CB342)),
  Condicion('protesis', 'Prótesis', Color(0xFF3949AB)),
  Condicion('movilidad', 'Movilidad', Color(0xFFD81B60)),
  Condicion('diente_retenido', 'Diente retenido', Color(0xFF795548)),
  Condicion(
    'tratamiento_pendiente',
    'Tratamiento pendiente',
    Color(0xFFFDD835),
  ),
  Condicion(
    'tratamiento_realizado',
    'Tratamiento realizado',
    Color(0xFF43A047),
  ),
];

final _porCodigo = {for (final c in condiciones) c.codigo: c};

/// Un código que el teléfono aún no conoce se muestra tal cual y en gris, en
/// vez de desaparecer: es un hallazgo clínico y no puede perderse.
Condicion condicionDe(String codigo) =>
    _porCodigo[codigo] ?? Condicion(codigo, codigo, const Color(0xFFBDBDBD));

const etiquetasSuperficie = <String, String>{
  'whole': 'Pieza completa',
  'mesial': 'Mesial',
  'distal': 'Distal',
  'vestibular': 'Vestibular',
  'lingual': 'Lingual / palatina',
  'oclusal': 'Oclusal / incisal',
};

/// Las piezas que ya no están en boca se tachan en vez de colorearse.
bool esPiezaAusente(String? codigo) =>
    codigo == 'ausente' || codigo == 'extraccion_realizada';
