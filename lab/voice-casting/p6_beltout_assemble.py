#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import librosa, numpy as np, soundfile as sf, torch, torch.nn.functional as F, torchaudio
from pydub import AudioSegment

BASELINE_AUDIO_SHA256="474c2e41a5d702b2a84524aa3be9a0559ed7378af18d507ac082b666029d64ae"
BASELINE_REPORT_SHA256="366091a73e7597626384535e900a5b30e7943c485d0197ec25f015c384b6d891"
ANCHOR_SEGMENTS=(6,7,8)
TARGETS={2:"Non.",4:"Ce lit ne sort pas de cette chambre.",10:"Tu le savais.",12:"Pénélope…",15:"Notre lit."}
BELTOUT_REV="f71295e33cc9c0092083089ed0f9c1a532e77e6b"
CHECKPOINTS={"decoder":"cfm_step_117580.safetensors","pitch":"pitchmvmt_step_117580.safetensors","encoder":"encoder_step_0.safetensors","flow":"flow_step_0.safetensors","mel2wav":"mel2wav_step_0.safetensors","speaker":"speaker_encoder_step_0.safetensors","tokenizer":"tokenizer_step_0.safetensors"}

def sha256(p:Path):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()

def cosine(a,b):
 return float(F.cosine_similarity(a.detach().float().reshape(1,-1).cpu(),b.detach().float().reshape(1,-1).cpu(),dim=1).item())

def gate(p:Path):
 y,sr=sf.read(p,dtype="float32",always_2d=False); y=np.asarray(y,dtype=np.float32)
 if y.ndim==2:y=y.mean(1)
 dur=len(y)/sr if sr else 0; rms=float(np.sqrt(np.mean(y*y))) if len(y) else 0; peak=float(np.max(np.abs(y))) if len(y) else 0
 ok=bool(np.isfinite(y).all()) and .08<=dur<=14 and .0015<=rms<=.8 and peak<=1
 return {"status":"PASS" if ok else "REJECT","sample_rate":int(sr),"duration_seconds":float(dur),"rms":rms,"peak":peak}

def load_baseline(audio,report_path):
 if sha256(audio)!=BASELINE_AUDIO_SHA256: raise SystemExit("BASELINE_AUDIO_SHA_REJECT")
 if sha256(report_path)!=BASELINE_REPORT_SHA256: raise SystemExit("BASELINE_REPORT_SHA_REJECT")
 report=json.loads(report_path.read_text(encoding="utf-8")); by={int(x["i"]):x for x in report["segments"]}
 for i,t in TARGETS.items():
  s=by.get(i)
  if not s or s.get("speaker")!="Ulysse" or s.get("text")!=t: raise SystemExit(f"TARGET_BINDING_REJECT:{i}")
 base=AudioSegment.from_file(audio).set_frame_rate(24000).set_channels(2)
 return base,report

def bounds(report):
 out={}; cur=0
 for s in report["segments"]:
  i=int(s["i"]); a=int(s["audio_ms"]); p=int(s.get("pause_ms",0)); out[i]=(cur,cur+a,cur+a+p); cur+=a+p
 return out,cur

def derive_anchor(base,report,out):
 b,_=bounds(report); mono=AudioSegment.empty()
 for n,i in enumerate(ANCHOR_SEGMENTS):
  st,en,_=b[i]; mono+=base[st:en].set_frame_rate(24000).set_channels(1)
  if n<len(ANCHOR_SEGMENTS)-1: mono+=AudioSegment.silent(duration=160,frame_rate=24000)
 p=out/"ulysse-henri-anchor.wav"; mono.export(p,format="wav"); return p

def convert(model,source,target_x):
 wav24=torch.from_numpy(source).float().unsqueeze(0)
 wav16=torchaudio.functional.resample(wav24,model.sr,16000)
 with torch.inference_mode():
  tok,_=model.tokenizer(wav16); spk=model.flow.spk_embed_affine_layer(target_x)
  emb=model.flow.input_embedding(tok); lens=torch.tensor([emb.shape[1]])
  h,_=model.encoder(emb,lens); mu=model.flow.encoder_proj(h).transpose(1,2); ml=mu.shape[2]
  hop=160; need=ml*2*hop; padded=wav16
  if need>padded.shape[1]: padded=F.pad(padded,(0,need-padded.shape[1]))
  import torchcrepe
  ce=torchcrepe.embed(padded,16000,hop_length=hop,model="tiny",device="cpu")[:,:ml*2,:,:]
  pi=ce.reshape(-1,2,256); pf=model.pitchmvmt(pi); pitch=pf.reshape(1,-1,80).transpose(1,2)
  mask=torch.ones(1,1,mu.shape[2],dtype=torch.bool)
  mel,_=model.decoder(mu=mu,mask=mask,spks=spk,cond=pitch,n_timesteps=10); wav,_=model.mel2wav.inference(speech_feat=mel)
 return wav.squeeze().cpu().numpy().astype(np.float32)

def review_html(out):
 html="""<!doctype html><html lang=fr><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>P6 VoiceDesign→BeltOut</title><style>body{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}audio,textarea{width:100%}label{display:block;margin:.5rem}fieldset{margin:1rem 0}</style><h1>P6 — Ulysse / VoiceDesign → BeltOut</h1><audio controls src="p6-voicedesign-beltout.mp3"></audio><fieldset><legend>Impact</legend>"""+"".join(f"<label><input type=radio name=impact value={i}>{i}/5</label>" for i in range(1,6))+"""</fieldset><fieldset><legend>Réaction</legend><label><input type=radio name=reaction value=PASS>PASS</label><label><input type=radio name=reaction value=FAIL>FAIL</label></fieldset><fieldset><legend>Identité</legend><label><input type=radio name=identity value=PASS>PASS</label><label><input type=radio name=identity value=FAIL>FAIL</label></fieldset><fieldset><legend>Français</legend><label><input type=radio name=french value=PASS>PASS</label><label><input type=radio name=french value=FAIL>FAIL</label></fieldset><fieldset><legend>Mélodrame</legend><label><input type=radio name=melodrama value=NONE>NONE</label><label><input type=radio name=melodrama value=PRESENT>PRESENT</label></fieldset><fieldset><legend>Staging</legend><label><input type=radio name=staging value=PASS>PASS</label><label><input type=radio name=staging value=FAIL>FAIL</label></fieldset><button id=b>Produire JSON</button><textarea id=o></textarea><script>const v=n=>document.querySelector('input[name="'+n+'"]:checked')?.value||null;b.onclick=()=>{o.value=JSON.stringify({schema:'odyssee-p6-voicedesign-beltout-human-v1',impact:Number(v('impact'))||null,reaction:v('reaction'),identity:v('identity'),french:v('french'),melodrama:v('melodrama'),staging:v('staging')},null,2);navigator.clipboard?.writeText(o.value)}</script></html>"""
 (out/"index.html").write_text(html,encoding="utf-8")

def main():
 ap=argparse.ArgumentParser()
 for n in ["beltout-source","checkpoint-dir","donors-dir","baseline-audio","baseline-report","out"]: ap.add_argument("--"+n,required=True)
 a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True); slots=out/"slots"; slots.mkdir(exist_ok=True)
 base,report=load_baseline(Path(a.baseline_audio),Path(a.baseline_report)); anchor=derive_anchor(base,report,out)
 dman=json.loads((Path(a.donors_dir)/"donors.json").read_text(encoding="utf-8")); rec={int(x["i"]):x for x in dman["records"]}
 if set(rec)!=set(TARGETS): raise SystemExit("DONOR_SET_REJECT")
 for i,t in TARGETS.items():
  if rec[i]["text"]!=t or sha256(Path(a.donors_dir)/rec[i]["file"])!=rec[i]["sha256"]: raise SystemExit(f"DONOR_BINDING_REJECT:{i}")
 ck=Path(a.checkpoint_dir)
 for f in CHECKPOINTS.values():
  if not (ck/f).is_file(): raise SystemExit(f"MISSING_CHECKPOINT:{f}")
 sys.path.insert(0,str(Path(a.beltout_source).resolve()/"src")); from beltout import BeltOutTTM
 model=BeltOutTTM.from_local(*(str(ck/CHECKPOINTS[k]) for k in ["decoder","pitch","encoder","flow","mel2wav","speaker","tokenizer"]),device="cpu")
 ay,_=librosa.load(anchor,sr=model.sr,mono=True); at=torch.from_numpy(ay).float().unsqueeze(0)
 with torch.inference_mode(): target_x=model.embed_ref_x_vector(at,model.sr,device="cpu")
 results=[]; converted={}
 for i in sorted(TARGETS):
  sp=Path(a.donors_dir)/rec[i]["file"]; sy,_=librosa.load(sp,sr=model.sr,mono=True); st=torch.from_numpy(sy).float().unsqueeze(0)
  with torch.inference_mode(): source_x=model.embed_ref_x_vector(st,model.sr,device="cpu")
  oy=convert(model,sy,target_x); op=slots/f"{i:02d}.wav"; sf.write(op,oy,model.sr,subtype="PCM_16"); g=gate(op)
  if g["status"]!="PASS": raise SystemExit(f"SLOT_TECH_REJECT:{i}")
  ot=torch.from_numpy(librosa.load(op,sr=model.sr,mono=True)[0]).float().unsqueeze(0)
  with torch.inference_mode(): out_x=model.embed_ref_x_vector(ot,model.sr,device="cpu")
  s2t=cosine(source_x,target_x); o2t=cosine(out_x,target_x); o2s=cosine(out_x,source_x); ratio=g["duration_seconds"]/rec[i]["technical_gate"]["duration_seconds"]
  direction=o2t>s2t
  if not (.75<=ratio<=1.25 and direction): raise SystemExit(f"SLOT_CAPABILITY_REJECT:{i}:{ratio}:{s2t}:{o2t}")
  seg=AudioSegment.from_file(op).set_frame_rate(24000).set_channels(2)
  if math.isfinite(seg.dBFS): seg=seg.apply_gain(max(-8,min(8,-20-seg.dBFS)))
  converted[i]=seg; results.append({"i":i,"text":TARGETS[i],"source_sha256":rec[i]["sha256"],"output_sha256":sha256(op),"technical_gate":g,"duration_ratio":ratio,"cosine_source_to_target":s2t,"cosine_output_to_target":o2t,"cosine_output_to_source":o2s,"direction_pass":direction})
 b,total=bounds(report); final=AudioSegment.empty(); preserved=[]
 for s in report["segments"]:
  i=int(s["i"]); st,en,se=b[i]
  if i in converted:
   final+=converted[i]
   if se>en: final+=base[en:se]
  else:
   fr=base[st:se]; final+=fr; preserved.append({"i":i,"pcm_sha256":hashlib.sha256(fr.raw_data).hexdigest()})
 if total<len(base): final+=base[total:]
 cand=out/"p6-voicedesign-beltout.mp3"; final.export(cand,format="mp3",bitrate="128k")
 man={"schema":"odyssee-p6-voicedesign-beltout-one-shot-v1","status":"MACHINE_PASS","cloud_tts":False,"nuc_required":False,"baseline":{"audio_sha256":BASELINE_AUDIO_SHA256,"report_sha256":BASELINE_REPORT_SHA256},"beltout_revision":BELTOUT_REV,"anchor_sha256":sha256(anchor),"slots":results,"preserved":preserved,"candidate_sha256":sha256(cand),"human_gate":"PENDING"}
 (out/"manifest.json").write_text(json.dumps(man,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); review_html(out); print(json.dumps(man,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
