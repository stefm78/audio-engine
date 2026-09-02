#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, random, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf, torch, yaml
from pydub import AudioSegment

BASELINE_AUDIO_SHA256="474c2e41a5d702b2a84524aa3be9a0559ed7378af18d507ac082b666029d64ae"
BASELINE_REPORT_SHA256="366091a73e7597626384535e900a5b30e7943c485d0197ec25f015c384b6d891"
ANCHOR_SEGMENTS=(6,7,8)
TARGETS={
  2:"Non.",
  4:"Ce lit ne sort pas de cette chambre.",
  10:"Tu le savais.",
  12:"Pénélope…",
  15:"Notre lit.",
}
SEEDS={2:2026090202,4:2026090204,10:2026090210,12:2026090212,15:2026090215}
SOURCE_REV="45f83890b72ba26d1954dab5001600301ebe8dd3"
CONFUCIUS_HF_REV="696981f"; W2V_HF_REV="da985ba"; CAMPPLUS_HF_REV="e4b6ede"; BIGVGAN_HF_REV="633ff70"

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def load_baseline(audio:Path,report_path:Path):
    if sha256(audio)!=BASELINE_AUDIO_SHA256: raise SystemExit("P6_BASELINE_AUDIO_SHA_REJECT")
    if sha256(report_path)!=BASELINE_REPORT_SHA256: raise SystemExit("P6_BASELINE_REPORT_SHA_REJECT")
    report=json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("variant")!="p6-b": raise SystemExit("P6_BASELINE_VARIANT_REJECT")
    by_i={int(x["i"]):x for x in report["segments"]}
    for i,t in TARGETS.items():
        s=by_i.get(i)
        if not s or s.get("speaker")!="Ulysse" or s.get("text")!=t:
            raise SystemExit(f"P6_TARGET_BINDING_REJECT:{i}")
    for i in ANCHOR_SEGMENTS:
        if by_i.get(i,{}).get("speaker")!="Ulysse": raise SystemExit(f"P6_ANCHOR_BINDING_REJECT:{i}")
    return AudioSegment.from_file(audio).set_frame_rate(24000).set_channels(2),report

def bounds(report):
    out={}; cursor=0
    for s in report["segments"]:
        i=int(s["i"]); a=int(s["audio_ms"]); p=int(s.get("pause_ms",0))
        out[i]=(cursor,cursor+a,cursor+a+p); cursor+=a+p
    return out,cursor

def derive_anchor(baseline,report,out):
    b,_=bounds(report); mono=AudioSegment.empty(); parts=[]
    for n,i in enumerate(ANCHOR_SEGMENTS):
        start,end,_=b[i]; clip=baseline[start:end].set_channels(1).set_frame_rate(16000)
        mono+=clip
        parts.append({"i":i,"audio_ms":len(clip),"pcm_sha256":hashlib.sha256(clip.raw_data).hexdigest()})
        if n<len(ANCHOR_SEGMENTS)-1: mono+=AudioSegment.silent(duration=160,frame_rate=16000)
    p=out/"ulysse-henri-anchor.wav"; mono.export(p,format="wav")
    return p,parts

def tech(path):
    y,sr=sf.read(path,dtype="float32",always_2d=False); y=np.asarray(y,dtype=np.float32)
    if y.ndim==2:y=y.mean(1)
    finite=bool(np.isfinite(y).all()); dur=float(len(y)/sr) if sr else 0; rms=float(np.sqrt(np.mean(y*y))) if len(y) else 0; peak=float(np.max(np.abs(y))) if len(y) else 0
    ok=finite and 0.08<=dur<=14 and 0.0015<=rms<=0.7 and peak<=1
    return {"status":"PASS" if ok else "REJECT","sample_rate":int(sr),"duration_seconds":dur,"rms":rms,"peak":peak,"finite":finite}

def align_level(seg,target=-20.0):
    seg=seg.set_frame_rate(24000).set_channels(2)
    if math.isfinite(seg.dBFS):
        seg=seg.apply_gain(max(-8.0,min(8.0,target-seg.dBFS)))
    return seg

def configure_model(source_dir,conf_dir,w2v_dir,camp_dir,big_dir,out):
    cfg=yaml.safe_load((source_dir/"config/inference_config.yaml").read_text(encoding="utf-8"))
    cfg["paths"]["tokenizer_path"]=str(conf_dir); cfg["paths"]["w2v_bert_path"]=str(w2v_dir)
    cfg["paths"]["w2v_stat"]=str(conf_dir/"wav2vec2bert_stats.pt"); cfg["paths"]["vocoder_path"]=str(big_dir)
    cfg["paths"]["style_encoder"]["checkpoint"]="campplus_cn_common.bin"; cfg["paths"]["t2s_checkpoint"]="t2s_model.safetensors"; cfg["paths"]["s2a_checkpoint"]="s2a_model.pt"
    local=out/"inference-pinned.yaml"; local.write_text(yaml.safe_dump(cfg,sort_keys=False),encoding="utf-8")
    sys.path.insert(0,str(source_dir))
    import confuciustts.cli.inference as inf
    def pinned(repo_id,filename,*a,**kw):
        if repo_id=="netease-youdao/Confucius4-TTS": p=conf_dir/filename
        elif repo_id=="funasr/campplus": p=camp_dir/filename
        else: raise RuntimeError(f"UNPINNED_HF_DOWNLOAD_REJECT:{repo_id}:{filename}")
        if not p.is_file(): raise FileNotFoundError(p)
        return str(p)
    inf.hf_hub_download=pinned
    return inf.ConfuciusTTS(config_path=str(local),device="cpu")

def write_review(out):
    html="""<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Odyssée P6 — Confucius4</title><style>body{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}audio{width:100%}label{display:block;margin:.5rem 0}fieldset{margin:1rem 0}textarea{width:100%;min-height:15rem}</style>
<h1>P6 — Ulysse émotionnel / Confucius4</h1><p>Une seule scène figée. Évaluez Ulysse, pas la technologie.</p><audio controls src='p6-confucius4.mp3'></audio>
<fieldset><legend>Impact émotionnel</legend>"""+"".join(f"<label><input type=radio name=impact value={n}> {n}/5</label>" for n in range(1,6))+"""</fieldset>
<fieldset><legend>Réaction d’Ulysse</legend><label><input type=radio name=reaction value=PASS>PASS</label><label><input type=radio name=reaction value=FAIL>FAIL</label></fieldset>
<fieldset><legend>Identité Ulysse</legend><label><input type=radio name=identity value=PASS>PASS</label><label><input type=radio name=identity value=FAIL>FAIL</label></fieldset>
<fieldset><legend>Français</legend><label><input type=radio name=french value=PASS>PASS</label><label><input type=radio name=french value=FAIL>FAIL</label></fieldset>
<fieldset><legend>Mélodrame</legend><label><input type=radio name=melodrama value=NONE>aucun</label><label><input type=radio name=melodrama value=PRESENT>présent</label></fieldset>
<fieldset><legend>Pénélope / staging</legend><label><input type=radio name=staging value=PASS>PASS</label><label><input type=radio name=staging value=FAIL>FAIL</label></fieldset>
<button id=b>Produire le verdict</button><textarea id=o></textarea><script>
const v=n=>document.querySelector('input[name="'+n+'"]:checked')?.value||null;
b.onclick=()=>{const r={schema:'odyssee-p6-confucius4-human-v1',impact:Number(v('impact'))||null,reaction:v('reaction'),identity:v('identity'),french:v('french'),melodrama:v('melodrama'),staging:v('staging')};o.value=JSON.stringify(r,null,2);navigator.clipboard?.writeText(o.value)}
</script></html>"""
    (out/"index.html").write_text(html,encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    for a in ["source-dir","confucius-model-dir","w2v-dir","campplus-dir","bigvgan-dir","baseline-audio","baseline-report","out"]: ap.add_argument("--"+a,required=True)
    x=ap.parse_args(); out=Path(x.out); out.mkdir(parents=True,exist_ok=True); raw=out/"raw"; raw.mkdir(exist_ok=True); slots=out/"slots"; slots.mkdir(exist_ok=True)
    baseline,report=load_baseline(Path(x.baseline_audio),Path(x.baseline_report)); anchor,anchor_parts=derive_anchor(baseline,report,out)
    model=configure_model(Path(x.source_dir).resolve(),Path(x.confucius_model_dir).resolve(),Path(x.w2v_dir).resolve(),Path(x.campplus_dir).resolve(),Path(x.bigvgan_dir).resolve(),out)
    rendered={}; reps=[]
    for i in sorted(TARGETS):
        random.seed(SEEDS[i]); np.random.seed(SEEDS[i]%(2**32-1)); torch.manual_seed(SEEDS[i])
        audio=model.generate(text=TARGETS[i],lang="fr",prompt_wav=str(anchor),raw=True,temperature=0.8,top_p=0.8,top_k=30,num_beams=3,repetition_penalty=10.0,max_length=512,n_timesteps=25,inference_cfg_rate=0.7,max_text_tokens_per_segment=80,verbose=True)
        p=raw/f"{i:02d}.wav"; sf.write(p,audio.detach().cpu().numpy().squeeze(),model.sample_rate,subtype="PCM_16"); g=tech(p)
        if g["status"]!="PASS": raise SystemExit(f"P6_SLOT_TECHNICAL_REJECT:{i}:{json.dumps(g)}")
        seg=align_level(AudioSegment.from_file(p)); sp=slots/f"{i:02d}.wav"; seg.export(sp,format="wav"); rendered[i]=seg
        reps.append({"i":i,"text":TARGETS[i],"seed":SEEDS[i],"raw_sha256":sha256(p),"slot_sha256":sha256(sp),"technical_gate":g,"candidate_audio_ms":len(seg)})
    b,total=bounds(report); final=AudioSegment.empty(); preserved=[]
    for s in report["segments"]:
        i=int(s["i"]); start,end,slot_end=b[i]; pause=int(s.get("pause_ms",0))
        if i in rendered:
            final+=rendered[i]
            if pause: final+=baseline[end:slot_end]
        else:
            frozen=baseline[start:slot_end]; final+=frozen
            preserved.append({"i":i,"speaker":s["speaker"],"text":s["text"],"pcm_sha256":hashlib.sha256(frozen.raw_data).hexdigest()})
    if total<len(baseline): final+=baseline[total:]
    candidate=out/"p6-confucius4.mp3"; final.export(candidate,format="mp3",bitrate="128k")
    manifest={"schema":"odyssee-p6-confucius4-one-shot-v1","status":"MACHINE_PASS","cloud_tts":False,"nuc_required":False,"baseline":{"audio_sha256":BASELINE_AUDIO_SHA256,"report_sha256":BASELINE_REPORT_SHA256},"provider":{"source_revision":SOURCE_REV,"confucius_hf_revision":CONFUCIUS_HF_REV,"w2v_revision":W2V_HF_REV,"campplus_revision":CAMPPLUS_HF_REV,"bigvgan_revision":BIGVGAN_HF_REV},"identity_anchor":{"segments":list(ANCHOR_SEGMENTS),"sha256":sha256(anchor),"parts":anchor_parts},"parameters":{"raw":True,"temperature":0.8,"top_p":0.8,"top_k":30,"num_beams":3,"repetition_penalty":10.0,"max_length":512,"n_timesteps":25,"inference_cfg_rate":0.7,"level_alignment_dbfs":-20.0,"level_alignment_max_gain_db":8.0},"slots":reps,"preserved":preserved,"candidate_sha256":sha256(candidate),"human_gate":"PENDING"}
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); write_review(out); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
