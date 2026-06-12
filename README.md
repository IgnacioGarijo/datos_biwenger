# SuperComunio 2.0 Biwenger Lab

Dashboard estático para analizar una liga privada de Biwenger: evolución de la clasificación, producción por jugadores y posiciones, mercado, trading, fidelidad de plantilla y fichas individuales por equipo.

La web está preparada para publicarse directamente con GitHub Pages desde la raíz del repositorio.

## Estructura

```text
.
├── index.html              # Página principal
├── app.js                  # Lógica de visualización Plotly
├── data.js                 # Dataset agregado que consume la web
├── styles.css              # Estilos
├── assets/team-icons/      # Iconos personalizados de equipos
├── data/biwenger/          # CSV normalizados y JSON crudos cacheados
├── scripts/
│   ├── scrape_biwenger.py  # Scraper de Biwenger
│   └── build_dashboard_data.py
├── .env.example            # Plantilla de credenciales locales
└── requirements.txt
```

## Uso rápido

1. Instala dependencias:

```powershell
python -m pip install -r requirements.txt
```

2. Crea un `.env` a partir de `.env.example`:

```powershell
Copy-Item .env.example .env
```

3. Rellena en `.env`:

```text
BIWENGER_TOKEN=...
BIWENGER_LEAGUE_ID=...
BIWENGER_USER_ID=...
```

4. Scrapea o refresca datos:

```powershell
python scripts\scrape_biwenger.py --players lineups --delay 1.2
```

5. Regenera el dataset de la web:

```powershell
python scripts\build_dashboard_data.py
```

6. Previsualiza localmente:

```powershell
python -m http.server 8766
```

Abre `http://localhost:8766/`.

## Publicación

En GitHub Pages selecciona:

- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/ (root)`

La página usa solo archivos estáticos, así que no requiere backend.

## Datos generados

`data/biwenger/` contiene:

- `league_round_standings.csv`: clasificación y puntos por jornada.
- `lineups_long.csv`: jugadores alineados por equipo y jornada.
- `market_movements.csv`: compras, ventas y movimientos publicados en el tablón.
- `player_reports_long.csv`: detalle histórico de puntuaciones y estadísticas de jugador.
- `player_prices_long.csv`: serie histórica de precios.
- `raw/`: respuestas JSON cacheadas para no repetir peticiones innecesarias.

El scraper reusa la caché. Si Biwenger devuelve `429 Too Many Requests`, espera y relanza el mismo comando: continuará con lo que falte.

## Métricas destacadas

- Carrera animada de puntos totales.
- Jornadas ganadas y farolillos.
- Goles, dependencia goleadora y dependencia de puntos.
- Índice de palos: amarilla efectiva `2.5`, roja efectiva `5`, doble amarilla como roja.
- Trading: beneficios y ROI emparejando compras visibles con ventas posteriores publicadas por Biwenger; si falta venta explícita, se usa la siguiente compra visible como respaldo.
- Volumen de mercado: compras visibles, ventas publicadas y ventas inferidas.
- Rendimiento y dependencia por posición.
- Ficha por equipo con galardones positivos/negativos y mejores jugadores por línea.

## Notas de privacidad

Las credenciales no deben versionarse. El archivo `.env` está ignorado por Git; solo se incluye `.env.example`.

Los datos normalizados y la web sí se versionan para que GitHub Pages pueda servir el dashboard sin ejecutar el scraper.
