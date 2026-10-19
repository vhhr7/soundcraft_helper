# Dos procesos en paralelo: RC propio y contribución a SoundCraft

Estado: 2026-10-19. No se ha publicado un PR, creado un release remoto ni contactado a mantenedores.

## 1. Nuestra distribución Mac

Nombre de trabajo: **SoundCraft AAF Preview**. La versión preparada es `0.9.0-aaf.1-dev.1`; **todavía no es un RC universal validado**.

Hecho:

- Bundle ARM64 con lanzador nativo Rust y perfil separado.
- Python portable 3.13.16 de Astral, release 20261013, y pyaaf2 1.7.1 fijados por SHA-256. Recursos relativos al bundle; no requiere venv, Homebrew ni una ruta a este repo.
- Lectura AAF con entorno PATH mínimo y variables externas de Python inválidas, en ruta con espacios y Unicode.
- Importación gráfica real del fixture de dos pistas mono/estéreo y tres cortes. Pruebas de coordenadas, extensión de ambos bordes, medios cargados y guardar/reabrir pasadas.
- Runtime Intel descargado y su lector probado bajo Rosetta. Lanzador Intel compilado. **Rosetta no sustituye una prueba física en Intel**.
- Preparado `scripts/build-universal-preview.sh`: dos targets Rust, dos runtimes incluidos, ejecutables universales, firma ad hoc local, DMG y SHA-256. La compilación universal completa aún no se ha ejecutado.

Ayuda de Víctor:

1. Liberar espacio hasta contar con al menos 15–20 GB libres antes de la compilación completa. El script exige al menos 12 GiB en el volumen de compilación; no borra archivos del usuario.
2. Registrar macOS instalado en el MacBook Pro 2012 (**confirmado: 10.8, incompatible**). El bundle, el binario ARM64 y el runtime ARM64 actuales declaran mínimo 11.0 (verificado también con vtool). Según [Apple](https://support.apple.com/en-us/108052), el soporte oficial de ese modelo llega a Catalina; no se debe prometer que el build actual correrá en él ni cambiar su OS como parte de esta tarea. Si tiene 10.15 o anterior, necesitaremos otro Intel compatible o un trabajo de compatibilidad separado.
3. No hay cuenta Apple Developer por ahora. Se preparará una distribución de prueba sin Developer ID/notarización. No afirmar que pasará Gatekeeper como un instalador notarizado. Firma ad hoc no es firma Developer ID.

Reproducción del paquete ARM64 de desarrollo:

```sh
# Python 3.12+ para extracción segura; Rust 1.95 y las herramientas de Xcode.
python3 scripts/prepare-python-runtime.py arm64
.venv/bin/python -m pip download --require-hashes --only-binary=:all: --no-deps --dest local-build/downloads -r requirements.txt
mkdir -p local-build/launchers
rustc +1.95.0 --edition 2024 -O packaging/preview-launcher.rs -o local-build/launchers/arm64
python3 scripts/package-portable-preview.py \
  --binary local-build/target/debug/soundcraft \
  --launcher local-build/launchers/arm64 \
  --output 'local-build/SoundCraft AAF Portable dev.1.app' --architectures arm64
```

Este comando usa el ejecutable de desarrollo ya compilado con `scripts/build-dev-app.sh`. No confundirlo con un build release nuevo.

Para preparar el universal después de liberar espacio:

```sh
./scripts/build-universal-preview.sh --check
# El checkout de contribución debe estar preparado (ver proceso 2).
./scripts/build-universal-preview.sh
# Opcional: poner sólo los productos de compilación en un disco externo:
# SOUNDCRAFT_BUILD_DIR='/Volumes/Disco/Build SoundCraft' ./scripts/build-universal-preview.sh
```

El script no sube nada, no usa certificados y no instala en Applications. Conserva fuentes y cachés; rechaza salidas existentes. Se deben revisar sus resultados antes de distribuir. El paquete conserva licencias de Python y sus dependencias y las de SoundCraft/helper; no incluye el material de clase ni las imágenes de marca de docs/brand.

Gates antes de etiquetar `rc.1`:

- Build release universal, `lipo` confirma arm64+x86_64 en app y lanzador; verificar arquitectura del runtime elegido.
- Auditoría de dependencias dinámicas y del mínimo de macOS real, no sólo Info.plist.
- Versión y aviso de distribución no oficial coherentes en Finder, CLI, About y notas. El About del ejecutable base todavía muestra la versión upstream.
- Instalar desde DMG copiado a otro Mac sin repositorio ni Python; abrir por Finder y verificar permisos.
- En ambos equipos: importar fixture y Pinguino, escuchar y verificar canales, guardar/reabrir, extender handles, undo/redo y errores por medio faltante.
- Ensayo continuo de duración real con el hardware del aula, sin grabar material original ni sobrescribir sesiones.
- Registrar modelo, macOS, CPU, salida de audio, resultados y limitaciones de Gatekeeper. Sin Intel físico aprobado, no declarar “validado en Intel”.

Evidencia privada: `local-tests/portable-reader-test.json`, `local-tests/portable-app-validation-v4/summary.json`, `local-tests/intel-runtime-rosetta.json` y `local-tests/portable-pinguino-reader.json` (el plan real de 22 pistas/124 cortes es idéntico al contrastado con Pro Tools). Se inspeccionó la ventana por CUA. Las pruebas de modelo se ejecutaron con `--skip-screenshots` porque la captura GPU de la API puede fallar si no hay frame presentado. La primera salida del validador tenía un campo audio_disabled fijo; fue corregido para registrar el dispositivo real. Víctor confirmó por escucha que el fixture suena y que el ambiente sale por ambos canales en Apple Silicon. No equivale al ensayo prolongado de clase.

## 2. Contribución a SoundCraft

Hecho:

- `scripts/export-upstream.py` genera `integration/upstream-aaf.patch` contra el commit upstream fijado, usando un índice temporal.
- El **mismo** constructor Rust se coloca en `crates/interchange`, registrado como capa 3 y con dependencias del workspace. El motor ya no depende de una ruta al helper en ese parche.
- Se genera un manifiesto de base, hash y archivos; el parche aplica a una base limpia. Exportación y checkout no crean commits, push ni PR.
- Checkout de contribución separado: `local-build/upstream-contribution` (Git local compartido; conserva intacto el checkout original).
- CI completo pasado en sandbox sin lectura de VST3 instalados: fmt, clippy, tests, assets, layers y WASM; 1156 pruebas pasadas y un benchmark ya ignorado por upstream. Sin filtros adicionales. El intento normal quedó bloqueado cargando módulos VST3 y fue terminado; no se certifica ese entorno de plugins. Ver integration/validation-2026-10-19.json.

Reproducción:

```sh
# El overlay de desarrollo debe estar aplicado y coincidir con integration/soundcraft-aaf.patch.
python3 scripts/export-upstream.py --checkout local-build/upstream-contribution
cd local-build/upstream-contribution
cargo +1.95.0 xtask ci
```

El exportador requiere rustfmt 1.95, respeta la configuración de formato de upstream, no sobrescribe un checkout existente y mantiene la autoría/licencia MIT del constructor original. La carpeta de contribución usa objetos Git compartidos con el submódulo; conservar ambos mientras se trabaja.

Pendiente antes de pedir revisión upstream:

- Revisar el diff; CI aislado completo pasado. Registrar el bloqueo separado con plugins instalados y repetir en un runner limpio antes de publicar.
- Recuperar/revisar craftrules, todavía no accesible en la investigación inicial.
- Actualizar contra main vigente y volver a revisar issues/PR para no duplicar trabajo.
- Acordar el lector Python opcional y su distribución frente a la dirección Rust puro. El contrato Plan permite sustituir sólo el lector.
- Añadir instrucciones de configuración del lector para quien pruebe el PR, y actualizar inventarios de compatibilidad/progreso sin declarar soporte AAF/OMF completo.
- Confirmar el crédito que Víctor quiere usar, hacer commits revisables y actualizar el borrador de PR.
- Sólo tras instrucción explícita: crear fork/rama remotos y abrir PR. La revisión y el merge a main corresponden a los mantenedores. El release oficial sigue su pipeline separado.

No adjuntar Pinguino ni sus WAV al PR sin una autorización específica de redistribución; los fixtures públicos son los sintéticos originales.

## Avance guardado

La contribución está en el commit local `f8ad3c0083c5414b42719164001ece0a983cfd3a`, rama `feat/aaf-session-data`, con el nombre público elegido **Vic Herrera (@vhhr)** bajo la entrada GitHub `vhhr7`. El bundle incremental `integration/aaf-session-data.bundle` conserva ese commit aunque se borren cachés/checkouts locales; requiere el commit base fijado. El parche de texto permite revisar los cambios sin herramientas especiales. El registro generado de estadísticas de contribuidores no se modificó.

El 19/10 se terminó el CI completo en el entorno aislado (1156 pruebas aprobadas, 1 benchmark ignorado por upstream, ningún filtro añadido) y se guardó su informe con el SHA del parche. Luego se eliminaron sólo 9,8 GB de nuestra caché de compilación para construir el universal en `local-build/universal-target`; las apps de prueba y los informes se conservaron. Los comandos que esperan el antiguo target/debug requieren reconstruirlo con build-dev-app.sh.

El siguiente test físico Intel requiere otro Mac: el equipo disponible tiene macOS 10.8, incompatible con el mínimo 11.0 de esta distribución. No se ha modificado su sistema operativo.
