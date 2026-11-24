import 'package:intl/intl.dart';

final _numero = NumberFormat.decimalPatternDigits(
  locale: 'es',
  decimalDigits: 2,
);

String dinero(num valor) => '\$ ${_numero.format(valor)}';
