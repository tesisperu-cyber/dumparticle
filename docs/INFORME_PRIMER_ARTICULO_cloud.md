# Informe de recuperación de un artículo real
Generado: 2026-11-26T19:31:21.678866Z
Colección: per  PID: None

| Paso | Resultado | Detalle |
|---|---|---|
| 1. Colecciones (ArticleMeta) | FALLA | HTTP None  ConnectionError: HTTPSConnectionPool(host='articlemeta.scielo.org', port=443): Max retries exceeded with url: /api/v1/collection/ (Caused by NameResolutionError("HTTPSConnection(host='articlemeta.scielo.org', port=443): Failed to resolve 'articlemeta.scielo.org' ([Errno -2] Name or service not known)")) |
| 2. Identificadores | FALLA | HTTP None; 0 objetos; muestra=[] |
| 3. Metadatos | FALLA | sin PID: no se puede continuar |

Resultado global: NO APROBADO

=== PANEL DE DIAGNÓSTICO ===
Identificadores listados: 0
Registros solicitados (metadatos): 0
Registros recibidos: 0
Metadatos completos: 0
Metadatos incompletos: 0
Coincidencias temporales/filtros (año, ISSN, tipo): 0
Coincidencias temáticas: 0
Artículos identificados (con PID): 0
XML solicitados: 0
XML recuperados y válidos: 0
XML inválidos / no disponibles: 0
Textos completos extraídos: 0
Errores HTTP/red: {'red:ConnectionError': 2}
Tiempo de ejecución: 12.01 s
Explicación: CERO porque no se obtuvo ni un identificador del servicio: errores HTTP/red = {'red:ConnectionError': 2}. Revise conectividad y endpoint (python main.py probe).