# Arquitectura y siguiente etapa

El prototipo usa dos fronteras y un único constructor. `python/soundcraft_aaf/reader.py` conoce los objetos AAF y produce `Plan` esquema 1. `src/lib.rs::build_session` conoce SoundCraft y transforma ese plan en un `Session` real de upstream; no sabe de Python, AAF binario, UI o archivos. `src/bin/plan-to-session.rs` es el harness de disco para probar el mismo módulo. `scripts/import-aaf.sh` sólo conecta ambas capas.

Plan v1 usa `Rational(i64,i64)` como segundos [numerador, denominador], denominador positivo y tiempos no negativos. Cada clip lleva `start`, `end` y `offset`: `start/end` son coordenadas absolutas de montaje; `offset` es tiempo desde el inicio de la fuente. Cada fuente tiene clave estable MobID, ruta absoluta resuelta, nombre, frames, channels y sample_rate. El JSON rechaza campos desconocidos en Rust. Los campos `schema_version` y `warnings` evitan tratar un futuro plan como si fuese la versión actual.

Se usa el modelo existente:

| Concepto | Modelo SoundCraft revisado |
|---|---|
| Sesión | `crates/model/src/session.rs`: Session, sample_rate, frame_rate, timecode_start, sources, tracks, next_id |
| Pista | `track.rs`: Track, ChannelFormat, playlists, active_playlist; orden del Vec |
| Corte | `clip.rs`: Clip.start/length, ClipContent::Audio {source, offset}; muestras i64 |
| Fuente | `source.rs`: Source.path/channels/frames/sample_rate; audio decodificado aparte en SourcePool |
| Tiempo | `crates/time`: SampleRate, FrameRate con racionales; MAX_POSITION |
| Flujo existente | `crates/engine/src/cmd/file.rs`, `io.rs`: comandos file.import_audio, session.open, controles de archivos, carga de pool |

No se genera el formato de sesión a mano. Session::to_json serializa usando los tipos de upstream. Cada fuente conserva todos sus frames; mover un borde no exige regenerar el audio.

## Estado por etapas

1. Implementación mínima: hecha y probada automáticamente con AAF sintéticos binarios.
2. Apertura y edición: hecha en la instalación nativa 0.8.0; modelo compilado 0.9.0. Un AAF real de 22 pistas/124 clips también se abrió y pasó la comprobación de medios/offsets, edición de handles y copia/reapertura. La comparación independiente con Pro Tools también pasó para los 124 eventos/offsets/handles, sin diferencias en muestras tras igualar el origen. Falta ejecutar una build completa 0.9.0 y comparar la reproducción audible.
3. Menú de importación: pendiente. No se ha parcheado el motor ni la interfaz de upstream con una dependencia Python no empaquetada. La validación de un subconjunto sintético no resuelve el contrato pure-Rust, el acceso seguro a archivos ni los formatos de exportación reales.
4. Documentación, fixture y cambios revisables: preparados en este repo. El borrador es para revisar la base, no afirma que AAF esté resuelto en SoundCraft.

## Continuación concreta, sin reescribir el constructor

1. Ampliar la prueba real actual (22 pistas mono y 124 clips, ya comparada con Pro Tools) con entregas estéreo y otros exportadores. Guardar la exportación original aparte; registrar formato de editor, tasas, slot graph, nombres, locators y elementos rechazados. Añadir un fixture sintético mínimo por cada incompatibilidad encontrada.
2. Revisar `craftrules` cuando esté accesible. Confirmar la política pure-Rust al revisar la futura propuesta, sin contactar ahora. Opción A: lector Rust CFB/AAF que emita Plan. Opción B: lector Python opcional en proceso aislado, timeout, límite de salida, runtime empaquetado y ejecución sin shell. Ese lector no tocaría el realtime thread.
3. Reubicar `src/lib.rs` como `crates/interchange` en SoundCraft (L3: depende del modelo L2, no del engine/UI), convertir dependencias a workspace, registrar en Cargo.toml y en el verificador de capas. Conservar los tests actuales. La CLI del helper pasa a depender de ese crate.
4. Añadir `file.import_aaf` con nuevo módulo de comandos y una línea en cmd/mod.rs. Leer archivos a través de `Engine`/file_access; validar la carpeta de medios antes de leer locators, impedir accesos remotos inesperados y pasar bytes/metadatos verificados al constructor. No ejecutar procesos desde la librería del modelo.
5. Construir todo fuera del audio callback y sin mutar el documento activo. Resolver política de sesión nueva frente a insertar tracks: esta etapa crea sesión nueva con su propio sample rate/timecode. Comprobar missing, canales y rate antes de sustituir el documento, y devolver reporte en respuesta del comando, CLI y UI.
6. Interfaz fina: selector .aaf, composición, relink explícito y reporte de compatibilidad. Sólo las invocaciones de menú abren diálogos. El comando debe ser usable desde CLI/control/MCP y disponer de prueba de fallo sin mutación y undo cuando proceda.
7. `cargo xtask ci` completo, prueba nativa con build actual, atribución de fixtures y actualización de docs de progreso antes de crear un PR upstream. Mantener G-03 abierto/reducir alcance, sin declararlo resuelto por este subconjunto.

La CLI copia fuentes completas a una carpeta nueva. No usa las políticas file_access del engine, y no debe enchufarse tal cual al comando de la aplicación. El núcleo puro sí es reutilizable. El submódulo upstream permanece sin cambios para que la separación sea revisable.
