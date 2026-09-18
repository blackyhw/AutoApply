from __future__ import annotations

import argparse
import asyncio
import logging

from autoapply.heartbeat.watchdog import HeartbeatWatchdog
from autoapply.logging import configure_logging
from autoapply.notify.composite import CompositeNotifier, LogNotifier
from autoapply.notify.emailer import EmailNotifier
from autoapply.notify.telegram import TelegramNotifier
from autoapply.orchestrator import Agent
from autoapply.settings import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autoapply", description="Isolated job-application agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the 24/7 loop")
    run_p.add_argument("--dry-run", action="store_true", help="Force dry-run applies")

    once_p = sub.add_parser("once", help="Run a single collect-match-apply cycle")
    once_p.add_argument("--dry-run", action="store_true")

    sub.add_parser("heartbeat", help="Send a heartbeat now")

    watch_p = sub.add_parser("watchdog", help="Alert if the heartbeat is stale")
    watch_p.add_argument("--loop", action="store_true")

    args = parser.parse_args(argv)
    configure_logging(logging.INFO)
    settings = load_settings()
    if getattr(args, "dry_run", False):
        settings.dry_run = True

    if args.command == "run":
        asyncio.run(Agent(settings).run_forever())
        return 0
    if args.command == "once":
        stats = asyncio.run(Agent(settings).run_once())
        print(stats)
        return 0
    if args.command == "heartbeat":
        asyncio.run(Agent(settings).emit_heartbeat())
        return 0
    if args.command == "watchdog":
        notifier = CompositeNotifier(
            [
                LogNotifier(),
                TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id),
                EmailNotifier(settings),
            ]
        )
        watchdog = HeartbeatWatchdog(settings.heartbeat_path, notifier, settings.heartbeat_stale_after_hours)
        if args.loop:
            asyncio.run(watchdog.loop())
        else:
            ok = asyncio.run(watchdog.check())
            return 0 if ok else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
