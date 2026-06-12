#!/usr/bin/env python3
"""Genera el dataset agregado para el dashboard estático de GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "0_data" / "biwenger"
DOCS = ROOT / "docs"
WEB_DIRS = [ROOT, DOCS]
ARREGUI_USER_ID = 8127478
ARREGUI_MANUAL_POINTS = 56
ARREGUI_MANUAL_POINTS_ROUND_NAME = "Jornada 15"
POSITION_NAMES = {
    1: "Portería",
    2: "Defensa",
    3: "Centro del campo",
    4: "Delantera",
    5: "Entrenador",
}


def clean_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def records(df: pd.DataFrame) -> list[dict]:
    clean = df.replace({np.nan: None})
    return clean.to_dict(orient="records")


def top_records(df: pd.DataFrame, n: int = 10, by: str | None = None, ascending: bool = False) -> list[dict]:
    if by:
        df = df.sort_values(by, ascending=ascending)
    return records(df.head(n))


def hhi(values: pd.Series) -> float:
    positive = clean_number(values).dropna()
    positive = positive[positive > 0]
    total = positive.sum()
    if total <= 0:
        return np.nan
    shares = positive / total
    return float((shares**2).sum())


def apply_manual_standing_adjustments(standings: pd.DataFrame) -> pd.DataFrame:
    """Move Arregui's manual Jornada 15 points out of the pre-season baseline."""
    adjusted = standings.copy()
    target_rounds = adjusted[
        (adjusted["user_id"] == ARREGUI_USER_ID)
        & (adjusted["round_name"] == ARREGUI_MANUAL_POINTS_ROUND_NAME)
    ]
    if target_rounds.empty:
        return adjusted

    first_target_order = target_rounds["round_order"].min()
    mask = (adjusted["user_id"] == ARREGUI_USER_ID) & (adjusted["round_order"] < first_target_order)
    for column in ["total_points_before_round", "total_points_after_round"]:
        adjusted.loc[mask, column] = adjusted.loc[mask, column] - ARREGUI_MANUAL_POINTS

    adjusted["league_position"] = (
        adjusted.groupby("round_order")["total_points_after_round"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    return adjusted


def main() -> None:
    for web_dir in WEB_DIRS:
        web_dir.mkdir(parents=True, exist_ok=True)

    standings = pd.read_csv(DATA / "league_round_standings.csv")
    lineups = pd.read_csv(DATA / "lineups_long.csv")
    movements = pd.read_csv(DATA / "market_movements.csv")
    summary = json.loads((DATA / "scrape_summary.json").read_text(encoding="utf-8"))

    numeric_cols = [
        "round_order",
        "round_id",
        "user_id",
        "total_points_after_round",
        "team_value",
        "league_position",
        "lineup_points",
        "lineup_position",
        "lineup_date",
        "total_points_before_round",
        "lineup_order",
        "player_id",
        "player_position",
        "current_price",
        "fantasy_price",
        "player_round_points_selected",
        "player_round_points_as",
        "goals",
        "assists",
        "yellowCard",
        "redCard",
        "secondYellowCard",
        "ownGoal",
        "minutesPlayed",
        "sofascore",
    ]
    for col in numeric_cols:
        if col in lineups:
            lineups[col] = clean_number(lineups[col])
        if col in standings:
            standings[col] = clean_number(standings[col])

    for col in ["date", "amount", "player_id", "to_user_id", "from_user_id"]:
        if col in movements:
            movements[col] = clean_number(movements[col])

    standings = apply_manual_standing_adjustments(standings)

    teams = (
        standings[["user_id", "user_name"]]
        .drop_duplicates()
        .sort_values("user_name")
        .to_dict(orient="records")
    )

    latest = (
        standings.sort_values(["round_order", "league_position"])
        .groupby("user_id", as_index=False)
        .tail(1)
        .sort_values("league_position")
    )

    position_progress = standings.sort_values(["round_order", "league_position"])[
        [
            "round_order",
            "round_id",
            "round_name",
            "round_short",
            "user_id",
            "user_name",
            "league_position",
            "total_points_after_round",
            "lineup_points",
            "team_value",
        ]
    ]

    round_team = standings[
        [
            "round_order",
            "round_id",
            "round_name",
            "round_short",
            "user_id",
            "user_name",
            "lineup_points",
            "lineup_position",
            "total_points_after_round",
        ]
    ].copy()
    round_team["round_rank"] = round_team.groupby("round_id")["lineup_points"].rank(
        method="min", ascending=False
    )
    round_team["reverse_round_rank"] = round_team.groupby("round_id")["lineup_points"].rank(
        method="min", ascending=True
    )

    round_counts = (
        round_team.groupby(["user_id", "user_name"], as_index=False)
        .agg(
            jornadas_ganadas=("round_rank", lambda s: int((s == 1).sum())),
            jornadas_perdidas=("reverse_round_rank", lambda s: int((s == 1).sum())),
            puntos_jornada_media=("lineup_points", "mean"),
            puntos_jornada_max=("lineup_points", "max"),
            puntos_jornada_min=("lineup_points", "min"),
        )
        .round(2)
    )

    lineups["goals"] = clean_number(lineups["goals"]).fillna(0)
    lineups["assists"] = clean_number(lineups["assists"]).fillna(0)
    lineups["yellowCard"] = clean_number(lineups["yellowCard"]).fillna(0)
    lineups["redCard"] = clean_number(lineups["redCard"]).fillna(0)
    lineups["secondYellowCard"] = clean_number(lineups["secondYellowCard"]).fillna(0)
    lineups["player_points"] = clean_number(lineups["player_round_points_selected"])
    available_points = lineups.dropna(subset=["player_points"]).copy()

    team_goals = (
        lineups.groupby(["user_id", "user_name"], as_index=False)
        .agg(goles=("goals", "sum"), asistencias=("assists", "sum"))
        .sort_values("goles", ascending=False)
    )

    player_goals = (
        lineups.groupby(["user_id", "user_name", "player_id", "player_name"], as_index=False)
        .agg(player_goals=("goals", "sum"))
    )
    goal_dependence = player_goals.merge(team_goals[["user_id", "goles"]], on="user_id", how="left")
    goal_dependence["share"] = np.where(
        goal_dependence["goles"] > 0,
        goal_dependence["player_goals"] / goal_dependence["goles"],
        np.nan,
    )
    goal_dependence = goal_dependence.sort_values("share", ascending=False)
    goal_dependence = goal_dependence.groupby("user_id", as_index=False).head(1)

    player_points = (
        available_points.groupby(["user_id", "user_name", "player_id", "player_name"], as_index=False)
        .agg(player_points=("player_points", "sum"))
    )
    team_points = (
        available_points.groupby(["user_id", "user_name"], as_index=False)
        .agg(total_player_points=("player_points", "sum"))
    )
    point_dependence = player_points.merge(team_points[["user_id", "total_player_points"]], on="user_id", how="left")
    point_dependence["share"] = np.where(
        point_dependence["total_player_points"] > 0,
        point_dependence["player_points"] / point_dependence["total_player_points"],
        np.nan,
    )
    point_dependence = point_dependence.sort_values("share", ascending=False)
    point_dependence = point_dependence.groupby("user_id", as_index=False).head(1)

    position_points = available_points.copy()
    position_points["position_id"] = clean_number(position_points["player_position"]).astype("Int64")
    position_points["position_name"] = position_points["position_id"].map(POSITION_NAMES).fillna("Sin posición")
    position_summary = (
        position_points.groupby(["user_id", "user_name", "position_id", "position_name"], as_index=False)
        .agg(
            position_points=("player_points", "sum"),
            position_goals=("goals", "sum"),
            position_assists=("assists", "sum"),
            players_used=("player_id", "nunique"),
            aligned_rounds=("round_id", "nunique"),
        )
        .merge(team_points[["user_id", "total_player_points"]], on="user_id", how="left")
    )
    position_summary["point_share"] = np.where(
        position_summary["total_player_points"] > 0,
        position_summary["position_points"] / position_summary["total_player_points"],
        np.nan,
    )
    position_summary = position_summary.round(4).sort_values(["position_id", "position_points"], ascending=[True, False])

    position_best_players = (
        position_points.groupby(
            ["user_id", "user_name", "position_id", "position_name", "player_id", "player_name"],
            as_index=False,
        )
        .agg(
            player_points=("player_points", "sum"),
            goals=("goals", "sum"),
            assists=("assists", "sum"),
            rounds=("round_id", "nunique"),
        )
        .sort_values(["user_id", "position_id", "player_points"], ascending=[True, True, False])
        .groupby(["user_id", "position_id"], as_index=False)
        .head(1)
        .round(2)
    )

    discipline = (
        lineups.assign(
            effective_yellow_cards=lambda d: (d["yellowCard"] - d["secondYellowCard"]).clip(lower=0),
            effective_red_cards=lambda d: d["redCard"] + d["secondYellowCard"],
            palos_index=lambda d: d["effective_yellow_cards"] * 2.5 + d["effective_red_cards"] * 5,
        )
        .groupby(["user_id", "user_name"], as_index=False)
        .agg(
            palos_index=("palos_index", "sum"),
            amarillas=("effective_yellow_cards", "sum"),
            rojas=("effective_red_cards", "sum"),
            segundas_amarillas=("secondYellowCard", "sum"),
        )
        .sort_values("palos_index", ascending=False)
    )

    # Compra/venta: se reconstruye como secuencia de compradores por jugador.
    completed_trades = []
    trade_events = movements[
        movements["player_id"].notna() & movements["to_user_id"].notna() & movements["amount"].notna()
    ].sort_values(["player_id", "date", "content_index"])
    for player_id, group in trade_events.groupby("player_id"):
        group = group.sort_values(["date", "content_index"]).reset_index(drop=True)
        for idx in range(len(group) - 1):
            buy = group.iloc[idx]
            sell = group.iloc[idx + 1]
            if buy["to_user_id"] == sell["to_user_id"]:
                continue
            buy_amount = float(buy["amount"])
            sell_amount = float(sell["amount"])
            if buy_amount <= 0:
                continue
            completed_trades.append(
                {
                    "user_id": buy["to_user_id"],
                    "user_name": buy["to_user_name"],
                    "player_id": buy["player_id"],
                    "player_name": "",
                    "buy_date": buy["date"],
                    "buy_date_iso": buy["date_iso"],
                    "sell_date": sell["date"],
                    "sell_date_iso": sell["date_iso"],
                    "buy_amount": buy_amount,
                    "sell_amount": sell_amount,
                    "profit": sell_amount - buy_amount,
                    "roi": (sell_amount - buy_amount) / buy_amount,
                    "holding_days": (sell["date"] - buy["date"]) / 86400 if pd.notna(sell["date"]) else np.nan,
                }
            )
    trades = pd.DataFrame(completed_trades)
    if len(trades):
        name_lookup = lineups[["player_id", "player_name"]].dropna().drop_duplicates("player_id")
        trades = trades.merge(name_lookup, on="player_id", how="left", suffixes=("", "_lookup"))
        trades["player_name"] = trades["player_name_lookup"].fillna(trades["player_name"])
        trade_summary = (
            trades.groupby(["user_id", "user_name"], as_index=False)
            .agg(
                operaciones_cerradas=("profit", "count"),
                beneficio_bruto=("profit", "sum"),
                inversion_total=("buy_amount", "sum"),
                venta_total=("sell_amount", "sum"),
                rentabilidad=("profit", lambda s: s.sum()),
                dias_medio=("holding_days", "mean"),
            )
            .round(2)
        )
        trade_summary["rentabilidad"] = np.where(
            trade_summary["inversion_total"] > 0,
            trade_summary["beneficio_bruto"] / trade_summary["inversion_total"],
            np.nan,
        )
        trade_summary = trade_summary.round(4)
    else:
        trade_summary = pd.DataFrame(
            columns=[
                "user_id",
                "user_name",
                "operaciones_cerradas",
                "beneficio_bruto",
                "inversion_total",
                "venta_total",
                "rentabilidad",
                "dias_medio",
            ]
        )

    market_activity = standings[["user_id", "user_name"]].drop_duplicates()
    if len(trade_events):
        purchases = (
            trade_events.groupby(["to_user_id", "to_user_name"], as_index=False)
            .agg(compras_visibles=("player_id", "count"), inversion_visible=("amount", "sum"))
            .rename(columns={"to_user_id": "user_id", "to_user_name": "user_name"})
        )
        inferred_sales_rows = []
        for _, group in trade_events.groupby("player_id"):
            group = group.sort_values(["date", "content_index"]).reset_index(drop=True)
            for idx in range(len(group) - 1):
                owner = group.iloc[idx]
                next_owner = group.iloc[idx + 1]
                if owner["to_user_id"] == next_owner["to_user_id"]:
                    continue
                inferred_sales_rows.append(
                    {
                        "user_id": owner["to_user_id"],
                        "user_name": owner["to_user_name"],
                        "ventas_inferidas": 1,
                        "importe_ventas_inferidas": next_owner["amount"],
                    }
                )
        inferred_sales = pd.DataFrame(inferred_sales_rows)
        if len(inferred_sales):
            inferred_sales = inferred_sales.groupby(["user_id", "user_name"], as_index=False).sum(numeric_only=True)
        else:
            inferred_sales = pd.DataFrame(
                columns=["user_id", "user_name", "ventas_inferidas", "importe_ventas_inferidas"]
            )
        market_activity = (
            market_activity.merge(purchases, on=["user_id", "user_name"], how="left")
            .merge(inferred_sales, on=["user_id", "user_name"], how="left")
        )
    else:
        market_activity = market_activity.assign(
            compras_visibles=0,
            inversion_visible=0,
            ventas_inferidas=0,
            importe_ventas_inferidas=0,
        )
    for col in ["compras_visibles", "ventas_inferidas", "inversion_visible", "importe_ventas_inferidas"]:
        market_activity[col] = market_activity[col].fillna(0)
    market_activity["movimientos_visibles"] = market_activity["compras_visibles"] + market_activity["ventas_inferidas"]
    market_activity = market_activity.round(2).sort_values("movimientos_visibles", ascending=False)

    acquisitions = movements[
        movements["player_id"].notna() & movements["to_user_id"].notna() & movements["amount"].notna()
    ][["player_id", "to_user_id", "to_user_name", "date", "date_iso", "amount"]].copy()
    acquisitions = acquisitions.rename(
        columns={
            "to_user_id": "user_id",
            "to_user_name": "user_name",
            "date": "acquired_date",
            "date_iso": "acquired_date_iso",
            "amount": "acquired_amount",
        }
    )

    fichaje_rows = []
    first_round_rows = []
    if len(acquisitions) and len(available_points):
        for _, acq in acquisitions.iterrows():
            owned_rows = available_points[
                (available_points["user_id"] == acq["user_id"])
                & (available_points["player_id"] == acq["player_id"])
                & (available_points["lineup_date"] >= acq["acquired_date"])
            ].sort_values("lineup_date")
            if owned_rows.empty:
                continue
            player_name = owned_rows.iloc[0]["player_name"]
            total_points = float(owned_rows["player_points"].sum())
            fichaje_rows.append(
                {
                    "user_id": acq["user_id"],
                    "user_name": acq["user_name"],
                    "player_id": acq["player_id"],
                    "player_name": player_name,
                    "acquired_date": acq["acquired_date"],
                    "acquired_date_iso": acq["acquired_date_iso"],
                    "acquired_amount": acq["acquired_amount"],
                    "points_after_signing": total_points,
                    "rounds_after_signing": int(owned_rows["round_id"].nunique()),
                }
            )
            first = owned_rows.iloc[0]
            first_round_rows.append(
                {
                    "user_id": acq["user_id"],
                    "user_name": acq["user_name"],
                    "player_id": acq["player_id"],
                    "player_name": player_name,
                    "acquired_date_iso": acq["acquired_date_iso"],
                    "first_round": first["round_name"],
                    "first_round_order": first["round_order"],
                    "first_round_points": first["player_points"],
                }
            )

    fichajes = pd.DataFrame(fichaje_rows)
    if len(fichajes):
        signing_points = (
            fichajes.groupby(["user_id", "user_name"], as_index=False)
            .agg(
                puntos_por_fichajes=("points_after_signing", "sum"),
                fichajes_con_puntos=("player_id", "count"),
                rondas_fichajes=("rounds_after_signing", "sum"),
            )
            .round(2)
            .sort_values("puntos_por_fichajes", ascending=False)
        )
    else:
        signing_points = pd.DataFrame(columns=["user_id", "user_name", "puntos_por_fichajes"])

    first_fichajes = pd.DataFrame(first_round_rows)
    if len(first_fichajes):
        first_round_signing_points = (
            first_fichajes.groupby(["user_id", "user_name"], as_index=False)
            .agg(
                puntos_primera_jornada_fichaje=("first_round_points", "sum"),
                fichajes_puntuando_primera_jornada=("player_id", "count"),
            )
            .round(2)
            .sort_values("puntos_primera_jornada_fichaje", ascending=False)
        )
    else:
        first_round_signing_points = pd.DataFrame(
            columns=["user_id", "user_name", "puntos_primera_jornada_fichaje"]
        )

    loyalty = (
        lineups.groupby(["user_id", "user_name", "player_id", "player_name"], as_index=False)
        .agg(
            first_round=("round_order", "min"),
            last_round=("round_order", "max"),
            aligned_rounds=("round_id", "nunique"),
        )
    )
    loyalty["span_rounds"] = loyalty["last_round"] - loyalty["first_round"] + 1
    loyalty_summary = (
        loyalty.groupby(["user_id", "user_name"], as_index=False)
        .agg(
            rondas_medias_por_jugador=("aligned_rounds", "mean"),
            span_medio=("span_rounds", "mean"),
            jugadores_usados=("player_id", "nunique"),
        )
        .round(2)
        .sort_values(["rondas_medias_por_jugador", "span_medio"], ascending=False)
    )

    concentration = (
        available_points.groupby(["user_id", "user_name"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "concentracion_hhi": hhi(g.groupby("player_id")["player_points"].sum()),
                    "puntos_cubiertos": g["player_points"].sum(),
                    "jugadores_con_puntos": g["player_id"].nunique(),
                }
            )
        )
        .reset_index(drop=True)
        .round(4)
        .sort_values("concentracion_hhi", ascending=False)
    )

    # Extras útiles.
    volatility = (
        round_team.groupby(["user_id", "user_name"], as_index=False)
        .agg(
            regularidad_std=("lineup_points", "std"),
            peor_jornada=("lineup_points", "min"),
            mejor_jornada=("lineup_points", "max"),
        )
        .round(2)
        .sort_values("regularidad_std")
    )
    value_efficiency = latest[["user_id", "user_name", "total_points_after_round", "team_value"]].copy()
    value_efficiency["puntos_por_millon"] = np.where(
        value_efficiency["team_value"] > 0,
        value_efficiency["total_points_after_round"] / (value_efficiency["team_value"] / 1_000_000),
        np.nan,
    )
    value_efficiency = value_efficiency.round(3).sort_values("puntos_por_millon", ascending=False)

    data = {
        "meta": {
            **summary,
            "generated_for": "GitHub Pages",
            "coverage": {
                "lineup_rows": int(len(lineups)),
                "lineup_rows_with_player_points": int(lineups["player_round_points_selected"].notna().sum()),
                "lineup_rows_with_goals": int(lineups["goals"].notna().sum()),
                "completed_trade_reconstructions": int(len(trades)),
                "visible_market_purchases": int(trade_events["to_user_id"].notna().sum()) if len(trade_events) else 0,
            },
            "limitations": [
                "A Arregui se le corrigen 56 puntos manuales de la Jornada 15 en los acumulados previos a esa jornada para que la carrera de puntos no arranque inflada.",
                "Quedan algunos jugadores sin detalle histórico completo porque no aparecen en el catálogo público actual de Biwenger; sus fichas básicas sí se conservan cuando la API autenticada las devuelve.",
                "No aparece una estadística de faltas cometidas en rawStats; el índice de palos es parcial y suma amarilla=2.5 y roja=5. Las dobles amarillas cuentan como roja, no como amarilla adicional.",
                "Beneficio de compra/venta se infiere por la siguiente compra visible del mismo jugador en el tablón; no distingue perfectamente ventas al mercado si Biwenger no publica el vendedor.",
            ],
        },
        "teams": teams,
        "latest_standings": records(
            latest[
                [
                    "league_position",
                    "user_id",
                    "user_name",
                    "total_points_after_round",
                    "team_value",
                    "lineup_points",
                ]
            ]
        ),
        "position_progress": records(position_progress),
        "round_team": records(round_team),
        "round_counts": records(round_counts),
        "team_goals": records(team_goals),
        "goal_dependence": records(goal_dependence),
        "point_dependence": records(point_dependence),
        "discipline": records(discipline),
        "trade_summary": records(trade_summary),
        "market_activity_summary": records(market_activity),
        "completed_trades": records(trades.sort_values("profit", ascending=False).head(30)) if len(trades) else [],
        "signing_points": records(signing_points),
        "first_round_signing_points": records(first_round_signing_points),
        "position_summary": records(position_summary),
        "position_best_players": records(position_best_players),
        "loyalty": records(loyalty_summary),
        "concentration": records(concentration),
        "volatility": records(volatility),
        "value_efficiency": records(value_efficiency),
        "top_signings": records(fichajes.sort_values("points_after_signing", ascending=False).head(25)) if len(fichajes) else [],
        "top_first_round_signings": records(first_fichajes.sort_values("first_round_points", ascending=False).head(25)) if len(first_fichajes) else [],
    }
    data["meta"]["limitations"] = [
        "A Arregui se le corrigen 56 puntos manuales de la Jornada 15 en los acumulados previos a esa jornada para que la carrera de puntos no arranque inflada.",
        "El detalle histórico de los jugadores que aparecen en alineaciones queda completo en esta extracción.",
        "No aparece una estadística de faltas cometidas en rawStats; el índice de palos es parcial y suma amarilla=2.5 y roja=5. Las dobles amarillas cuentan como roja, no como amarilla adicional.",
        "Beneficio de compra/venta se infiere por la siguiente compra visible del mismo jugador en el tablón; el volumen de mercado añade compras visibles y ventas inferidas, pero Biwenger puede contar ventas privadas o al mercado que no publica con vendedor explícito.",
    ]

    payload = "window.BIWENGER_DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    for web_dir in WEB_DIRS:
        (web_dir / "data.js").write_text(payload, encoding="utf-8")
    print(json.dumps(data["meta"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
