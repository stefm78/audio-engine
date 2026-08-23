import argparse
import json
import sys

from . import __version__
from .ambience.catalog import ambience_info, public_catalog as public_ambience_catalog
from .ambience.discovery import discovery_plan
from .ambience.qualification import qualify_candidate
from .assemble import assemble_plan
from .batch import render_batch
from .contract import ContractError, load_json, validate_assembly, validate_program
from .render import render_program
from .sound.catalog import SOUND_TYPES, public_catalog as public_sound_catalog, sound_info
from .voices import load_voice_config, public_catalog, recommend_presets


def build_parser():
    parser = argparse.ArgumentParser(prog="audio-engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render one structured audio program")
    render.add_argument("program")
    render.add_argument("--out", default="output")
    render.add_argument("--voices", default=None)
    render.add_argument("--sounds", default=None, help="Optional validated sound catalog JSON")

    batch = sub.add_parser("batch", help="Render a glob of programs, best effort")
    batch.add_argument("pattern")
    batch.add_argument("--out", default="output")
    batch.add_argument("--voices", default=None)
    batch.add_argument("--sounds", default=None, help="Optional validated sound catalog JSON")

    assemble = sub.add_parser("assemble", help="Assemble existing audio assets")
    assemble.add_argument("plan")
    assemble.add_argument("--out", default="output")

    validate = sub.add_parser("validate", help="Validate a JSON contract")
    validate.add_argument("file")
    validate.add_argument("--kind", choices=("program", "assembly"), default="program")

    voices = sub.add_parser("voices", help="Publish the validated voice catalog and selection rules")
    voices.add_argument("--voices", default=None)

    recommend = sub.add_parser("recommend", help="Rank voice presets for a requested target profile")
    recommend.add_argument("--target", required=True, help="Target profile as a JSON object")
    recommend.add_argument("--limit", type=int, default=3)
    recommend.add_argument("--voices", default=None)

    sounds = sub.add_parser("sounds", help="Publish the validated production sound meta-index")
    sounds.add_argument("--catalog", default=None, help="Optional sound catalog JSON")
    sounds.add_argument("--id", default=None, help="Return one validated sound by id")
    sounds.add_argument("--type", choices=SOUND_TYPES, default=None, dest="sound_type")
    sounds.add_argument("--tag", action="append", default=[], help="Require a tag; repeat to combine tags")

    ambiences = sub.add_parser("ambiences", help="Publish the legacy curated ambience catalog and asset policy")
    ambiences.add_argument("--id", default=None, help="Return one curated ambience by id")
    ambiences.add_argument("--tag", action="append", default=[], help="Require a tag; repeat to combine tags")

    ambience = sub.add_parser("ambience", help="Discover and qualify ambience candidates before rendering")
    ambience_sub = ambience.add_subparsers(dest="ambience_command", required=True)

    discover = ambience_sub.add_parser("discover", help="Create a multi-source discovery plan without network requests")
    discover.add_argument("query")
    discover.add_argument("--source", action="append", default=[], help="Limit to a source id; repeat to combine sources")

    qualify = ambience_sub.add_parser("qualify", help="Probe and fingerprint a downloaded local ambience candidate")
    qualify.add_argument("file")
    qualify.add_argument("--id", default=None, help="Stable candidate id; defaults to a slug of the filename")
    qualify.add_argument("--source-provider", default=None)
    qualify.add_argument("--source-page", default=None)
    qualify.add_argument("--source-identifier", default=None)
    qualify.add_argument("--license", default=None, dest="license_id")
    qualify.add_argument("--attribution", default=None)
    qualify.add_argument(
        "--raw-redistribution",
        choices=("unknown", "allowed", "embedded-only", "forbidden"),
        default="unknown",
    )
    qualify.add_argument("--tag", action="append", default=[])
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "render":
            result = render_program(
                args.program,
                args.out,
                voices_path=args.voices,
                sounds_path=args.sounds,
            )
        elif args.command == "batch":
            result = render_batch(
                args.pattern,
                args.out,
                voices_path=args.voices,
                sounds_path=args.sounds,
            )
        elif args.command == "assemble":
            result = assemble_plan(args.plan, args.out)
        elif args.command == "voices":
            config, _ = load_voice_config(args.voices)
            result = public_catalog(config)
        elif args.command == "recommend":
            try:
                target = json.loads(args.target)
            except json.JSONDecodeError as exc:
                raise ValueError(f"--target must be valid JSON: {exc}") from exc
            if not isinstance(target, dict):
                raise ValueError("--target must be a JSON object")
            config, _ = load_voice_config(args.voices)
            result = recommend_presets(target, config, args.limit)
        elif args.command == "sounds":
            if args.id:
                entry, _ = sound_info(args.id, args.catalog)
                result = {"entry": entry}
            else:
                result = public_sound_catalog(args.catalog, tags=args.tag, sound_type=args.sound_type)
        elif args.command == "ambiences":
            result = ambience_info(args.id) if args.id else public_ambience_catalog(tags=args.tag)
        elif args.command == "ambience":
            if args.ambience_command == "discover":
                result = discovery_plan(args.query, args.source)
            else:
                result = qualify_candidate(
                    args.file,
                    candidate_id=args.id,
                    source_provider=args.source_provider,
                    source_page=args.source_page,
                    source_identifier=args.source_identifier,
                    license_id=args.license_id,
                    attribution=args.attribution,
                    raw_redistribution=args.raw_redistribution,
                    tags=args.tag,
                )
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
