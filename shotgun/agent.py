from __future__ import annotations

import asyncio
import logging

from .config import ZerostackConfig

logger = logging.getLogger("shotgun")


async def run_agent(prompt: str, config: ZerostackConfig) -> tuple[str, bool]:
    cmd = ["zerostack", "-p", prompt, "--no-color"]

    if config.permission == "yolo":
        cmd.append("--yolo")
    else:
        cmd.append("--read-only")

    if config.provider:
        cmd.extend(["--provider", config.provider])
    if config.model:
        cmd.extend(["--model", config.model])
    if config.prompt:
        cmd.extend(["--prompt", config.prompt])
    if config.extra_args:
        cmd.extend(config.extra_args)

    logger.debug("Spawning: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    success = proc.returncode == 0
    logger.debug("Agent exited with code %d, output: %s", proc.returncode, output[:200])

    return output, success
