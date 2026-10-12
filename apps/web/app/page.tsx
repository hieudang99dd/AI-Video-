"use client";
import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Project = { id:string; name:string; status:string };
type Asset = { id:string; filename:string; analyzed:boolean; width?:number; height?:number };
type Shot = { id:string; name:string; mode:string; duration_sec:number; fps:number };
type Job = { id:string; status:string; progress:number; error?:string|null; output_uri?:string|null; provenance:Record<string,unknown> };

export default function Home() {
  const [projects,setProjects]=useState<Project[]>([]);
  const [projectId,setProjectId]=useState("");
  const [assets,setAssets]=useState<Asset[]>([]);
  const [selected,setSelected]=useState<string[]>([]);
  const [shot,setShot]=useState<Shot|null>(null);
  const [job,setJob]=useState<Job|null>(null);
  const [message,setMessage]=useState("");
  const current = useMemo(()=>projects.find(p=>p.id===projectId),[projects,projectId]);

  async function loadProjects(){ const r=await fetch(`${API}/api/v1/projects`); const d=await r.json(); setProjects(d); if(!projectId && d[0]) setProjectId(d[0].id); }
  async function loadAssets(pid=projectId){ if(!pid)return; const r=await fetch(`${API}/api/v1/projects/${pid}/assets`); setAssets(await r.json()); }
  useEffect(()=>{ loadProjects().catch(()=>{}); },[]);
  useEffect(()=>{ setSelected([]); setShot(null); setJob(null); loadAssets().catch(()=>{}); },[projectId]);
  useEffect(()=>{ if(!job || ["completed","failed","cancelled"].includes(job.status)) return; const t=setInterval(async()=>{ const r=await fetch(`${API}/api/v1/render-jobs/${job.id}`); setJob(await r.json()); },1200); return()=>clearInterval(t); },[job]);

  async function createProject(fd:FormData){ const name=String(fd.get("name")||"").trim(); if(!name)return; const r=await fetch(`${API}/api/v1/projects`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({name})}); const p=await r.json(); await loadProjects(); setProjectId(p.id); }
  async function upload(files:FileList|null){ if(!files||!projectId)return; setMessage("Uploading..."); for(const f of Array.from(files)){ const fd=new FormData(); fd.append("file",f); const r=await fetch(`${API}/api/v1/projects/${projectId}/assets`,{method:"POST",body:fd}); if(!r.ok) setMessage(`Upload failed: ${await r.text()}`); } await loadAssets(); setMessage("Upload complete"); }
  async function analyze(){ setMessage("Analyzing images..."); const r=await fetch(`${API}/api/v1/projects/${projectId}/analyze`,{method:"POST"}); const d=await r.json(); setMessage(`Suggested mode: ${d.suggested_mode}`); await loadAssets(); }
  async function createShot(){ if(!selected.length)return; const r=await fetch(`${API}/api/v1/projects/${projectId}/shots`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({name:"Shot 01",asset_ids:selected,duration_sec:5,fps:30,mode:"auto",easing:"cinematic"})}); setShot(await r.json()); }
  async function preview(){ if(!shot)return; const r=await fetch(`${API}/api/v1/shots/${shot.id}/preview`,{method:"POST"}); setJob(await r.json()); }
  function toggle(id:string){ setSelected(s=>s.includes(id)?s.filter(x=>x!==id):[...s,id]); }

  return <main>
    <h1>CineVideo Core MVP</h1>
    <p className="muted">Geometry-first architecture. Safe fallback now; COLMAP/3DGS is an explicit next capability, never faked.</p>

    <div className="grid">
      <section className="card">
        <h2>1. Project</h2>
        <form action={createProject}><input name="name" placeholder="Villa demo"/><button>Create project</button></form>
        <select value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">Select project</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select>
        {current && <span className="badge">{current.status}</span>}
      </section>

      <section className="card">
        <h2>2. Upload & Analyze</h2>
        <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={e=>upload(e.target.files)}/>
        <button className="secondary" disabled={!assets.length} onClick={analyze}>Analyze</button>
        <p className="muted">{message}</p>
      </section>
    </div>

    <section className="card">
      <h2>3. Storyboard</h2>
      {assets.length===0?<p className="muted">Upload images first.</p>:assets.map(a=><label className="asset" key={a.id}><input style={{width:18,margin:0}} type="checkbox" checked={selected.includes(a.id)} onChange={()=>toggle(a.id)}/><div><strong>{a.filename}</strong><div className="muted">{a.analyzed?`${a.width}×${a.height} · analyzed`:"not analyzed"}</div></div></label>)}
      <br/><button disabled={!selected.length} onClick={createShot}>Create 5s shot</button>
      {shot && <p><span className="badge">{shot.mode}</span>{shot.duration_sec}s · {shot.fps}fps</p>}
    </section>

    <section className="card">
      <h2>4. Render</h2>
      <button disabled={!shot} onClick={preview}>Render preview</button>
      {job && <div style={{marginTop:16}}><p><strong>{job.status}</strong> · {Math.round(job.progress*100)}%</p><div className="progress"><div style={{width:`${job.progress*100}%`}}/></div>{job.error&&<pre>{job.error}</pre>}{job.status==="completed"&&<p><a href={`${API}/api/v1/render-jobs/${job.id}/download`}>Download MP4</a></p>}<pre>{JSON.stringify(job.provenance,null,2)}</pre></div>}
    </section>
  </main>
}
