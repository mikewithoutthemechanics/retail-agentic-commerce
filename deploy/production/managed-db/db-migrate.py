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

"""Idempotent schema migration/seed step for a managed database.

The demo uses ``SQLModel.metadata.create_all`` to provision its schema. This
script runs that provisioning (and the initial seed) against whatever
``DATABASE_URL`` is configured, which is the safe migration path when moving
from the local SQLite file to a managed Postgres instance.

Usage:
    python deploy/production/managed-db/db-migrate.py
"""

from __future__ import annotations

import sys

from src.merchant.config import get_settings
from src.merchant.db.database import get_engine, init_and_seed_db, reset_engine


def main() -> int:
    settings = get_settings()
    database_url = settings.database_url
    scheme = database_url.split("://", 1)[0]
    print(f"[db-migrate] target scheme: {scheme}")
    print(f"[db-migrate] initializing schema against configured DATABASE_URL")

    # Ensure a fresh engine is built against the resolved URL.
    reset_engine()
    engine = get_engine()
    if engine is None:
        print("[db-migrate] ERROR: could not build database engine", file=sys.stderr)
        return 1

    try:
        init_and_seed_db()
    except Exception as exc:  # pragma: no cover - surface real provisioning errors
        print(f"[db-migrate] ERROR: {exc}", file=sys.stderr)
        return 1

    print("[db-migrate] schema initialized and seeded successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
