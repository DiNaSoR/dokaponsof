from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dokapon_explorer.report import write_json_report, write_logic_report, write_markdown_report
from dokapon_explorer.scanner import analyze_debug, scan_map_groups


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan DOKAPON! Sword of Fury map/debug assets.")
    parser.add_argument("--game-dir", type=Path, required=True, help="Game installation directory")
    parser.add_argument("--out", type=Path, default=Path("out"), help="Output directory for reports")
    args = parser.parse_args()

    game_dir = args.game_dir.resolve()
    out_dir = args.out.resolve()

    debug = analyze_debug(game_dir)
    map_groups = scan_map_groups(game_dir)

    json_path = write_json_report(out_dir, debug, map_groups)
    md_path = write_markdown_report(out_dir, debug, map_groups)
    logic_path = write_logic_report(out_dir, map_groups)

    print(f"[+] JSON report: {json_path}")
    print(f"[+] Markdown report: {md_path}")
    print(f"[+] Logic report: {logic_path}")
    print(f"[+] Map groups scanned: {len(map_groups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
