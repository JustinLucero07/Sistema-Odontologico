class PacienteResumen {
  const PacienteResumen({
    required this.id,
    required this.nombre,
    required this.apellido,
    this.cedula,
    this.telefono,
    this.edad,
  });

  final String id;
  final String nombre;
  final String apellido;
  final String? cedula;
  final String? telefono;
  final int? edad;

  String get nombreCompleto => '$nombre $apellido';
  String get iniciales {
    final a = nombre.isNotEmpty ? nombre[0] : '';
    final b = apellido.isNotEmpty ? apellido[0] : '';
    return '$a$b'.toUpperCase();
  }

  factory PacienteResumen.fromJson(Map<String, dynamic> json) =>
      PacienteResumen(
        id: json['id'] as String,
        nombre: json['first_name'] as String,
        apellido: json['last_name'] as String,
        cedula: json['national_id'] as String?,
        telefono: json['phone'] as String? ?? json['whatsapp'] as String?,
        edad: json['age'] as int?,
      );
}
