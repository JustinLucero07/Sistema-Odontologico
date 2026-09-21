class Cita {
  const Cita({
    required this.id,
    required this.pacienteId,
    required this.pacienteNombre,
    required this.profesionalNombre,
    required this.inicio,
    required this.fin,
    required this.estado,
    this.tratamientoNombre,
    this.notas,
  });

  final String id;
  final String pacienteId;
  final String pacienteNombre;
  final String profesionalNombre;
  final DateTime inicio;
  final DateTime fin;
  final String estado;
  final String? tratamientoNombre;
  final String? notas;

  int get duracionMinutos => fin.difference(inicio).inMinutes;

  factory Cita.fromJson(Map<String, dynamic> json) => Cita(
    id: json['id'] as String,
    pacienteId: json['patient_id'] as String,
    pacienteNombre: json['patient_name'] as String? ?? '',
    profesionalNombre: json['professional_name'] as String? ?? '',
    // El servidor manda UTC; se convierte a la hora del dispositivo para
    // que «11:00» sea las once donde está el odontólogo.
    inicio: DateTime.parse(json['starts_at'] as String).toLocal(),
    fin: DateTime.parse(json['ends_at'] as String).toLocal(),
    estado: json['status'] as String,
    tratamientoNombre: json['treatment_name'] as String?,
    notas: json['notes'] as String?,
  );
}
