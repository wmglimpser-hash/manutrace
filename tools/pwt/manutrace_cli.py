# -*- coding: utf-8 -*-
"""ManuTrace command dispatcher."""
import importlib
import sys


COMMANDS = {
    "build": "build_manuscript",
    "pipeline": "pipeline",
    "init": "pwt_init",
    "extract-rules": "extract_journal_rules",
    "summaries": "reference_summaries",
    "evidence-map": "build_evidence_map",
    "candidate": "reference_candidate",
    "outline": "outline_gate",
    "coverage": "coverage_report",
    "parse-refs": "parse_references",
    "render-refs": "render_reference_preview",
    "rename-refs": "rename_ref_keys",
    "migrate": "migrate_manuscript",
}


def print_help():
    print("ManuTrace command line")
    print("")
    print("Usage:")
    print("  manutrace <command> [args...]")
    print("")
    print("Commands:")
    for name in sorted(COMMANDS):
        print(f"  {name}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print_help()
        return 0

    command = sys.argv[1]
    module_name = COMMANDS.get(command)
    if not module_name:
        print(f"FAIL: 未知命令：{command}")
        print_help()
        return 1

    sys.argv = [f"manutrace {command}", *sys.argv[2:]]
    module = importlib.import_module(module_name)
    return int(module.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
