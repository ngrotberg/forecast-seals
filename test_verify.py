# test_verify.py: tests for verify.py on a synthetic seal and synthetic rows.
# Run with: python -m unittest test_verify.py
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import verify

SEALED_AT = "2026-09-07T17:53:15.359104+00:00"

# Two rows whose digest was computed by the ledger's own seal code (prior_ledger.seal.digest)
# on 2026-09-23. They cover float repr (0.30000000000000004, 1e-05), a non-ASCII label, a
# missing field (the second row has no commit_hash) and fields outside the seal.
REFERENCE_ROWS = [
    {
        "prediction_id": "b2",
        "question_id": "q-happiness",
        "method_id": "ensemble_mean@0.3.0",
        "cut": "education=college",
        "distribution": {
            "labels": ["café", "not"],
            "probs": [0.30000000000000004, 0.7],
            "intervals": {"0.80": {"level": 0.8, "lower": [1e-05, 0.6], "upper": [0.4, 0.99999]}},
            "n_effective": 357.6594563568708,
        },
        "made_at": "2026-09-06T17:22:20.623858+00:00",
        "commit_hash": "c" * 64,
        "status": "open",
        "provenance": {"ignored": True},
        "tenant": "public",
    },
    {
        "prediction_id": "a1",
        "question_id": "q-happiness",
        "method_id": "carry_forward@0.1.0",
        "cut": "total",
        "distribution": {"labels": ["yes", "no"], "probs": [0.1, 0.9], "intervals": {}, "n_effective": None},
        "made_at": "2026-09-02T21:50:43.528147+00:00",
        "status": "void",
    },
]
REFERENCE_SHA256 = "ed1fc87fdc8550fb3d69b0f1f2470743cb02d5ad43bc479a0d48997850facf14"


def question(qid: str, item: str, source: str, wave: str) -> dict:
    return {
        "question_id": qid,
        "item_id": item,
        "resolution": {"source": source, "wave": wave, "item_id": item, "kind": "survey_wave"},
    }


def row(pid: str, qid: str, method: str, made_at: str, p: float = 0.4, tenant: str = "public") -> dict:
    return {
        "prediction_id": pid,
        "question_id": qid,
        "method_id": method,
        "cut": "total",
        "distribution": {"labels": ["a", "b"], "probs": [p, 1 - p], "intervals": {}, "n_effective": None},
        "made_at": made_at,
        "commit_hash": hashlib.sha256(pid.encode()).hexdigest(),
        "status": "open",
        "tenant": tenant,
        "population_version": "frame:2023",
    }


QUESTIONS = [
    question("q1", "happiness", "gss", "2026"),
    question("q2", "trust", "gss", "2026"),
    question("q3", "turnout", "ces", "2026"),
]
EARLY = "2026-09-06T10:00:00+00:00"
ROWS = [
    row("p1", "q1", "carry_forward@0.1.0", EARLY),
    row("p2", "q1", "ensemble_mean@0.3.0", EARLY),
    row("p3", "q2", "carry_forward@0.1.0", EARLY),
    row("p4", "q2", "ensemble_mean@0.3.0", "2026-09-07T10:53:15.359104-07:00"),  # the bound, exactly
    row("p5", "q3", "carry_forward@0.1.0", EARLY),  # another wave
    row("p6", "q1", "ensemble_mean@0.3.0", EARLY, tenant="backtest"),  # another tenant
    row("p7", "q1", "ensemble_mean@0.4.0", "2026-09-20T00:00:00+00:00"),  # after the seal
]


def make_seal(rows: list[dict], questions: list[dict], source: str = "gss", wave: str = "2026") -> dict:
    """A seal built the way the ledger builds one, from rows already selected for the wave."""
    covered, _after, _bad = verify.split_at(rows, SEALED_AT)
    items = {q["question_id"]: q["item_id"] for q in questions}
    methods: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for r in covered:
        methods[r["method_id"]] = methods.get(r["method_id"], 0) + 1
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    names = sorted({items[r["question_id"]] for r in covered})
    return {
        "protocol": "forecast-seal-1",
        "source": source,
        "wave": wave,
        "tenant": "public",
        "sealed_at": SEALED_AT,
        "code_commit": "0" * 40,
        "n_predictions": len(covered),
        "n_by_status": dict(sorted(statuses.items())),
        "n_items": len(names),
        "items": names,
        "methods": dict(sorted(methods.items())),
        "sealed_fields": list(verify.SEALED_FIELDS),
        "predictions_sha256": verify.digest(covered),
    }


GSS_ROWS = [r for r in ROWS if r["prediction_id"] in ("p1", "p2", "p3", "p4")]
SEAL = make_seal(GSS_ROWS, QUESTIONS)


def document(rows: list[dict]) -> dict:
    return {"export_version": 2, "tenant": "public", "questions": QUESTIONS, "predictions": rows}


def varuint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def varbytes(b: bytes) -> bytes:
    return varuint(len(b)) + b


class Workspace:
    """A temporary folder holding a seal file and whatever row files a test writes."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def write(self, name: str, content: str | bytes) -> str:
        path = self.dir / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return str(path)

    def seal(self, seal: dict, name: str = "gss-2026.json") -> str:
        return self.write(name, verify.canonical_json(seal) + "\n")

    def run(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = verify.main(list(args))
        return code, out.getvalue()

    def close(self) -> None:
        self._tmp.cleanup()


class DigestTest(unittest.TestCase):
    def test_matches_the_ledgers_own_digest(self):
        self.assertEqual(verify.digest(REFERENCE_ROWS), REFERENCE_SHA256)

    def test_does_not_depend_on_row_order(self):
        self.assertEqual(verify.digest(list(reversed(REFERENCE_ROWS))), REFERENCE_SHA256)

    def test_survives_a_json_round_trip(self):
        rows = json.loads(json.dumps(REFERENCE_ROWS))
        self.assertEqual(verify.digest(rows), REFERENCE_SHA256)

    def test_the_bound_is_inclusive_and_zone_aware(self):
        covered, after, bad = verify.split_at(ROWS, SEALED_AT)
        self.assertIn("p4", {r["prediction_id"] for r in covered})
        self.assertEqual([r["prediction_id"] for r in after], ["p7"])
        self.assertEqual(bad, [])


class StructureTest(unittest.TestCase):
    def check(self, seal: dict) -> list[str]:
        raw = (verify.canonical_json(seal) + "\n").encode()
        return verify.check_structure(seal, raw)[0]

    def test_a_good_seal_has_no_problems(self):
        self.assertEqual(self.check(SEAL), [])

    def test_each_broken_field_is_named(self):
        cases = {
            "protocol": ("forecast-seal-2", "protocol"),
            "sealed_fields": (["prediction_id"], "sealed_fields"),
            "n_predictions": (0, "n_predictions"),
            "predictions_sha256": ("ABC", "predictions_sha256"),
            "methods": ({"x": 1}, "methods sums"),
            "sealed_at": ("yesterday", "sealed_at"),
            "items": (["b", "a"], "items"),
        }
        for key, (value, expected) in cases.items():
            with self.subTest(key=key):
                seal = dict(SEAL, **{key: value})
                self.assertTrue(any(expected in p for p in self.check(seal)), self.check(seal))

    def test_malformed_seal_exits_2_without_a_row_check(self):
        ws = Workspace()
        try:
            path = ws.seal(dict(SEAL, n_predictions=0))
            code, out = ws.run(path, ws.write("ledger.json", json.dumps(document(ROWS))))
            self.assertEqual(code, 2)
            self.assertIn("malformed", out)
            self.assertNotIn("recomputed", out)
        finally:
            ws.close()

    def test_no_rows_says_where_they_will_be_published(self):
        ws = Workspace()
        try:
            code, out = ws.run(ws.seal(SEAL))
            self.assertEqual(code, 0)
            self.assertIn("structure: ok", out)
            self.assertIn("byte for byte", out)
            self.assertIn("rows: not checked", out)
            self.assertIn("ledger-gss-2026.json", out)
        finally:
            ws.close()


class RowCheckTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.seal = self.ws.seal(SEAL)

    def tearDown(self):
        self.ws.close()

    def run_doc(self, rows: list[dict]) -> tuple[int, str]:
        return self.ws.run(self.seal, self.ws.write("ledger.json", json.dumps(document(rows))))

    def test_document_ok_and_later_rows_reported(self):
        code, out = self.run_doc(ROWS)
        self.assertEqual(code, 0, out)
        self.assertIn("result: ok", out)
        self.assertIn("rows made after sealed_at: 1 (ensemble_mean@0.4.0 1", out)

    def test_a_changed_distribution_is_a_mismatch(self):
        rows = copy.deepcopy(ROWS)
        rows[1]["distribution"]["probs"] = [0.4000000001, 0.5999999999]
        code, out = self.run_doc(rows)
        self.assertEqual(code, 1)
        self.assertIn("MISMATCH: the row count and every per-method count match", out)

    def test_status_and_provenance_do_not_matter(self):
        rows = copy.deepcopy(ROWS)
        for r in rows:
            r["status"] = "resolved"
            r["provenance"] = {"diagnostics": {"new_key": 1}}
        code, out = self.run_doc(rows)
        self.assertEqual(code, 0, out)

    def test_a_missing_row_names_its_method(self):
        rows = [r for r in ROWS if r["prediction_id"] != "p3"]
        code, out = self.run_doc(rows)
        self.assertEqual(code, 1)
        self.assertIn("first difference: carry_forward@0.1.0 has 1 here and 2 in the seal", out)

    def test_a_backdated_row_breaks_the_seal(self):
        rows = copy.deepcopy(ROWS) + [row("p8", "q2", "carry_forward@0.1.0", EARLY)]
        code, out = self.run_doc(rows)
        self.assertEqual(code, 1)
        self.assertIn("5 rows made by sealed_at, the seal says 4", out)

    def test_a_mangled_made_at_fails_closed(self):
        rows = copy.deepcopy(ROWS)
        rows[0]["made_at"] = "last week"
        code, out = self.run_doc(rows)
        self.assertEqual(code, 1)
        self.assertIn("made_at does not parse: 1", out)

    def test_no_rows_for_the_wave_is_a_mismatch(self):
        code, out = self.run_doc([r for r in ROWS if r["prediction_id"] == "p5"])
        self.assertEqual(code, 1)
        self.assertIn("no public rows for gss 2026", out)

    def test_event_log_replay(self):
        events = [{"id": 1, "kind": "question_registered", "payload": q} for q in QUESTIONS]
        for i, r in enumerate(ROWS, 10):
            events.append({"id": i, "kind": "prediction_made", "payload": r})
            events.append({"id": 100 + i, "kind": "voided", "payload": {"prediction_id": r["prediction_id"]}})
        path = self.ws.write("public-events.jsonl", "".join(json.dumps(e) + "\n" for e in events))
        code, out = self.ws.run(self.seal, path)
        self.assertEqual(code, 0, out)
        self.assertIn("event log", out)

    def test_sharded_index_and_wave_files(self):
        gss = [r for r in ROWS if r["question_id"] in ("q1", "q2")]
        ces = [r for r in ROWS if r["question_id"] == "q3"]
        shard_gss = self.ws.write(
            "ledger-gss-2026.json",
            json.dumps({"source": "gss", "wave": "2026", "tenant": "public", "predictions": gss}),
        )
        shard_ces = self.ws.write(
            "ledger-ces-2026.json",
            json.dumps({"source": "ces", "wave": "2026", "tenant": "public", "predictions": ces}),
        )
        index = dict(document([]), shards=[
            {"file": "ledger-ces-2026.json", "source": "ces", "wave": "2026", "n_predictions": len(ces)},
            {"file": "ledger-gss-2026.json", "source": "gss", "wave": "2026", "n_predictions": len(gss)},
        ])
        index_path = self.ws.write("index.json", json.dumps(index))
        code, out = self.ws.run(self.seal, index_path)
        self.assertEqual(code, 0, out)
        code, out = self.ws.run(self.seal, shard_gss)
        self.assertEqual(code, 0, out)
        code, out = self.ws.run(self.seal, shard_ces)  # another wave's file says nothing here
        self.assertEqual(code, 0, out)
        self.assertIn("rows: not checked", out)
        Path(shard_gss).unlink()
        code, out = self.ws.run(self.seal, index_path)
        self.assertEqual(code, 2)
        self.assertIn("download every file the index lists", out)


class ProofTest(unittest.TestCase):
    def proof(self, file_bytes: bytes) -> tuple[bytes, str]:
        """A proof with one pending branch and one Bitcoin branch, and the Bitcoin
        branch's merkle root in explorer byte order."""
        file_digest = hashlib.sha256(file_bytes).digest()
        prefix = b"\x01\x02"
        pending = b"\xf0" + varbytes(b"n" * 16) + b"\x08" + b"\x00" + verify.OTS_PENDING + varbytes(
            varbytes(b"https://calendar.example")
        )
        height = varbytes(varuint(915000))
        bitcoin = b"\xf1" + varbytes(prefix) + b"\x08" + b"\x00" + verify.OTS_BITCOIN + height
        data = verify.OTS_MAGIC + b"\x01" + b"\x08" + file_digest + b"\xff" + pending + bitcoin
        root = hashlib.sha256(prefix + file_digest).digest()[::-1].hex()
        return data, root

    def test_reads_both_attestations(self):
        raw = (verify.canonical_json(SEAL) + "\n").encode()
        data, root = self.proof(raw)
        ws = Workspace()
        try:
            ws.write("gss-2026.json.ots", data)
            ok, lines = verify.describe_proof(ws.dir / "gss-2026.json.ots", raw)
            text = "\n".join(lines)
            self.assertTrue(ok, text)
            self.assertIn("commits to this file's sha256", text)
            self.assertIn("block 915,000", text)
            self.assertIn(root, text)
        finally:
            ws.close()

    def test_a_proof_of_another_file_is_flagged(self):
        data, _root = self.proof(b"something else")
        ws = Workspace()
        try:
            path = ws.seal(SEAL)
            ws.write("gss-2026.json.ots", data)
            code, out = ws.run(path)
            self.assertEqual(code, 1)
            self.assertIn("NOT this file", out)
        finally:
            ws.close()

    def test_a_truncated_proof_is_reported_not_raised(self):
        raw = (verify.canonical_json(SEAL) + "\n").encode()
        data, _root = self.proof(raw)
        ws = Workspace()
        try:
            ws.write("x.ots", data[:-3])
            ok, lines = verify.describe_proof(ws.dir / "x.ots", raw)
            self.assertFalse(ok)
            self.assertIn("could not be read", lines[0])
        finally:
            ws.close()


if __name__ == "__main__":
    unittest.main()
