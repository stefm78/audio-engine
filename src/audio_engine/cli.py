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
from .sound.selection import select_candidates
from .voices import load_voice_config, public_catalog, recommend_presets


def _add_qualify_args(parser, include_type=True):
    parser.add_argument("file")
    if include_type:
        parser.add_argument("--type", choices=SOUND_TYPES, required=True, dest="sound_type")
    parser.add_argument("--id", default=None)
    parser.add_argument("--source-provider", default=None)
    parser.add_argument("--source-page", default=None)
    parser.add_argument("--source-identifier", default=None)
    parser.add_argument("--license", default=None, dest="license_id")
    parser.add_argument("--attribution", default=None)
    parser.add_argument(
        "--raw-redistribution",
        choices=("unknown", "allowed", "embedded-only", "forbidden"),
        default="unknown",
    )
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--preview-dir", default=None)


def build_parser():
    parser = argparse.ArgumentParser(prog="audio-engine")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render one structured audio program")
    render.add_argument("program")
    render.add_argument("--out", default="output")
    render.add_argument("--voices", default=None)
    render.add_argument("--sounds", default=None)

    batch = sub.add_parser("batch", help="Render a glob of programs, best effort")
    batch.add_argument("pattern")
    batch.add_argument("--out", default="output")
    batch.add_argument("--voices", default=None)
    batch.add_argument("--sounds", default=None)

    assemble = sub.add_parser("assemble", help="Assemble existing audio assets")
    assemble.add_argument("plan")
    assemble.add_argument("--out", default="output")

    validate = sub.add_parser("validate", help="Validate a JSON contract")
    validate.add_argument("file")
    validate.add_argument("--kind", choices=("program", "assembly"), default="program")

    voices = sub.add_parser("voices", help="Publish the validated voice catalog and selection rules")
    voices.add_argument("--voices", default=None)

    recommend = sub.add_parser("recommend", help="Rank voice presets for a requested target profile")
    recommend.add_argument("--target", required=True)
    recommend.add_argument("--limit", type=int, default=3)
    recommend.add_argument("--voices", default=None)

    sounds = sub.add_parser("sounds", help="Publish the validated production sound meta-index")
    sounds.add_argument("--catalog", default=None)
    sounds.add_argument("--id", default=None)
    sounds.add_argument("--type", choices=SOUND_TYPES, default=None, dest="sound_type")
    sounds.add_argument("--tag", action="append", default=[])

    sound = sub.add_parser("sound", help="Autonomous sound qualification and selection")
    sound_sub = sound.add_subparsers(dest="sound_command", required=True)
    sound_qualify = sound_sub.add_parser("qualify", help="Machine-qualify one downloaded sound candidate")
    _add_qualify_args(sound_qualify, include_type=True)
    sound_select = sound_sub.add_parser("select", help="Automatically select the best machine-qualified candidate")
    sound_select.add_argument("candidates", nargs="+")
    sound_select.add_argument("--type", choices=SOUND_TYPES, required=True, dest="sound_type")
    sound_select.add_argument("--require-tag", action="append", default=[])
    sound_select.add_argument("--prefer-tag", action="append", default=[])
    sound_select.add_argument("--min-score", type=float, default=70.0)

    ambiences = sub.add_parser("ambiences", help="Publish the legacy curated ambience catalog and asset policy")
    ambiences.add_argument("--id", default=None)
    ambiences.add_argument("--tag", action="append", default=[])

    ambience = sub.add_parser("ambience", help="Legacy ambience discovery/qualification alias")
    ambience_sub = ambience.add_subparsers(dest="ambience_command", required=True)
    discover = ambience_sub.add_parser("discover", help="Create a multi-source discovery plan without network requests")
    discover.add_argument("query")
    discover.add_argument("--source", action="append", default=[])
    qualify = ambience_sub.add_parser("qualify", help="Machine-qualify an ambience candidate")
    _add_qualify_args(qualify, include_type=False)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "render":
            result = render_program(args.program, args.out, voices_path=args.voices, sounds_path=args.sounds)
        elif args.command == "batch":
            result = render_batch(args.pattern, args.out, voices_path=args.voices, sounds_path=args.sounds)
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
        elif args.command == "sound":
            if args.sound_command == "qualify":
                result = qualify_candidate(
                    args.file,
                    candidate_id=args.id,
                    candidate_type=args.sound_type,
                    source_provider=args.source_provider,
                    source_page=args.source_page,
                    source_identifier=args.source_identifier,
                    license_id=args.license_id,
                    attribution=args.attribution,
                    raw_redistribution=args.raw_redistribution,
                    tags=args.tag,
                    preview_dir=args.preview_dir,
                )
            else:
                result = select_candidates(
                    args.candidates,
                    sound_type=args.sound_type,
                    required_tags=args.require_tag,
                    preferred_tags=args.prefer_tag,
                    min_score=args.min_score,
                )
        elif args.command == "ambiences":
            result = ambience_info(args.id) if args.id else public_ambience_catalog(tags=args.tag)
        elif args.command == "ambience":
            if args.ambience_command == "discover":
                result = discovery_plan(args.query, args.source)
            else:
                result = qualify_candidate(
                    args.file,
                    candidate_id=args.id,
                    candidate_type="ambience",
                    source_provider=args.source_provider,
                    source_page=args.source_page,
                    source_identifier=args.source_identifier,
                    license_id=args.license_id,
                    attribution=args.attribution,
                    raw_redistribution=args.raw_redistribution,
                    tags=args.tag,
                    preview_dir=args.preview_dir,
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
