"""CPU appearance baseline and offline CityFlow association evaluator."""
from __future__ import annotations
import csv, hashlib, json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/cityflow/AICity22_Track1_MTMC_Tracking"

@dataclass(frozen=True)
class Tracklet:
    scenario: str; camera: str; local_id: int; first_s: float; last_s: float
    embedding: list[float]; gt_ids: tuple[int, ...]; evidence_frame: int; evidence_path: str

def _hist(image: np.ndarray) -> np.ndarray:
    hsv=cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h=cv2.calcHist([hsv],[0,1],None,[16,8],[0,180,0,256]).flatten().astype("float32")
    n=np.linalg.norm(h); return h/n if n else h

def _row(path: Path) -> Iterable[list[str]]:
    for line in path.read_text(errors="ignore").splitlines():
        p=line.split(",")
        if len(p)>=6: yield p

def _frame(video: Path, number: int) -> np.ndarray | None:
    cap=cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, number-1)); ok, im=cap.read(); cap.release(); return im if ok else None

def load_tracklets(start_s: float, end_s: float, scenario: str="S04", baseline_name: str="mtsc_deepsort_mask_rcnn.txt", max_tracklets: int = 30) -> list[Tracklet]:
    offsets={r[0]:float(r[1]) for r in (x.split() for x in (DATA/'cam_timestamp'/f'{scenario}.txt').read_text().splitlines())}
    out=[]
    for camdir in sorted((DATA/'train'/scenario).glob('c*')):
        cam=camdir.name; path=camdir/'mtsc'/baseline_name
        if not path.exists(): continue
        groups: dict[int,list[list[str]]]={}
        for p in _row(path):
            lid=int(p[1]); frame=int(p[0]); t=offsets[cam]+(frame-1)/10
            if start_s<=t<=end_s: groups.setdefault(lid,[]).append(p)
        for lid, rows in groups.items():
            rows.sort(key=lambda p:int(p[0])); first,last=rows[0],rows[-1]
            frame=int(rows[len(rows)//2][0]); im=_frame(camdir/'vdo.avi',frame)
            if im is None: continue
            x,y,w,h=map(float, rows[len(rows)//2][2:6]); crop=im[max(0,int(y)):max(1,int(y+h)),max(0,int(x)):max(1,int(x+w))]
            if crop.size==0: continue
            gtpath=camdir/'gt'/'gt.txt'; gids=set()
            if gtpath.exists():
                for g in _row(gtpath):
                    if int(g[0])==frame and abs(float(g[2])-x)<3 and abs(float(g[3])-y)<3: gids.add(int(g[1]))
            out.append(Tracklet(scenario,cam,lid,offsets[cam]+(int(first[0])-1)/10,offsets[cam]+(int(last[0])-1)/10,_hist(crop).tolist(),tuple(sorted(gids)),frame,str((camdir/'vdo.avi').relative_to(ROOT))))
            if len(out) >= max_tracklets: return out
    return out

def associate(tracklets: list[Tracklet], max_gap_s: float=45.0, min_similarity: float=.72, margin: float=.03) -> tuple[list[dict],dict[str,str]]:
    ordered=sorted(tracklets,key=lambda t:(t.first_s,t.camera,t.local_id)); groups=[]; links=[]
    for t in ordered:
        candidates=[]
        for gi,g in enumerate(groups):
            prev=g[-1]
            if prev.camera==t.camera or t.first_s<prev.last_s or t.first_s-prev.last_s>max_gap_s: continue
            sim=float(np.dot(prev.embedding,t.embedding)); candidates.append((sim,gi))
        candidates.sort(reverse=True)
        if candidates and candidates[0][0]>=min_similarity and (len(candidates)==1 or candidates[0][0]-candidates[1][0]>=margin):
            sim,gi=candidates[0]; prev=groups[gi][-1]; groups[gi].append(t)
            links.append({"from_camera":prev.camera,"from_local_id":prev.local_id,"to_camera":t.camera,"to_local_id":t.local_id,"similarity":sim,"temporal_gap_s":t.first_s-prev.last_s,"reason":"HSV appearance cosine + forward time + distinct camera"})
        else: groups.append([t])
    ids={f"{t.camera}:{t.local_id}":f"roadeye_{i:05d}" for i,g in enumerate(groups) for t in g}
    return links,ids

def evaluate(tracklets: list[Tracklet], ids: dict[str,str], links: list[dict]) -> dict:
    by_global={};
    for t in tracklets:
        rid=ids.get(f'{t.camera}:{t.local_id}');
        if rid: by_global.setdefault(rid,set()).update(t.gt_ids)
    predicted_pairs=correct_pairs=0
    for l in links:
        predicted_pairs+=1
        a=ids.get(f"{l['from_camera']}:{l['from_local_id']}"); b=ids.get(f"{l['to_camera']}:{l['to_local_id']}")
        ga=next((t.gt_ids for t in tracklets if f'{t.camera}:{t.local_id}'==f"{l['from_camera']}:{l['from_local_id']}"),())
        gb=next((t.gt_ids for t in tracklets if f'{t.camera}:{t.local_id}'==f"{l['to_camera']}:{l['to_local_id']}"),())
        if set(ga)&set(gb): correct_pairs+=1
    return {"tracklets":len(tracklets),"predicted_links":predicted_pairs,"correct_links":correct_pairs,"link_precision":correct_pairs/predicted_pairs if predicted_pairs else None,"global_ids":len(set(ids.values())),"gt_coverage_tracklets":sum(bool(t.gt_ids) for t in tracklets),"runtime_gt_used":False}

def run(start_s:float=10.1,end_s:float=204.044)->dict:
    ts=load_tracklets(start_s,end_s); links,ids=associate(ts); metrics=evaluate(ts,ids,links)
    out=ROOT/'artifacts/phase2'; out.mkdir(parents=True,exist_ok=True)
    (out/'tracklets.json').write_text(json.dumps([asdict(t) for t in ts],indent=2)); (out/'links.json').write_text(json.dumps(links,indent=2)); (out/'global_ids.json').write_text(json.dumps(ids,indent=2)); (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    return metrics

if __name__=='__main__': print(json.dumps(run(),indent=2))
