import argparse
import json
import sys

from . import __version__
from .assemble import assemble_plan
from .batch import render_batch
from .contract import ContractError, load_json, validate_assembly, validate_program
from .render import render_program

def build_parser():
    parser = argparse.ArgumentParser(prog="audio-engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render one structured audio program")
    render.add_argument("program")
    render.add_argument("--out", default="output")
    render.add_argument("--voices", default=None)

    batch = sub.add_parser("batch", help="Render a glob of programs, best effort")
    batch.add_argument("pattern")
    batch.add_argument("--out", default="output")
    batch.add_argument("--voices", default=None)

    assemble = sub.add_parser("assemble", help="Assemble existing audio assets")
    assemble.add_argument("plan")
    assemble.add_argument("--out", default="output")

    validate = sub.add_parser("validate", help="Validate a JSON contract")
    validate.add_argument("file")
    validate.add_argument("--kind", choices=("program", "assembly"), default="program")
    return parser

def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "render":
            result = render_program(args.program, args.out, args.voices)
        elif args.command == "batch":
            result = render_batch(args.pattern, args.out, args.voices)
        elif args.command == "assemble":
            result = assemble_plan(args.plan, args.out)
        else:
            data = load_json(args.file)
            result = validate_program(data) if args.kind == "program" else validate_assembly(data)
            result = {"status": "valid", "kind": args.kind, "id": result.get("id")}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ContractError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
