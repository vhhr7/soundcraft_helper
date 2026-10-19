# Demostración de cinco minutos

Preparación previa: compilar y pasar los tests del README; abrir una copia de `demo/Sesión SoundCraft/session.scraft`. Usar volumen bajo: los medios son tonos sintéticos con pulsos. La comprobación automatizada usa `--no-audio`; la reproducción audible requiere ensayo humano previo con la interfaz del aula. Llevar Pro Tools como alternativa y una copia de la demo sin modificar.

| Tiempo | Acción y concepto |
|---|---|
| 0:00–1:00 | Mostrar AAF + los dos WAV originales. Ejecutar `./scripts/import-aaf.sh 'demo/AAF con espacios ñ/Montaje sintético.aaf' '/tmp/Clase AAF nueva'` usando un destino que no exista. Abrir `/tmp/Clase AAF nueva/session.scraft`. Explicar que el AAF describe decisiones de montaje |
| 1:00–2:00 | Mostrar dos pistas: `01 Diálogo` mono y `02 Ambiente estéreo`. Dos clips de diálogo en 1–3 s y 4–5 s; ambiente en 0–5 s. Los silencios tienen posiciones, no relleno consolidado |
| 2:00–3:00 | En Slip, extender el primer diálogo de 1–3 s a 0.5–3.5 s con Trim. Explicar que su offset baja de 48000 a 24000 muestras y que aparece audio ya existente antes/después del corte. Restaurar los bordes originales |
| 3:00–4:00 | Mostrar `import-report.json`: handles antes/después del primer clip = 48000/240000 muestras, es decir 1/5 s a 48 kHz. La fuente completa dura 8 s. Guardar una copia y reabrirla |
| 4:00–5:00 | Mostrar un fallo controlado con una copia del fixture a la que le falte un WAV; mantener intacto el fixture original. Leer el diagnóstico. Explicar los límites: no OMF, embebidos, efectos, automatización ni ruteos; la próxima comparación será un AAF real abierto también en Pro Tools |

Si la interfaz falla, usar `docs/app-validation/verified-montage.png` y los resultados de pruebas como material explicativo; no afirmar que esa captura equivale a estabilidad comprobada para una clase.
