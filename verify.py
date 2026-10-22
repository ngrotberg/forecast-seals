#!/usr/bin/env python3
# verify.py: check a forecast seal (protocol forecast-seal-1) against the published rows.
#
# MIT License
#
# Copyright (c) 2026 [PUBLISHER NAME]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Check a forecast seal against the published prediction rows.

    python verify.py SEAL.json [SEAL.json ...] [ROWS ...]

A seal (protocol forecast-seal-1) is a sha256 over seven fields of every prediction row
for one survey wave, taken at the moment in the seal's `sealed_at`. This script recomputes
that digest from the published rows and prints ok or the first mismatch. Standard library
only; Python 3.12 is the tested version.

SEAL is a seal file such as seals/gss-2026.json. If `<SEAL>.ots` sits beside it, the script
also reads the OpenTimestamps proof and says which file digest it commits to and whether it
carries a Bitcoin attestation yet. It does not contact Bitcoin; `ots verify` does that.

ROWS is any of:
  - ledger.json, the public ledger export (a whole document, or the index of a sharded
    export with its per-wave files ledger-<source>-<wave>.json in the same folder);
  - one per-wave file on its own, ledger-<source>-<wave>.json;
  - public-events.jsonl, the public event log, replayed here.

With no ROWS, only the seal file's own structure is checked.

The digest, exactly as the ledger computes it:
  1. take the rows whose question resolves against the seal's source and wave, under the
     seal's tenant;
  2. keep the rows with made_at at or before sealed_at (a made_at without a zone is UTC;
     one that does not parse is left out, so a sealed row with a mangled time fails);
  3. reduce each row to prediction_id, question_id, method_id, cut, distribution, made_at,
     commit_hash (a missing field is null);
  4. sort by prediction_id;
  5. serialize the list as JSON with sorted keys, no whitespace and ASCII escapes, which is
     Python's json.dumps(rows, sort_keys=True, separators=(",", ":"));
  6. sha256 the UTF-8 bytes.
The seal is ok when that digest equals predictions_sha256 and the number of rows kept equals
n_predictions (which must be above zero). Rows made after sealed_at are outside the seal and
cannot break it; they are counted and reported.

Exit status: 0 when every check run passed; 1 when a row check found a mismatch or a proof
beside a seal commits to a different file; 2 when an input could not be read or a seal file
is malformed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTOCOL = "forecast-seal-1"
SEALED_FIELDS = (
    "prediction_id",
    "question_id",
    "method_id",
    "cut",
    "distribution",
    "made_at",
    "commit_hash",
)
ROWS_LOCATION = (
    "The sealed rows are not in this repository. They will be published with the public "
    "ledger page at [LEDGER PAGE URL, pending] as ledger.json plus one file per wave "
    "(ledger-gss-2026.json, ledger-ces-2026.json), and archived with this repository's "
    "tagged release. Put ledger.json and its wave files in one folder, then run:\n"
    "      python verify.py {seal} path/to/ledger.json"
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


# --- the digest -------------------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sealed_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        ({k: r.get(k) for k in SEALED_FIELDS} for r in rows),
        key=lambda r: str(r["prediction_id"]),
    )


def digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json(sealed_rows(rows)).encode("utf-8")).hexdigest()


def instant(value: Any) -> datetime:
    moment = datetime.fromisoformat(str(value))
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def split_at(rows: list[dict[str, Any]], sealed_at: str) -> tuple[list, list, list]:
    """(made at or before sealed_at, made after it, made_at does not parse)."""
    bound = instant(sealed_at)
    covered, after, unparsable = [], [], []
    for row in rows:
        try:
            moment = instant(row.get("made_at"))
        except (TypeError, ValueError):
            unparsable.append(row)
            continue
        (covered if moment <= bound else after).append(row)
    return covered, after, unparsable


# --- the seal file ----------------------------------------------------------------------


def check_structure(seal: Any, raw: bytes) -> tuple[list[str], list[str]]:
    """(problems, notes) for a seal file. Any problem means the row check is not run."""
    if not isinstance(seal, dict):
        return ["the file is not a JSON object"], []
    problems: list[str] = []
    notes: list[str] = []

    def count(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    if seal.get("protocol") != PROTOCOL:
        problems.append(
            f"protocol is {seal.get('protocol')!r}; this script implements {PROTOCOL} only"
        )
    if seal.get("sealed_fields") != list(SEALED_FIELDS):
        problems.append(f"sealed_fields is not the {PROTOCOL} list {list(SEALED_FIELDS)}")
    for key in ("source", "wave", "tenant"):
        if not isinstance(seal.get(key), str) or not seal.get(key):
            problems.append(f"{key} is missing or not a string")
    try:
        instant(seal.get("sealed_at"))
    except (TypeError, ValueError):
        problems.append(f"sealed_at {seal.get('sealed_at')!r} is not an ISO-8601 time")
    n = seal.get("n_predictions")
    if not count(n) or n <= 0:
        problems.append(
            f"n_predictions is {n!r}; a seal of no rows is never valid, because the digest "
            "of an empty list matches any ledger without rows for the wave"
        )
    if not isinstance(seal.get("predictions_sha256"), str) or not _HEX64.match(
        seal["predictions_sha256"]
    ):
        problems.append("predictions_sha256 is not 64 lowercase hex characters")
    for key in ("methods", "n_by_status"):
        table = seal.get(key)
        if not isinstance(table, dict) or not all(count(v) for v in table.values()):
            problems.append(f"{key} is missing or not a table of counts")
        elif count(n) and sum(table.values()) != n:
            problems.append(f"{key} sums to {sum(table.values()):,}, not n_predictions {n:,}")
    items = seal.get("items")
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        problems.append("items is missing or not a list of strings")
    elif items != sorted(set(items)):
        problems.append("items is not sorted and unique")
    elif not count(seal.get("n_items")) or not len(items) <= seal["n_items"] <= len(items) + 1:
        problems.append(f"n_items {seal.get('n_items')!r} does not match the {len(items)} items")
    if seal.get("code_commit") is not None and not isinstance(seal.get("code_commit"), str):
        problems.append("code_commit is neither a string nor null")
    if raw == (canonical_json(seal) + "\n").encode("utf-8"):
        notes.append("the file is byte for byte the canonical form the ledger writes")
    else:
        notes.append(
            "the file is not in the ledger's canonical form (the digest check is unaffected; "
            "a timestamp proof covers the bytes as they are)"
        )
    return problems, notes


# --- the OpenTimestamps proof beside it -------------------------------------------------

OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
OTS_PENDING = bytes.fromhex("83dfe30d2ef90c8e")
OTS_BITCOIN = bytes.fromhex("0588960d73d71901")
# Unary hash operations: tag -> (hashlib name, digest length).
OTS_HASHES = {0x08: ("sha256", 32), 0x02: ("sha1", 20), 0x03: ("ripemd160", 20), 0x67: ("keccak256", 32)}


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data, self.pos = data, 0

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError("the proof ends early")
        out = self.data[self.pos : self.pos + n]
        self.pos += n
        return out

    def varuint(self) -> int:
        value = shift = 0
        while True:
            byte = self.take(1)[0]
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value
            shift += 7

    def varbytes(self, limit: int = 8192) -> bytes:
        n = self.varuint()
        if n > limit:
            raise ValueError(f"a field of {n} bytes is longer than the format allows")
        return self.take(n)


def _hash(tag: int, msg: bytes | None) -> bytes | None:
    if msg is None:
        return None
    try:
        return hashlib.new(OTS_HASHES[tag][0], msg).digest()
    except ValueError:  # keccak256 is not in hashlib; some builds lack ripemd160
        return None


def _walk(r: _Reader, msg: bytes | None, found: list, depth: int = 0) -> None:
    """Follow every branch of a timestamp, applying each operation to the message, and
    collect (kind, detail, message) for every attestation at a leaf."""
    if depth > 256:
        raise ValueError("the proof nests too deeply")

    def one(tag: int) -> None:
        if tag == 0x00:
            kind = r.take(8)
            payload = _Reader(r.varbytes())
            if kind == OTS_PENDING:
                found.append(("pending", payload.varbytes().decode("utf-8", "replace"), msg))
            elif kind == OTS_BITCOIN:
                found.append(("bitcoin", payload.varuint(), msg))
            else:
                found.append(("other", kind.hex(), msg))
            return
        if tag in (0xF0, 0xF1):  # append, prepend
            arg = r.varbytes(4096)
            nxt = None if msg is None else (msg + arg if tag == 0xF0 else arg + msg)
        elif tag in OTS_HASHES:
            nxt = _hash(tag, msg)
        elif tag == 0xF2:  # reverse
            nxt = None if msg is None else msg[::-1]
        elif tag == 0xF3:  # hexlify
            nxt = None if msg is None else msg.hex().encode("ascii")
        else:
            raise ValueError(f"unknown operation 0x{tag:02x}")
        _walk(r, nxt, found, depth + 1)

    tag = r.take(1)[0]
    while tag == 0xFF:  # a fork: one more branch follows before the last one
        one(r.take(1)[0])
        tag = r.take(1)[0]
    one(tag)


def read_proof(data: bytes) -> tuple[str, bytes, list]:
    """(file hash name, the file digest the proof commits to, attestations)."""
    r = _Reader(data)
    if r.take(len(OTS_MAGIC)) != OTS_MAGIC:
        raise ValueError("not an OpenTimestamps proof")
    version = r.varuint()
    if version != 1:
        raise ValueError(f"proof format version {version} is not supported")
    tag = r.take(1)[0]
    if tag not in OTS_HASHES:
        raise ValueError(f"unknown file hash operation 0x{tag:02x}")
    name, length = OTS_HASHES[tag]
    file_digest = r.take(length)
    found: list = []
    _walk(r, file_digest, found)
    if r.pos != len(data):
        raise ValueError(f"{len(data) - r.pos} unread bytes after the timestamp")
    return name, file_digest, found


def describe_proof(ots_path: Path, raw: bytes) -> tuple[bool, list[str]]:
    """(the proof commits to these bytes, lines to print)."""
    try:
        name, file_digest, found = read_proof(ots_path.read_bytes())
    except (OSError, ValueError) as exc:
        return False, [f"proof {ots_path.name}: could not be read: {exc}"]
    ours = hashlib.new(name, raw).digest()
    if file_digest != ours:
        return False, [
            f"proof {ots_path.name}: commits to {name} {file_digest.hex()}, which is NOT this "
            f"file ({ours.hex()})"
        ]
    lines = [f"proof {ots_path.name}: commits to this file's {name}"]
    bitcoin = sorted({(d, m) for k, d, m in found if k == "bitcoin"}, key=lambda x: x[0])
    for height, msg in bitcoin:
        root = "not computed (an operation this Python lacks)" if msg is None else msg[::-1].hex()
        lines.append(
            f"  Bitcoin attestation: block {height:,}; merkle root {root} (byte order as block "
            "explorers show it). That block's time is the independent date. `ots verify` "
            "checks this against a Bitcoin node; without one, compare the root with the block."
        )
    if not bitcoin:
        calendars = sorted({d for k, d, _m in found if k == "pending"})
        lines.append(
            "  no Bitcoin attestation yet: pending at "
            + (", ".join(calendars) or "no calendar")
            + ". `ots upgrade` adds it once a calendar's transaction is confirmed."
        )
    others = sorted({d for k, d, _m in found if k == "other"})
    if others:
        lines.append(f"  other attestation types, not read here: {', '.join(others)}")
    return True, lines


# --- the published rows -----------------------------------------------------------------


class InputError(Exception):
    """A file that cannot be read as a seal or as published rows."""


class Selection:
    def __init__(self, rows: list[dict[str, Any]], items: set[str] | None, what: str) -> None:
        self.rows, self.items, self.what = rows, items, what


class RowSource:
    """One ROWS argument: a public document, a sharded index, a wave file or an event log."""

    def __init__(self, path: Path, data: Any = None) -> None:
        self.path = path
        if data is None:
            self.kind, self.data = "events", self._replay(path)
        elif isinstance(data, dict) and isinstance(data.get("predictions"), list):
            if "questions" in data:
                self.kind = "index" if data.get("shards") else "document"
            elif "source" in data and "wave" in data:
                self.kind = "shard"
            else:
                raise InputError(f"{path}: has predictions but neither questions nor a wave")
            self.data = data
        else:
            raise InputError(
                f"{path}: not a seal, a public ledger export, a wave file or an events file"
            )

    @staticmethod
    def _replay(path: Path) -> dict[str, Any]:
        """The questions and the final state of each prediction's sealed fields, from the
        log. A later prediction_made for the same id replaces the earlier one, as a replay
        into the ledger does; other event kinds do not touch the sealed fields."""
        questions: dict[str, Any] = {}
        predictions: dict[str, Any] = {}
        n = 0
        try:
            with path.open(encoding="utf-8") as fh:
                for number, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise InputError(f"{path}: line {number} is not JSON ({exc})") from exc
                    n += 1
                    payload = event.get("payload") or {}
                    if event.get("kind") == "question_registered":
                        questions[str(payload.get("question_id"))] = payload
                    elif event.get("kind") == "prediction_made":
                        predictions[str(payload.get("prediction_id"))] = payload
        except OSError as exc:
            raise InputError(f"{path}: {exc}") from exc
        return {"questions": questions, "predictions": list(predictions.values()), "n": n}

    def describe(self) -> str:
        if self.kind == "events":
            return f"{self.path.name} (event log: {self.data['n']:,} events)"
        if self.kind == "shard":
            return f"{self.path.name} (wave file: {self.data['source']} {self.data['wave']})"
        if self.kind == "index":
            return f"{self.path.name} (sharded export index)"
        return f"{self.path.name} (public export: {len(self.data['predictions']):,} rows)"

    def select(self, source: str, wave: str, tenant: str) -> Selection | None:
        """The rows this file holds for the wave, or None when the file is a wave file
        for a different wave (it says nothing about this seal)."""
        if self.kind == "shard":
            if (str(self.data["source"]), str(self.data["wave"])) != (source, wave):
                return None
            default = self.data.get("tenant")
            rows = [r for r in self.data["predictions"] if r.get("tenant", default) == tenant]
            return Selection(rows, None, "the wave file (it carries no questions)")

        if self.kind == "events":
            questions = self.data["questions"]
            candidates = [r for r in self.data["predictions"] if r.get("tenant") == tenant]
        else:
            questions = {str(q.get("question_id")): q for q in self.data["questions"]}
            default = self.data.get("tenant")
            if self.kind == "index":
                candidates = self._shard_rows(source, wave)
            else:
                candidates = self.data["predictions"]
            candidates = [r for r in candidates if r.get("tenant", default) == tenant]

        rows: list[dict[str, Any]] = []
        items: set[str] = set()
        for row in candidates:
            question = row.get("question") or questions.get(str(row.get("question_id"))) or {}
            resolution = question.get("resolution") or {}
            if resolution.get("source") == source and str(resolution.get("wave")) == wave:
                rows.append(row)
                items.add(str(question.get("item_id", "")))
        return Selection(rows, {i for i in items if i}, "question resolution")

    def _shard_rows(self, source: str, wave: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for shard in self.data.get("shards") or []:
            if (str(shard.get("source")), str(shard.get("wave"))) != (source, wave):
                continue
            shard_path = self.path.parent / str(shard.get("file"))
            try:
                loaded = json.loads(shard_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise InputError(
                    f"{self.path.name} names {shard.get('file')}, which could not be read "
                    f"beside it ({exc}); download every file the index lists"
                ) from exc
            got = loaded.get("predictions", [])
            if "n_predictions" in shard and len(got) != shard["n_predictions"]:
                raise InputError(
                    f"{shard.get('file')} holds {len(got):,} rows; the index says "
                    f"{shard['n_predictions']:,}"
                )
            rows.extend(got)
        return rows


def load(path: Path) -> tuple[str, Any, bytes]:
    """('seal', seal, raw bytes) or ('rows', RowSource, b'')."""
    if path.suffix == ".ots":
        raise InputError(f"{path}: pass the seal's .json; its .ots proof is read from beside it")
    if path.suffix == ".jsonl":
        return "rows", RowSource(path), b""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise InputError(f"{path}: not UTF-8 text ({exc})") from exc
    except json.JSONDecodeError as exc:
        if exc.msg == "Extra data":  # one JSON value per line: an event log
            return "rows", RowSource(path), b""
        raise InputError(f"{path}: not JSON ({exc})") from exc
    if isinstance(data, dict) and ("predictions_sha256" in data or "protocol" in data):
        return "seal", data, raw
    return "rows", RowSource(path, data), b""


# --- the check --------------------------------------------------------------------------


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[str(row.get(key))] = out.get(str(row.get(key)), 0) + 1
    return out


def first_mismatch(seal: dict[str, Any], sel: Selection, covered: list, got: str) -> str | None:
    n = seal["n_predictions"]
    if not sel.rows:
        return f"no {seal['tenant']} rows for {seal['source']} {seal['wave']} in this file"
    if len(covered) != n:
        found = _counts(covered, "method_id")
        for method in sorted(set(found) | set(seal["methods"])):
            a, b = found.get(method, 0), seal["methods"].get(method, 0)
            if a != b:
                return (
                    f"{len(covered):,} rows made by sealed_at, the seal says {n:,}; first "
                    f"difference: {method} has {a:,} here and {b:,} in the seal"
                )
        return f"{len(covered):,} rows made by sealed_at, the seal says {n:,}"
    if sel.items is not None and sel.items != set(seal["items"]):
        missing = sorted(set(seal["items"]) - sel.items)
        extra = sorted(sel.items - set(seal["items"]))
        return f"the items differ: sealed but absent {missing[:5]}, present but unsealed {extra[:5]}"
    if got != seal["predictions_sha256"]:
        return (
            "the row count and every per-method count match, but the digest does not: at "
            "least one sealed field of one row differs from what was sealed"
        )
    return None


def check_rows(seal: dict[str, Any], src: RowSource, sel: Selection) -> tuple[bool, list[str]]:
    covered, after, unparsable = split_at(sel.rows, seal["sealed_at"])
    got = digest(covered)
    n = seal["n_predictions"]
    ok = n > 0 and got == seal["predictions_sha256"] and len(covered) == n
    lines = [
        f"rows from {src.describe()}: {len(sel.rows):,} for {seal['source']} {seal['wave']} "
        f"({seal['tenant']}), selected by {sel.what}",
        f"  recomputed sha256 {got}",
        f"  sealed sha256     {seal['predictions_sha256']}",
        f"  rows made by sealed_at: {len(covered):,} (sealed: {n:,})",
    ]
    if after:
        stamps = sorted(str(r.get("made_at")) for r in after)
        span = stamps[0] if stamps[0] == stamps[-1] else f"{stamps[0]} to {stamps[-1]}"
        by_method = ", ".join(f"{m} {c:,}" for m, c in sorted(_counts(after, "method_id").items()))
        lines.append(
            f"  rows made after sealed_at: {len(after):,} ({by_method}; made {span}). They "
            "are outside the seal and cannot break it."
        )
    else:
        lines.append("  rows made after sealed_at: 0")
    if unparsable:
        lines.append(
            f"  rows whose made_at does not parse: {len(unparsable):,}. They are left out, so "
            "a sealed row with a mangled time fails the check."
        )
        if sys.version_info < (3, 11):
            lines.append(
                "  (Python before 3.11 parses fewer ISO-8601 forms; rerun with 3.11 or later.)"
            )
    mismatch = None if ok else first_mismatch(seal, sel, covered, got)
    if not ok and mismatch is None:
        mismatch = "the digest or the row count does not match"
    lines.append("  result: ok" if ok else f"  result: MISMATCH: {mismatch}")
    return ok, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify.py",
        description="Check forecast seals (forecast-seal-1) against published rows.",
        epilog="With no ROWS, only each seal file's own structure is checked.",
    )
    parser.add_argument("files", nargs="+", metavar="FILE", help="seal files, then row files")
    args = parser.parse_args(argv)

    seals: list[tuple[Path, dict[str, Any], bytes]] = []
    sources: list[RowSource] = []
    try:
        for name in args.files:
            kind, value, raw = load(Path(name))
            if kind == "seal":
                seals.append((Path(name), value, raw))
            else:
                sources.append(value)
    except InputError as exc:
        print(f"error: {exc}")
        return 2
    if not seals:
        print("error: no seal file given (for example seals/gss-2026.json)")
        return 2

    status = 0
    for path, seal, raw in seals:
        print(f"seal {path}")
        problems, notes = check_structure(seal, raw)
        print(f"  file sha256 {hashlib.sha256(raw).hexdigest()}")
        if problems:
            for problem in problems:
                print(f"  structure: PROBLEM: {problem}")
            print("  result: the seal file is malformed; rows were not checked")
            status = 2
            print()
            continue
        print(
            f"  structure: ok. {seal['source']} {seal['wave']}, tenant {seal['tenant']}, "
            f"sealed_at {seal['sealed_at']}, {seal['n_predictions']:,} rows over "
            f"{len(seal['items'])} items, code {seal.get('code_commit') or 'not recorded'}"
        )
        for note in notes:
            print(f"  structure: {note}")
        ots = path.with_name(path.name + ".ots")
        if ots.exists():
            proof_ok, lines = describe_proof(ots, raw)
            for line in lines:
                print(f"  {line}")
            if not proof_ok:
                status = max(status, 1)
        else:
            print(f"  no proof at {ots.name}")

        checked = False
        for src in sources:
            try:
                sel = src.select(str(seal["source"]), str(seal["wave"]), str(seal["tenant"]))
            except InputError as exc:
                print(f"  error: {exc}")
                status = 2
                continue
            if sel is None:
                continue
            checked = True
            ok, lines = check_rows(seal, src, sel)
            for line in lines:
                print(f"  {line}")
            if not ok:
                status = max(status, 1)
        if not checked:
            print("  rows: not checked, because no published rows for this wave were given.")
            print("  " + ROWS_LOCATION.format(seal=path))
        print()
    return status


if __name__ == "__main__":
    sys.exit(main())
