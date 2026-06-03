#!/usr/bin/env python3

# Copyright 2023-2026 Nils Knieling. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Fetch all available Google Cloud Organization Policy constraints via direct
REST calls to the Org Policy v2 API:

    GET https://orgpolicy.googleapis.com/v2/{parent}/constraints

For each constraint the ID, display name and description are collected.

Authentication:
    The OAuth2 access token is supplied explicitly via ``--token`` / the
    ``GCLOUD_TOKEN`` environment variable, or obtained from ``gcloud`` (a
    single call to ``gcloud auth print-access-token`` at startup). No refresh
    is performed; a typical run completes well within the token lifetime.
    The required OAuth scope is
    ``https://www.googleapis.com/auth/cloud-platform``.

Parent resource:
    The ``constraints.list`` endpoint needs a parent resource. Provide one of
    ``--organization``, ``--folder`` or ``--project`` (or the matching
    ``GCLOUD_ORGANIZATION`` / ``GCLOUD_FOLDER`` / ``GCLOUD_PROJECT`` env var).

Outputs (compatible with ``build.pl``):
    * policies.json - list of {id, name, description} objects.
    * policies.txt  - sorted constraint IDs, one per line, each wrapped in
                      double quotes.

Uses only the Python 3 standard library (no third-party dependencies and no
Google Cloud SDK / client libraries).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_ROOT = "https://orgpolicy.googleapis.com/v2"
OAUTH_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
HTTP_TIMEOUT = 30  # seconds


def get_token_from_gcloud() -> str:
    """Run ``gcloud auth print-access-token`` and return the token."""
    if shutil.which("gcloud") is None:
        raise RuntimeError(
            "gcloud not found in PATH. Install the Google Cloud SDK or "
            "pass a token via --token / GCLOUD_TOKEN."
        )
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"`gcloud auth print-access-token` failed (exit {exc.returncode}): "
            f"{exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("`gcloud auth print-access-token` timed out") from exc

    token = result.stdout.strip()
    if not token:
        raise RuntimeError("`gcloud auth print-access-token` returned an empty token")
    return token


def http_get_json(
    url: str,
    token: str,
    params: dict[str, Any] | None = None,
    *,
    max_attempts: int = 6,
) -> dict[str, Any]:
    """GET a URL with bearer auth, decode JSON, retry on 429 / 5xx / transient errors.

    Uses ``urllib.request`` from the standard library (no third-party deps,
    no Google Cloud SDK).
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    backoff = 1.0
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "gcloud-org-policies/1.0 (+stdlib-urllib)",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                # 2xx responses always reach this branch.
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status in (429, 500, 502, 503, 504) and attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(
                f"GET {url} failed: HTTP {status} {exc.reason}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            # DNS errors, connection resets, timeouts, etc.
            if attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc
        except TimeoutError as exc:
            if attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            raise RuntimeError(f"GET {url} timed out") from exc

    raise RuntimeError(f"GET {url} exhausted retries")


def list_constraints(parent: str, token: str) -> list[dict[str, Any]]:
    """List every constraint for the given parent (paginated)."""
    constraints: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        data = http_get_json(f"{API_ROOT}/{parent}/constraints", token, params=params)
        constraints.extend(data.get("constraints", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return constraints


def constraint_id(name: str) -> str:
    """Extract the short constraint ID from its full resource name."""
    # name looks like: organizations/123/constraints/compute.disableSerialPort
    return name.split("/constraints/", 1)[-1] if name else name


def resolve_parent(args: argparse.Namespace) -> str:
    """Determine the parent resource from CLI flags or environment variables."""
    organization = args.organization or os.environ.get("GCLOUD_ORGANIZATION")
    folder = args.folder or os.environ.get("GCLOUD_FOLDER")
    project = args.project or os.environ.get("GCLOUD_PROJECT")

    provided = [p for p in (organization, folder, project) if p]
    if len(provided) > 1:
        raise SystemExit(
            "Provide only one of --organization / --folder / --project."
        )
    if organization:
        return f"organizations/{organization}"
    if folder:
        return f"folders/{folder}"
    if project:
        return f"projects/{project}"
    raise SystemExit(
        "No parent resource. Pass --organization / --folder / --project or set "
        "GCLOUD_ORGANIZATION / GCLOUD_FOLDER / GCLOUD_PROJECT."
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_argument_group("parent resource (choose one)")
    scope.add_argument(
        "--organization", metavar="ORG_ID",
        help="Organization ID, e.g. 123456789012",
    )
    scope.add_argument(
        "--folder", metavar="FOLDER_ID",
        help="Folder ID, e.g. 987654321098",
    )
    scope.add_argument(
        "--project", metavar="PROJECT",
        help="Project ID or number",
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            "OAuth2 access token. If omitted, falls back to the GCLOUD_TOKEN "
            "environment variable, then to `gcloud auth print-access-token`."
        ),
    )
    parser.add_argument(
        "--policies-json",
        default="policies.json",
        help="Output path for the policies list JSON (default: policies.json).",
    )
    parser.add_argument(
        "--policies-txt",
        default="policies.txt",
        help=(
            "Output path for the sorted constraint-ID list, one per line, each "
            "wrapped in double quotes (default: policies.txt)."
        ),
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="Print the JSON to stdout instead of writing the output files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    parent = resolve_parent(args)

    # Resolve token: --token > $GCLOUD_TOKEN > `gcloud auth print-access-token`.
    token = args.token or os.environ.get("GCLOUD_TOKEN")
    if token:
        token = token.strip()
        print("Using access token from CLI/env.", flush=True)
    else:
        print("Fetching access token via `gcloud auth print-access-token`...", flush=True)
        token = get_token_from_gcloud()

    print(f"Get constraints for {parent}... Please wait...", flush=True)
    constraints = list_constraints(parent, token)

    # Reduce to just ID, name and description; sort by ID for clean diffs.
    records = sorted(
        (
            {
                "id": constraint_id(c.get("name", "")),
                "name": c.get("displayName", ""),
                "description": (c.get("description", "") or "").strip(),
            }
            for c in constraints
        ),
        key=lambda r: r["id"],
    )

    if args.stdout:
        print(json.dumps(records, indent=2, ensure_ascii=False))
        return 0

    with open(args.policies_json, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  -> {len(records)} constraints written to {args.policies_json}", flush=True)

    # Sorted, quoted constraint-ID list (mirrors the roles.txt approach used to
    # detect catalog changes in commit.sh).
    sorted_ids = sorted({r["id"] for r in records if r["id"]})
    with open(args.policies_txt, "w", encoding="utf-8") as f:
        for cid in sorted_ids:
            f.write(f'"{cid}"\n')
    print(f"  -> {len(sorted_ids)} constraint IDs written to {args.policies_txt}", flush=True)

    if not records:
        print("WARNING: no constraints returned.", file=sys.stderr)

    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
