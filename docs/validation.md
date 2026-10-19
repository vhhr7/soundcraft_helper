# Validación — 19 de octubre de 2026

## Resultado y alcance

Etapa funcional de importación AAF externa comprobada. Cinco pruebas Rust y nueve pruebas Python pasan. La CLI produce una sesión editable y portable con fuentes completas. SoundCraft abrió esa sesión, cargó los dos medios, extendió un clip hacia ambos handles y guardó/reabrió una copia.

Esto **no certifica SoundCraft para uso continuo en clase**. No se ha probado reproducción audible, interfaz del aula, latencia, grabación, plugins, sesiones largas, recuperación de fallos ni un archivo real de Resolve/Premiere/Pro Tools. Para la primera clase, usar la demo ensayada y una alternativa disponible; el importador y la estabilidad del DAW son dos validaciones diferentes.

## Entorno y trazabilidad

- Mac Apple silicon, Python 3.10.12, pyaaf2 1.7.1.
- Rust 1.90.0 y Cargo.lock, con modelo SoundCraft 0.9.0 del commit `25d52c646aea780c8076ff966076f994ad256221`.
- La aplicación encontrada al inicio informó 0.7.0; durante la validación la instalación informó 0.8.0 en CLI, Info.plist y About. No se instaló ni actualizó SoundCraft desde este trabajo; no se asume que el binario inicial y el final fueran el mismo.
- Binario confirmado al registrar la evidencia: `/Applications/SoundCraft.app/Contents/MacOS/SoundCraft`, SHA256 `956f959adfc51be2da4506215c3630925db5273213599bacd938d176565992b7`. No se conoce el commit exacto de ese binario.
- Instancia de prueba separada, `--no-audio --control 49381`. Se utilizó la API local documentada; no se armó ninguna pista ni se inició grabación.

La primera apertura mediante entrada AX no aplicó el cambio del campo de ruta: la interfaz siguió vacía con el diagnóstico del directorio inicial. No se contó como fallo del importador. Se lanzó una instancia dedicada con el archivo como argumento y se verificó por inspección, edición y reapertura.

## Resultados automáticos

| Comprobación | Resultado |
|---|---|
| cargo build/test --locked | Pasa; 5 tests de biblioteca, sin tests omitidos |
| cargo fmt --check | Pasa |
| cargo clippy --locked --all-targets -- -D warnings | Pasa |
| unittest Python | 9 pasan: AAF real binario sintético, rutas especiales, composición ambigua, rate fraccional, operación de ganancia rechazada, embebido rechazado, origen no cero, locator remoto, medios faltantes y E2E |
| Posición/duración/offset | Valores exactos en muestras, tabla inferior |
| Handles / medios | Copias CLI SHA256 idénticas a originales; 384000 frames por fuente, mono/estéreo |
| Deriva temporal | 1000 cortes a 24000/1001 fps sobre 44.1 kHz: cada final coincide con inicio siguiente; final total 1839338 muestras. Sin acumular duración redondeada de cada frame |
| Protección de originales | Lector AAF en modo r; salida sólo en carpeta nueva, rechazo de sobrescritura; WAV original no se modifica |
| Errores de fuentes | Falta de archivo y discrepancia del header/metadatos abortan antes de crear la salida |
| Recarga del modelo | Session::to_json → from_json preserva ventana y offset |
| Suite completa upstream / GUI 0.9 | No ejecutada/compilada. Upstream no tiene cambios |

El AAF fue generado por pyaaf2 y leído por pyaaf2: esto prueba el contrato del prototipo, no compatibilidad independiente con los exportadores de los editores. Los valores esperados se especifican manualmente en tests, no se derivan del resultado de importación.

## Valores conocidos del fixture (48 kHz)

Fuentes de 8 segundos. El MasterMob agrega 0.5 s al offset del SourceClip: se comprueba toda la cadena.

| Pista / clip | Inicio | Duración | Offset fuente | Handle antes | Handle después |
|---|---:|---:|---:|---:|---:|
| 01 Diálogo / primero | 48000 | 96000 | 48000 | 48000 | 240000 |
| 01 Diálogo / segundo | 192000 | 48000 | 168000 | 168000 | 168000 |
| 02 Ambiente estéreo | 0 | 240000 | 72000 | 72000 | 72000 |

Timecode de muestra 0: 172800000 muestras = 01:00:00:00 a 25 fps. La biblioteca y el JSON de la copia guardada por SoundCraft conservan este valor. La inspección por API confirmó 48 kHz y 25 fps; la presentación del contador como timecode no se comprobó visualmente.

## Comprobado dentro de la aplicación

`docs/app-validation/transcript.json` guarda solicitudes/respuestas de la API nativa. `scripts/validate_app.py` reproduce las aserciones con una instancia dedicada y un directorio de evidencia nuevo:

```sh
/Applications/SoundCraft.app/Contents/MacOS/SoundCraft \
  --no-audio --control 49381 "$PWD/demo/Sesión SoundCraft/session.scraft"
# En otra terminal, dentro del repo:
.venv/bin/python scripts/validate_app.py --port 49381 --output /tmp/validacion-aaf-nueva
```

- `session.inspect`: 2 pistas en orden, mono/estéreo, 3 clips con los valores de la tabla, dos fuentes `loaded=true` y 384000 frames cada una.
- `edit.trim_clip` del primer diálogo a [24000,168000): inicio 24000, duración 144000, offset 24000. Se recupera medio segundo de fuente por cada borde. Se restauraron después los cortes iniciales.
- `session.save_copy`, seguido de `session.open`: sin medios faltantes; posiciones, duraciones y offsets siguen exactos y ambos medios siguen cargados.
- El propio Save Copy de SoundCraft reescribe audio a la profundidad de la sesión; no se exige identidad binaria de esas copias del DAW. La CLI sí preserva bytes de los WAV que copia.
- [Captura revisada del montaje reabierto](app-validation/verified-montage.png): dos pistas, dos cortes y huecos en diálogo, ambiente estéreo continuo con sus dos canales. La captura anterior `montage.png` contiene About superpuesto; no se usó sola para validar visualmente el montaje.

La extensión se verificó mediante el comando real del motor de la aplicación, no arrastrando bordes manualmente con el ratón. No se afirma aceptación de interacción manual o reproducción por escuchas.

## Comparación pendiente con Pro Tools y ensayo de clase

1. Conservar AAF y carpeta de medios originales, trabajar siempre con copias. Registrar editor/versión y ajustes de exportación; empezar con WAV externos y sin efectos.
2. Abrir la misma entrega en Pro Tools y en el prototipo; comprobar sample rate, inicio, frame rate/drop y orden/nombres/canales.
3. Elegir al menos tres cortes y un punto de sincronía tardío. Anotar posición, duración y offset en muestras en Pro Tools. Comparar con plan JSON, `.scraft` y `session.inspect`. La tolerancia es como máximo una muestra por redondeo de frontera desde una tasa que no cae en muestras enteras, no una deriva acumulada.
4. Extender por ambos lados hasta los límites de fuente disponibles. Escuchar y comparar impulsos/transitorios y contenido; distinguir handles entregados de audio que el editor no exportó.
5. Probar un medio faltante y un locator que requiera relink; debe fallar claramente y conservar originales. Añadir regression fixture antes de ampliar el lector.
6. Ensayar 30–60 minutos con la misma interfaz del aula, reproducir/editar/guardar/reabrir varias veces y revisar logs. Anotar versión/binario y cualquier fallo del DAW por separado de los errores del importador. Sólo después decidir si usarlo como herramienta principal en clase.
