"""Textos legales que la consulta acepta frente al proveedor del sistema.

Se generan en el servidor para que la web y el celular muestren exactamente el
mismo texto y la misma versión. Son una base razonable para Ecuador (LOPDP);
el proveedor debe revisarlos con su asesor legal antes de vender.
"""

from app.core.config import get_settings
from app.modules.clinics.models import Clinic
from app.modules.privacy.constants import TERMS_VERSION


def _proveedor() -> str:
    p = get_settings().PROVIDER_NAME
    if get_settings().PROVIDER_TAX_ID:
        p += f", RUC {get_settings().PROVIDER_TAX_ID}"
    return p


def _Proveedor() -> str:
    """Al inicio de una oración."""
    p = _proveedor()
    return p[:1].upper() + p[1:]


def _cliente(c: Clinic) -> str:
    nombre = c.legal_name or c.name
    return f"{nombre}{f', RUC {c.tax_id}' if c.tax_id else ''}"


def terms_of_use(c: Clinic) -> list[dict]:
    contacto = get_settings().PROVIDER_EMAIL or "los canales de soporte del proveedor"
    return [
        {"title": "Objeto", "paragraphs": [
            f"Estos términos regulan el uso del sistema de gestión odontológica que {_proveedor()} (el «proveedor») "
            f"pone a disposición de {_cliente(c)} (el «cliente»): agenda, historia clínica, odontograma, planes de "
            "tratamiento, cobros, finanzas, documentos y la aplicación móvil.",
        ]},
        {"title": "Licencia de uso", "paragraphs": [
            "El cliente recibe una licencia de uso no exclusiva e intransferible mientras su suscripción esté vigente. "
            "No puede revender, sublicenciar, copiar ni descompilar el sistema.",
            "El cliente es responsable de las cuentas que crea para su personal, de asignar permisos adecuados y de "
            "que cada persona use su propio usuario.",
        ]},
        {"title": "Datos del cliente", "paragraphs": [
            "Los datos de pacientes, historias clínicas, imágenes y cobros pertenecen al cliente. El proveedor no los "
            "usa para fines propios, no los vende y solo accede a ellos para dar soporte cuando el cliente lo pide o "
            "cuando lo exija una ley.",
            "El cliente puede exportar sus datos en cualquier momento. Al terminar la relación, el proveedor los "
            "entrega en un formato legible y los elimina de sus servidores en un plazo razonable, salvo obligación "
            "legal de conservarlos.",
        ]},
        {"title": "Responsabilidad clínica", "paragraphs": [
            "El sistema es una herramienta de registro y gestión. Las decisiones clínicas, los diagnósticos, las "
            "recetas y el contenido de la historia clínica son responsabilidad exclusiva del profesional que los "
            "registra. Las sugerencias automáticas, si las hay, son orientativas.",
        ]},
        {"title": "Disponibilidad y respaldos", "paragraphs": [
            "El proveedor procura que el sistema esté disponible de forma continua y realiza respaldos periódicos. "
            "Puede haber interrupciones por mantenimiento, que se avisarán con anticipación cuando sea posible.",
        ]},
        {"title": "Obligaciones del cliente", "paragraphs": [
            "Cumplir la normativa sanitaria y de protección de datos que le aplica como responsable del tratamiento: "
            "informar a sus pacientes, obtener sus autorizaciones, atender sus solicitudes y conservar la historia "
            "clínica durante el plazo legal.",
            "Mantener sus credenciales en reserva y avisar de inmediato de cualquier acceso indebido.",
        ]},
        {"title": "Pagos, vigencia y terminación", "paragraphs": [
            "El servicio se paga según el plan contratado. Si el pago se retrasa, el proveedor puede limitar el "
            "acceso tras avisar al cliente, sin borrar sus datos. Cualquiera de las partes puede terminar la "
            "relación con el aviso previsto en el plan.",
        ]},
        {"title": "Limitación de responsabilidad", "paragraphs": [
            "El proveedor no responde por daños indirectos ni por el uso indebido del sistema por parte del cliente "
            "o de su personal. Su responsabilidad total se limita a lo pagado por el cliente en los últimos doce meses.",
        ]},
        {"title": "Cambios, ley y contacto", "paragraphs": [
            "Si estos términos cambian, se publica una nueva versión y el sistema pide aceptarla de nuevo. Se rigen por "
            f"las leyes de la República del Ecuador. Consultas: {contacto}.",
            f"Versión {TERMS_VERSION}.",
        ]},
    ]


def processor_agreement(c: Clinic) -> list[dict]:
    return [
        {"title": "Partes y objeto", "paragraphs": [
            f"{_cliente(c)} actúa como responsable del tratamiento de los datos personales de sus pacientes y "
            f"personal. {_Proveedor()} actúa como encargado del tratamiento, en los términos de la Ley Orgánica de "
            "Protección de Datos Personales (LOPDP), únicamente para prestar el servicio del sistema.",
        ]},
        {"title": "Datos y finalidad", "paragraphs": [
            "Se tratan datos de identificación, contacto y salud (datos sensibles) de pacientes, y datos de "
            "identificación del personal, con la sola finalidad de alojar, procesar, respaldar y mostrar la "
            "información que el responsable registra en el sistema.",
        ]},
        {"title": "Obligaciones del encargado", "paragraphs": [
            "Tratar los datos solo siguiendo las instrucciones documentadas del responsable, que son el uso del "
            "sistema y sus configuraciones.",
            "Garantizar la confidencialidad de las personas autorizadas a acceder a los datos.",
            "Aplicar medidas de seguridad técnicas y organizativas: cifrado en tránsito, control de acceso por "
            "permisos, registro de accesos a historias clínicas, contraseñas seguras y respaldos.",
            "No subcontratar el tratamiento sin informarlo al responsable; los subencargados (por ejemplo, el "
            "alojamiento en la nube) quedan sujetos a las mismas obligaciones.",
            "Ayudar al responsable a atender las solicitudes de los titulares (acceso, rectificación, eliminación, "
            "oposición, portabilidad y suspensión), para lo cual el sistema permite exportar los datos del paciente.",
            "Notificar al responsable, sin dilación indebida, cualquier vulneración de seguridad que afecte a los "
            "datos, para que este pueda informar a la autoridad y a los titulares en los plazos legales.",
        ]},
        {"title": "Obligaciones del responsable", "paragraphs": [
            "Contar con la base legal para tratar los datos, informar a los titulares con el aviso de privacidad, "
            "registrar sus autorizaciones y atender sus solicitudes en plazo.",
        ]},
        {"title": "Fin del encargo", "paragraphs": [
            "Al terminar el servicio, el encargado devuelve los datos al responsable y los suprime de sus sistemas, "
            "salvo que una ley exija conservarlos, en cuyo caso los mantiene bloqueados.",
            f"Versión {TERMS_VERSION}.",
        ]},
    ]


DOCUMENTS = {"terminos": ("Términos de uso del sistema", terms_of_use),
             "encargo": ("Contrato de encargo de tratamiento de datos", processor_agreement)}
