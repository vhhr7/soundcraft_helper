# Importación gráfica AAF: versión de desarrollo para Mac

Esta etapa integra el módulo `soundcraft-interchange` ya probado en el motor y la interfaz nativa de SoundCraft 0.9.0. La aplicación separada **SoundCraft AAF Preview** conserva intacta `/Applications/SoundCraft.app` y usa su propio perfil en `local-build/profile`. No se ha publicado ningún PR ni instalador.

## Probar la compilación preparada

Desde `helper-aaf`, abrir con Finder `local-build/SoundCraft AAF Preview.app` o ejecutar:

```sh
"$PWD/local-build/SoundCraft AAF Preview.app/Contents/MacOS/SoundCraftAAF"
```

1. Crear una sesión vacía y detener el transporte.
2. **File → Import → Session Data...**. Elegir `Pinguino.aaf` con **Browse…**.
3. Si los WAV no están junto al AAF, usar **Choose media folder…**. Pulsar **Analyze AAF**.
4. Revisar nombre, inicio, frecuencia, frame rate, pistas y avisos. Seleccionar las pistas que se quieren añadir. Todas se crean como **New Track**; no se reemplazan playlists existentes.
5. Mantener **Maintain absolute timecode**, offset `0` para reproducir el montaje original. Una sesión vacía adopta el reloj del AAF; en una existente se compensa la diferencia entre orígenes. **Relative to session start** ignora esa diferencia. El offset se expresa en muestras del destino.
6. **Import** añade pistas y clips como una sola operación que puede deshacerse. El informe permite **Go to first imported clip** y copiar el reporte completo.
7. **Save Session** en una carpeta nueva recoge los archivos fuente completos en `Audio Files`. Guardar antes de mover los originales. No se consolidan pistas ni se recortan handles.

SoundCraft guarda el audio recogido como WAV float32; conserva las muestras decodificadas y los archivos completos, pero no promete identidad binaria ni todos los metadatos BWF del WAV original. El CLI existente sí copia los bytes originales. La opción de enlazado externo persistente queda pendiente porque Save Session recoge actualmente los medios del pool.

## Compilar desde cero

Requisitos: macOS, herramientas de línea de comandos de Xcode, Git, Python 3.10+, rustup y varios GB libres. La herramienta CLI conserva Rust 1.90; la interfaz upstream requiere Rust 1.95.

```sh
cd /ruta/a/soundcraft_helper/helper-aaf
# Si el clon todavía no tiene el submódulo:
git submodule update --init --recursive
rustup toolchain install 1.95.0 --profile minimal --component rustfmt,clippy
./scripts/build-dev-app.sh
```

El script aplica un parche revisable sobre el commit upstream fijado; verifica la revisión y conflictos antes de escribir. No resetea archivos, no instala en Applications y no publica cambios. `integration/soundcraft-aaf.patch` incluye la ventana, los comandos y sus pruebas. `scripts/aaf_bridge.py` lee AAF mediante pyaaf2 1.7.1 fijado por hash; el ejecutable llama al Python del venv con aislamiento `-I`, sin shell. Las rutas de intérprete y lector son configuración del lanzador, no datos tomados del AAF.

```sh
./scripts/check.sh
cd upstream
cargo +1.95.0 test --locked -p soundcraft-engine --test aaf_import
cargo +1.95.0 test --locked -p soundcraft-ui-egui --lib aaf_import
cargo +1.95.0 clippy --locked -p soundcraft-engine -p soundcraft-ui-egui -p soundcraft --all-targets -- -D warnings
```

## Alcance y límites

AAF con medios WAV PCM externos mono o estéreo intercalado; selección de pistas, cortes editables, offsets y handles completos, tiempos racionales y timecode. Importación sólo con transporte detenido. No hay resampling: se rechaza una frecuencia distinta en una sesión no vacía. Límite de 512 MiB por archivo y aproximadamente 512 MiB de muestras float decodificadas por importación; análisis limitado a 45 segundos. La lectura del AAF ocurre en segundo plano; la decodificación/inserción final puede bloquear brevemente la interfaz.

No implementados: OMF, medios embebidos, vídeo, estéreo dividido, ganancia de clip, fundidos paramétricos, automatizaciones, plugins, ruteos, sustitución/merge de playlists y todas las variantes de AAF de otros exportadores. Las estructuras editoriales fuera del subconjunto producen error; las omisiones de metadatos se reportan. Un archivo llamado Fade puede ser audio ya renderizado: no demuestra soporte de transiciones.

La ventana sigue el flujo observado en Pro Tools con controles propios de SoundCraft; no se copian sus recursos gráficos. No se ofrecen controles de funciones que aún no estén implementadas.

## Arquitectura y futura contribución

`AAF → lector pyaaf2 → Plan racional → soundcraft-interchange → comando de motor → sesión y pool → UI`.

La UI no genera JSON de sesión ni mantiene otro conversor. `file.preview_aaf` analiza sin modificar el documento; `file.import_aaf` comprueba selección, tiempos, rutas y medios antes de insertar y permite undo. Los comandos respetan los límites de acceso a archivos del motor.

El parche de desarrollo depende de `soundcraft-interchange` mediante ruta al helper. Para proponerlo upstream hay que trasladar **el mismo** crate a `crates/interchange`, cambiar la dependencia a una ruta del workspace y acordar la distribución del lector opcional. La política upstream favorece Rust puro: no se presupone que aceptarán un runtime Python. Mantener el contrato Plan permite cambiar sólo la lectura del formato. Las reglas compartidas craftrules no estuvieron disponibles; revisar antes de una contribución. No se debe actualizar el gitlink a un commit local no publicado: el pin más este parche reproducen el trabajo.

## Validación de esta etapa

El AAF real Pinguino importado mediante la ventana produjo 22 pistas, 124 clips y 124 fuentes cargadas, con 48 kHz, 23.976 fps e inicio 00:57:00:00. Posiciones, duraciones, offsets y tamaños de fuente coinciden exactamente con la sesión previamente contrastada con Pro Tools: diferencia 0 muestras en los 124 eventos. Se verificaron guardar una copia, origen temporal, undo/redo único e invocación del menú. Evidencia privada en `local-tests/native-import`, excluida de Git.

Las pruebas automáticas nuevas cubren mapeo absoluto/relativo, selección, transporte, errores sin mutación, límites de acceso, medios faltantes, rutas Unicode y con espacios, guardado de fuentes completas y ventana de menú. Ver `validation.md` para las pruebas previas del lector, mono/estéreo y comparación independiente.

Esto valida el importador en este montaje; no certifica estabilidad de SoundCraft para una clase completa. Antes de clase: repetir apertura/guardado y reproducción con la interfaz de audio del aula, comprobar salida activa y hacer una sesión de ensayo de duración real. Conservar Pro Tools como referencia para detectar diferencias de ganancia, automatización y mezclas.

Comprobaciones de esta revisión: 5 pruebas del core, 11 del lector, 6 del comando de motor y 1 de UI; fmt y clippy de helper y engine/ui/app pasaron. El build nativo pasó. No se ejecutó el gate upstream completo ni WASM.

La compilación final también guardó y reabrió `local-tests/native-import/Pinguino final/session.scraft`: las 124 fuentes quedaron cargadas, con longitud completa y sin cambios de coordenadas. Se dejó esa sesión abierta en la app de desarrollo, con salida Bocinas de MacBook Pro y transporte situado en el primer evento (8648640 muestras).
