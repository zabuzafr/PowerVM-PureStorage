#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRA.py — Discover LPAR WWPNs/MACs from IBM HMC and update Pure Storage hosts

- Python 3 only
- Robust CLI (argparse)
- Paramiko SSH to HMC
- Optional Pure Storage update (SDK or REST)
- Dry-run by default

Author: Pierre-Jacques MIMIFIR (zabuzafr)
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

import paramiko

try:
    import purestorage  # type: ignore
    HAVE_PURE_SDK = True
except Exception:
    HAVE_PURE_SDK = False

import urllib.request
import urllib.error
import ssl


# -----------------------------
# Helpers: normalization & logs
# -----------------------------

def normalize_wwpn(s: str) -> str:
    """Return WWPN in canonical form: 16 hex bytes separated by ':' (ex: 50:01:43:80:1A:2B:3C:4D)"""
    s = re.sub(r"[^0-9A-Fa-f]", "", s).upper()
    if len(s) != 16:
        # some HMC return full 16 bytes (32 hex chars) -> keep as is; others return with colon already
        # for safety, if length is 16 bytes (32 hex chars), okay; if not, try to pad left
        if len(s) < 16:
            s = s.rjust(16, "0")
        elif len(s) > 16 and len(s) != 32:
            # if 32 it's ok; if >32 truncate right
            s = s[:16]
    # if 32 hex chars (i.e., 16 bytes), keep them; if 16 hex chars (8 bytes), also split per 2
    step = 2
    return ":".join(s[i:i+step] for i in range(0, len(s), step))


def normalize_mac(s: str) -> str:
    """Return MAC in canonical form: 6 bytes separated by ':' (ex: 12:34:56:78:9A:BC)"""
    s = re.sub(r"[^0-9A-Fa-f]", "", s).upper()
    s = s[:12].rjust(12, "0")
    return ":".join(s[i:i+2] for i in range(0, 12, 2))


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# -----------------------------
# SSH / HMC
# -----------------------------

def ssh_run(host: str, user: str, password: str, cmd: str, timeout: int = 30) -> Tuple[int, List[str], str]:
    """
    Run a command over SSH on HMC, return (exit_code, stdout_lines, stderr_text)
    """
    cli = paramiko.SSHClient()
    cli.load_system_host_keys()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(host, username=user, password=password, timeout=timeout)
        _stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="ignore").splitlines()
        err = stderr.read().decode(errors="ignore")
        rc = stdout.channel.recv_exit_status()
        return rc, out, err
    except paramiko.ssh_exception.SSHException as ex:
        return 255, [], f"SSHException: {ex}"
    except Exception as ex:
        return 255, [], f"Exception: {ex}"
    finally:
        try:
            cli.close()
        except Exception:
            pass


# -----------------------------
# Discovery from HMC
# -----------------------------

def list_managed_systems(hmc: str, user: str, pwd: str) -> List[str]:
    rc, out, err = ssh_run(hmc, user, pwd, "lsyscfg -r sys -F name")
    if rc != 0:
        eprint(f"[ERROR] HMC lsyscfg failed rc={rc} err={err.strip()}")
        return []
    return [line.strip() for line in out if line.strip()]


def discover_fc(hmc: str, user: str, pwd: str, msys: str) -> List[Tuple[str, List[str]]]:
    """
    Returns list of (lpar_name, [wwpn, ...]) on a given managed system
    """
    # -F "lpar_name;wwpns" returns lines like:
    # mylpar;500143801A2B3C4D,500143801A2B3C4E
    cmd = f'lshwres -r virtualio --rsubtype fc --level lpar -m {msys} -F "lpar_name;wwpns"'
    rc, out, err = ssh_run(hmc, user, pwd, cmd)
    if rc != 0:
        eprint(f"[WARN] HMC lshwres FC failed on {msys} rc={rc} err={err.strip()}")
        return []
    results: List[Tuple[str, List[str]]] = []
    for line in out:
        if ";" not in line:
            continue
        lpar, wwpns_csv = line.split(";", 1)
        wwpns = [normalize_wwpn(x) for x in wwpns_csv.split(",") if x.strip()]
        wwpns = list(dict.fromkeys(wwpns))  # dedupe keep order
        results.append((lpar, wwpns))
    return results


def discover_mac(hmc: str, user: str, pwd: str, msys: str) -> List[Tuple[str, List[str]]]:
    """
    Returns list of (lpar_name, [mac, ...]) by parsing virtual ethernet adapters
    Some HMC levels: lshwres -r virtualio --rsubtype eth --level lpar -m <msys> -F "lpar_name;mac_addr"
    Other levels: might expose multiple adapters; adjust -F accordingly if needed.
    """
    cmd = f'lshwres -r virtualio --rsubtype eth --level lpar -m {msys} -F "lpar_name;mac_addr"'
    rc, out, err = ssh_run(hmc, user, pwd, cmd)
    if rc != 0:
        eprint(f"[INFO] HMC lshwres ETH failed on {msys} rc={rc} err={err.strip()} (MAC discovery optional)")
        return []
    results: List[Tuple[str, List[str]]] = []
    for line in out:
        if ";" not in line:
            continue
        lpar, macs_csv = line.split(";", 1)
        macs = [normalize_mac(x) for x in re.split(r"[,\s]+", macs_csv) if x.strip()]
        macs = list(dict.fromkeys(macs))
        results.append((lpar, macs))
    return results


def discover_lpars(hmc: str, user: str, pwd: str,
                   managed_system: Optional[str],
                   exclude: Set[str]) -> Dict[str, Dict[str, List[str]]]:
    """
    Return mapping:
      { lpar_name: { "wwpns": [...], "macs": [...] } }
    """
    systems = [managed_system] if managed_system else list_managed_systems(hmc, user, pwd)
    inventory: Dict[str, Dict[str, List[str]]] = {}
    for msys in systems:
        fc = discover_fc(hmc, user, pwd, msys)
        mac = discover_mac(hmc, user, pwd, msys)
        mac_map = {l: v for l, v in mac}
        for lpar, wwpns in fc:
            if lpar in exclude:
                continue
            inventory.setdefault(lpar, {})
            inventory[lpar]["wwpns"] = wwpns
            inventory[lpar]["macs"] = mac_map.get(lpar, [])
    return inventory


# -----------------------------
# Pure Storage update
# -----------------------------

def pure_sdk_update(array: str, user: str, password: str,
                    host_name: str, wwpns: List[str], verify_ssl: bool = True) -> None:
    """
    Update or create host and set its physical ports (WWPNs) using Pure SDK.
    Idempotent: only adds missing WWPNs.
    """
    if not HAVE_PURE_SDK:
        raise RuntimeError("purestorage SDK not available")

    fa = purestorage.FlashArray(array, api_token=password if user.lower() == "token" else None,
                                username=None if user.lower() == "token" else user,
                                password=None if user.lower() != "token" else None,
                                verify_https=verify_ssl)

    try:
        try:
            host = fa.get_host(host_name)
        except purestorage.PureHTTPError:
            host = fa.create_host(host_name)
        current = [p.get("wwn") for p in fa.get_host(host_name).get("ports", []) if p.get("wwn")]
        to_add = [w for w in wwpns if w not in current]
        if to_add:
            fa.set_host(host_name, add_wwnlist=to_add)
    finally:
        try:
            fa.invalidate_cookie()
        except Exception:
            pass


def pure_rest_update(array: str, user: str, password: str,
                     host_name: str, wwpns: List[str], verify_ssl: bool = True) -> None:
    """
    Minimal REST fallback for Pure if SDK is absent.
    Requires user/password (or API token) and array reachable over HTTPS.
    This is intentionally simple and may need to be adapted to your array's API version.
    """
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    # NOTE: For production, prefer the official SDK. REST here is placeholder/minimal.
    # You should implement proper auth (API token headers) and endpoints per your FA version.
    raise NotImplementedError("Pure REST fallback not implemented. Install 'purestorage' SDK or add REST calls.")


def update_pure_host(array: str, user: str, password: str,
                     host_name: str, wwpns: List[str],
                     verify_ssl: bool, dry_run: bool) -> None:
    wwpns = list(dict.fromkeys(wwpns))  # dedupe
    msg = f"[PURE] host={host_name} wwpns={','.join(wwpns)}"
    if dry_run:
        print(f"[DRY-RUN] {msg}")
        return
    if HAVE_PURE_SDK:
        pure_sdk_update(array, user, password, host_name, wwpns, verify_ssl=verify_ssl)
        print(f"[OK] {msg}")
    else:
        pure_rest_update(array, user, password, host_name, wwpns, verify_ssl=verify_ssl)


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Discover LPAR WWPNs/MACs from HMC and update Pure Storage hosts (idempotent).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-H", "--hmc", required=True, help="HMC hostname or IP")
    p.add_argument("-u", "--hmc-user", required=True, help="HMC username")
    p.add_argument("-w", "--hmc-password", required=True, help="HMC password")
    p.add_argument("-m", "--managed-system", help="Limit to one managed system (optional)")
    p.add_argument("--exclude-lpar", default="", help="Comma-separated list of LPAR names to skip")
    p.add_argument("-P", "--purestorage", required=True, help="Pure Storage management IP/FQDN")
    p.add_argument("-s", "--pure-user", required=True,
                   help="Pure username, or 'token' if using API token in --pure-password")
    p.add_argument("-p", "--pure-password", required=True, help="Pure password or API token")
    p.add_argument("--host-prefix", default="", help="Optional prefix to build Pure host names (prefix + LPAR)")
    p.add_argument("--verify-ssl", action="store_true", help="Verify Pure HTTPS certificate")
    p.add_argument("--no-verify-ssl", dest="verify_ssl", action="store_false", help="Disable HTTPS verification (not recommended)")
    p.add_argument("--apply", action="store_true", help="Apply changes to Pure (default is dry-run)")
    p.add_argument("--json", action="store_true", help="Print inventory as JSON at the end")
    p.set_defaults(verify_ssl=True)
    return p.parse_args()


# -----------------------------
# Main
# -----------------------------

def main() -> int:
    args = parse_args()
    excluded = {x.strip() for x in args.exclude_lpar.split(",") if x.strip()}
    dry_run = not args.apply

    print(f"[INFO] Connecting HMC={args.hmc} user={args.hmc_user}  systems={args.managed_system or 'ALL'}  dry_run={dry_run}")

    inv = discover_lpars(args.hmc, args.hmc_user, args.hmc_password, args.managed_system, excluded)

    if not inv:
        eprint("[ERROR] No LPARs discovered. Check HMC credentials/filters.")
        return 2

    # Report + Pure update
    for lpar, data in sorted(inv.items()):
        wwpns = data.get("wwpns", [])
        macs = data.get("macs", [])
        host_name = f"{args.host_prefix}{lpar}"
        print(f"[LPAR] {lpar}  WWPNs={','.join(wwpns) or '-'}  MACs={','.join(macs) or '-'}  → host={host_name}")

        if wwpns:
            try:
                update_pure_host(args.purestorage, args.pure_user, args.pure_password,
                                 host_name, wwpns, verify_ssl=args.verify_ssl, dry_run=dry_run)
            except NotImplementedError as nie:
                eprint(f"[WARN] {nie}")
            except Exception as ex:
                eprint(f"[ERROR] Pure update failed for host={host_name} :: {ex}")

    if args.json:
        print(json.dumps(inv, indent=2, ensure_ascii=False))

    print("[DONE]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
