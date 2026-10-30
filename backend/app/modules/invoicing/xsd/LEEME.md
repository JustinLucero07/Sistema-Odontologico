Esquemas XSD del SRI (comprobantes electrónicos, esquema offline) con los que
las pruebas validan el XML que genera el sistema:

- factura_V1.1.0.xsd y notaCredito_V1.1.0.xsd: tomados del paquete NuGet
  Acontplus.Billing (vienen incrustados como recursos); son los mismos que el
  SRI publica junto a su ficha técnica. Si el SRI publica una ficha nueva,
  reemplácelos por los oficiales de sri.gob.ec.
- xmldsig-core-schema.xsd: del W3C (lo importan los dos anteriores).
