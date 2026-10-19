# Validación — 19 de octubre de 2026

## Resultado y alcance

Etapa funcional de importación AAF externa comprobada. Cinco pruebas Rust y once pruebas Python pasan. La CLI produce una sesión editable y portable con fuentes completas. SoundCraft abrió esa sesión, cargó los dos medios, extendió un clip hacia ambos handles y guardó/reabrió una copia.

Esto **no certifica SoundCraft para uso continuo en clase**. No se ha probado reproducción audible, interfaz del aula, latencia, grabación, plugins, sesiones largas, recuperación de fallos ni compatibilidad general con todos los exportadores de Resolve/Premiere/Pro Tools. Para la primera clase, usar la demo ensayada y una alternativa disponible; el importador y la estabilidad del DAW son dos validaciones diferentes.

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
| unittest Python | 11 pasan: AAF binario sintético, relink explícito, tasas de edición de fuente distintas de sample rate, rutas especiales, composición ambigua, rate fraccional, operación de ganancia rechazada, embebido rechazado, origen no cero, locator remoto, medios faltantes y E2E |
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


## Ampliación con entrega real externa

Se importó una entrega real con 22 slots de audio, 124 SourceClip y 124 WAV mono PCM 24-bit a 48 kHz. La composición y los slots de fuente usan 24000/1001 fps. Los locators originales apuntaban a una carpeta antigua: se resolvieron mediante `--media-dir`, dejando el AAF y los WAV originales intactos. Los nombres de los slots de pista estaban vacíos: se asignaron Audio 1–22 con advertencias.

Se compararon en la API de SoundCraft los 124 inicios, duraciones y offsets con la sesión generada, y se confirmó `loaded=true` para todos los medios. Las 124 copias de fuentes de la CLI son byte-idénticas a los originales. Se extendió por ambos bordes un clip aislado, se restauró su ventana, se guardó una copia nativa y se reabrió sin perder los valores ni el timecode. Un intento de extender otro clip encontró el límite de su vecino contiguo; no se contó como fallo de handles.

La entrega y sus resultados se mantienen sólo en `local-tests/` (ignorado por Git), sin agregar audio del usuario al repositorio. La captura fue revisada y el montaje quedó abierto para inspección. La coincidencia contra el plan no demuestra por sí sola equivalencia con el editor de origen. Después se realizó la comparación independiente con Pro Tools descrita abajo; sigue pendiente la escucha.


## Comparación independiente con Pro Tools abierto

Se revisaron las dos sesiones abiertas sin cambiar ni guardar el montaje. Mediante PTSL se obtuvo el informe público de sesión en muestras y la lista real de clips (JSON original del servidor), y se compararon con `session.inspect` vivo de SoundCraft:

- 22 pistas mono en ambos, 124 eventos colocados en ambos y mismo número de cortes por pista.
- 124/124 inicios, finales y duraciones coinciden exactamente: **0 muestras de diferencia** después de expresar las posiciones sobre el mismo origen.
- 124/124 offsets, finales de ventana de fuente, tamaños de fuente y handles antes/después coinciden exactamente.
- 124/124 asociaciones evento → WAV coinciden; las copias importadas son byte-idénticas a los archivos utilizados por Pro Tools. No hay medios offline ni cambio de mute de clips.
- Pro Tools muestra 248 entradas en su lista: 124 fuentes completas y 124 recortes; no son 248 eventos colocados.
- La sesión Pro Tools comienza en 00:00; SoundCraft conserva 00:57:00:00 NDF del AAF (164324160 muestras). Sumar ese origen a sus posiciones locales hace coincidir todos los eventos. No es un desfase del montaje.
- Nombres de pistas: A1–A22 en Pro Tools frente a Audio 1–Audio 22 en nuestro fallback de slots sin nombre. Pro Tools añade sufijos únicos a los nombres de clips. No se cambió la nomenclatura del usuario.
- Se observaron ambas ventanas reales. La instancia de SoundCraft visible estaba sin motor de audio (`--no-audio`); no se inició escucha ni grabación. No se valida equivalencia de mezcla, panoramas, automatización o ruteos.

PTSL GetPlaylistElements requiere una API privada que no estaba habilitada; no se habilitó. La EDL pública y GetClipList fueron suficientes para la comparación de montaje y offsets. Las bindings Python omiten un campo nuevo del servidor (`clip_list`), por lo que se conservó y validó la respuesta JSON original. Los archivos de evidencia e informe detallado quedan en `local-tests/protools-comparison/`, ignorado por Git para no incorporar material del usuario. Esto valida la importación básica de esta entrega, no todos los AAF ni la estabilidad continua del DAW.

## Integración gráfica de desarrollo — 19/10/2026

Se compiló SoundCraft 0.9.0 con el overlay nativo del helper. Se abrió un bundle separado y se pulsaron Analyze AAF e Import sobre Pinguino. La API de esa instancia confirmó 22 pistas, 124 clips y 124 fuentes cargadas. Todos los inicios, duraciones, offsets y tamaños de fuente son idénticos al resultado contrastado con Pro Tools. Guardar copia conservó el origen 164324160 muestras; undo quitó toda la importación y redo recuperó las 22 pistas. Se comprobó el mapeo del menú File → Import → Session Data.

Comprobaciones automáticas pasadas: 5 pruebas del constructor Rust, 11 del lector Python, 6 del nuevo comando de motor y 1 de la ventana/menú; fmt y clippy con warnings como errores para helper y para engine/ui/app (todos sus targets). El parche se verifica contra un índice temporal del commit upstream fijado y el script detecta cuando ya está aplicado. Inspección visual de la ventana real, con corrección del alto del panel y retirada de la opción de enlazado persistente.

No se ha ejecutado `cargo xtask ci` completo ni se han validado WASM, otras plataformas, todos los exportadores o una clase de duración completa. La evidencia con audio cargado no certifica la salida acústica del aula. La aplicación instalada y la sesión abierta por el usuario permanecen separadas de estas pruebas. Ver `graphical-import.md` para compilar, usar y continuar.

Repetición con el bundle final: All/Clear actualizan la selección y deshabilitan Import cuando está vacía; Go to first imported clip sitúa el transporte en 8648640 muestras. Save As y reapertura cargaron las 124 fuentes, manteniendo las longitudes completas y las coordenadas de todos los clips. Evidencia: `local-tests/native-import/final-roundtrip.json` y captura `final-montage.png`.
