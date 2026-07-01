from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class MatrixConfig:
    homeserver: str
    user_id: str
    access_token: str


@dataclass
class ZerostackConfig:
    permission: str = "read-only"
    provider: str | None = None
    model: str | None = None
    prompt: str | None = None
    extra_args: list[str] = field(default_factory=list)


@dataclass
class FiltersConfig:
    allowlist: list[str] = field(default_factory=list)
    denylist: list[str] = field(default_factory=list)


@dataclass
class ShotgunConfig:
    matrix: MatrixConfig
    zerostack: ZerostackConfig
    filters: FiltersConfig
    allow_dm: bool = True
    zerostack_dm: ZerostackConfig | None = None
    filters_dm: FiltersConfig | None = None


def load_config(path: Path | None = None) -> ShotgunConfig:
    if path is None:
        path = Path("shotgun.toml")

    if not path.exists():
        print(f"Config file not found: {path}", file=sys.stderr)
        print("Create a shotgun.toml or pass --config <path>", file=sys.stderr)
        sys.exit(1)

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    matrix_raw = raw.get("matrix", {})
    homeserver = matrix_raw["homeserver"]
    user_id = matrix_raw["user_id"]

    token_env = matrix_raw.get("access_token_env")
    if token_env:
        access_token = os.environ.get(token_env, "")
        if not access_token:
            print(f"Environment variable {token_env} is not set", file=sys.stderr)
            sys.exit(1)
    else:
        access_token = matrix_raw.get("access_token", "")

    if not access_token:
        print("No access_token or access_token_env configured", file=sys.stderr)
        sys.exit(1)

    matrix = MatrixConfig(
        homeserver=homeserver,
        user_id=user_id,
        access_token=access_token,
    )

    zs_raw = raw.get("zerostack", {})
    perm = zs_raw.get("permission", "read-only")
    if perm not in ("yolo", "read-only"):
        print(f"Invalid zerostack.permission: {perm}. Use 'yolo' or 'read-only'", file=sys.stderr)
        sys.exit(1)

    zerostack = ZerostackConfig(
        permission=perm,
        provider=zs_raw.get("provider"),
        model=zs_raw.get("model"),
        prompt=zs_raw.get("prompt"),
        extra_args=zs_raw.get("extra_args", []),
    )

    filters_raw = raw.get("filters", {})
    filters = FiltersConfig(
        allowlist=filters_raw.get("allowlist", []),
        denylist=filters_raw.get("denylist", []),
    )

    dm_raw = raw.get("dm", {})
    allow_dm = dm_raw.get("allow", True)
    if not isinstance(allow_dm, bool):
        print(f"Invalid dm.allow: {allow_dm}. Must be true or false", file=sys.stderr)
        sys.exit(1)

    zerostack_dm = None
    if "zerostack" in dm_raw:
        zs_dm_raw = dm_raw["zerostack"]
        perm_dm = zs_dm_raw.get("permission", "read-only")
        if perm_dm not in ("yolo", "read-only"):
            print(f"Invalid dm.zerostack.permission: {perm_dm}. Use 'yolo' or 'read-only'", file=sys.stderr)
            sys.exit(1)
        zerostack_dm = ZerostackConfig(
            permission=perm_dm,
            provider=zs_dm_raw.get("provider"),
            model=zs_dm_raw.get("model"),
            prompt=zs_dm_raw.get("prompt"),
            extra_args=zs_dm_raw.get("extra_args", []),
        )

    filters_dm = None
    if "filters" in dm_raw:
        f_dm_raw = dm_raw["filters"]
        filters_dm = FiltersConfig(
            allowlist=f_dm_raw.get("allowlist", []),
            denylist=f_dm_raw.get("denylist", []),
        )

    return ShotgunConfig(
        matrix=matrix,
        zerostack=zerostack,
        filters=filters,
        allow_dm=allow_dm,
        zerostack_dm=zerostack_dm,
        filters_dm=filters_dm,
    )
