/**
 * Enlace a una conversación de WhatsApp con el mensaje ya escrito. No envía
 * nada: abre WhatsApp y la persona decide si lo manda.
 *
 * Los números locales de Ecuador (09…) se pasan a formato internacional
 * (5939…), que es el que exige wa.me.
 */
export function whatsappUrl(numero: string | null | undefined, texto = ''): string | null {
  if (!numero) return null;
  let digits = numero.replace(/[^\d]/g, '');
  if (digits.length === 10 && digits.startsWith('0')) digits = `593${digits.slice(1)}`;
  if (digits.length < 8) return null;
  return `https://wa.me/${digits}${texto ? `?text=${encodeURIComponent(texto)}` : ''}`;
}
