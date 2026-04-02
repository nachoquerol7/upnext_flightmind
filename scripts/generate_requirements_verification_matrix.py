#!/usr/bin/env python3
"""
Genera docs/vnv/REQUIREMENTS_VERIFICATION_MATRIX.csv desde el texto extraído
de los PDF SUB_* (docs/vnv/_pdf_extract/) y cruza con XFAIL_INDEX.md (ARCH-* ABIERTO).
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACT_DIR = ROOT / "docs" / "vnv" / "_pdf_extract"
XFAIL_PATH = ROOT / "src" / "mission_fsm" / "docs" / "vnv" / "XFAIL_INDEX.md"
OUT_CSV = ROOT / "docs" / "vnv" / "REQUIREMENTS_VERIFICATION_MATRIX.csv"

REQ_PREFIXES = r"(?:ACAS|AIR|C2|DAA|FDIR|FSM|GCS|GPP|NAV|REPL|TEST|TRAJ|VM)"
ANCHOR_RE = re.compile(
    rf"^\s*({REQ_PREFIXES}-\d{{3}})\s.*\b(SHALL|SHOULD)\s+"
    r"(CUBIERTO|PARCIAL|XFAIL|PENDIENTE|N/A-DEMO)\s*$"
)

# TC-XXX-NNN o rangos TC-DAI-001..004
TC_RE = re.compile(r"TC-[A-Z]+-\d{3}(?:\.\.[.\d\-]*)?")

# Prefijo TC (hasta el segundo guión) -> fichero pytest SIL
TC_PREFIX_TO_TEST_FILE: dict[str, str] = {
    "TC-DAI": "src/mission_fsm/test/m5_daidalus/test_daidalus_alerts.py",
    "TC-FSM": "src/mission_fsm/test/m1_fsm_transitions/test_fsm_transitions.py",
    "TC-LOC": "src/mission_fsm/test/m4_localization/test_localization_interface.py",
    "TC-FDIR": "src/mission_fsm/test/m6_fdir/test_fdir.py",
    "TC-FAULT": "src/mission_fsm/test/m10_e2e_faults/test_e2e_faults.py",
    "TC-NAV": "src/mission_fsm/test/m7_nav2/test_nav2_interface.py",
    "TC-E2E": "src/mission_fsm/test/m9_e2e_nominal/test_e2e_nominal.py",
    "TC-TO": "src/mission_fsm/test/m2_fsm_timeouts/test_fsm_timeouts.py",
    "TC-MW": "src/mission_fsm/test/m8_middleware/test_ros2_middleware.py",
    "TC-PERF": "src/mission_fsm/test/m11_performance/test_performance.py",
    "TC-INT": "src/mission_fsm/test/m3_fsm_integrity/test_fsm_integrity.py",
    "TC-ATOM": "src/mission_fsm/test/m13_safety_atoms/test_m13_safety_atoms.py",
    "TC-REPL": "src/local_replanner/test/test_repl_rrt_stub.py",
    "TC-TRAJ": "src/trajectory_gen/test/test_trajectory_waypoints.py",
}

# Subsistema PDF (nombre fichero) -> prefijo de paquete src para rutas sueltas
SUB_IMPL_HINT: dict[str, str] = {
    "FDIR": "src/fdir/fdir/",
    "DAA": "src/",  # daidalus / icarous paths vary
    "FSM": "src/mission_fsm/mission_fsm/",
    "GPP": "src/gpp/gpp/",
    "NAV": "src/navigation_bridge/navigation_bridge/",
    "ACAS": "src/",
    "AIR": "src/",
    "C2": "src/",
    "GCS": "src/",
    "VM": "src/",
    "TRAJ": "src/trajectory_gen/trajectory_gen/",
    "REPL": "src/local_replanner/local_replanner/",
    "TEST": "testbench/",
}


def parse_xfail_arch() -> tuple[dict[str, str], set[str]]:
    """TC-XXX-NNN -> ARCH-ID para gaps ABIERTOS; y conjunto de todos los TC bajo ARCH abierto."""
    if not XFAIL_PATH.is_file():
        return {}, set()
    text = XFAIL_PATH.read_text(encoding="utf-8", errors="replace")
    tc_to_arch: dict[str, str] = {}
    open_tcs: set[str] = set()
    current_arch: str | None = None
    current_open = False
    for line in text.splitlines():
        if line.startswith("## ARCH-"):
            current_arch = line[3:].split("—", 1)[0].strip()
            current_open = False
        elif line.startswith("**Estado:**") and "ABIERTO" in line:
            current_open = True
        elif line.startswith("**Estado:**") and "CERRADO" in line:
            current_open = False
        elif current_open and line.startswith("**Tests bloqueados:**"):
            rest = line.split(":", 1)[-1]
            for m in TC_RE.finditer(rest):
                tc = m.group(0).split("..")[0].strip()
                if tc.startswith("TC-"):
                    tc_to_arch[tc] = current_arch or "ARCH-?"
                    open_tcs.add(tc)
    return tc_to_arch, open_tcs


def split_blocks(lines: list[str]) -> list[list[str]]:
    """Bloques separados por líneas ancla REQ-ID + SHALL/SHOULD + estado PDF."""
    indices: list[int] = []
    for i, line in enumerate(lines):
        if ANCHOR_RE.match(line):
            indices.append(i)
    blocks: list[list[str]] = []
    for j, start in enumerate(indices):
        end = indices[j + 1] if j + 1 < len(indices) else len(lines)
        # Incluir líneas de título envueltas antes de la ancla
        real_start = start
        while real_start > 0:
            prev = lines[real_start - 1].rstrip()
            if not prev.strip():
                break
            pl = prev.strip()
            if pl.startswith(("Descripción", "Fuentes", "Verificación", "Traza impl.")):
                break
            if ANCHOR_RE.match(lines[real_start - 1]):
                break
            real_start -= 1
        blocks.append(lines[real_start:end])
    return blocks


def extract_labeled_section(block: list[str], label: str, stop_labels: tuple[str, ...]) -> str:
    parts: list[str] = []
    mode = False
    for raw in block:
        line = raw.rstrip()
        s = line.strip()
        if not mode:
            if s.startswith(label):
                mode = True
                _, _, tail = line.partition(label)
                tail = tail.strip()
                if tail:
                    parts.append(tail)
            continue
        if any(s.startswith(sl) for sl in stop_labels):
            break
        parts.append(line.strip())
    return sanitize_cell(re.sub(r"\s+", " ", " ".join(parts)).strip())


def extract_traza_impl(block: list[str]) -> str:
    """Traza impl. suele ser una línea; cortar antes del siguiente requisito (ancla)."""
    parts: list[str] = []
    mode = False
    for raw in block:
        line = raw.rstrip()
        s = line.strip()
        if not mode:
            if s.startswith("Traza impl."):
                mode = True
                _, _, tail = line.partition("Traza impl.")
                tail = tail.strip()
                if tail:
                    parts.append(tail)
            continue
        if ANCHOR_RE.match(line):
            break
        if not s:
            break
        parts.append(s)
    return sanitize_cell(re.sub(r"\s+", " ", " ".join(parts)).strip())


def sanitize_cell(text: str) -> str:
    if not text:
        return ""
    t = text
    t = re.sub(r"CONFIDENTIAL — UpNext / Airbus UpNext — Flightmind Autonomy Stack\s*Page\s+\d+", " ", t)
    t = re.sub(r"FLIGHTMIND — SUB-[^:]+", " ", t)
    t = re.sub(r"v1\.\d+ · 20\d\d-\d\d-\d\d", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def extract_req_id(block: list[str]) -> tuple[str | None, str | None]:
    for line in block:
        m = ANCHOR_RE.match(line)
        if m:
            return m.group(1), m.group(3)
    return None, None


def extract_title_one_liner(block: list[str], req_id: str) -> str:
    """Primera frase corta del encabezado (título del req en PDF)."""
    bits: list[str] = []
    for line in block:
        s = line.strip()
        if s.startswith("Descripción"):
            break
        if req_id in line:
            idx = line.find(req_id)
            rest = line[idx + len(req_id) :].strip()
            m = re.search(r"\b(SHALL|SHOULD)\b", rest)
            if m:
                rest = rest[: m.start()].strip()
            if rest:
                bits.append(rest)
        elif bits and s and not ANCHOR_RE.match(line):
            bits.append(s)
    t = " ".join(bits)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:240] + ("…" if len(t) > 240 else "")


def normalize_implemented(traza: str, sub: str, req_id: str) -> str:
    traza = re.sub(r"\s+", " ", traza.strip())
    if not traza:
        return ""
    lower = traza.lower()
    if lower.startswith("testbench/") or "/testbench/" in lower:
        return traza.split()[0] if traza.split() else traza
    if traza.strip().startswith("src/"):
        return traza.strip().split()[0]
    # rutas tipo config/mission_fsm.yaml
    if traza.startswith("config/mission_fsm") or "mission_fsm.yaml" in traza:
        return "src/mission_fsm/config/mission_fsm.yaml"
    if "fsm.py" in traza and "MissionFsm" in traza:
        return "src/mission_fsm/mission_fsm/fsm.py"
    if "upnext_airspace" in lower or "polycarp" in lower:
        return "src/upnext_airspace/upnext_airspace/airspace_monitor_node.py"
    m_msg = re.search(r"flightmind_msgs/([\w]+\.msg)", traza)
    if m_msg:
        return f"src/flightmind_msgs/msg/{m_msg.group(1)}"
    if "daidalus_parameters.conf" in traza:
        for cand in ROOT.rglob("daidalus_parameters.conf"):
            rel = cand.relative_to(ROOT)
            return str(rel).replace("\\", "/")
        return "config/daidalus_parameters.conf"
    if "daidalus_node.py" in traza:
        for cand in ROOT.rglob("daidalus_node.py"):
            rel = cand.relative_to(ROOT)
            return str(rel).replace("\\", "/")
    if "fdir_node.py" in traza:
        return "src/fdir/fdir/fdir_node.py"
    if "airspace_monitor_node.py" in traza:
        return "src/upnext_airspace/upnext_airspace/airspace_monitor_node.py"
    if "upnext_icarous_daa" in traza:
        for cand in ROOT.rglob("daidalus_node.py"):
            rel = cand.relative_to(ROOT)
            return str(rel).replace("\\", "/")
    hint = SUB_IMPL_HINT.get(sub, "src/")
    if traza.endswith(".py") and "/" not in traza:
        pkg = hint.rstrip("/")
        guess = ROOT / pkg / traza.split()[-1]
        if guess.is_file():
            return str(guess.relative_to(ROOT)).replace("\\", "/")
        return f"{pkg}/{traza.split()[-1]}"
    first = traza.split()[0]
    if "/" in first or first.endswith((".py", ".yaml", ".yml", ".msg", ".sh", ".js", ".html", ".desktop")):
        if not first.startswith("src/") and not first.startswith("testbench/"):
            trial = ROOT / "src" / first
            if trial.is_file():
                return str(trial.relative_to(ROOT)).replace("\\", "/")
        return first
    return traza[:200]


def infer_test_file(verification: str) -> str:
    found = TC_RE.findall(verification)
    if not found:
        return ""
    # Tomar primer TC concreto (sin ..)
    for token in verification.split():
        m = re.match(r"(TC-[A-Z]+-\d{3})", token)
        if m:
            prefix = m.group(1).rsplit("-", 1)[0]  # TC-DAI
            # TC-DAI de TC-DAI-001 -> prefix TC-DAI - wrong
            # m.group is TC-DAI-001 -> prefix should be TC-DAI
            parts = m.group(1).split("-")
            if len(parts) >= 3:
                pkey = f"{parts[0]}-{parts[1]}"
            else:
                pkey = m.group(1)
            if pkey in TC_PREFIX_TO_TEST_FILE:
                return TC_PREFIX_TO_TEST_FILE[pkey]
    for m in TC_RE.finditer(verification):
        raw = m.group(0)
        base = raw.split("..")[0]
        m2 = re.match(r"(TC-[A-Z]+)-\d{3}", base)
        if m2 and m2.group(1) in TC_PREFIX_TO_TEST_FILE:
            return TC_PREFIX_TO_TEST_FILE[m2.group(1)]
    return ""


def pdf_status_to_row_status(pdf_s: str) -> str:
    if pdf_s == "CUBIERTO":
        return "PASS"
    if pdf_s == "PARCIAL":
        return "PARTIAL"
    if pdf_s in ("XFAIL", "PENDIENTE"):
        return "GAP"
    if pdf_s == "N/A-DEMO":
        return "PARTIAL"
    return "PARTIAL"


def apply_arch(
    verification: str,
    base_status: str,
    tc_to_arch: dict[str, str],
    open_tcs: set[str],
) -> str:
    refs: list[str] = []
    for m in TC_RE.finditer(verification):
        token = m.group(0)
        # expand simple range TC-DAI-001..004 -> check 001-004
        if ".." in token:
            left, _, right = token.partition("..")
            mleft = re.search(r"(\d{3})$", left)
            mright = re.search(r"(\d{3})$", right)
            if mleft and mright:
                pre = left[: mleft.start()]
                a, b = int(mleft.group(1)), int(mright.group(1))
                for n in range(min(a, b), max(a, b) + 1):
                    tcn = f"{pre}{n:03d}"
                    if tcn in tc_to_arch:
                        refs.append(tc_to_arch[tcn])
            continue
        tc = token.split(".")[0]
        if tc in tc_to_arch:
            refs.append(tc_to_arch[tc])
    if not refs:
        return base_status
    uniq = sorted(set(refs))
    suffix = " (" + "; ".join(uniq) + ")"
    if base_status == "PASS":
        return "PARTIAL" + suffix
    if base_status == "PARTIAL":
        return "PARTIAL" + suffix
    return "GAP" + suffix


def subsystem_from_filename(name: str) -> str:
    # SUB_DAA_Requirements.txt -> DAA
    m = re.match(r"SUB_([A-Z0-9]+)_Requirements", name)
    return m.group(1) if m else "UNK"


def parse_pdf_txt(path: Path, tc_to_arch: dict[str, str], open_tcs: set[str]) -> list[dict[str, str]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    sub = subsystem_from_filename(path.stem)
    rows: list[dict[str, str]] = []
    for block in split_blocks(lines):
        req_id, pdf_status = extract_req_id(block)
        if not req_id or not pdf_status:
            continue
        desc = extract_labeled_section(block, "Descripción", ("Fuentes",))
        if not desc:
            desc = sanitize_cell(extract_title_one_liner(block, req_id))
        verification = extract_labeled_section(
            block, "Verificación", ("Traza impl.",)
        )
        traza = extract_traza_impl(block)
        # Traza no debe cortar por Descripción del siguiente (no debería aparecer)
        impl = normalize_implemented(traza, sub, req_id)
        test_f = infer_test_file(verification)
        if sub == "TEST" or (impl.startswith("testbench/") or "testbench/" in impl):
            eff_sub = "TEST"
        else:
            eff_sub = sub
        base_st = pdf_status_to_row_status(pdf_status)
        status = apply_arch(verification, base_st, tc_to_arch, open_tcs)
        rows.append(
            {
                "Subsystem": eff_sub,
                "Req_ID": req_id,
                "Description": desc,
                "Verification_Method": verification,
                "Implemented_File": impl,
                "Test_File": test_f,
                "Status": status,
            }
        )
    return rows


def main() -> int:
    tc_to_arch, open_tcs = parse_xfail_arch()
    if not EXTRACT_DIR.is_dir():
        print(f"No existe {EXTRACT_DIR}; ejecuta pdftotext sobre los PDF.", file=sys.stderr)
        return 1
    all_rows: list[dict[str, str]] = []
    for txt in sorted(EXTRACT_DIR.glob("SUB_*_Requirements.txt")):
        all_rows.extend(parse_pdf_txt(txt, tc_to_arch, open_tcs))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Subsystem",
        "Req_ID",
        "Description",
        "Verification_Method",
        "Implemented_File",
        "Test_File",
        "Status",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows -> {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
