# Datos Biwenger normalizados

Generado con:

```powershell
python 1_code\scrape_biwenger.py --players lineups
```

Tablas principales:

- `lineups_long.csv`: una fila por jugador alineado, usuario y jornada. Incluye puntos del usuario antes/despues de la jornada, puntos de alineacion, datos del jugador, puntos del jugador en esa jornada y `rawStats` comunes como goles, asistencias, tarjetas, minutos, porteria a cero, picas y SofaScore cuando el detalle estaba disponible.
- `player_reports_long.csv`: informes por jugador y partido/jornada, con puntos por sistema de puntuacion y estadisticas crudas.
- `player_prices_long.csv`: historico diario de precios descargado desde la ficha de cada jugador.
- `market_movements.csv`: movimientos del tablon de liga (`market`, `transfer`, `exchange`, `loan`, etc.) aplanados.
- `ownership_periods_from_movements.csv`: periodos inferidos de propiedad a partir de movimientos de mercado. Es una reconstruccion aproximada: no conoce plantillas iniciales si no hubo movimiento previo visible.
- `league_round_standings.csv`: clasificacion de cada usuario por jornada.
- `round_finished_bonuses.csv` y `manual_bonuses.csv`: bonus automaticos de jornada y bonus manuales.
- `current_market.csv` y `current_my_squad.csv`: foto actual de mercado y plantilla del usuario autenticado.

La carpeta `raw/` guarda las respuestas JSON originales. Si Biwenger devuelve `429 Too Many Requests`, relanza el mismo comando mas tarde: el script reutiliza la cache y continua con lo que falte.
