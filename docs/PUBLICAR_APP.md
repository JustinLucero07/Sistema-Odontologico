# Publicar la app móvil

La app es la misma para todas las clínicas. Cada clínica la configura una sola vez escribiendo su dominio en el login (**«Configurar servidor de la clínica»**).

## 1. Crear la clave de firma (una sola vez)

```bash
keytool -genkey -v -keystore ~/odonto-publicacion.jks -keyalg RSA \
  -keysize 2048 -validity 10000 -alias odonto
```

Guarde el archivo `.jks` y sus contraseñas en un lugar seguro. **Si se pierden, no se puede volver a actualizar la app en Google Play.**

Cree `mobile/android/key.properties`. Este archivo no se sube al repositorio:

```properties
storeFile=/home/USUARIO/odonto-publicacion.jks
storePassword=CLAVE_DEL_ALMACEN
keyAlias=odonto
keyPassword=CLAVE_DE_LA_LLAVE
```

Sin este archivo, el release se firma con la clave de depuración. Sirve para probar, pero Google Play lo rechaza.

## 2. Compilar

```bash
cd mobile
flutter build appbundle --release            # para Google Play (.aab)
flutter build apk --release --split-per-abi  # APK para instalar directo (más livianos)
```

Para entregar a una clínica una app ya apuntada a su servidor, sin que tenga que configurarlo:

```bash
flutter build apk --release --dart-define=API_BASE=https://sonrisa.sudominio.com
```

## 3. Google Play

1. Cree una cuenta de desarrollador en Google Play Console (pago único).
2. Cree la app y suba el `.aab` de `build/app/outputs/bundle/release/`.
3. La ficha necesita: ícono 512×512 (`android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png` es el mismo logo), capturas, descripción y una **URL de política de privacidad** (publique el texto de *Privacidad y legal*).
4. En «Seguridad de los datos», declare que la app maneja datos de salud y personales, cifrados en tránsito (HTTPS), y que el responsable es cada clínica.

## 4. Versiones

Antes de cada publicación, suba la versión en `mobile/pubspec.yaml` (`version: 1.0.1+2`). El número después de `+` debe aumentar siempre.
