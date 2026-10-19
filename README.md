# soundcraft_helper — importación AAF editable

Primera etapa funcional, en la rama local `feat/aaf-import`. Lee un subconjunto de AAF reales (binarios CFB), construye una `soundcraft_model::Session` con el módulo Rust reutilizable y escribe una sesión `.scraft` portable con sus WAV completos. **No consolida pistas**: cada corte sigue siendo un clip con offset sobre la fuente.

Validado con AAF sintético original: 2 pistas mono/estéreo, 3 clips, silencios, offsets encadenados y handles. También se importó y abrió un AAF real con 22 pistas, 124 clips y 124 WAV externos mono, usando relink explícito. La sesión abrió en SoundCraft 0.8.0; la aplicación extendió ambos bordes de un clip, guardó una copia y la reabrió con los medios cargados. La comparación independiente con la sesión abierta en Pro Tools coincide para los 124 inicios/finales/duraciones, offsets, archivos fuente y handles (0 muestras de diferencia tras igualar el origen). Sigue pendiente comprobar reproducción audible y estabilidad durante una clase.

## Preparar y compilar en macOS

Requisitos: herramientas de línea de comandos de Xcode (`xcode-select --install` si faltan), Python 3.10 o superior y Rust mediante [rustup](https://rustup.rs/). `rust-toolchain.toml` fija Rust 1.90.0. No se necesita compilar la interfaz de SoundCraft para probar el módulo.

```sh
cd /ruta/al/checkout/soundcraft_helper
# Este checkout local está en .../soundcraft_helper/helper-aaf
# Después de clonar este repo, recuperar el modelo upstream fijado:
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.txt
cargo build --locked
cargo test --locked
cargo fmt -- --check
cargo clippy --locked --all-targets -- -D warnings
PYTHONPATH=python .venv/bin/python -m unittest discover -s tests -v
```

El submódulo `upstream/` está fijado a `25d52c646aea780c8076ff966076f994ad256221` de `storytold/soundcraft` (modelo 0.9.0). `Cargo.lock` fija las dependencias Rust; `requirements.txt` fija versión y hashes de pyaaf2. No ejecutar `git submodule update --remote` para reproducir esta revisión.

En esta máquina Rust se descargó de forma aislada en `/tmp`, sin cambiar el PATH global. Mientras exista ese directorio se puede usar:

```sh
export RUSTUP_HOME=/tmp/soundcraft-rustup
export CARGO_HOME=/tmp/soundcraft-cargo
export PATH="$CARGO_HOME/bin:$PATH"
```

Esos directorios son temporales; para trabajar después de un reinicio usar la instalación normal de rustup.

## Importar

```sh
./scripts/import-aaf.sh '/ruta/montaje.aaf' '/ruta/Sesión nueva'
```

En macOS 0.8.0, `open -a SoundCraft archivo.scraft` puede mostrar “cannot open files” por el mecanismo de apertura de documentos del sistema. Para esta prueba, iniciar directamente el ejecutable con la ruta como argumento:

```sh
/Applications/SoundCraft.app/Contents/MacOS/SoundCraft --no-audio \
  "$PWD/demo/Sesión SoundCraft/session.scraft"
```

Este comando permite revisar pistas, cortes y handles sin activar la salida de audio. Para una escucha posterior, omitir `--no-audio`. Mantener esa Terminal abierta mientras se usa esta instancia. Para otra sesión, reemplazar la última ruta por su ruta absoluta.

El destino **no debe existir**. La salida contiene `session.scraft`, `import-report.json` y `Audio Files/` con copias completas de las fuentes, sin modificar los originales. Abrir `session.scraft` en SoundCraft. El reporte enumera advertencias y handles en muestras. Si falla la publicación puede quedar un directorio nuevo incompleto, identificado como tal por el error; no se reutiliza automáticamente.

Para inspeccionar las dos capas por separado o escoger composición por MobID:

```sh
PYTHONPATH=python .venv/bin/python -m soundcraft_aaf \
  '/ruta/montaje.aaf' '/tmp/montaje-plan.json' --composition 'urn:smpte:umid:...'
./target/debug/plan-to-session '/tmp/montaje-plan.json' '/ruta/Sesión nueva'
```

Si el AAF conserva locators de una ubicación antigua, indicar explícitamente la carpeta que contiene los medios:

```sh
./scripts/import-aaf.sh '/ruta/montaje.aaf' '/ruta/Sesión nueva' \
  --media-dir '/ruta/carpeta de WAV'
```

`--media-dir` busca únicamente el nombre exacto de cada locator dentro de esa carpeta, sin búsqueda recursiva ni coincidencias aproximadas. El relink queda registrado en `import-report.json`. Los slots fuente pueden tener una tasa de edición distinta del sample rate: los offsets usan la primera y los WAV se validan contra el segundo.

El plan debe ser nuevo y no contiene audio. La biblioteca Rust `build_session(Plan)` no ejecuta procesos ni accede al disco: es la misma que usa la CLI. El adaptador Python sólo lee AAF y emite tiempos racionales; **no escribe JSON de SoundCraft**. El ejecutable Rust verifica metadatos contra los WAV antes de construir y copiar. Otros consumidores de la biblioteca deben hacer esa verificación y aplicar sus propias restricciones de acceso a archivos.

## Demo y documentación

- [Sesión mínima lista para abrir](demo/Sesión%20SoundCraft/session.scraft), con fuentes relativas y reporte.
- [AAF sintético y fuentes](demo/AAF%20con%20espacios%20ñ/), regenerable con `scripts/generate_fixture.py NUEVA_CARPETA`.
- [Compatibilidad, investigación y decisiones](docs/compatibility.md).
- [Validación automática y en la aplicación](docs/validation.md).
- [Arquitectura y continuación de la integración](docs/integration.md).
- [Guion de clase de cinco minutos](docs/class-demo.md).
- [Borrador de descripción de PR](docs/PR_DRAFT.md).

No hay importación directa de AAF en el menú de SoundCraft todavía. OMF, medios embebidos, fades y ganancia quedan fuera de esta etapa. Consultar la matriz completa antes de usar un archivo real. No se publicó ningún PR ni se contactó a mantenedores.
