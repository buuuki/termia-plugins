# SPDX-FileCopyrightText: 2026 Jordi Pons
# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Server:
    id: str
    name: str
    user: str
    host: str
    port: int


@dataclass
class StatisticsSettings:
    connections: int = 0
    completed_sessions: int = 0
    duration_total: float = 0.0
    duration_min: float | None = None
    duration_max: float = 0.0
    server_connections: dict[str, int] = field(default_factory=dict)
