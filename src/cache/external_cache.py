from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Tuple

DB_PATH = Path("data/cache/external_data.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_cache() -> None:
    """
    Initialize all external-data cache tables.

    Tables:
      - electricity_price(market, timestamp, price_EUR_per_MWh, source)
      - weather(location, timestamp, temperature_K, source)
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS electricity_price (
            market TEXT,
            timestamp TEXT,
            price_EUR_per_MWh REAL,
            source TEXT,
            PRIMARY KEY (market, timestamp)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS weather (
            location TEXT,
            timestamp TEXT,
            temperature_K REAL,
            source TEXT,
            PRIMARY KEY (location, timestamp)
        )
        """
    )

    conn.commit()
    conn.close()


# -----------------------------
# PRICE CACHE
# -----------------------------

def upsert_prices(rows: Iterable[Tuple[str, str, float, str]]) -> None:
    """
    rows: (market, timestamp_iso, price_EUR_per_MWh, source)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR REPLACE INTO electricity_price (market, timestamp, price_EUR_per_MWh, source)
        VALUES (?, ?, ?, ?)
        """,
        list(rows),
    )
    conn.commit()
    conn.close()


def get_price(market: str, timestamp_iso: str) -> Optional[float]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT price_EUR_per_MWh FROM electricity_price WHERE market=? AND timestamp=?",
        (market, timestamp_iso),
    )
    row = cur.fetchone()
    conn.close()
    return None if row is None else float(row[0])


def has_any_price(market: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM electricity_price WHERE market=? LIMIT 1",
        (market,),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def has_price(market: str, timestamp_iso: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM electricity_price WHERE market=? AND timestamp=?",
        (market, timestamp_iso),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


# -----------------------------
# WEATHER CACHE
# -----------------------------

def upsert_weather(rows: Iterable[Tuple[str, str, float, str]]) -> None:
    """
    rows: (location, timestamp_iso, temperature_K, source)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR REPLACE INTO weather (location, timestamp, temperature_K, source)
        VALUES (?, ?, ?, ?)
        """,
        list(rows),
    )
    conn.commit()
    conn.close()


def insert_weather(location: str, timestamp_iso: str, temperature_K: float, source: str = "DWD") -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO weather(location, timestamp, temperature_K, source)
        VALUES (?, ?, ?, ?)
        """,
        (location, timestamp_iso, float(temperature_K), source),
    )
    conn.commit()
    conn.close()


def get_weather(location: str, timestamp_iso: str) -> Optional[float]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT temperature_K FROM weather WHERE location=? AND timestamp=?",
        (location, timestamp_iso),
    )
    row = cur.fetchone()
    conn.close()
    return None if row is None else float(row[0])


def has_weather(location: str, timestamp_iso: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM weather WHERE location=? AND timestamp=?",
        (location, timestamp_iso),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def has_any_weather(location: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM weather WHERE location=? LIMIT 1",
        (location,),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None
