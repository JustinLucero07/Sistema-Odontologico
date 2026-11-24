class Usuario {
  const Usuario({
    required this.id,
    required this.clinicaId,
    required this.email,
    required this.nombre,
    required this.apellido,
    required this.esSuperadmin,
    required this.roles,
    required this.permisos,
    this.confidencialidadPendiente = false,
    this.debeCambiarClave = false,
  });

  final String id;
  final String clinicaId;
  final String email;
  final String nombre;
  final String apellido;
  final bool esSuperadmin;
  final List<String> roles;
  final List<String> permisos;

  final bool confidencialidadPendiente;

  final bool debeCambiarClave;

  String get nombreCompleto => '$nombre $apellido';
  String get iniciales {
    final a = nombre.isNotEmpty ? nombre[0] : '';
    final b = apellido.isNotEmpty ? apellido[0] : '';
    return '$a$b'.toUpperCase();
  }

  bool puede(String permiso) => esSuperadmin || permisos.contains(permiso);

  factory Usuario.fromJson(Map<String, dynamic> json) => Usuario(
    id: json['id'] as String,
    clinicaId: json['clinic_id'] as String,
    email: json['email'] as String,
    nombre: json['first_name'] as String,
    apellido: json['last_name'] as String,
    esSuperadmin: json['is_superadmin'] as bool? ?? false,
    roles: (json['roles'] as List? ?? []).cast<String>(),
    permisos: (json['permissions'] as List? ?? []).cast<String>(),
    confidencialidadPendiente:
        json['confidentiality_required'] as bool? ?? false,
    debeCambiarClave: json['must_change_password'] as bool? ?? false,
  );
}
