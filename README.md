# SIGA — Motor de Priorización (OGPL - UNMSM)

Aplicación de escritorio para priorizar la bandeja de expedientes del SIGA de la Oficina General de Planificación (OGPL) de la UNMSM. Ordena los expedientes según un modelo **AHP** de tres filtros y puede evaluarlos con **IA (Claude)** usando como referencia la Ley de Presupuesto, el PEI y el POI de la universidad.

**Meta:** reducir los tiempos de espera atendiendo primero lo que la ley permite y lo que más aporta a la universidad.

## Modelo de priorización

| Filtro | Peso por defecto | Qué evalúa |
|---|---|---|
| 1. Legal (austeridad) | 50 % | Cumplimiento de la Ley de Presupuesto, gastos prohibidos, cruce de fondos |
| 2. Estratégico (impacto) | 30 % | Licenciamiento y acreditación, inversiones en ejecución, servicios básicos, vínculo con OEI/AEI del PEI |
| 3. Técnico (sustento) | 20 % | Certificación de crédito presupuestario (CCP), formatos completos, riesgo fiscal |

Los pesos se pueden ajustar desde la aplicación (deben sumar 100 %). Cada expediente recibe un puntaje de 0 a 100 y uno de estos estados:

- **Prioridad máxima** — puntaje ≥ 80; pasa al inicio de la bandeja.
- **Atención regular** — trámite legal y sustentado, sin urgencia crítica.
- **Observado** — falta la CCP u otro documento indispensable; se devuelve a origen.
- **Rechazo automático** — solicita conceptos prohibidos por la Ley de Presupuesto.

El detalle de los criterios está en [`contexto_normativo/00_criterios_ogpl.md`](contexto_normativo/00_criterios_ogpl.md).

## Motores de evaluación

- **Reglas AHP (sin IA):** evaluación local e inmediata a partir del asunto del expediente. No requiere conexión ni clave de API.
- **IA (Claude):** evalúa cada expediente con todas sus columnas, contrastándolo con los documentos de `contexto_normativo/`, y explica el sustento de cada puntaje y de cada puesto. Modelos disponibles: Claude Opus 5.5 (recomendado) y Claude Sonnet 5.5 (más económico).

### Memoria institucional

Las evaluaciones de la IA se guardan en una base local (`memoria_ia.db`). Desde **🧠 Memoria IA** un analista puede confirmar o corregir cada decisión; esas validaciones se usan como precedente en los siguientes procesamientos. Este archivo se crea automáticamente y **no se sube al repositorio**.

## Requisitos

- Windows, macOS o Linux con Python 3.10 o superior (desarrollado con Python 3.14) y Tkinter.
- Para el motor de IA: una clave de API de Anthropic.

## Instalación

```bash
git clone https://github.com/ulisesvasquezgallardo/siga-motor-priorizacion.git
cd siga-motor-priorizacion
python -m venv .venv
```

Activar el entorno virtual:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Uso

```bash
python oriol.py
```

1. En la pantalla de inicio (estructura AHP) pulsar **⚙️ INICIAR MOTOR AHP ➔**; **📘 VER GUÍA DE ESTADOS** explica cada estado.
2. Elegir el motor (**IA (Claude)** o **Reglas AHP**) y, si corresponde, el modelo.
3. Procesar la bandeja: si existe `MES DE FEBRERO.xlsx` en la carpeta del proyecto se usa ese archivo; si no, se pide seleccionar un Excel.
4. Revisar el ranking, el panel de indicadores y el detalle (auditoría) de cada expediente.
5. Exportar el plan de trabajo con **💾 Exportar Excel** (`Plan_Trabajo_SIGA_AAAAMMDD_HHMM.xlsx`).

### Formato del Excel de entrada

- Hoja: `CAT_1_Aprobación, Modifica`
- Encabezados en la fila 4.
- Columnas usadas: `NRO EXP`, `REMITENTE`, `ASUNTO`. Con el motor de IA se envían también todas las demás columnas no vacías.

### Clave de API (motor de IA)

La aplicación toma la clave de la variable de entorno `ANTHROPIC_API_KEY`; si no existe, la solicita al procesar con IA (solo para la sesión en curso).

```powershell
# Windows (PowerShell), de forma permanente para el usuario
setx ANTHROPIC_API_KEY "tu-clave"
```

> No escriba la clave en ningún archivo del proyecto: el repositorio es público.

## Contexto normativo

La carpeta `contexto_normativo/` contiene los documentos que la IA usa como referencia obligatoria (se leen en orden alfabético):

- `00_criterios_ogpl.md` — criterios institucionales del modelo AHP (editable).
- Ley N.° 32513 — Ley de Presupuesto del Sector Público para el Año Fiscal 2026.
- Plan Estratégico Institucional (PEI) de la UNMSM.
- Plan Operativo Institucional (POI) 2024, 2025 y 2026.

Formatos aceptados: `.pdf` con texto seleccionable, `.txt` y `.md` (los PDF escaneados requieren OCR). Para agregar documentos use **📚 Contexto normativo → ⬆ Subir archivos** dentro de la aplicación. Incluya `ley` en el nombre del archivo de la Ley de Presupuesto y `pei` en el del Plan Estratégico para que la aplicación los reconozca.

## Estructura del proyecto

```
oriol.py              Interfaz gráfica (Tkinter) y motor de reglas AHP
motor_ia.py           Motor de evaluación con Claude y carga del contexto normativo
memoria_ia.py         Memoria institucional (SQLite): evaluaciones y validaciones
requirements.txt      Dependencias de Python
contexto_normativo/   Documentos de referencia para la IA
```
