from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from .bot import ShotgunBot
from .config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Shotgun — Zerostack-powered Matrix bot")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("shotgun.toml"),
        help="Path to config file (default: shotgun.toml in cwd)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config(args.config)
    logger = logging.getLogger("shotgun")
    logger.info("Starting Shotgun bot, homeserver=%s user=%s", config.matrix.homeserver, config.matrix.user_id)

    bot = ShotgunBot(config)

    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
