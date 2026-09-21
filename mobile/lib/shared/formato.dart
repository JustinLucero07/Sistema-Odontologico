import 'package:intl/intl.dart';

/// Importe con el símbolo delante y coma decimal, igual que en la web.
///
/// `NumberFormat.currency(locale: 'es')` sigue el patrón del idioma y pone el
/// símbolo DETRÁS («180,00 $»); la misma cantidad no puede leerse distinto en
/// el móvil y en el escritorio.
final _numero = NumberFormat.decimalPatternDigits(
  locale: 'es',
  decimalDigits: 2,
);

String dinero(num valor) => '\$ ${_numero.format(valor)}';
