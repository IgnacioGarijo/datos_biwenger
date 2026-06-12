# Datos Biwenger normalizados

Estos archivos se generan con:

```powershell
python scripts\scrape_biwenger.py --players lineups --delay 1.2
```

Tablas principales:

- `lineups_long.csv`: una fila por jugador alineado, usuario y jornada. Incluye puntos del equipo antes/después de la jornada, puntos de alineación, datos del jugador, puntos del jugador en esa jornada y estadísticas comunes como goles, asistencias, tarjetas, minutos, picas y SofaScore.
- `player_reports_long.csv`: informes por jugador y partido/jornada, con puntos por sistema de puntuación y estadísticas crudas.
- `player_prices_long.csv`: histórico diario de precios descargado desde la ficha de cada jugador.
- `market_movements.csv`: movimientos del tablón de liga (`market`, `transfer`, `exchange`, `loan`, etc.) aplanados.
- `ownership_periods_from_movements.csv`: períodos inferidos de propiedad a partir de movimientos de mercado.
- `league_round_standings.csv`: clasificación de cada usuario por jornada.
- `round_finished_bonuses.csv` y `manual_bonuses.csv`: bonus automáticos de jornada y bonus manuales.
- `current_market.csv` y `current_my_squad.csv`: foto actual de mercado y plantilla del usuario autenticado.

La carpeta `raw/` guarda las respuestas JSON originales. Si Biwenger devuelve `429 Too Many Requests`, relanza el mismo comando más tarde: el script reutiliza la caché y continúa con lo que falte.
