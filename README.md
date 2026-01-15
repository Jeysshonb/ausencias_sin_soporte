# 📌 Ausencias sin Soporte - TimeShift Analytics

Sistema integral para el análisis y detección de ausencias sin soporte, cruzando información de TimeShift, reportes de ausentismos, SAP, retiros y master data.

## 🎯 Características

- ✅ **Análisis automatizado** de ausencias sin marcación ni justificación
- 📊 **Cruces múltiples** entre 6 fuentes de datos diferentes
- 🔍 **Detección inteligente** de inconsistencias y anomalías
- 📈 **Reportes consolidados** con métricas detalladas por empleado
- 💾 **Exportación a Excel** con múltiples hojas de análisis
- 🚀 **Interfaz web intuitiva** con Streamlit
- 🎨 **Código refactorizado** y modular para fácil mantenimiento

## 📋 Requisitos

### Archivos de entrada necesarios:
1. **Rep_Horas_laboradas.xlsx** - Marcaciones de TimeShift
2. **Rep_aususentismos.xlsx** - Reporte de ausentismos
3. **Retiros.xlsx** - Información de retiros
4. **Md_activos.xlsx** - Master Data de empleados activos
5. **funciones_marcación.xlsx** - Funciones autorizadas para marcación
6. **Ausentismos_SAP** (.xls/.xlsx) - Ausentismos registrados en SAP

### Dependencias:
```
Python 3.13+
streamlit
pandas
numpy
openpyxl
xlrd
lxml
html5lib
```

## 🚀 Instalación

### Opción 1: Instalación local

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/ausencias-sin-soporte.git
cd ausencias-sin-soporte

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
streamlit run app.py
```

### Opción 2: Desplegar en Streamlit Cloud

1. Haz fork del repositorio
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. ¡Listo! Tu app estará disponible en línea

## 📖 Uso

1. **Cargar archivos**: Sube los 6 archivos requeridos
2. **Seleccionar periodo**: Define fecha inicio y fin del análisis
3. **Generar consolidado**: Click en el botón "🚀 Generar consolidado"
4. **Revisar resultados**: Explora las diferentes pestañas con análisis
5. **Descargar Excel**: Exporta el reporte completo

## 📊 Reportes Generados

El sistema genera un Excel con las siguientes hojas:

- **Parámetros**: Configuración utilizada en el análisis
- **Ausencias_sin_soporte**: Detalle día a día de ausencias sin justificación
- **Resumen_periodo**: Consolidado por empleado con métricas clave
- **Retiros_fuera_rango**: Empleados retirados antes del periodo con movimientos
- **Ingresos_posteriores**: Empleados con fecha de ingreso posterior al periodo
- **Inconsistencias**: Detección de anomalías y datos conflictivos

## 🔧 Arquitectura del Código

```
.
├── app.py              # Frontend Streamlit (UI)
├── processor.py        # Lógica de negocio y cálculos
├── parsers.py          # Parseo de archivos SAP
├── utils.py            # Utilidades y funciones auxiliares
├── requirements.txt    # Dependencias Python
├── packages.txt        # Dependencias del sistema
└── .streamlit/
    └── config.toml     # Configuración de Streamlit
```

### Módulos principales:

- **`app.py`**: Interfaz de usuario con Streamlit
- **`processor.py`**: Clase `AusenciasProcessor` con toda la lógica de análisis
- **`parsers.py`**: Parser robusto para diferentes formatos de SAP
- **`utils.py`**: Funciones de normalización, limpieza y transformación de datos

## 📐 Reglas de Negocio

### Cálculo de fechas clave:
- **Fecha de retiro**: `Desde - 1 día` (campo "Desde" del archivo Retiros)
- **Fecha de ingreso**: Fecha donde `Clase de fecha` contiene "alta" (Master Data)
- **Empleados activos**: Solo IDs con función autorizada en TS (según `funciones_marcación`)

### Identificación de ausencias sin soporte:
Un día se considera "sin soporte" cuando:
- ✅ El empleado está vigente ese día (entre ingreso y retiro)
- ❌ NO tiene marcación en TimeShift
- ❌ NO tiene ausentismo registrado en Reporte
- ❌ NO tiene ausentismo registrado en SAP

### Estados de empleados:
- **Activo (MD)**: En periodo y autorizado en TS
- **Retirado en el periodo**: Retiro dentro del rango analizado
- **Retirado antes del periodo**: Retiro anterior al inicio
- **Retiro después del periodo**: Retiro posterior al fin
- **Ingreso posterior al periodo**: Alta después del periodo
- **Sin masterdata**: No aparece en Master Data (posible retirado)

## 🎨 Características de la Refactorización

### Antes:
- ❌ 623 líneas en un solo archivo
- ❌ Lógica mezclada con UI
- ❌ Difícil mantenimiento
- ❌ No reutilizable

### Después:
- ✅ Código modular en 4 archivos especializados
- ✅ Separación clara de responsabilidades
- ✅ Fácil de testear y mantener
- ✅ Componentes reutilizables
- ✅ 70% menos líneas en el frontend

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### Error: "Columnas faltantes"
Verifica que los archivos tengan los nombres de columnas esperados:
- **Rep_Horas_laboradas**: `IdentificacionEmpleado`, `FechaEntrada`
- **Rep_aususentismos**: `Identificacion`, `Fecha_Inicio`, `Fecha_Final`
- **Retiros**: `Número ID`, `Desde`
- **Md_activos**: `N° pers.`, `Función`, `Clase de fecha`, `Fecha`
- **funciones_marcación**: `Función`

### La app no carga en Streamlit Cloud
- Verifica que `requirements.txt` y `packages.txt` estén en el repo
- Haz "Reboot app" desde el dashboard de Streamlit Cloud
- Revisa los logs en el panel de administración

## 📝 Logs y Diagnóstico

Activa la opción "Mostrar diagnóstico (logs)" en la barra lateral para ver:
- Columnas detectadas en cada archivo
- Número de registros procesados
- Advertencias y errores durante el análisis

## 🤝 Contribuciones

### Creado por:
**Andrés Huerfano** - Versión inicial

### Adaptado y mejorado por:
**Jeysshon Bustos** - Nómina Data Analytics, Jerónimo Martins (2026)
- ♻️ Refactorización completa del código
- 🏗️ Arquitectura modular
- 🎨 Mejoras en UI/UX
- 🐛 Corrección de bugs y optimizaciones
- 📚 Documentación completa

## 📄 Licencia

Este proyecto es de uso interno para Jerónimo Martins.

## 📧 Soporte

Para reportar bugs o sugerencias, contacta al equipo de Nómina Data Analytics.

---

**Nómina Data Analytics** | Jerónimo Martins © 2026
