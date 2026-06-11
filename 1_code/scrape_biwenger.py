#!/usr/bin/env python3
"""
Scraper amplio para una liga de Biwenger.

Genera CSV normalizados en 0_data/biwenger y guarda respuestas JSON crudas en
0_data/biwenger/raw para poder re-procesar sin volver a pedirlo todo.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "0_data" / "biwenger"
PUBLIC_COMPETITION_URL = (
    "https://cf.biwenger.com/api/v2/competitions/la-liga/data"
    "?lang=es&score={score}&callback=jsonp_1465365482"
)
PLAYER_FIELDS = "*,team,reports,prices,competition,seasons,news,threads"
BOARD_TYPES = "transfer,market,exchange,loan,loanReturn,clauseIncrement"
SCORE_COLUMNS = {
    "1": "points_as",
    "2": "points_sofascore",
    "5": "points_average",
    "3": "points_stats",
    "6": "points_social",
}
COMMON_RAW_STATS = [
    "goals",
    "assists",
    "yellowCard",
    "redCard",
    "secondYellowCard",
    "ownGoal",
    "penaltyMissed",
    "penaltySave",
    "goalsConceded",
    "cleanSheet",
    "minutesPlayed",
    "picas",
    "sofascore",
    "home",
    "away",
    "win",
    "draw",
    "lost",
]


def read_main_config() -> dict[str, str]:
    text = (ROOT / "1_code" / "main.R").read_text(encoding="utf-8")
    config = {}
    patterns = {
        "token": r'token\s*<-\s*"([^"]+)"',
        "league": r'x_league\s*<-\s*"([^"]+)"',
        "user": r'x_user\s*<-\s*"([^"]+)"',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            config[key] = match.group(1)
    config["token"] = os.getenv("BIWENGER_TOKEN", config.get("token", ""))
    config["league"] = os.getenv("BIWENGER_LEAGUE", config.get("league", ""))
    config["user"] = os.getenv("BIWENGER_USER", config.get("user", ""))
    missing = [key for key in ("token", "league", "user") if not config.get(key)]
    if missing:
        raise RuntimeError(f"Faltan credenciales/configuracion: {', '.join(missing)}")
    return config


def authed_headers(config: dict[str, str]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config['token']}",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (compatible; biwenger-data-scraper/1.0)",
        "X-League": config["league"],
        "X-User": config["user"],
        "X-Lang": "es",
    }


def request_json(url: str, headers: dict[str, str] | None = None) -> Any:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        text = response.read().decode("utf-8", "replace")
    text = re.sub(r"^jsonp_\d+\(", "", text)
    text = re.sub(r"\);?\s*$", "", text)
    return json.loads(text)


def cached_json(
    path: Path,
    url: str,
    headers: dict[str, str] | None = None,
    refresh: bool = False,
    delay: float = 0.0,
) -> Any:
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        data = request_json(url, headers=headers)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} en {url}: {body[:300]}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if delay:
        time.sleep(delay)
    return data


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compact_json(value: Any) -> str:
    if value is None or value == "":
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def unix_to_iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def price_day_to_iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).zfill(6)
    try:
        return datetime.strptime(text, "%y%m%d").date().isoformat()
    except ValueError:
        return ""


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def season_round_rows(competition: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for order, round_data in enumerate(competition["data"]["season"]["rounds"], start=1):
        rows.append(
            {
                "round_order": order,
                "round_id": round_data.get("id"),
                "round_name": round_data.get("name"),
                "round_short": round_data.get("short"),
                "round_part": round_data.get("part"),
                "round_status": round_data.get("status"),
            }
        )
    return rows


def player_catalog_rows(competition: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    players = competition["data"]["players"]
    rows = []
    by_id = {}
    for item in players.values():
        row = dict(item)
        row["fitness_json"] = compact_json(row.pop("fitness", None))
        rows.append(row)
        by_id[int(item["id"])] = item
    return rows, by_id


def team_rows(competition: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for team in competition["data"].get("teams", {}).values():
        row = dict(team)
        row["nextGames_json"] = compact_json(row.pop("nextGames", None))
        rows.append(row)
    return rows


def fetch_rounds(
    round_rows: list[dict[str, Any]],
    config: dict[str, str],
    out: Path,
    refresh: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int]]:
    headers = authed_headers(config)
    standings_rows: list[dict[str, Any]] = []
    lineup_rows: list[dict[str, Any]] = []
    lineup_player_ids: set[int] = set()
    meta = {int(r["round_id"]): r for r in round_rows}
    for round_id, round_meta in meta.items():
        url = f"https://biwenger.as.com/api/v2/rounds/league/{round_id}"
        data = cached_json(out / "raw" / "rounds" / f"{round_id}.json", url, headers, refresh)
        for standing in data["data"]["league"].get("standings", []):
            lineup = standing.get("lineup") or {}
            base = {
                **round_meta,
                "user_id": standing.get("id"),
                "user_name": standing.get("name"),
                "user_icon": standing.get("icon"),
                "total_points_after_round": standing.get("points"),
                "team_value": standing.get("teamValue"),
                "team_value_increment": standing.get("teamValueInc"),
                "league_position": standing.get("position"),
                "lineup_type": lineup.get("type"),
                "lineup_points": lineup.get("points"),
                "lineup_position": lineup.get("position"),
                "lineup_date": lineup.get("date"),
                "lineup_date_iso": unix_to_iso(lineup.get("date")),
                "lineup_count": lineup.get("count"),
                "bonus_point": (lineup.get("bonuses") or {}).get("bonusPoint"),
                "bonus_fixed": (lineup.get("bonuses") or {}).get("bonusFixed"),
            }
            base["total_points_before_round"] = (
                base["total_points_after_round"] - base["lineup_points"]
                if isinstance(base["total_points_after_round"], int)
                and isinstance(base["lineup_points"], int)
                else ""
            )
            standings_rows.append(base)
            for order, player_id in enumerate(as_list(lineup.get("players")), start=1):
                if player_id in (None, ""):
                    continue
                lineup_player_ids.add(int(player_id))
                lineup_rows.append({**base, "lineup_order": order, "player_id": player_id})
    return standings_rows, lineup_rows, lineup_player_ids


def fetch_board(
    config: dict[str, str],
    out: Path,
    board_type: str,
    filename: str,
    refresh: bool,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    headers = authed_headers(config)
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({"type": board_type, "offset": offset, "limit": page_size})
        url = f"https://biwenger.as.com/api/v2/league/{config['league']}/board?{params}"
        data = cached_json(out / "raw" / "board" / f"{filename}_{offset}.json", url, headers, refresh)
        page = data.get("data", [])
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return rows


def flatten_board_movements(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for idx, item in enumerate(items):
        contents = item.get("content")
        if isinstance(contents, dict):
            contents = [contents]
        for content_idx, content in enumerate(as_list(contents)):
            if not isinstance(content, dict):
                continue
            row = {
                "board_index": idx,
                "content_index": content_idx,
                "type": item.get("type"),
                "date": item.get("date"),
                "date_iso": unix_to_iso(item.get("date")),
                "fixed": item.get("fixed"),
                "title": item.get("title"),
                "author_id": (item.get("author") or {}).get("id") if isinstance(item.get("author"), dict) else "",
                "author_name": (item.get("author") or {}).get("name") if isinstance(item.get("author"), dict) else "",
                "player_id": content.get("player"),
                "amount": content.get("amount"),
                "from_user_id": (content.get("from") or {}).get("id") if isinstance(content.get("from"), dict) else "",
                "from_user_name": (content.get("from") or {}).get("name") if isinstance(content.get("from"), dict) else "",
                "to_user_id": (content.get("to") or {}).get("id") if isinstance(content.get("to"), dict) else "",
                "to_user_name": (content.get("to") or {}).get("name") if isinstance(content.get("to"), dict) else "",
                "content_json": compact_json(content),
            }
            rows.append(row)
    return rows


def flatten_round_finished(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        content = item.get("content") or {}
        round_data = content.get("round") or {}
        for result in content.get("results", []):
            user = result.get("user") or {}
            reason = result.get("reason") or {}
            rows.append(
                {
                    "date": item.get("date"),
                    "date_iso": unix_to_iso(item.get("date")),
                    "round_id": round_data.get("id"),
                    "round_name": round_data.get("name"),
                    "score_id": content.get("scoreID"),
                    "user_id": user.get("id"),
                    "user_name": user.get("name"),
                    "points": result.get("points"),
                    "bonus": result.get("bonus"),
                    **{f"reason_{key}": value for key, value in reason.items()},
                    "reason_json": compact_json(reason),
                }
            )
    return rows


def flatten_bonus(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        for content in as_list(item.get("content")):
            user = (content or {}).get("user") or {}
            author = item.get("author") or {}
            rows.append(
                {
                    "date": item.get("date"),
                    "date_iso": unix_to_iso(item.get("date")),
                    "user_id": user.get("id"),
                    "user_name": user.get("name"),
                    "amount": (content or {}).get("amount"),
                    "author_id": author.get("id") if isinstance(author, dict) else "",
                    "author_name": author.get("name") if isinstance(author, dict) else "",
                }
            )
    return rows


def fetch_player_details(
    player_ids: set[int],
    catalog_by_id: dict[int, dict[str, Any]],
    basic_by_id: dict[int, dict[str, Any]],
    out: Path,
    score_id: int,
    refresh: bool,
    delay: float,
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    details: dict[int, dict[str, Any]] = {}
    report_rows: list[dict[str, Any]] = []
    price_rows: list[dict[str, Any]] = []
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain, */*"}
    network_blocked = False
    for player_id in sorted(player_ids):
        slug = (catalog_by_id.get(player_id) or {}).get("slug") or (basic_by_id.get(player_id) or {}).get("slug")
        if not slug:
            continue
        params = urllib.parse.urlencode({"fields": PLAYER_FIELDS, "score": score_id, "lang": "es"}, safe="*,()")
        url = f"https://cf.biwenger.com/api/v2/players/la-liga/{slug}?{params}"
        cache_path = out / "raw" / "players" / f"{player_id}_{slug}.json"
        if network_blocked and not cache_path.exists():
            continue
        try:
            data = cached_json(cache_path, url, headers, refresh, delay)
        except RuntimeError as exc:
            if "HTTP 429" in str(exc):
                print(
                    "AVISO: Biwenger ha devuelto 429 Too Many Requests. "
                    "Paro nuevas descargas de detalles; seguire cargando la cache disponible."
                )
                network_blocked = True
                continue
            print(f"AVISO: no se pudo descargar jugador {player_id} ({slug}): {exc}")
            continue
        player = data.get("data") or {}
        details[player_id] = player
        base = {
            "player_id": player_id,
            "player_name": player.get("name"),
            "player_slug": player.get("slug"),
            "position": player.get("position"),
            "current_price": player.get("price"),
            "fantasy_price": player.get("fantasyPrice"),
            "current_status": player.get("status"),
            "price_increment": player.get("priceIncrement"),
            "real_team_id": (player.get("team") or {}).get("id") if isinstance(player.get("team"), dict) else "",
            "real_team_name": (player.get("team") or {}).get("name") if isinstance(player.get("team"), dict) else "",
        }
        for report in player.get("reports", []):
            match = report.get("match") or {}
            round_data = match.get("round") or {}
            points = report.get("points") or {}
            raw_stats = report.get("rawStats") or {}
            row = {
                **base,
                "match_id": match.get("id"),
                "match_date": match.get("date"),
                "match_date_iso": unix_to_iso(match.get("date")),
                "match_status": match.get("status"),
                "round_id": round_data.get("id"),
                "round_name": round_data.get("name"),
                "round_short": round_data.get("short"),
                "round_part": round_data.get("part"),
                "home_team_id": (match.get("home") or {}).get("id") if isinstance(match.get("home"), dict) else "",
                "home_team_name": (match.get("home") or {}).get("name") if isinstance(match.get("home"), dict) else "",
                "home_score": (match.get("home") or {}).get("score") if isinstance(match.get("home"), dict) else "",
                "away_team_id": (match.get("away") or {}).get("id") if isinstance(match.get("away"), dict) else "",
                "away_team_name": (match.get("away") or {}).get("name") if isinstance(match.get("away"), dict) else "",
                "away_score": (match.get("away") or {}).get("score") if isinstance(match.get("away"), dict) else "",
                "is_home": report.get("home"),
                "points_selected": points.get(str(score_id)),
                "events_json": compact_json(report.get("events")),
                "star_json": compact_json(report.get("star")),
                "raw_stats_json": compact_json(raw_stats),
            }
            for key, column in SCORE_COLUMNS.items():
                row[column] = points.get(key)
            for key in COMMON_RAW_STATS:
                row[key] = raw_stats.get(key)
            report_rows.append(row)
        for price in player.get("prices", []):
            if isinstance(price, list) and len(price) >= 2:
                price_rows.append(
                    {
                        **base,
                        "price_day": price[0],
                        "price_date": price_day_to_iso(price[0]),
                        "price": price[1],
                    }
                )
    return details, report_rows, price_rows


def load_basic_player_cache(out: Path) -> dict[int, dict[str, Any]]:
    basics: dict[int, dict[str, Any]] = {}
    basic_dir = out / "raw" / "players_basic"
    if not basic_dir.exists():
        return basics
    for path in basic_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            player = data.get("data") or {}
            if player:
                basics[int(path.stem)] = player
        except (ValueError, OSError):
            continue
    return basics


def fetch_basic_player_details(
    player_ids: set[int],
    catalog_by_id: dict[int, dict[str, Any]],
    detailed_by_id: dict[int, dict[str, Any]],
    config: dict[str, str],
    out: Path,
    refresh: bool,
) -> dict[int, dict[str, Any]]:
    basics: dict[int, dict[str, Any]] = {}
    headers = authed_headers(config)
    for player_id in sorted(player_ids):
        if player_id in detailed_by_id or player_id in catalog_by_id:
            continue
        params = urllib.parse.urlencode({"fields": "*,team"})
        url = f"https://biwenger.as.com/api/v2/players/la-liga/{player_id}?{params}"
        try:
            data = cached_json(out / "raw" / "players_basic" / f"{player_id}.json", url, headers, refresh)
        except RuntimeError as exc:
            print(f"AVISO: no se pudo descargar ficha basica {player_id}: {exc}")
            continue
        player = data.get("data") or {}
        if player:
            basics[player_id] = player
    return basics


def pending_player_detail_rows(
    player_ids: set[int],
    catalog_by_id: dict[int, dict[str, Any]],
    detailed_by_id: dict[int, dict[str, Any]],
    basic_by_id: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for player_id in sorted(player_ids):
        if player_id in detailed_by_id:
            continue
        catalog = catalog_by_id.get(player_id, {})
        basic = basic_by_id.get(player_id, {})
        rows.append(
            {
                "player_id": player_id,
                "player_name": basic.get("name") or catalog.get("name"),
                "player_slug": basic.get("slug") or catalog.get("slug"),
                "has_public_catalog_slug": bool(catalog.get("slug")),
                "has_basic_details": player_id in basic_by_id,
                "reason": "pending_detail_after_rate_limit"
                if catalog.get("slug")
                else "no_public_catalog_slug_or_pending_basic_only",
            }
        )
    return rows


def enrich_lineups(
    lineups: list[dict[str, Any]],
    catalog_by_id: dict[int, dict[str, Any]],
    details: dict[int, dict[str, Any]],
    basic_details: dict[int, dict[str, Any]],
    reports: list[dict[str, Any]],
    score_id: int,
) -> list[dict[str, Any]]:
    reports_by_player_round = {
        (int(row["player_id"]), int(row["round_id"])): row
        for row in reports
        if row.get("player_id") not in ("", None) and row.get("round_id") not in ("", None)
    }
    enriched = []
    for row in lineups:
        player_id = int(row["player_id"])
        catalog = catalog_by_id.get(player_id, {})
        detail = details.get(player_id, {}) or basic_details.get(player_id, {})
        report = reports_by_player_round.get((player_id, int(row["round_id"])), {})
        out = dict(row)
        out.update(
            {
                "player_name": detail.get("name") or catalog.get("name"),
                "player_slug": detail.get("slug") or catalog.get("slug"),
                "player_position": detail.get("position") or catalog.get("position"),
                "real_team_id": ((detail.get("team") or {}).get("id") if isinstance(detail.get("team"), dict) else "")
                or catalog.get("teamID"),
                "real_team_name": (detail.get("team") or {}).get("name") if isinstance(detail.get("team"), dict) else "",
                "current_price": detail.get("price") or catalog.get("price"),
                "fantasy_price": detail.get("fantasyPrice") or catalog.get("fantasyPrice"),
                "current_status": detail.get("status") or catalog.get("status"),
                "price_increment": detail.get("priceIncrement") or catalog.get("priceIncrement"),
                "player_round_points_selected": report.get("points_selected"),
            }
        )
        for key in SCORE_COLUMNS.values():
            out[f"player_round_{key}"] = report.get(key)
        for key in COMMON_RAW_STATS:
            out[key] = report.get(key)
        out["events_json"] = report.get("events_json")
        out["raw_stats_json"] = report.get("raw_stats_json")
        enriched.append(out)
    return enriched


def build_ownership_periods(movements: list[dict[str, Any]], catalog_by_id: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    by_player: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in movements:
        if row.get("player_id") in ("", None) or row.get("to_user_id") in ("", None):
            continue
        by_player[int(row["player_id"])].append(row)
    periods = []
    for player_id, events in by_player.items():
        open_period: dict[str, Any] | None = None
        for event in sorted(events, key=lambda r: (int(r.get("date") or 0), int(r.get("content_index") or 0))):
            if open_period:
                open_period["sold_date"] = event.get("date")
                open_period["sold_date_iso"] = event.get("date_iso")
                open_period["sold_to_user_id"] = event.get("to_user_id")
                open_period["sold_to_user_name"] = event.get("to_user_name")
                periods.append(open_period)
            catalog = catalog_by_id.get(player_id, {})
            open_period = {
                "player_id": player_id,
                "player_name": catalog.get("name"),
                "player_slug": catalog.get("slug"),
                "owner_user_id": event.get("to_user_id"),
                "owner_user_name": event.get("to_user_name"),
                "acquired_date": event.get("date"),
                "acquired_date_iso": event.get("date_iso"),
                "acquired_amount": event.get("amount"),
                "acquired_type": event.get("type"),
                "sold_date": "",
                "sold_date_iso": "",
                "sold_to_user_id": "",
                "sold_to_user_name": "",
            }
        if open_period:
            periods.append(open_period)
    return periods


def fetch_current_market(config: dict[str, str], out: Path, refresh: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    headers = authed_headers(config)
    market = cached_json(out / "raw" / "market.json", "https://biwenger.as.com/api/v2/market", headers, refresh)
    market_rows = []
    for sale in market.get("data", {}).get("sales", []):
        user = sale.get("user") if isinstance(sale.get("user"), dict) else {}
        market_rows.append(
            {
                "date": sale.get("date"),
                "date_iso": unix_to_iso(sale.get("date")),
                "until": sale.get("until"),
                "until_iso": unix_to_iso(sale.get("until")),
                "price": sale.get("price"),
                "player_id": (sale.get("player") or {}).get("id"),
                "seller_user_id": user.get("id") if user else "",
                "seller_user_name": user.get("name") if user else "",
            }
        )
    user_url = "https://biwenger.as.com/api/v2/user?" + urllib.parse.urlencode(
        {"fields": "*,lineup(type,playersID),players(*,fitness,team,owner),market(*,-userID),offers,-trophies"}
    )
    user_data = cached_json(out / "raw" / "current_user.json", user_url, headers, refresh)
    squad_rows = []
    for player in user_data.get("data", {}).get("players", []):
        owner = player.get("owner") or {}
        team = player.get("team") or {}
        squad_rows.append(
            {
                "user_id": user_data.get("data", {}).get("id"),
                "user_name": user_data.get("data", {}).get("name"),
                "player_id": player.get("id"),
                "player_name": player.get("name"),
                "player_slug": player.get("slug"),
                "position": player.get("position"),
                "price": player.get("price"),
                "fantasy_price": player.get("fantasyPrice"),
                "status": player.get("status"),
                "owner_date": owner.get("date"),
                "owner_date_iso": unix_to_iso(owner.get("date")),
                "owner_price": owner.get("price"),
                "real_team_id": team.get("id"),
                "real_team_name": team.get("name"),
                "fitness_json": compact_json(player.get("fitness")),
            }
        )
    return market_rows, squad_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrapea y normaliza datos de una liga Biwenger.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--refresh", action="store_true", help="Ignora cache JSON y vuelve a pedir todo.")
    parser.add_argument("--score", type=int, default=1, help="ScoreID de Biwenger. 1 = Diario AS.")
    parser.add_argument("--players", choices=["lineups", "all"], default="lineups")
    parser.add_argument("--delay", type=float, default=0.25, help="Pausa entre peticiones de jugador.")
    args = parser.parse_args()

    config = read_main_config()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    competition = cached_json(
        out / "raw" / "competition_la_liga.json",
        PUBLIC_COMPETITION_URL.format(score=args.score),
        {"User-Agent": "Mozilla/5.0"},
        args.refresh,
    )
    round_rows = season_round_rows(competition)
    player_rows, catalog_by_id = player_catalog_rows(competition)
    team_rows_data = team_rows(competition)
    standings, lineups, lineup_player_ids = fetch_rounds(round_rows, config, out, args.refresh)

    movement_items = fetch_board(config, out, BOARD_TYPES, "movements", args.refresh)
    bonus_items = fetch_board(config, out, "bonus", "bonus", args.refresh)
    round_finished_items = fetch_board(config, out, "roundFinished", "round_finished", args.refresh)
    movements = flatten_board_movements(movement_items)
    bonuses = flatten_bonus(bonus_items)
    round_finished = flatten_round_finished(round_finished_items)
    market_rows, current_squad_rows = fetch_current_market(config, out, args.refresh)

    player_ids = set(catalog_by_id) if args.players == "all" else set(lineup_player_ids)
    player_ids.update(int(row["player_id"]) for row in movements if row.get("player_id") not in ("", None))
    player_ids.update(int(row["player_id"]) for row in market_rows if row.get("player_id") not in ("", None))
    cached_basic_details = load_basic_player_cache(out)
    details, reports, prices = fetch_player_details(
        player_ids,
        catalog_by_id,
        cached_basic_details,
        out,
        args.score,
        args.refresh,
        args.delay,
    )
    basic_details = cached_basic_details | fetch_basic_player_details(player_ids, catalog_by_id, details, config, out, args.refresh)
    pending_details = pending_player_detail_rows(player_ids, catalog_by_id, details, basic_details)
    lineups_enriched = enrich_lineups(lineups, catalog_by_id, details, basic_details, reports, args.score)
    ownership_periods = build_ownership_periods(movements, catalog_by_id)

    league_data = cached_json(
        out / "raw" / "league.json",
        f"https://biwenger.as.com/api/v2/league/{config['league']}",
        authed_headers(config),
        args.refresh,
    )
    users = league_data.get("data", {}).get("users", [])

    write_csv(out / "users.csv", users)
    write_csv(out / "rounds.csv", round_rows)
    write_csv(out / "players_catalog.csv", player_rows)
    write_csv(out / "real_teams.csv", team_rows_data)
    write_csv(out / "league_round_standings.csv", standings)
    write_csv(out / "lineups_long.csv", lineups_enriched)
    write_csv(out / "player_reports_long.csv", reports)
    write_csv(out / "player_prices_long.csv", prices)
    write_csv(out / "market_movements.csv", movements)
    write_csv(out / "ownership_periods_from_movements.csv", ownership_periods)
    write_csv(out / "round_finished_bonuses.csv", round_finished)
    write_csv(out / "manual_bonuses.csv", bonuses)
    write_csv(out / "current_market.csv", market_rows)
    write_csv(out / "current_my_squad.csv", current_squad_rows)
    write_csv(out / "pending_player_details.csv", pending_details)

    summary = {
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "score_id": args.score,
        "players_mode": args.players,
        "users": len(users),
        "rounds": len(round_rows),
        "standings_rows": len(standings),
        "lineup_rows": len(lineups_enriched),
        "players_with_details": len(details),
        "players_pending_details": len(pending_details),
        "players_pending_details_with_public_slug": sum(1 for row in pending_details if row["has_public_catalog_slug"]),
        "player_reports": len(reports),
        "price_points": len(prices),
        "market_movements": len(movements),
        "ownership_periods_from_movements": len(ownership_periods),
        "round_finished_bonus_rows": len(round_finished),
    }
    (out / "scrape_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
