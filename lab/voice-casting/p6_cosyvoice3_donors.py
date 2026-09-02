#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random, time
from pathlib import Path

import numpy as np
import torch
import torchaudio
from pydub import AudioSegment

BASELINE_AUDIO_SHA256="474c2e41a5d702b2a84524aa3be9a0559ed7378af18d507ac082b666029d64ae"
BASELINE_REPORT_SHA256="366091a73e7597626384535e900a5b30e7943c485d0197ec25f015c384b6d891"
ANCHOR_SEGMENTS=(6,7,8)
COSY_SOURCE_REV="074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc"
MODEL_ID="FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
MODEL_REV="ed5fc9fb5d640ee5d8199235df412530f6abe9e0"

CASES=(
 {"i":2,"text":"Non.","seed":2026090402,"instruction":"You are a helpful assistant. Speak fluent native French. Deliver this as a very brief, natural, restrained shock reaction: immediate refusal, low voice, short breath, no shouting, no theatrical emphasis, no melodrama. Keep it conversational and concise."},
 {"i":4,"text":"Ce lit ne sort pas de cette chambre.","seed":2026090404,"instruction":"You are a helpful assistant. Speak fluent native French. Deliver this with intimate certainty under tension: firm, natural and restrained, emotionally charged but conversational, never declamatory, never theatrical."},
 {"i":10,"text":"Tu le savais.","seed":2026090410,"instruction":"You are a helpful assistant. Speak fluent native French. Deliver this as contained recognition and relief mixed with pain: emotionally real, fragile but controlled, natural conversational French, no sobbing, no pathos, no theatrical emphasis."},
 {"i":12,"text":"Pénélope…","seed":2026090412,"instruction":"You are a helpful assistant. Speak fluent native French. Deliver only the name, softly and naturally, as an intimate recognition. Keep it brief and suspended, not whispered, not prolonged, not theatrical."},
 {"i":15,"text":"Notre lit.","seed":2026090415,"instruction":"You are a helpful assistant. Speak fluent native French. Deliver this as a simple intimate release after shock: grave warmth and certainty, restrained and conversational, brief, no pathos, no theatrical ending."},
)

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def load_report(audio:Path, report_path:Path):
    if sha256(audio)!=BASELINE_AUDIO_SHA256: raise SystemExit("BASELINE_AUDIO_SHA_REJECT")
    if sha256(report_path)!=BASELINE_REPORT_SHA256: raise SystemExit("BASELINE_REPORT_SHA_REJECT")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("variant")!="p6-b": raise SystemExit("BASELINE_VARIANT_REJECT")
    by={int(x["i"]):x for x in report["segments"]}
    for c in CASES:
        s=by.get(c["i"])
        if not s or s.get("speaker")!="Ulysse" or s.get("text")!=c["text"]:
            raise SystemExit(f"TARGET_BINDING_REJECT:{c['i']}")
    for i in ANCHOR_SEGMENTS:
        if i not in by or by[i].get("speaker")!="Ulysse":
            raise SystemExit(f"ANCHOR_BINDING_REJECT:{i}")
    return report

def derive_anchor(audio:Path, report:dict, out:Path)->Path:
    base=AudioSegment.from_file(audio)
    cur=0; bounds={}
    for s in report["segments"]:
        i=int(s["i"]); a=int(s["audio_ms"]); p=int(s.get("pause_ms",0))
        bounds[i]=(cur,cur+a); cur+=a+p
    anchor=AudioSegment.empty()
    for n,i in enumerate(ANCHOR_SEGMENTS):
        st,en=bounds[i]
        anchor += base[st:en].set_channels(1).set_frame_rate(16000)
        if n<len(ANCHOR_SEGMENTS)-1:
            anchor += AudioSegment.silent(duration=160,frame_rate=16000)
    p=out/"ulysse-henri-prompt.wav"
    anchor.export(p,format="wav")
    return p

def tech_gate(path:Path)->dict:
    wav,sr=torchaudio.load(str(path))
    if wav.ndim==2 and wav.shape[0]>1: wav=wav.mean(0,keepdim=True)
    y=wav.squeeze().float()
    finite=bool(torch.isfinite(y).all().item())
    dur=float(y.numel()/sr) if sr else 0.0
    rms=float(torch.sqrt(torch.mean(y*y)).item()) if y.numel() else 0.0
    peak=float(torch.max(torch.abs(y)).item()) if y.numel() else 0.0
    ok=finite and 0.08<=dur<=14.0 and 0.0015<=rms<=0.8 and peak<=1.0
    return {"status":"PASS" if ok else "REJECT","sample_rate":int(sr),"duration_seconds":dur,"rms":rms,"peak":peak,"finite":finite}

def normalize_instruction(s:str)->str:
    s=str(s).strip()
    if "<|endofprompt|>" not in s:
        s += "<|endofprompt|>"
    return s

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cosy-source",required=True)
    ap.add_argument("--model-dir",required=True)
    ap.add_argument("--baseline-audio",required=True)
    ap.add_argument("--baseline-report",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()

    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    report=load_report(Path(a.baseline_audio),Path(a.baseline_report))
    by={int(x["i"]):x for x in report["segments"]}
    prompt=derive_anchor(Path(a.baseline_audio),report,out)

    import sys
    root=Path(a.cosy_source).resolve()
    sys.path.insert(0,str(root))
    sys.path.insert(0,str(root/"third_party"/"Matcha-TTS"))
    from cosyvoice.cli.cosyvoice import AutoModel

    model=AutoModel(model_dir=str(Path(a.model_dir).resolve()),load_trt=False,load_vllm=False,fp16=False)
    sr=int(model.sample_rate)
    records=[]
    for c in CASES:
        random.seed(c["seed"]); np.random.seed(c["seed"]%(2**32-1)); torch.manual_seed(c["seed"])
        started=time.monotonic()
        pieces=[]
        for result in model.inference_instruct2(c["text"],normalize_instruction(c["instruction"]),str(prompt),stream=False):
            speech=result.get("tts_speech")
            if speech is not None: pieces.append(speech)
        if not pieces: raise SystemExit(f"COSY_NO_SPEECH:{c['i']}")
        wav=pieces[0] if len(pieces)==1 else torch.cat(pieces,dim=-1)
        p=out/f"{c['i']:02d}.wav"
        torchaudio.save(str(p),wav.cpu(),sr)
        g=tech_gate(p)
        if g["status"]!="PASS": raise SystemExit(f"COSY_TECH_REJECT:{c['i']}:{g}")
        records.append({
            **c,
            "file":p.name,
            "sha256":sha256(p),
            "technical_gate":g,
            "baseline_slot_duration_seconds":float(int(by[c["i"]]["audio_ms"])/1000.0),
            "render_seconds":round(time.monotonic()-started,2),
        })
    manifest={
      "schema":"odyssee-p6-cosyvoice3-performance-donors-v1",
      "status":"PASS",
      "cosy_source_revision":COSY_SOURCE_REV,
      "model_id":MODEL_ID,
      "model_revision":MODEL_REV,
      "prompt_sha256":sha256(prompt),
      "render_count":len(records),
      "records":records,
    }
    (out/"donors.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
