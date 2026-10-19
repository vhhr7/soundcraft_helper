# Compatibilidad e investigación — 19 de octubre de 2026

## Repositorios e instrucciones

`vhhr7/soundcraft_helper` estaba vacío al clonarlo; este checkout separado conserva su remoto y trabaja en `feat/aaf-import`. El upstream conserva su commit fijado; la etapa gráfica añade un overlay de desarrollo reproducible en `integration/soundcraft-aaf.patch`. Se leyeron el AGENTS.md del directorio de desarrollo, [AGENTS.md de SoundCraft](../upstream/AGENTS.md), ROADMAP.md, docs/gaps.md, docs/file-format-parity.md y el código del modelo/importación. No se encontraron CONTRIBUTING.md ni AGENTS.md adicionales dentro de upstream. Los archivos locales ignorados `plan/STATUS.md` y `plan/execution-plan.md` no están en el clon.

El AGENTS.md de upstream remite a `storytold/craftrules`: el clon devolvió `repository not found`; esas reglas adicionales no pudieron leerse. Antes de una contribución upstream se deben recuperar/revisar y correr sus gates. Se respetaron las reglas disponibles: assets originales, no leer recursos de Pro Tools, no código GPL/LGPL, sin `unsafe` ni panics intencionados en producción. No se estudió código de Ardour ni de otros lectores copyleft.

SoundCraft declara AAF y OMF pendientes en [su inventario](https://github.com/storytold/soundcraft/blob/25d52c646aea780c8076ff966076f994ad256221/docs/file-format-parity.md). GitHub se consultó con el plugin seleccionado: búsqueda AAF/OMF en issues; PR abiertos con AAF/OMF/interchange y búsquedas por título AAF y OMF. No se encontró un PR abierto equivalente en los resultados. Esto es una revisión de búsquedas, no una garantía sobre todas las ramas externas. Referencias:

- [#40, Unable to import AAF session](https://github.com/storytold/soundcraft/issues/40): entrega de DaVinci Resolve para Pro Tools; no devolvió comentarios al consultarlo.
- [#650, fiabilidad y compatibilidad](https://github.com/storytold/soundcraft/issues/650): incluye problemas de reapertura y solicitudes de intercambio. Es un reporte, no una reproducción nuestra.
- [#725, OpenTimelineIO](https://github.com/storytold/soundcraft/issues/725): propuesta de otro mecanismo de intercambio.
- [#173, respaldos y medios separados](https://github.com/storytold/soundcraft/issues/173): contexto de portabilidad.

## Bibliotecas evaluadas

| Opción | Compatibilidad / licencia | Mantenimiento observado y uso desde Rust | Decisión |
|---|---|---|---|
| [pyaaf2 1.7.1](https://pypi.org/project/pyaaf2/1.7.1/) | AAF CFB, MIT, Python puro sin AAF SDK | Release fijada del 17-09-2023; releases espaciadas, no asumir mantenimiento rápido. El lector y escritor funcionaron con nuestros AAF. Integración por proceso/JSON, sin FFI | Elegida para leer; riesgo de runtime y distribución reconocido |
| [oximedia-aaf 0.2.1](https://docs.rs/crate/oximedia-aaf/0.2.1/source/src/object_model.rs) | Apache-2.0, Rust nativo | Release 12-08-2026. Se descargó el paquete publicado: `read_content_storage` devuelve `ContentStorage::new()` sin leer mobs; `read_header` también usa un valor por defecto. No basta la lista de capacidades de su README | No sirve como lector de montaje en esta revisión; no se compiló ni se afirma rendimiento |
| [LibAAF](https://github.com/agfline/LibAAF) | Orientado a audio y variantes de DAWs; [GPLv2](https://github.com/agfline/LibAAF/blob/master/LICENSE) | Proyecto especializado, C; integración requeriría FFI/unsafe o proceso. No se evaluó su código ni se midió su actividad reciente | Excluida por las reglas expresas de upstream; sin usar su implementación |
| [Omfoo](https://github.com/OmfooGuy/Omfoo) | OMF, Windows COM; [licencia propia](https://github.com/OmfooGuy/Omfoo/blob/main/LICENSE.md) con atribución, cambios de IID y restricciones de nombre | Repositorio pequeño, sin release mostrada en la consulta; mantenimiento no establecido. DLL/COM no portable al Mac; Rust requeriría bindings y trabajo de plataforma | Posponer OMF; no es un lector Rust/macOS listo para integrar |
| [AAF SDK](https://aaf.sourceforge.net/docs/aafguide.pdf) | Modelo estándar, C++ | Integración más pesada (SDK, compilación, bindings); licencia exacta de una distribución concreta y mantenimiento no verificados en esta etapa | No seleccionado ni redistribuido |

Las crates llamadas `omf`/`omf-rust` que encontramos describen Open Mining Format, no Open Media Framework Interchange. No son alternativas para montaje audiovisual.

La elección AAF permite probar archivos binarios y fuentes reales con una dependencia permisiva pequeña. El proceso Python es una consecuencia práctica del lector elegido, no una afirmación de que sea imposible escribir uno en Rust. Upstream se define como pure-Rust: empaquetar este lector no está aprobado por sus mantenedores. El módulo de construcción permanece en Rust y se puede integrar sin reescribirlo si cambia el lector.

## Matriz del prototipo

| Elemento | Comportamiento actual |
|---|---|
| Pistas y orden | Slots de sonido en el orden de composición; nombres preservados, incluidos duplicados. SlotName vacío: Audio + PhysicalTrackNumber/SlotID con advertencia |
| Clips | SourceClip directos y Sequence plana con SourceClip/Filler; tiempos y offsets racionales; nombres de Mob referenciado (no metadatos de nombres específicos de cada editor) |
| Fuentes / handles | WAV PCM local externo con WAVEDescriptor (no PCMDescriptor), completo, copiado sin reconsolidar; clip = ventana sobre SourceId. Handles limitados al archivo efectivamente entregado |
| Mono / estéreo | WAV mono e interleaved estéreo; no pairing de archivos L/R ni selección PhysicalTrackNumber |
| Frecuencia de muestreo | Una frecuencia real común; discrepancia de sample rate entre archivo y descriptor o mezcla de frecuencias produce error. El edit rate del slot fuente puede ser distinto del sample rate; sus offsets se convierten desde su propia tasa. No hay resampling |
| Tiempos | Segundos racionales con i128 en Rust; cada inicio/final redondeado al más cercano, empates positivos hacia arriba. Duración = final redondeado − inicio redondeado |
| Cadena de fuentes | SourceClip → MasterMob(s) de un solo SourceClip → SourceMob WAV; suma offsets y detecta ciclos. Secuencias dentro de un MasterMob se rechazan |
| Inicio / frame rate | Un slot Timecode directo de composición con Origin=0; tasas de FrameRate del modelo, incluido drop válido. Sin Timecode: 0 y 30 fps con advertencia. Orígenes no cero se rechazan |
| Archivos faltantes | Error que identifica el archivo y locator; no genera sesión parcial deliberadamente. `--media-dir` permite relink explícito por nombre exacto con registro en advertencias |
| Rutas | file URI local o ruta relativa al AAF, percent-decoding; espacios, ñ, á y # escapado probados. HTTP/SMB y hosts remotos rechazados; locators múltiples se consideran ambiguos |
| Ganancia/fades/transiciones | No implementados. OperationGroup (incluida ganancia) y Transition abortan; no aplana el efecto ni sustituye por audio procesado |
| Medios embebidos | Detectados en fuente referenciada y rechazados; no extracción todavía |
| Composiciones múltiples | Exige escoger una por MobID; no elige arbitrariamente |
| Vídeo, MIDI, otros slots | No se transfieren; reporte por cada slot omitido |
| Plugins, ruteos, automatización, metadatos de DAW | No se transfieren ni se promete equivalencia; advertencia general persistida. No es una copia completa de toda la semántica AAF |
| Otros | OMF, MXF, AIFF, WAV float/extensible en el lector Python, fades por metadatos propietarios, nested scopes, selectors, essence groups, timewarp, solapamientos y clips fuera de fuente: no soportados |

El lector debe seguir ampliando su inventario de metadatos propietarios: no se ha certificado que detecte todas las formas posibles de ganancia/fades de todos los fabricantes. Las estructuras editoriales desconocidas del árbol soportado abortan; los metadatos que no se leen quedan expresamente fuera de la compatibilidad declarada.

Límites conservadores: AAF ≤512 MiB; plan JSON ≤32 MiB; cada WAV ≤512 MiB en la CLI; ≤100000 elementos principales; profundidad de referencias ≤32; tiempos dentro de MAX_POSITION de SoundCraft. No es todavía un parser sometido a fuzzing ni un entorno aislado para archivos hostiles. Los WAV deben ser de confianza. La ventana exige una carpeta de medios explícita y el lector comprueba su contención, incluidos symlinks; el motor aplica además sus límites de acceso a archivos.


La [etapa gráfica](graphical-import.md) reutiliza este lector y el constructor Rust. Recoge las fuentes completas al guardar como WAV float32: no mantiene identidad binaria/BWF original. La CLI conserva copia byte a byte. Enlazado persistente externo no se ofrece en la ventana.
