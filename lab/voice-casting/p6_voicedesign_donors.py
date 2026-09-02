#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random, time
from pathlib import Path
import numpy as np
import soundfile as sf
import torch

QWEN_REV="022e286b98fbec7e1e916cb940cdf532cd9f488e"
MODEL_ID="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
MODEL_REV="5ecdb67327fd37bb2e042aab12ff7391903235d3"

CASES=(
 {"i":2,"text":"Non.","seed":2026090302,"instruct":"Voix masculine adulte française claire et naturelle. Choc contenu et refus immédiat, souffle court, réaction instinctive mais basse. Pas de cri, pas de colère jouée, pas de mélodrame."},
 {"i":4,"text":"Ce lit ne sort pas de cette chambre.","seed":2026090304,"instruct":"Voix masculine adulte française claire et naturelle. Certitude intime sous tension, ferme mais retenue, comme si une vérité impossible venait d'être touchée. Pas d'emphase théâtrale."},
 {"i":10,"text":"Tu le savais.","seed":2026090310,"instruct":"Voix masculine adulte française claire et naturelle. Reconnaissance bouleversée et contenue, soulagement mêlé de douleur, voix presque fragile mais sans sanglot ni mélodrame."},
 {"i":12,"text":"Pénélope…","seed":2026090312,"instruct":"Voix masculine adulte française claire et naturelle. Reconnaissance incrédule, très douce et suspendue, émotion réelle mais retenue. Ne pas chuchoter, ne pas surjouer."},
 {"i":15,"text":"Notre lit.","seed":2026090315,"instruct":"Voix masculine adulte française claire et naturelle. Retombée intime après le choc, chaleur grave, certitude retrouvée, presque un soulagement. Très simple, sans pathos."},
)

def sha256(p:Path):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()

def gate(p:Path):
 y,sr=sf.read(p,dtype="float32",always_2d=False); y=np.asarray(y,dtype=np.float32)
 if y.ndim==2:y=y.mean(1)
 dur=len(y)/sr if sr else 0; rms=float(np.sqrt(np.mean(y*y))) if len(y) else 0; peak=float(np.max(np.abs(y))) if len(y) else 0
 ok=bool(np.isfinite(y).all()) and .08<=dur<=14 and .0015<=rms<=.8 and peak<=1
 return {"status":"PASS" if ok else "REJECT","sample_rate":int(sr),"duration_seconds":float(dur),"rms":rms,"peak":peak}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--model-dir",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
 from qwen_tts import Qwen3TTSModel
 from transformers.utils import logging as tl
 out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 model=Qwen3TTSModel.from_pretrained(a.model_dir,device_map="cpu",dtype=torch.bfloat16,attn_implementation="eager")
 tl.disable_progress_bar()
 records=[]
 for n,c in enumerate(CASES,1):
  random.seed(c["seed"]); np.random.seed(c["seed"]%(2**32-1)); torch.manual_seed(c["seed"])
  started=time.monotonic()
  wavs,sr=model.generate_voice_design(text=c["text"],instruct=c["instruct"],language="French",non_streaming_mode=True,do_sample=True,max_new_tokens=512)
  p=out/f"{c['i']:02d}.wav"; sf.write(p,wavs[0],sr)
  g=gate(p)
  if g["status"]!="PASS": raise SystemExit(f"DONOR_TECHNICAL_REJECT:{c['i']}:{g}")
  records.append({**c,"file":p.name,"sha256":sha256(p),"technical_gate":g,"render_seconds":round(time.monotonic()-started,2)})
 manifest={"schema":"odyssee-p6-voicedesign-donors-v1","status":"PASS","qwen_source_revision":QWEN_REV,"model_id":MODEL_ID,"model_revision":MODEL_REV,"render_count":len(records),"records":records}
 (out/"donors.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
