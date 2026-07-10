# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Database connection and session management for the PSP service."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from src.payment.config import get_payment_settings

# Create engine lazily to allow settings to be loaded
_engine = None


def _normalize_database_url(url: str) -> str:
    """Normalize a configured database URL for SQLAlchemy/SQLModel.

    Managed Postgres providers commonly emit ``postgres://`` style URLs
    (e.g. Amazon RDS, Cloud SQL, Azure Flexible Server). SQLAlchemy requires
    the ``postgresql://`` dialect, so rewrite the scheme here to avoid
    ``NoSuchModuleError`` when pointing the PSP at a managed database.

    Args:
        url: Raw ``DATABASE_URL`` value.

    Returns:
        Normalized database URL string.
    """
    if url.startswith("postgres://"):
        return "postgresql" + url[len("postgres"):]
    return url


def get_engine():
    """Get or create the database engine.

    Returns:
        Engine: SQLAlchemy engine instance.
    """
    global _engine
    if _engine is None:
        settings = get_payment_settings()
        url = _normalize_database_url(settings.database_url)
        # ``check_same_thread`` is a SQLite-only connect argument. Managed
        # databases (Postgres/MySQL) reject it, so only apply it for SQLite.
        connect_args: dict = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        # ``pool_pre_ping`` and ``pool_recycle`` keep long-lived connections to
        # a managed database healthy across provider-side idle timeouts.
        _engine = create_engine(
            url,
            echo=settings.debug,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return _engine


def get_session() -> Generator[Session, None, None]:
    """Get a database session.

    Yields:
        Session: A SQLModel session for database operations.
    """
    with Session(get_engine()) as session:
        yield session


def init_payment_tables() -> None:
    """Initialize the PSP database tables.

    Creates the vault_token, payment_intent, and idempotency_store tables.
    Also creates the merchant tables if they don't exist (for testing).
    """
    # Import models to register them with SQLModel metadata
    # These imports are necessary for table creation even if not directly used
    from src.payment.db import (
        models as _models,  # noqa: F401  # pyright: ignore[reportUnusedImport]
    )

    SQLModel.metadata.create_all(get_engine())


def reset_engine() -> None:
    """Reset the database engine. Useful for testing."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
