from __future__ import annotations

import argparse
import logging
import os
import subprocess
from pathlib import Path

from client import netinfo, wg
from client.api import DuplicatePubkeyError, ServerClient, server_url
from client.config import IFACE, LISTEN_PORT, STATE_DIR
from client.render import render_config
from client.state import load_or_create_state, save_state, write_private

log = logging.getLogger("client")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="client")
    commands = parser.add_subparsers(dest="command", required=True)

    join = commands.add_parser("join", help="join the overlay")
    join.add_argument("--server", required=True, help="coordination server, host[:port] or URL")
    join.add_argument("--key", default=os.environ.get("API_KEY"), help="API key (or env API_KEY)")
    join.add_argument("--listen-port", type=int, default=LISTEN_PORT)
    join.add_argument("--state-dir", type=Path, default=STATE_DIR)
    join.set_defaults(run=_join)

    down = commands.add_parser("down", help="take the tunnel down, identity is kept")
    down.add_argument("--state-dir", type=Path, default=STATE_DIR)
    down.set_defaults(run=_down)
    return parser


def _config_path(state_dir: Path) -> Path:
    return state_dir / f"{IFACE}.conf"


def _join(args: argparse.Namespace) -> int:
    if not args.key:
        log.error("missing API key: pass --key or set API_KEY")
        return 2

    base_url = server_url(args.server)
    state = load_or_create_state(args.state_dir, args.listen_port)
    private_key = wg.load_or_create_private_key(args.state_dir)
    pubkey = wg.public_key(private_key)
    endpoint = f"{netinfo.local_ip_towards(base_url)}:{state.listen_port}"

    try:
        registration = ServerClient(base_url, args.key).register(state.node_id, pubkey, endpoint)
    except DuplicatePubkeyError:
        log.error("server rejected this node: pubkey belongs to another node_id")
        return 1

    config_path = _config_path(args.state_dir)
    if state.overlay_ip != registration.overlay_ip:
        wg.down(config_path)

    state = state.with_overlay_ip(registration.overlay_ip)
    save_state(args.state_dir, state)
    write_private(
        config_path,
        render_config(private_key, registration.overlay_ip, state.listen_port, registration.peers),
    )
    wg.up(config_path)
    log.info("joined as %s with overlay ip %s", state.node_id, state.overlay_ip)
    return 0


def _down(args: argparse.Namespace) -> int:
    wg.down(_config_path(args.state_dir))
    log.info("tunnel down")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except subprocess.CalledProcessError as exc:
        log.error("%s failed: %s", exc.cmd[0], exc.stderr.strip())
        return 1
