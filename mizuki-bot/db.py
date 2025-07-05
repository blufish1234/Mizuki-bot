from collections.abc import Buffer
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import SupportsLenAndGetItem

import aiosqlite

db: Optional[aiosqlite.Connection] = None


async def connect(path: str | Path = "data.db"):
    global db
    db = await aiosqlite.connect(path)


def get_db():
    global db
    if db is None:
        raise ValueError("database is not initialized, call setup() first")


@asynccontextmanager
async def execute_ctx(
    sql: str,
    parameters: "SupportsLenAndGetItem[str | Buffer | int | float | None]"
    | Mapping[str, str | Buffer | int | float | None] = (),
):
    try:
        c: aiosqlite.Cursor = await db.execute(sql, parameters)
        yield c
    finally:
        await c.close()


async def execute(
    sql: str,
    parameters: "SupportsLenAndGetItem[str | Buffer | int | float | None]"
    | Mapping[str, str | Buffer | int | float | None] = (),
) -> aiosqlite.Cursor:
    return await db.execute(sql, parameters)


async def commit():
    return await db.commit()
