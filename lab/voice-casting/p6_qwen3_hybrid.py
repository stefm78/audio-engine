#!/usr/bin/env python3
"""P6 Ulysse emotional scene-local Qwen3 hybrid cell.

Composition of already evidenced capabilities:
- first two high-charge Ulysse reactions: Qwen3 Base x-vector-only;
- last three recognition-release lines: historical contained-sadness style transplant.

The H1b-B P6 scene is the immutable baseline. All non-target material is preserved
from that scene, including Pénélope, pauses and explanatory Ulysse lines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from pydub import AudioSegment

from audio_engine.providers.qwen3_style_transplant_lab import Qwen3StyleTransplantLabProvider

BASELINE_AUDIO_SHA256 = "474c2e41a5d702b2a84524aa3be9a0559ed7378af18d507ac082b666029d64ae"
BASELINE_REPORT_SHA256 = "366091a73e7597626384535e900a5b30e7943c485d0197ec25f015c384b6d891"

UPSTREAM_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
BASE_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
BASE_MODEL_REVISION = "74a6279626edc2d5a787d5b6467668eba0b86ef6"
LICENSE = "Apache-2.0"

DONOR_RUN_ID = 32811700540
DONOR_ARTIFACT = "qwen3-style-transplant-donors"
DONOR_ARTIFACT_DIGEST = "sha256:a9cb83397164ec017a6fd20994ad511bb7bac380d0d9c0bffc4acacd6111861a"
DONOR_ID = "sadness-contained"
DONOR_TEXT = "Je savais que ce jour viendrait... mais cela fait quand même mal."
DONOR_SEED = 2026082503

ANCHOR_SEGMENTS = (6, 7, 8)
TARGETS = {
    2: {"speaker":"Ulysse","text":"Non.","mode":"xvector"},
    4: {"speaker":"Ulysse","text":"Ce lit ne sort pas de cette chambre.","mode":"xvector"},
    10: {"speaker":"Ulysse","text":"Tu le savais.","mode":"contained-sadness"},
    12: {"speaker":"Ulysse","text":"Pénélope…","mode":"contained-sadness"},
    15: {"speaker":"Ulysse","text":"Notre lit.","mode":"contained-sadness"},
}
SEEDS = {
    2: 2026090202,
    4: 2026090204,
    10: 2026090210,
    12: 2026090212,
    15: 2026090215,
}


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(seg: AudioSegment, target=-20.0) -> AudioSegment:
    seg=seg.set_frame_rate(24000).set_channels(2)
    if math.isfinite(seg.dBFS):
        seg=seg.apply_gain(max(-8,min(8,target-seg.dBFS)))
    return seg


def technical_gate(path: Path) -> dict:
    y,sr=sf.read(path,dtype="float32",always_2d=False)
    y=np.asarray(y,dtype=np.float32)
    if y.ndim==2:
        y=y.mean(1)
    finite=bool(np.isfinite(y).all())
    duration=float(len(y)/sr) if sr else 0.0
    rms=float(np.sqrt(np.mean(np.square(y)))) if len(y) else 0.0
    peak=float(np.max(np.abs(y))) if len(y) else 0.0
    passed=finite and 0.08 <= duration <= 14.0 and 0.0015 <= rms <= 0.6 and peak <= 1.0
    return {
        "status":"PASS" if passed else "REJECT",
        "sample_rate":int(sr),
        "duration_seconds":duration,
        "rms":rms,
        "peak":peak,
        "finite":finite,
    }


def load_baseline(audio_path:Path, report_path:Path):
    if sha256(audio_path)!=BASELINE_AUDIO_SHA256:
        raise SystemExit("P6_BASELINE_AUDIO_SHA_REJECT")
    if sha256(report_path)!=BASELINE_REPORT_SHA256:
        raise SystemExit("P6_BASELINE_REPORT_SHA_REJECT")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("variant")!="p6-b":
        raise SystemExit("P6_BASELINE_VARIANT_REJECT")
    by_i={int(s["i"]):s for s in report["segments"]}
    for i,t in TARGETS.items():
        s=by_i.get(i)
        if not s or s["speaker"]!=t["speaker"] or s["text"]!=t["text"]:
            raise SystemExit(f"P6_TARGET_BINDING_REJECT:{i}")
    for i in ANCHOR_SEGMENTS:
        s=by_i.get(i)
        if not s or s["speaker"]!="Ulysse":
            raise SystemExit(f"P6_ANCHOR_BINDING_REJECT:{i}")
    audio=AudioSegment.from_file(audio_path).set_frame_rate(24000).set_channels(2)
    return audio,report


def segment_bounds(report):
    out={}
    cursor=0
    for s in report["segments"]:
        i=int(s["i"])
        audio_ms=int(s["audio_ms"])
        pause_ms=int(s.get("pause_ms",0))
        out[i]=(cursor,cursor+audio_ms,cursor+audio_ms+pause_ms)
        cursor += audio_ms+pause_ms
    return out,cursor


def derive_anchor(audio,report,out:Path):
    bounds,_=segment_bounds(report)
    anchor=AudioSegment.empty()
    parts=[]
    for n,i in enumerate(ANCHOR_SEGMENTS):
        start,speech_end,_=bounds[i]
        clip=audio[start:speech_end]
        anchor += clip
        parts.append({"i":i,"pcm_sha256":hashlib.sha256(clip.raw_data).hexdigest(),"audio_ms":len(clip)})
        if n < len(ANCHOR_SEGMENTS)-1:
            anchor += AudioSegment.silent(duration=160,frame_rate=24000).set_channels(2)
    anchor=anchor.set_channels(1).set_frame_rate(24000)
    path=out/"ulysse-henri-anchor.wav"
    anchor.export(path,format="wav")
    return path,parts


def validate_donor(donor_dir:Path):
    donor=donor_dir/"sadness-contained.wav"
    meta=donor_dir/"donors.json"
    if not donor.is_file() or not meta.is_file():
        raise SystemExit("P6_DONOR_FILES_MISSING")
    data=json.loads(meta.read_text(encoding="utf-8"))
    matches=[r for r in data.get("records",[]) if r.get("id")==DONOR_ID]
    if len(matches)!=1:
        raise SystemExit("P6_DONOR_METADATA_REJECT")
    rec=matches[0]
    if rec.get("text")!=DONOR_TEXT or int(rec.get("seed",-1))!=DONOR_SEED:
        raise SystemExit("P6_DONOR_METADATA_REJECT")
    return donor,rec


def render(model_dir,baseline_audio,baseline_report,donor_dir,out):
    out.mkdir(parents=True,exist_ok=True)
    raw_dir=out/"raw"; raw_dir.mkdir(exist_ok=True)
    slots_dir=out/"slots"; slots_dir.mkdir(exist_ok=True)

    baseline,report=load_baseline(baseline_audio,baseline_report)
    donor,donor_meta=validate_donor(donor_dir)
    anchor,anchor_parts=derive_anchor(baseline,report,out)

    provider=Qwen3StyleTransplantLabProvider(model_dir=model_dir,device="cpu")
    identity=provider.build_identity_embedding(anchor)
    xprompt=provider.build_xvector_prompt(anchor)
    style_prompt=provider.build_style_prompt(identity,donor,DONOR_TEXT)

    rendered={}
    slot_reports=[]
    for i in sorted(TARGETS):
        t=TARGETS[i]
        raw=raw_dir/f"{i:02d}-{t['mode']}.wav"
        prompt=xprompt if t["mode"]=="xvector" else style_prompt
        provider.synthesize(
            {
                "text":t["text"],
                "language":"French",
                "seed":SEEDS[i],
                "max_new_tokens":768,
            },
            raw,
            voice_clone_prompt=prompt,
        )
        gate=technical_gate(raw)
        if gate["status"]!="PASS":
            raise SystemExit(f"P6_SLOT_TECHNICAL_REJECT:{i}:{json.dumps(gate)}")
        a=normalize(AudioSegment.from_file(raw))
        slot=slots_dir/f"{i:02d}-{t['mode']}.wav"
        a.export(slot,format="wav")
        rendered[i]=a
        slot_reports.append({
            "i":i,
            "speaker":t["speaker"],
            "text":t["text"],
            "mode":t["mode"],
            "seed":SEEDS[i],
            "raw_sha256":sha256(raw),
            "slot_sha256":sha256(slot),
            "technical_gate":gate,
            "candidate_audio_ms":len(a),
        })

    bounds,scheduled_end=segment_bounds(report)
    final=AudioSegment.empty()
    preserved=[]
    for s in report["segments"]:
        i=int(s["i"])
        start,speech_end,slot_end=bounds[i]
        pause_ms=int(s.get("pause_ms",0))
        if i in rendered:
            final += rendered[i]
            if pause_ms:
                final += baseline[speech_end:slot_end]
        else:
            frozen=baseline[start:slot_end]
            final += frozen
            preserved.append({
                "i":i,
                "speaker":s["speaker"],
                "text":s["text"],
                "pcm_sha256":hashlib.sha256(frozen.raw_data).hexdigest(),
                "audio_ms":int(s["audio_ms"]),
                "pause_ms":pause_ms,
            })
    if scheduled_end < len(baseline):
        final += baseline[scheduled_end:]

    candidate=out/"p6-qwen3-hybrid.mp3"
    final.export(candidate,format="mp3",bitrate="128k")
    manifest={
        "schema":"odyssee-p6-qwen3-hybrid-v1",
        "status":"MACHINE_PASS",
        "cloud_tts":False,
        "nuc_required":False,
        "baseline":{
            "repo":"stefm78/recit-audioguide",
            "release":"odyssee-h1b-corrective-review-v1",
            "variant":"p6-b",
            "audio_sha256":BASELINE_AUDIO_SHA256,
            "report_sha256":BASELINE_REPORT_SHA256,
        },
        "provider":{
            "runtime":"QwenLM/Qwen3-TTS",
            "upstream_revision":UPSTREAM_REVISION,
            "model":BASE_MODEL_ID,
            "model_revision":BASE_MODEL_REVISION,
            "license":LICENSE,
        },
        "identity_anchor":{
            "source_segments":list(ANCHOR_SEGMENTS),
            "derived_sha256":sha256(anchor),
            "parts":anchor_parts,
        },
        "style_donor":{
            "run_id":DONOR_RUN_ID,
            "artifact":DONOR_ARTIFACT,
            "artifact_digest":DONOR_ARTIFACT_DIGEST,
            "id":DONOR_ID,
            "file_sha256":sha256(donor),
            "metadata":donor_meta,
        },
        "modes":{
            "xvector_lines":[2,4],
            "contained_sadness_lines":[10,12,15],
        },
        "slots":slot_reports,
        "preserved":preserved,
        "candidate_sha256":sha256(candidate),
        "duration_seconds":len(final)/1000,
        "human_gate":"PENDING",
        "pass_requires":[
            "impact_GTE_4_OF_5",
            "ulysse_reaction_PASS",
            "identity_continuity_PASS",
            "french_PASS",
            "no_melodrama",
            "penelope_staging_no_regression",
        ],
    }
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model-dir",required=True)
    ap.add_argument("--baseline-audio",required=True)
    ap.add_argument("--baseline-report",required=True)
    ap.add_argument("--donor-dir",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    result=render(Path(args.model_dir),Path(args.baseline_audio),Path(args.baseline_report),Path(args.donor_dir),Path(args.out))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
