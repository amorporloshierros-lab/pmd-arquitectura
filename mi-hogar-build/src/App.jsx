import { useState, useEffect, useRef } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from "recharts";

// ─── ASSETS ───────────────────────────────────────────────────────────────
const boot = () => {
  if (document.getElementById("pmd4")) return;
  const l = document.createElement("link");
  l.id = "pmd4"; l.rel = "stylesheet";
  l.href = "https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900&family=JetBrains+Mono:wght@400;700;800&display=swap";
  document.head.appendChild(l);
  const s = document.createElement("style");
  s.innerHTML = `
    *{box-sizing:border-box;margin:0;padding:0;}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
    @keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(74,222,128,.4)}70%{box-shadow:0 0 0 8px rgba(74,222,128,0)}}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
    .up{animation:up .25s ease}
    .hl{transition:all .18s;} .hl:hover{transform:translateY(-2px);box-shadow:0 10px 32px rgba(30,58,95,.11)!important}
    .btn{transition:all .14s;cursor:pointer;font-family:'DM Sans',sans-serif;}
    .btn:hover{filter:brightness(1.07);transform:translateY(-1px);}
    input,textarea,select{font-family:'DM Sans',sans-serif!important;outline:none;}
    ::-webkit-scrollbar{width:4px;height:4px}
    ::-webkit-scrollbar-thumb{background:#ddd;border-radius:4px}
    .inpEdit{border:1.5px solid transparent;background:transparent;border-radius:8px;padding:4px 8px;font-size:12px;color:#1E2A3A;width:100%;}
    .inpEdit:focus{border-color:#3A6EA5;background:#fff;}
    .inpEdit:hover{background:#F0EDE8;}
  `;
  document.head.appendChild(s);
};

// ─── PALETTE ──────────────────────────────────────────────────────────────
const C = {
  bg:"#F0EDE8", card:"#FFF",
  b1:"#5B8EC2", b2:"#3A6EA5", b3:"#1E3A5F",
  txt:"#1E2A3A", txt2:"#5C6A7A", dim:"#94A0AE", border:"#E2DED8", tag:"#EAF0F8",
  green:"#2D8B57", gBg:"#EAF6F0",
  red:"#B8453A", rBg:"#FAEEED",
  amber:"#A07020", aBg:"#FEF3E2", aBorder:"#F0C060",
  purple:"#6B48CC", pBg:"#F0ECFF",
};
const fmt  = n => new Intl.NumberFormat("es-AR").format(Math.round(n));
const fmtD = n => n == null ? "" : (Math.round(n * 100) / 100).toString();

// ─── TOKEN STORAGE ────────────────────────────────────────────────────────
const TOKEN_KEY = "pmd_mi_hogar_token";
const getToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
const setToken = (t) => { try { localStorage.setItem(TOKEN_KEY, t); } catch {} };
const clearToken = () => { try { localStorage.removeItem(TOKEN_KEY); } catch {} };

const apiCall = async (url, options = {}) => {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  return res.json();
};

// ─── SHARED COMPONENTS ────────────────────────────────────────────────────
const Logo = ({size=28,dark=false}) => {
  const [active,setActive] = useState(0);
  const sq = Math.round(size * 0.46);
  const pmdSize = Math.max(size * 0.82, 16);
  const archSize = Math.max(size * 0.55, 15);
  useEffect(()=>{
    const t = setInterval(()=>setActive(p=>(p+1)%3), 300);
    return ()=>clearInterval(t);
  },[]);
  return (
    <div style={{display:"flex",gap:8,alignItems:"center"}}>
      <div style={{display:"flex",gap:3,alignItems:"center",flexShrink:0}}>
        {[C.b1,C.b2,C.b3].map((col,i)=>(
          <div key={i} style={{width:sq,height:sq,background:col,borderRadius:3,opacity:active===i?1:0.25,transition:"opacity 0.2s ease"}}/>
        ))}
      </div>
      <div style={{display:"flex",alignItems:"baseline",gap:5,flexShrink:0}}>
        <span style={{fontFamily:"'DM Sans',sans-serif",fontWeight:900,color:dark?"#fff":C.b3,fontSize:pmdSize,letterSpacing:"-.03em",lineHeight:1,whiteSpace:"nowrap"}}>PMD</span>
        <span style={{fontFamily:"'DM Sans',sans-serif",fontWeight:800,color:dark?"#fff":C.b3,fontSize:archSize,letterSpacing:".01em",lineHeight:1,whiteSpace:"nowrap"}}>arquitectura</span>
      </div>
    </div>
  );
};
const Badge = ({status}) => {
  const m={paid:{bg:C.gBg,col:C.green,lbl:"Pagado"},pending:{bg:C.aBg,col:C.amber,lbl:"Pendiente"},approved:{bg:C.gBg,col:C.green,lbl:"Aprobada"},rejected:{bg:C.rBg,col:C.red,lbl:"Rechazada"},vigente:{bg:C.tag,col:C.b2,lbl:"Vigente"},emitido:{bg:C.pBg,col:C.purple,lbl:"Emitido"}}[status]||{bg:"#eee",col:"#666",lbl:status};
  return <span style={{padding:"3px 9px",borderRadius:999,background:m.bg,color:m.col,fontSize:10,fontWeight:800,letterSpacing:".05em",fontFamily:"'DM Sans',sans-serif",textTransform:"uppercase",whiteSpace:"nowrap"}}>{m.lbl}</span>;
};
const Mono = ({ch,size=14,color=C.b2,weight=700}) => <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:size,color,fontWeight:weight}}>{ch}</span>;
const Card = ({children,style={}}) => <div style={{background:C.card,borderRadius:20,border:`1px solid ${C.border}`,boxShadow:"0 2px 12px rgba(30,58,95,.05)",...style}}>{children}</div>;

// ─── SPLASH (mientras carga la sesión inicial) ────────────────────────────
const Splash = () => (
  <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans',sans-serif"}}>
    <div style={{textAlign:"center"}}>
      <div style={{display:"flex",justifyContent:"center",marginBottom:18}}><Logo size={42}/></div>
      <p style={{color:C.txt2,fontSize:13}}>Cargando...</p>
    </div>
  </div>
);

// ─── LOGIN (usa /api/mi-hogar/login) ──────────────────────────────────────
const Login = ({onLogin, onForgot}) => {
  const [email,setEmail]=useState(""); const [pass,setPass]=useState("");
  const [err,setErr]=useState(""); const [loading,setLoading]=useState(false);
  const go = async () => {
    setErr(""); setLoading(true);
    try {
      const data = await apiCall("/api/mi-hogar/login", { method: "POST", body: JSON.stringify({ email, password: pass }) });
      if (data.ok) {
        setToken(data.token);
        onLogin(data.user, data.token);
      } else {
        setErr(data.error || "Error de login.");
      }
    } catch (e) { setErr("Problema de conexion. Reintenta."); }
    setLoading(false);
  };
  return (
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans',sans-serif"}}>
      <div style={{position:"fixed",inset:0,backgroundImage:`linear-gradient(${C.border} 1px,transparent 1px),linear-gradient(90deg,${C.border} 1px,transparent 1px)`,backgroundSize:"48px 48px",opacity:.4,pointerEvents:"none"}}/>
      <div className="up" style={{position:"relative",width:"100%",maxWidth:420,padding:"0 20px"}}>
        <div style={{textAlign:"center",marginBottom:28}}>
          <div style={{display:"flex",justifyContent:"center",marginBottom:18}}><Logo size={42}/></div>
          <h1 style={{fontSize:30,fontWeight:900,color:C.b3,letterSpacing:"-.04em",marginBottom:5}}>Mi Hogar</h1>
          <p style={{color:C.txt2,fontSize:13}}>Portal privado de seguimiento de obra</p>
        </div>
        <Card style={{padding:30,boxShadow:"0 12px 60px rgba(30,58,95,.12)"}}>
          {[["Email","email","tu@mail.com",email,setEmail],["Contrasena","password","........",pass,setPass]].map(([lbl,type,ph,val,set])=>(
            <div key={lbl} style={{marginBottom:12}}>
              <label style={{display:"block",fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".1em",marginBottom:5}}>{lbl}</label>
              <input type={type} value={val} onChange={e=>set(e.target.value)} onKeyDown={e=>e.key==="Enter"&&go()} placeholder={ph} disabled={loading}
                style={{width:"100%",padding:"11px 14px",border:`1.5px solid ${C.border}`,borderRadius:12,background:C.bg,color:C.txt,fontSize:14}}/>
            </div>
          ))}
          {err&&<p style={{color:C.red,fontSize:13,marginBottom:12,padding:"9px 13px",background:C.rBg,borderRadius:9}}>{err}</p>}
          <button className="btn" onClick={go} disabled={loading||!email||!pass} style={{width:"100%",padding:13,background:loading?C.dim:C.b2,color:"#fff",border:"none",borderRadius:12,fontSize:15,fontWeight:800}}>
            {loading?"Ingresando...":"Ingresar"}
          </button>
          <div style={{textAlign:"center",marginTop:14}}>
            <button onClick={onForgot} className="btn" style={{background:"none",border:"none",color:C.b2,fontSize:12,fontWeight:600,padding:6}}>Olvide mi contrasena</button>
          </div>
        </Card>
      </div>
    </div>
  );
};

// ─── SET PASSWORD (cuando viene con ?invite=xxx o ?reset=xxx) ─────────────
const SetPasswordForm = ({token, onDone}) => {
  const [p1,setP1]=useState(""); const [p2,setP2]=useState("");
  const [err,setErr]=useState(""); const [loading,setLoading]=useState(false);
  const submit = async () => {
    setErr("");
    if (p1.length < 4) return setErr("La contrasena debe tener al menos 4 caracteres.");
    if (p1 !== p2) return setErr("Las contrasenas no coinciden.");
    setLoading(true);
    try {
      const data = await apiCall("/api/mi-hogar/set-password", { method: "POST", body: JSON.stringify({ token, password: p1 }) });
      if (data.ok) {
        setToken(data.token);
        window.history.replaceState({}, "", "/mi-hogar");
        onDone(data.user, data.token);
      } else {
        setErr(data.error || "Token invalido o expirado.");
      }
    } catch { setErr("Problema de conexion. Reintenta."); }
    setLoading(false);
  };
  return (
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans',sans-serif"}}>
      <div className="up" style={{width:"100%",maxWidth:420,padding:"0 20px"}}>
        <div style={{textAlign:"center",marginBottom:28}}>
          <div style={{display:"flex",justifyContent:"center",marginBottom:18}}><Logo size={42}/></div>
          <h1 style={{fontSize:24,fontWeight:900,color:C.b3,letterSpacing:"-.03em",marginBottom:5}}>Crea tu contrasena</h1>
          <p style={{color:C.txt2,fontSize:13}}>Eligi una contrasena para tu cuenta de Mi Hogar.</p>
        </div>
        <Card style={{padding:30,boxShadow:"0 12px 60px rgba(30,58,95,.12)"}}>
          {[["Nueva contrasena",p1,setP1],["Repetir contrasena",p2,setP2]].map(([lbl,v,s])=>(
            <div key={lbl} style={{marginBottom:12}}>
              <label style={{display:"block",fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".1em",marginBottom:5}}>{lbl}</label>
              <input type="password" value={v} onChange={e=>s(e.target.value)} onKeyDown={e=>e.key==="Enter"&&submit()} disabled={loading}
                style={{width:"100%",padding:"11px 14px",border:`1.5px solid ${C.border}`,borderRadius:12,background:C.bg,color:C.txt,fontSize:14}}/>
            </div>
          ))}
          {err&&<p style={{color:C.red,fontSize:13,marginBottom:12,padding:"9px 13px",background:C.rBg,borderRadius:9}}>{err}</p>}
          <button className="btn" onClick={submit} disabled={loading||!p1||!p2} style={{width:"100%",padding:13,background:loading?C.dim:C.b2,color:"#fff",border:"none",borderRadius:12,fontSize:15,fontWeight:800}}>
            {loading?"Guardando...":"Crear contrasena y entrar"}
          </button>
        </Card>
      </div>
    </div>
  );
};

// ─── FORGOT PASSWORD ──────────────────────────────────────────────────────
const ForgotPasswordForm = ({onBack}) => {
  const [email,setEmail]=useState(""); const [sent,setSent]=useState(false);
  const [loading,setLoading]=useState(false); const [err,setErr]=useState("");
  const submit = async () => {
    setErr(""); setLoading(true);
    try {
      const data = await apiCall("/api/mi-hogar/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
      if (data.ok) { setSent(true); }
      else setErr(data.error || "Error.");
    } catch { setErr("Problema de conexion."); }
    setLoading(false);
  };
  return (
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans',sans-serif"}}>
      <div className="up" style={{width:"100%",maxWidth:420,padding:"0 20px"}}>
        <div style={{textAlign:"center",marginBottom:28}}>
          <div style={{display:"flex",justifyContent:"center",marginBottom:18}}><Logo size={42}/></div>
          <h1 style={{fontSize:24,fontWeight:900,color:C.b3,letterSpacing:"-.03em",marginBottom:5}}>Olvidaste tu contrasena</h1>
          <p style={{color:C.txt2,fontSize:13}}>Te enviamos un mail con un link para crear una nueva.</p>
        </div>
        <Card style={{padding:30,boxShadow:"0 12px 60px rgba(30,58,95,.12)"}}>
          {!sent ? (
            <>
              <div style={{marginBottom:12}}>
                <label style={{display:"block",fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".1em",marginBottom:5}}>Email</label>
                <input type="email" value={email} onChange={e=>setEmail(e.target.value)} onKeyDown={e=>e.key==="Enter"&&submit()} disabled={loading}
                  style={{width:"100%",padding:"11px 14px",border:`1.5px solid ${C.border}`,borderRadius:12,background:C.bg,color:C.txt,fontSize:14}}/>
              </div>
              {err&&<p style={{color:C.red,fontSize:13,marginBottom:12,padding:"9px 13px",background:C.rBg,borderRadius:9}}>{err}</p>}
              <button className="btn" onClick={submit} disabled={loading||!email} style={{width:"100%",padding:13,background:loading?C.dim:C.b2,color:"#fff",border:"none",borderRadius:12,fontSize:15,fontWeight:800}}>
                {loading?"Enviando...":"Enviar link"}
              </button>
            </>
          ) : (
            <div style={{textAlign:"center",padding:"20px 0"}}>
              <p style={{fontSize:14,color:C.green,fontWeight:700,marginBottom:8}}>Mail enviado</p>
              <p style={{fontSize:13,color:C.txt2}}>Revisa tu inbox (y spam) para el link de recuperacion.</p>
            </div>
          )}
          <div style={{textAlign:"center",marginTop:14}}>
            <button onClick={onBack} className="btn" style={{background:"none",border:"none",color:C.b2,fontSize:12,fontWeight:600,padding:6}}>Volver al login</button>
          </div>
        </Card>
      </div>
    </div>
  );
};

// ─── BUILD SYSTEM PROMPT (chat asesor — nombre custom por proyecto) ───────
const buildSP = (project, milestones, cac, updates) => {
  const advisorName = (project && project.advisor_name_in_chat) || "Valentina";
  if (!project || !milestones) return `Sos ${advisorName}, asesor/a de PMD. Respondé corto, en español rioplatense.`;
  const paid = milestones.filter(m=>m.status==="paid").reduce((s,m)=>s+m.usd,0);
  const total = milestones.reduce((s,m)=>s+m.usd,0);
  const next = milestones.find(m=>m.status==="pending");
  const cacVar = cac ? ((cac.current.value-cac.base.value)/cac.base.value*100).toFixed(2) : "0";
  return `Sos ${advisorName}, asesor/a comercial y tecnico/a de PMD Soluciones Arquitectonicas. Cordial, directa/o, espanol rioplatense.

IDENTIDAD - MUY IMPORTANTE:
Sos ${advisorName}, parte del equipo PMD. Nunca digas que sos IA, bot, asistente virtual ni nada por el estilo. Si te preguntan si sos real o humano/a, respondé natural: "Si, soy parte del equipo PMD aca para ayudarte." Nunca rompas el personaje.

PROYECTO ACTIVO: ${project.name} (${project.id}) - Cliente: ${project.client_id || project.client}
Sistema: ${project.system} - ${project.totalM2}m2 - ${project.location}
Avance: ${project.overallProgress}% - Fin estimado: ${project.estimatedEnd}

FINANZAS: Total USD ${fmt(total)} - Pagado USD ${fmt(paid)} - Saldo USD ${fmt(total-paid)}
${next ? `Proximo hito: "${next.name}" - USD ${fmt(next.usd)}` : ""}
CAC acumulado: +${cacVar}%

ULTIMA UPDATE (${updates?.[0]?.date || "-"}): ${updates?.[0]?.summary || "Sin datos"}

REGLAS: Siempre da respuestas concretas con rangos de precio cuando corresponda. Maximo 5 oraciones. Nunca pidas datos de contacto (ya los tenemos). Cerra con accion: "agendar llamada" o "cargar solicitud formal en el portal". Si excede tu conocimiento decir "te paso con Lucas". Decisiones ejecutivas: "le aviso a Augusto".`;
};

// ─── CHAT WIDGET (asesor con nombre custom por proyecto) ──────────────────
const ChatWidget = ({project, milestones, cac, updates, clientName}) => {
  const advisorName = (project && project.advisor_name_in_chat) || "Valentina";
  const advisorInitial = advisorName.charAt(0).toUpperCase();
  const [open,setOpen]=useState(false);
  const [msgs,setMsgs]=useState([{role:"assistant",content:`Hola ${clientName}! Soy ${advisorName} de PMD. En que te puedo ayudar?`}]);
  const [input,setInput]=useState(""); const [loading,setLoading]=useState(false);
  const bottom=useRef(null);
  useEffect(()=>{if(open&&bottom.current)bottom.current.scrollIntoView({behavior:"smooth"});},[msgs,open]);
  const send = async () => {
    const txt=input.trim(); if(!txt||loading) return;
    const newMsgs=[...msgs,{role:"user",content:txt}];
    setMsgs(newMsgs); setInput(""); setLoading(true);
    const apiMsgs=newMsgs.slice(1).map(m=>({role:m.role,content:m.content}));
    try {
      const res=await fetch("/api/mi-hogar/chat",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({system:buildSP(project,milestones,cac,updates),messages:apiMsgs,max_tokens:400})});
      const data=await res.json();
      const reply=data.content?.map(b=>b.text||"").join("")||"Hubo un problema. Intentalo de nuevo.";
      setMsgs(p=>[...p,{role:"assistant",content:reply}]);
    } catch { setMsgs(p=>[...p,{role:"assistant",content:"Problema de conexion. Intentalo en un momento."}]); }
    setLoading(false);
  };
  if(!open) return (
    <button onClick={()=>setOpen(true)} style={{position:"fixed",bottom:22,right:18,zIndex:200,width:56,height:56,borderRadius:"50%",background:`linear-gradient(135deg,${C.b2},${C.b3})`,border:"none",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",boxShadow:"0 6px 24px rgba(30,58,95,.35)",animation:"pulse 2s infinite",fontSize:24,color:"#fff",fontWeight:800}}>{advisorInitial}</button>
  );
  return (
    <div style={{position:"fixed",bottom:0,right:0,width:355,height:"86vh",maxHeight:610,zIndex:200,display:"flex",flexDirection:"column",background:C.card,borderRadius:"20px 20px 0 0",boxShadow:"0 -6px 50px rgba(30,58,95,.2)",border:`1px solid ${C.border}`,borderBottom:"none"}}>
      <div style={{background:`linear-gradient(135deg,${C.b3},${C.b2})`,padding:"14px 16px",borderRadius:"20px 20px 0 0"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:38,height:38,borderRadius:"50%",background:"rgba(255,255,255,.15)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,color:"#fff",fontWeight:800}}>{advisorInitial}</div>
            <div><p style={{fontSize:13,fontWeight:800,color:"#fff"}}>{advisorName}</p><p style={{fontSize:10,color:"rgba(255,255,255,.55)"}}>Equipo PMD - En linea</p></div>
          </div>
          <button onClick={()=>setOpen(false)} style={{background:"rgba(255,255,255,.1)",border:"none",color:"rgba(255,255,255,.7)",fontSize:16,cursor:"pointer",width:28,height:28,borderRadius:"50%"}}>X</button>
        </div>
      </div>
      <div style={{flex:1,overflowY:"auto",padding:"14px 12px",display:"flex",flexDirection:"column",gap:8}}>
        {msgs.map((msg,i)=>(
          <div key={i} style={{display:"flex",flexDirection:"column",alignItems:msg.role==="user"?"flex-end":"flex-start"}}>
            <div style={{maxWidth:"84%",padding:"9px 12px",borderRadius:msg.role==="user"?"14px 14px 3px 14px":"14px 14px 14px 3px",background:msg.role==="user"?`linear-gradient(135deg,${C.b2},${C.b3})`:"#F4F3F0",color:msg.role==="user"?"#fff":C.txt,fontSize:13,lineHeight:1.5}}>{msg.content}</div>
          </div>
        ))}
        {loading&&<div style={{display:"flex",gap:4,padding:"9px 12px",borderRadius:"14px 14px 14px 3px",background:"#F4F3F0",width:60}}>{[0,1,2].map(i=><div key={i} style={{width:5,height:5,borderRadius:"50%",background:C.dim,animation:`blink 1s ${i*.2}s infinite`}}/>)}</div>}
        <div ref={bottom}/>
      </div>
      <div style={{padding:"10px 12px",borderTop:`1px solid ${C.border}`,display:"flex",gap:7}}>
        <textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}}} placeholder="Escribi tu consulta..." rows={2} style={{flex:1,padding:"9px 11px",border:`1.5px solid ${C.border}`,borderRadius:10,background:C.bg,color:C.txt,fontSize:13,resize:"none"}}/>
        <button onClick={send} disabled={!input.trim()||loading} className="btn" style={{width:40,height:40,borderRadius:10,border:"none",alignSelf:"flex-end",background:input.trim()&&!loading?C.b2:C.border,color:"#fff",fontSize:16}}>{">"}</button>
      </div>
    </div>
  );
};

// ─── CLIENT DASH ──────────────────────────────────────────────────────────
const ClientDash = ({user, project, onLogout}) => {
  const [tab,setTab]=useState("inicio");
  const [mods, setMods] = useState(project.mods || []);
  const milestones = project.milestones || [];
  const cac = project.cac || {base:{value:1,date:""},current:{value:1,date:""},history:[]};
  const updates = project.updates || [];
  const documents = project.documents || [];
  const [eu,setEu]=useState(0);
  const [newMod,setNewMod]=useState({title:"",desc:""}); const [modSent,setModSent]=useState(false);

  const paid=milestones.filter(m=>m.status==="paid").reduce((s,m)=>s+m.usd,0);
  const totalContract=milestones.reduce((s,m)=>s+m.usd,0) || 1;
  const pending=totalContract-paid;
  const cacVar=cac.base.value ? (cac.current.value-cac.base.value)/cac.base.value : 0;
  const next=milestones.find(m=>m.status==="pending");

  const sendMod=()=>{
    if(!newMod.title.trim()||!newMod.desc.trim()) return;
    const newId = `MOD-${String(mods.length+1).padStart(3,"0")}`;
    const newRecord = {id:newId,date:"Hoy",title:newMod.title,description:newMod.desc,status:"pending",archNote:"",approvalNumber:null};
    setMods([newRecord, ...mods]);
    setNewMod({title:"",desc:""}); setModSent(true);
    setTimeout(()=>setModSent(false),4000);
  };

  const TABS=[["inicio","Inicio"],["avance","Avance"],["financiero","Financiero"],["planos","Planos"],["modificaciones",`Cambios (${mods.length})`]];

  const phaseData = (project.phases || []).map(ph=>({name:(ph.name||"").slice(0,9),value:ph.pct}));
  const progressData = [...updates].reverse().map(u=>({sem:u.week,pct:u.progress}));

  return (
    <div style={{minHeight:"100vh",background:C.bg,fontFamily:"'DM Sans',sans-serif",paddingBottom:80}}>
      <div style={{background:C.card,borderBottom:`1px solid ${C.border}`,padding:"12px 16px",display:"flex",alignItems:"center",justifyContent:"space-between",position:"sticky",top:0,zIndex:40,boxShadow:"0 2px 10px rgba(30,58,95,.06)"}}>
        <Logo size={26}/>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <span style={{fontSize:11,color:C.txt2}}>{user.name}</span>
          <button onClick={onLogout} className="btn" style={{background:C.bg,border:`1px solid ${C.border}`,color:C.txt2,fontSize:11,padding:"5px 11px",borderRadius:8,fontWeight:600}}>Salir</button>
        </div>
      </div>
      <div style={{background:C.card,borderBottom:`1px solid ${C.border}`,padding:"0 10px",display:"flex",overflowX:"auto"}}>
        {TABS.map(([id,lbl])=>(
          <button key={id} onClick={()=>setTab(id)} style={{padding:"11px 12px",border:"none",background:"transparent",color:tab===id?C.b2:C.txt2,fontSize:12,fontWeight:700,borderBottom:tab===id?`2px solid ${C.b2}`:"2px solid transparent",cursor:"pointer",whiteSpace:"nowrap",fontFamily:"'DM Sans',sans-serif"}}>{lbl}</button>
        ))}
      </div>
      <div style={{maxWidth:800,margin:"0 auto",padding:"16px 13px 20px"}}>
        {tab==="inicio" && (
          <div className="up">
            <div style={{borderRadius:22,padding:"22px 20px 18px",marginBottom:13,background:`linear-gradient(135deg,${C.b3},${C.b2})`}}>
              <p style={{fontSize:10,fontWeight:700,color:"rgba(255,255,255,.5)",textTransform:"uppercase",letterSpacing:".12em",marginBottom:2}}>Avance general</p>
              <div style={{display:"flex",alignItems:"baseline",gap:3,marginBottom:14}}>
                <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:52,fontWeight:900,color:"#fff",lineHeight:1,letterSpacing:"-.04em"}}>{project.overallProgress || 0}</span>
                <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:22,color:"rgba(255,255,255,.4)",fontWeight:700}}>%</span>
              </div>
              {(project.phases || []).map((ph,i)=>(
                <div key={i} style={{marginBottom:7}}>
                  <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
                    <span style={{fontSize:11,color:"rgba(255,255,255,.7)"}}>{ph.name}</span>
                    <Mono ch={`${ph.pct}%`} size={11} color={ph.pct===100?"#6EE7A0":"rgba(255,255,255,.85)"} weight={700}/>
                  </div>
                  <div style={{background:"rgba(255,255,255,.15)",borderRadius:4,height:4}}>
                    <div style={{width:`${ph.pct}%`,height:"100%",borderRadius:4,background:ph.pct===100?"#4ADE80":"rgba(255,255,255,.85)"}}/>
                  </div>
                </div>
              ))}
            </div>
            {progressData.length>0 && <Card style={{padding:16,marginBottom:11}}>
              <p style={{fontSize:11,fontWeight:800,color:C.txt,marginBottom:12}}>Evolucion semanal</p>
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={progressData} margin={{top:4,right:8,left:-22,bottom:0}}>
                  <XAxis dataKey="sem" tick={{fontSize:9,fill:C.dim}} axisLine={false} tickLine={false}/>
                  <YAxis domain={[0,100]} tick={{fontSize:9,fill:C.dim}} axisLine={false} tickLine={false}/>
                  <Tooltip contentStyle={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,fontSize:11}} formatter={v=>[`${v}%`,"Avance"]}/>
                  <Line type="monotone" dataKey="pct" stroke={C.b2} strokeWidth={2.5} dot={{fill:C.b2,r:4,strokeWidth:0}}/>
                </LineChart>
              </ResponsiveContainer>
            </Card>}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:11}}>
              <Card className="hl" style={{padding:14,cursor:"pointer"}} onClick={()=>setTab("financiero")}>
                <p style={{fontSize:9,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",marginBottom:4}}>Pagado</p>
                <Mono ch={`USD ${fmt(paid)}`} size={16} color={C.green} weight={900}/>
              </Card>
              <Card className="hl" style={{padding:14,cursor:"pointer",borderColor:C.aBorder}} onClick={()=>setTab("financiero")}>
                <p style={{fontSize:9,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",marginBottom:4}}>Proximo pago</p>
                <Mono ch={`USD ${fmt(next?.usd||0)}`} size={16} color={C.amber} weight={900}/>
                <p style={{fontSize:10,color:C.dim,marginTop:2,overflow:"hidden",whiteSpace:"nowrap",textOverflow:"ellipsis"}}>{next?.name||"-"}</p>
              </Card>
            </div>
            {updates[0]&&(
              <Card className="hl" style={{padding:15,cursor:"pointer"}} onClick={()=>setTab("avance")}>
                <p style={{fontSize:10,fontWeight:700,color:C.b2,textTransform:"uppercase",letterSpacing:".08em",marginBottom:3}}>{updates[0].week} - {updates[0].date}</p>
                <p style={{fontSize:14,fontWeight:700,color:C.txt,marginBottom:8}}>{updates[0].title}</p>
                <p style={{fontSize:12,color:C.txt2,lineHeight:1.5}}>{(updates[0].summary||"").slice(0,140)}...</p>
              </Card>
            )}
          </div>
        )}
        {tab==="avance" && (
          <div className="up">
            {updates.map((upd,i)=>(
              <Card key={upd.id} style={{marginBottom:12,overflow:"hidden"}}>
                <div onClick={()=>setEu(eu===i?-1:i)} style={{padding:"15px 18px",cursor:"pointer",display:"flex",justifyContent:"space-between"}}>
                  <div>
                    <span style={{fontSize:10,fontWeight:800,color:C.b2,textTransform:"uppercase",letterSpacing:".09em"}}>{upd.week}</span>
                    <p style={{fontSize:14,fontWeight:700,color:C.txt,marginTop:4}}>{upd.title}</p>
                  </div>
                  <Mono ch={`${upd.progress}%`} size={19} weight={900}/>
                </div>
                {eu===i&&<div style={{padding:"0 18px 18px"}}>
                  <p style={{fontSize:13,color:C.txt2,lineHeight:1.6,marginBottom:12}}>{upd.summary}</p>
                  {(upd.photos||[]).length>0 && <div style={{display:"flex",gap:7,marginBottom:12,overflowX:"auto"}}>{upd.photos.map((ph,j)=><img key={j} src={ph} alt="" style={{height:100,width:150,objectFit:"cover",borderRadius:9,flexShrink:0}}/>)}</div>}
                  {(upd.completed||[]).length>0 && <div style={{background:C.gBg,borderRadius:11,padding:"11px 13px",marginBottom:8}}>
                    <p style={{fontSize:9,fontWeight:800,color:C.green,textTransform:"uppercase",letterSpacing:".08em",marginBottom:7}}>Completado</p>
                    {upd.completed.map((it,j)=><p key={j} style={{fontSize:12,color:C.txt,marginBottom:4}}>* {it}</p>)}
                  </div>}
                  {(upd.next||[]).length>0 && <div style={{background:C.tag,borderRadius:11,padding:"11px 13px"}}>
                    <p style={{fontSize:9,fontWeight:800,color:C.b2,textTransform:"uppercase",letterSpacing:".08em",marginBottom:7}}>Proximos pasos</p>
                    {upd.next.map((it,j)=><p key={j} style={{fontSize:12,color:C.txt,marginBottom:4}}>* {it}</p>)}
                  </div>}
                </div>}
              </Card>
            ))}
          </div>
        )}
        {tab==="financiero" && (
          <div className="up">
            <p style={{fontSize:16,fontWeight:900,color:C.b3,marginBottom:13}}>Estado Financiero</p>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:9,marginBottom:13}}>
              <Card style={{padding:13,background:C.gBg,border:"none"}}>
                <p style={{fontSize:9,fontWeight:800,color:C.green,textTransform:"uppercase",marginBottom:4}}>Pagado</p>
                <Mono ch={`USD ${fmt(paid)}`} size={14} color={C.green} weight={900}/>
              </Card>
              <Card style={{padding:13,background:C.rBg,border:"none"}}>
                <p style={{fontSize:9,fontWeight:800,color:C.red,textTransform:"uppercase",marginBottom:4}}>Saldo</p>
                <Mono ch={`USD ${fmt(pending)}`} size={14} color={C.red} weight={900}/>
              </Card>
            </div>
            <Card style={{padding:16}}>
              <p style={{fontSize:13,fontWeight:800,color:C.txt,marginBottom:13}}>Cuotas por hito</p>
              {milestones.map((m,i)=>(
                <div key={m.id} style={{display:"flex",alignItems:"center",gap:10,paddingBottom:11,marginBottom:11,borderBottom:i<milestones.length-1?`1px dashed ${C.border}`:"none"}}>
                  <div style={{width:28,height:28,borderRadius:"50%",background:m.status==="paid"?C.gBg:C.aBg,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,fontSize:12,fontWeight:800,color:m.status==="paid"?C.green:C.amber}}>{m.status==="paid"?"OK":"--"}</div>
                  <div style={{flex:1,minWidth:0}}>
                    <p style={{fontSize:13,fontWeight:700,color:C.txt,overflow:"hidden",whiteSpace:"nowrap",textOverflow:"ellipsis"}}>{m.name}</p>
                    <p style={{fontSize:10,color:C.dim}}>{m.status==="paid"?`${m.paidDate} - ${m.certRef}`:"Pendiente"}</p>
                  </div>
                  <Mono ch={`USD ${fmt(m.usd)}`} size={13} color={m.status==="paid"?C.green:C.amber} weight={800}/>
                </div>
              ))}
            </Card>
          </div>
        )}
        {tab==="planos" && (
          <div className="up">
            <p style={{fontSize:16,fontWeight:900,color:C.b3,marginBottom:13}}>Planos & Documentos</p>
            {documents.map(doc=>(
              <Card key={doc.id} style={{padding:"12px 15px",marginBottom:9,display:"flex",alignItems:"center",gap:11}}>
                <div style={{width:36,height:36,borderRadius:9,background:C.tag,display:"flex",alignItems:"center",justifyContent:"center",fontSize:14,fontWeight:800,color:C.b2}}>{doc.icon}</div>
                <div style={{flex:1,minWidth:0}}>
                  <p style={{fontSize:13,fontWeight:700,color:C.txt}}>{doc.name}</p>
                  <p style={{fontSize:10,color:C.dim}}>{doc.date} - {doc.size}{doc.ref?` - ${doc.ref}`:""}</p>
                </div>
                <Badge status={doc.status}/>
              </Card>
            ))}
          </div>
        )}
        {tab==="modificaciones" && (
          <div className="up">
            <p style={{fontSize:16,fontWeight:900,color:C.b3,marginBottom:13}}>Modificaciones</p>
            <Card style={{padding:18,marginBottom:13,border:`1.5px solid ${C.b1}`}}>
              <p style={{fontSize:14,fontWeight:800,color:C.b3,marginBottom:13}}>Solicitar modificacion</p>
              {modSent&&<div style={{background:C.gBg,borderRadius:9,padding:"9px 13px",marginBottom:11,color:C.green,fontWeight:700,fontSize:13}}>Solicitud enviada.</div>}
              <input value={newMod.title} onChange={e=>setNewMod(p=>({...p,title:e.target.value}))} placeholder="Titulo" style={{width:"100%",padding:"10px 13px",border:`1.5px solid ${C.border}`,borderRadius:10,background:C.bg,color:C.txt,fontSize:13,marginBottom:9}}/>
              <textarea value={newMod.desc} onChange={e=>setNewMod(p=>({...p,desc:e.target.value}))} placeholder="Descripcion..." rows={3} style={{width:"100%",padding:"10px 13px",border:`1.5px solid ${C.border}`,borderRadius:10,background:C.bg,color:C.txt,fontSize:13,resize:"vertical",marginBottom:11}}/>
              <button className="btn" onClick={sendMod} style={{padding:"10px 20px",background:C.b2,color:"#fff",border:"none",borderRadius:9,fontSize:13,fontWeight:800}}>Enviar</button>
            </Card>
            {mods.map(mod=>(
              <Card key={mod.id} style={{padding:15,marginBottom:10}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                  <Mono ch={`${mod.id} - ${mod.date}`} size={10} color={C.dim} weight={600}/>
                  <Badge status={mod.status}/>
                </div>
                <p style={{fontSize:13,fontWeight:700,color:C.txt,marginBottom:6}}>{mod.title}</p>
                <p style={{fontSize:12,color:C.txt2,lineHeight:1.5}}>{mod.description}</p>
              </Card>
            ))}
          </div>
        )}
      </div>
      <ChatWidget project={project} milestones={milestones} cac={cac} updates={updates} clientName={user.name}/>
    </div>
  );
};

// ─── ARCH PANEL — equipo PMD (admin/asesor/architect) ──────────────────────
// Renderiza la vista completa del proyecto + selector si hay varios + card admin.
const ArchPanel = ({user, projects: initialProjects, onLogout}) => {
  const [projects, setProjectsState] = useState(initialProjects || []);
  useEffect(() => { setProjectsState(initialProjects || []); }, [initialProjects]);
  const [selectedId, setSelectedId] = useState(initialProjects?.[0]?.id || null);
  const project = projects?.find(p=>p.id===selectedId) || projects?.[0];
  const roleLabel = {admin:"Administrador", asesor:"Asesor", architect:"Arquitecto"}[user.role] || user.role;
  const handleProjectUpdate = (updated) => {
    setProjectsState(prev => prev.map(p => p.id === updated.id ? updated : p));
  };

  if (!project) {
    return (
      <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans',sans-serif"}}>
        <Card style={{padding:30,maxWidth:420,textAlign:"center"}}>
          <div style={{display:"flex",justifyContent:"center",marginBottom:16}}><Logo size={32}/></div>
          <p style={{fontSize:15,fontWeight:700,color:C.b3,marginBottom:8}}>Hola {user.name}</p>
          <p style={{color:C.txt2,fontSize:13,marginBottom:18}}>No hay proyectos cargados todavia. Crea clientes y proyectos desde Gestionar usuarios.</p>
          {user.role === "admin" && (
            <a href="/admin/users" target="_blank" rel="noopener" className="btn" style={{display:"inline-block",padding:"10px 20px",background:C.b2,color:"#fff",borderRadius:9,fontSize:13,fontWeight:700,textDecoration:"none",marginBottom:10}}>Gestionar usuarios</a>
          )}
          <div><button onClick={onLogout} className="btn" style={{padding:"8px 18px",background:"transparent",color:C.txt2,border:`1px solid ${C.border}`,borderRadius:9,fontSize:12}}>Salir</button></div>
        </Card>
      </div>
    );
  }

  return (
    <div style={{minHeight:"100vh",background:C.bg,fontFamily:"'DM Sans',sans-serif"}}>
      {/* Header oscuro: marca panel del EQUIPO (vs cliente que es claro) */}
      <div style={{background:C.b3,padding:"12px 16px",display:"flex",alignItems:"center",justifyContent:"space-between",position:"sticky",top:0,zIndex:40}}>
        <Logo size={26} dark/>
        <div style={{textAlign:"right",flex:1,marginRight:12}}>
          <p style={{fontSize:9,fontWeight:800,color:"rgba(255,255,255,.4)",textTransform:"uppercase",letterSpacing:".12em"}}>Panel {roleLabel}</p>
          <p style={{fontSize:13,fontWeight:700,color:"#fff"}}>{user.name}</p>
        </div>
        <button onClick={onLogout} className="btn" style={{background:"rgba(255,255,255,.1)",border:"none",color:"rgba(255,255,255,.85)",fontSize:11,padding:"6px 12px",borderRadius:8,fontWeight:600}}>Salir</button>
      </div>

      {/* Contenido principal */}
      <div style={{maxWidth:800,margin:"0 auto",padding:"18px 13px 48px"}}>

        {/* Panel de administracion — hub central con todos los accesos (solo admin) */}
        {user.role === "admin" && (
          <Card style={{padding:"18px 20px",marginBottom:14,background:`linear-gradient(135deg,${C.b1}15,${C.b2}10)`,border:`1px solid ${C.b1}40`}}>
            <p style={{fontSize:14,fontWeight:800,color:C.b3,marginBottom:3}}>Panel de administracion</p>
            <p style={{fontSize:12,color:C.txt2,marginBottom:14}}>Acceso completo a todas las herramientas de PMD</p>
            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:10}}>
              <a href="/admin" target="_blank" rel="noopener" className="btn hl" style={{display:"flex",flexDirection:"column",alignItems:"flex-start",gap:6,padding:"14px 16px",background:"#fff",border:`1px solid ${C.border}`,borderRadius:10,textDecoration:"none",color:C.txt}}>
                <span style={{fontSize:11,fontWeight:800,color:C.b2,textTransform:"uppercase",letterSpacing:".08em"}}>Atencion clientes</span>
                <span style={{fontSize:14,fontWeight:700,color:C.b3}}>Leads & Reuniones</span>
                <span style={{fontSize:11,color:C.txt2}}>Mensajes del chat Lucas + reuniones agendadas</span>
              </a>
              <a href="/admin" target="_blank" rel="noopener" className="btn hl" style={{display:"flex",flexDirection:"column",alignItems:"flex-start",gap:6,padding:"14px 16px",background:"#fff",border:`1px solid ${C.border}`,borderRadius:10,textDecoration:"none",color:C.txt}}>
                <span style={{fontSize:11,fontWeight:800,color:C.amber,textTransform:"uppercase",letterSpacing:".08em"}}>Cotizador</span>
                <span style={{fontSize:14,fontWeight:700,color:C.b3}}>Precios del cotizador</span>
                <span style={{fontSize:11,color:C.txt2}}>Editar valores de obra que ve el cliente</span>
              </a>
              <a href="/admin/users" target="_blank" rel="noopener" className="btn hl" style={{display:"flex",flexDirection:"column",alignItems:"flex-start",gap:6,padding:"14px 16px",background:"#fff",border:`1px solid ${C.border}`,borderRadius:10,textDecoration:"none",color:C.txt}}>
                <span style={{fontSize:11,fontWeight:800,color:C.green,textTransform:"uppercase",letterSpacing:".08em"}}>Equipo</span>
                <span style={{fontSize:14,fontWeight:700,color:C.b3}}>Gestionar usuarios</span>
                <span style={{fontSize:11,color:C.txt2}}>Crear clientes, asignar asesores, invites</span>
              </a>
              <a href="/admin/users" target="_blank" rel="noopener" className="btn hl" style={{display:"flex",flexDirection:"column",alignItems:"flex-start",gap:6,padding:"14px 16px",background:"#fff",border:`1px solid ${C.border}`,borderRadius:10,textDecoration:"none",color:C.txt}}>
                <span style={{fontSize:11,fontWeight:800,color:C.purple,textTransform:"uppercase",letterSpacing:".08em"}}>Asignaciones</span>
                <span style={{fontSize:14,fontWeight:700,color:C.b3}}>Proyectos & Equipo</span>
                <span style={{fontSize:11,color:C.txt2}}>Asignar asesor / arquitecto a cada cliente</span>
              </a>
            </div>
          </Card>
        )}

        {/* Project picker — si hay mas de uno */}
        {projects.length > 1 && (
          <Card style={{padding:"12px 16px",marginBottom:14}}>
            <p style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",marginBottom:8}}>Proyectos en curso ({projects.length})</p>
            <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              {projects.map(p=>(
                <button key={p.id} onClick={()=>setSelectedId(p.id)} className="btn" style={{padding:"7px 14px",background:p.id===selectedId?C.b2:C.bg,color:p.id===selectedId?"#fff":C.txt2,border:`1px solid ${C.border}`,borderRadius:9,fontSize:12,fontWeight:700}}>{p.name}</button>
              ))}
            </div>
          </Card>
        )}

        {/* Vista detallada del proyecto seleccionado — incluye actions de management */}
        <ArchProjectView project={project} canEdit={true} onProjectUpdate={handleProjectUpdate}/>

        {/* Footer info: rol y permisos */}
        <Card style={{padding:"14px 18px",marginTop:14,background:C.bg,border:`1px dashed ${C.border}`,boxShadow:"none"}}>
          <p style={{fontSize:11,color:C.txt2,lineHeight:1.6}}>
            <strong style={{color:C.b3}}>Como {roleLabel.toLowerCase()}</strong> podes subir avances con IA, marcar cuotas pagadas (genera certificado automatico) y aprobar/rechazar modificaciones desde las pestanas Avance, Financiero y Modif.
          </p>
        </Card>
      </div>

      {/* Chat de Valentina — para que el equipo vea como ven los clientes */}
      <ChatWidget project={project} milestones={project.milestones || []} cac={project.cac} updates={project.updates || []} clientName={user.name}/>
    </div>
  );
};

// ─── HELPER: persistir proyecto entero al backend ─────────────────────────
const saveProjectToBackend = async (project) => {
  const token = getToken();
  const res = await fetch("/api/admin/projects", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token}`},
    body: JSON.stringify({project}),
  });
  return res.json();
};

// ─── ARCH PROJECT VIEW — vista detallada + management actions (equipo) ─────
const ArchProjectView = ({project: initialProject, canEdit = true, onProjectUpdate}) => {
  const [project, setLocalProject] = useState(initialProject);
  useEffect(() => { setLocalProject(initialProject); }, [initialProject]);

  const [tab, setTab] = useState("inicio");
  const [eu, setEu] = useState(0);

  // Estados de management
  const [showUpload, setShowUpload] = useState(false);
  const [upDesc, setUpDesc] = useState("");
  const [upPct, setUpPct] = useState(initialProject.overallProgress || 0);
  const [upPhotos, setUpPhotos] = useState([]);
  const [upProcessing, setUpProcessing] = useState(false);
  const [upPreview, setUpPreview] = useState(null);
  const upFileRef = useRef(null);

  const [payModal, setPayModal] = useState(null);
  const [payNote, setPayNote] = useState("");
  const [paySaving, setPaySaving] = useState(false);

  const [modAction, setModAction] = useState(null);
  const [modNote, setModNote] = useState("");
  const [modSaving, setModSaving] = useState(false);

  const [savingFlash, setSavingFlash] = useState("");

  const [showEditMeta, setShowEditMeta] = useState(false);
  const [metaForm, setMetaForm] = useState({
    name: "", system: "", location: "", totalM2: 0,
    startDate: "", estimatedEnd: "",
  });
  const [metaSaving, setMetaSaving] = useState(false);

  const milestones = project.milestones || [];
  const cac = project.cac || {base:{value:1,date:""},current:{value:1,date:""},history:[]};
  const updates = project.updates || [];
  const documents = project.documents || [];
  const mods = project.mods || [];

  const persistAndFlash = async (newProject, msg) => {
    const r = await saveProjectToBackend(newProject);
    if (r.ok) {
      setLocalProject(r.project);
      if (onProjectUpdate) onProjectUpdate(r.project);
      setSavingFlash(msg);
      setTimeout(() => setSavingFlash(""), 3500);
      return true;
    }
    setSavingFlash("Error al guardar: " + (r.error || "?"));
    setTimeout(() => setSavingFlash(""), 4500);
    return false;
  };

  // Upload avance
  const handleUpFiles = (e) => {
    const files = Array.from(e.target.files || []);
    setUpPhotos(p => [...p, ...files.map(f => ({url: URL.createObjectURL(f), name: f.name}))]);
  };
  const processUpAI = async () => {
    if (!upDesc.trim()) return;
    setUpProcessing(true); setUpPreview(null);
    try {
      const res = await fetch("/api/mi-hogar/process-update", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({description: upDesc, pct: upPct, photos_count: upPhotos.length}),
      });
      const data = await res.json();
      setUpPreview(data);
    } catch {
      setUpPreview({title: "Actualizacion de avance", summary: upDesc, completed: ["Ver descripcion"], next: ["Confirmar proximos pasos"]});
    }
    setUpProcessing(false);
  };
  const publishUp = async () => {
    if (!upPreview) return;
    const newUpdate = {
      id: Date.now(),
      date: new Date().toLocaleDateString("es-AR", {day:"numeric",month:"short",year:"numeric"}),
      week: `Sem. ${(updates.length + 24)}`,
      title: upPreview.title,
      progress: upPct,
      summary: upPreview.summary,
      completed: upPreview.completed || [],
      next: upPreview.next || [],
      photos: upPhotos.length > 0 ? upPhotos.map(p => p.url) : ["https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=700&h=460&fit=crop"],
    };
    const newProject = {...project, updates: [newUpdate, ...updates], overallProgress: upPct};
    const ok = await persistAndFlash(newProject, "Avance publicado al cliente");
    if (ok) {
      setShowUpload(false); setUpDesc(""); setUpPhotos([]); setUpPreview(null);
    }
  };

  // Mark milestone paid
  const confirmPay = async () => {
    if (!payModal) return;
    setPaySaving(true);
    const today = new Date().toLocaleDateString("es-AR", {day:"numeric",month:"short",year:"numeric"});
    const paidCount = milestones.filter(m => m.status === "paid").length;
    const certRef = `PMD-CERT-${String(paidCount + 1).padStart(3, "0")}`;
    const newMilestones = milestones.map(m =>
      m.id === payModal.id ? {...m, status: "paid", paidDate: today, certRef} : m
    );
    const newDocuments = [...documents, {
      id: Date.now(), cat: "cert", icon: "C",
      name: `Certificado de Avance - ${payModal.name}`,
      date: today, size: "~200 KB", ref: certRef, status: "emitido",
    }];
    const newProject = {...project, milestones: newMilestones, documents: newDocuments};
    const ok = await persistAndFlash(newProject, `Cuota marcada pagada — certificado ${certRef} emitido`);
    if (ok) { setPayModal(null); setPayNote(""); }
    setPaySaving(false);
  };

  // Approve/Reject mod
  const confirmModAction = async () => {
    if (!modAction) return;
    setModSaving(true);
    const status = modAction.action === "approve" ? "approved" : "rejected";
    const approvedCount = mods.filter(m => m.approvalNumber).length;
    const approvalNumber = status === "approved" ? `PMD-AP-${String(1020 + approvedCount + 1).slice(-4)}` : null;
    const newMods = mods.map(m =>
      m.id === modAction.mod.id ? {...m, status, archNote: modNote || (status === "approved" ? "Aprobado." : "No es factible."), approvalNumber} : m
    );
    const newProject = {...project, mods: newMods};
    const ok = await persistAndFlash(newProject, status === "approved" ? `Modificacion aprobada (${approvalNumber})` : "Modificacion rechazada");
    if (ok) { setModAction(null); setModNote(""); }
    setModSaving(false);
  };

  const paid = milestones.filter(m=>m.status==="paid").reduce((s,m)=>s+m.usd,0);
  const totalContract = milestones.reduce((s,m)=>s+m.usd,0) || 1;
  const pending = totalContract - paid;
  const cacVar = cac.base.value ? (cac.current.value-cac.base.value)/cac.base.value : 0;
  const next = milestones.find(m=>m.status==="pending");
  const phaseData = (project.phases || []).map(ph=>({name:(ph.name||"").slice(0,9),value:ph.pct}));
  const progressData = [...updates].reverse().map(u=>({sem:u.week,pct:u.progress}));

  const TABS=[["inicio","Inicio"],["avance","Avance"],["financiero","Financiero"],["planos","Planos"],["mods",`Modif. (${mods.length})`]];

  const openEditMeta = () => {
    setMetaForm({
      name: project.name || "",
      system: project.system || "Steel Framing",
      location: project.location || "",
      totalM2: project.totalM2 || 0,
      startDate: project.startDate || "",
      estimatedEnd: project.estimatedEnd || "",
    });
    setShowEditMeta(true);
  };
  const confirmEditMeta = async () => {
    setMetaSaving(true);
    const newProject = {
      ...project,
      name: metaForm.name.trim() || project.name,
      system: metaForm.system,
      location: metaForm.location.trim(),
      totalM2: Number(metaForm.totalM2) || 0,
      startDate: metaForm.startDate.trim(),
      estimatedEnd: metaForm.estimatedEnd.trim(),
    };
    const ok = await persistAndFlash(newProject, "Datos del proyecto actualizados");
    if (ok) setShowEditMeta(false);
    setMetaSaving(false);
  };

  // Modal genérico
  const Modal = ({title, onClose, children}) => (
    <div style={{position:"fixed",inset:0,background:"rgba(20,30,50,.55)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000,padding:14}} onClick={onClose}>
      <Card style={{maxWidth:480,width:"100%",padding:20,maxHeight:"90vh",overflowY:"auto"}} onClick={e=>e.stopPropagation()}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
          <p style={{fontSize:15,fontWeight:900,color:C.b3,letterSpacing:"-.01em"}}>{title}</p>
          <button onClick={onClose} className="btn" style={{border:"none",background:"transparent",fontSize:18,color:C.txt2,cursor:"pointer"}}>x</button>
        </div>
        {children}
      </Card>
    </div>
  );

  return (
    <div>
      {savingFlash && <div style={{position:"sticky",top:8,zIndex:50,marginBottom:10,padding:"10px 14px",background:savingFlash.startsWith("Error")?C.rBg:C.gBg,color:savingFlash.startsWith("Error")?C.red:C.green,borderRadius:10,border:`1px solid ${savingFlash.startsWith("Error")?C.red:C.green}`,fontSize:12,fontWeight:700,boxShadow:"0 6px 18px rgba(30,58,95,.10)"}}>{savingFlash}</div>}

      <Card style={{padding:"14px 18px",marginBottom:11,position:"relative"}}>
        {canEdit && <button onClick={openEditMeta} className="btn" style={{position:"absolute",top:11,right:11,padding:"5px 11px",borderRadius:7,border:`1px solid ${C.border}`,background:C.bg,color:C.b2,fontSize:10,fontWeight:700,cursor:"pointer",letterSpacing:".04em"}}>EDITAR</button>}
        <p style={{fontSize:18,fontWeight:900,color:C.b3,letterSpacing:"-.02em",marginBottom:3,paddingRight:60}}>{project.name}</p>
        <p style={{fontSize:12,color:C.txt2}}>{project.system} - {project.totalM2}m2 - {project.location}</p>
        <p style={{fontSize:11,color:C.dim,marginTop:4}}>Inicio: {project.startDate} - Fin estimado: {project.estimatedEnd}</p>
      </Card>

      {showEditMeta && <Modal title="Editar datos del proyecto" onClose={()=>setShowEditMeta(false)}>
        <div style={{marginBottom:11}}>
          <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",display:"block",marginBottom:5}}>Nombre del proyecto (lo ve el cliente)</label>
          <input value={metaForm.name} onChange={e=>setMetaForm({...metaForm,name:e.target.value})} style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:14,fontWeight:700,color:C.b3}}/>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:11}}>
          <div>
            <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>Sistema</label>
            <select value={metaForm.system} onChange={e=>setMetaForm({...metaForm,system:e.target.value})} style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:13,background:"#fff"}}>
              <option value="Steel Framing">Steel Framing</option>
              <option value="Hormigon Armado">Hormigon Armado</option>
              <option value="Mixto">Mixto</option>
              <option value="Otro">Otro</option>
            </select>
          </div>
          <div>
            <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>m2 totales</label>
            <input type="number" min={0} value={metaForm.totalM2} onChange={e=>setMetaForm({...metaForm,totalM2:e.target.value})} style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:13}}/>
          </div>
        </div>
        <div style={{marginBottom:11}}>
          <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>Ubicacion</label>
          <input value={metaForm.location} onChange={e=>setMetaForm({...metaForm,location:e.target.value})} style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:13}}/>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
          <div>
            <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>Inicio</label>
            <input value={metaForm.startDate} onChange={e=>setMetaForm({...metaForm,startDate:e.target.value})} placeholder="01 Nov 2025" style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:13}}/>
          </div>
          <div>
            <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>Fin estimado</label>
            <input value={metaForm.estimatedEnd} onChange={e=>setMetaForm({...metaForm,estimatedEnd:e.target.value})} placeholder="01 Ago 2026" style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:13}}/>
          </div>
        </div>
        <div style={{display:"flex",gap:8}}>
          <button onClick={()=>setShowEditMeta(false)} className="btn" style={{flex:1,padding:"10px 12px",borderRadius:9,border:`1px solid ${C.border}`,background:C.card,color:C.txt2,fontSize:12,fontWeight:700,cursor:"pointer"}}>Cancelar</button>
          <button onClick={confirmEditMeta} disabled={metaSaving} className="btn" style={{flex:2,padding:"10px 12px",borderRadius:9,border:"none",background:C.b2,color:"#fff",fontSize:12,fontWeight:800,cursor:metaSaving?"wait":"pointer",opacity:metaSaving?0.6:1}}>{metaSaving?"Guardando...":"Guardar cambios"}</button>
        </div>
      </Modal>}

      <div style={{background:C.card,borderRadius:11,border:`1px solid ${C.border}`,padding:"0 8px",marginBottom:11,display:"flex",overflowX:"auto"}}>
        {TABS.map(([id,lbl])=>(
          <button key={id} onClick={()=>setTab(id)} style={{padding:"11px 14px",border:"none",background:"transparent",color:tab===id?C.b2:C.txt2,fontSize:12,fontWeight:700,borderBottom:tab===id?`2px solid ${C.b2}`:"2px solid transparent",cursor:"pointer",whiteSpace:"nowrap",fontFamily:"'DM Sans',sans-serif"}}>{lbl}</button>
        ))}
      </div>

      {tab==="inicio" && (
        <div className="up">
          <div style={{borderRadius:18,padding:"20px 18px 16px",marginBottom:11,background:`linear-gradient(135deg,${C.b3},${C.b2})`}}>
            <p style={{fontSize:10,fontWeight:700,color:"rgba(255,255,255,.5)",textTransform:"uppercase",letterSpacing:".12em",marginBottom:2}}>Avance general</p>
            <div style={{display:"flex",alignItems:"baseline",gap:3,marginBottom:14}}>
              <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:48,fontWeight:900,color:"#fff",lineHeight:1,letterSpacing:"-.04em"}}>{project.overallProgress || 0}</span>
              <span style={{fontFamily:"'JetBrains Mono',monospace",fontSize:20,color:"rgba(255,255,255,.4)",fontWeight:700}}>%</span>
            </div>
            {(project.phases || []).map((ph,i)=>(
              <div key={i} style={{marginBottom:7}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
                  <span style={{fontSize:11,color:"rgba(255,255,255,.7)"}}>{ph.name}</span>
                  <Mono ch={`${ph.pct}%`} size={11} color={ph.pct===100?"#6EE7A0":"rgba(255,255,255,.85)"} weight={700}/>
                </div>
                <div style={{background:"rgba(255,255,255,.15)",borderRadius:4,height:4}}>
                  <div style={{width:`${ph.pct}%`,height:"100%",borderRadius:4,background:ph.pct===100?"#4ADE80":"rgba(255,255,255,.85)"}}/>
                </div>
              </div>
            ))}
          </div>
          {progressData.length>0 && <Card style={{padding:14,marginBottom:11}}>
            <p style={{fontSize:11,fontWeight:800,color:C.txt,marginBottom:10}}>Evolucion semanal</p>
            <ResponsiveContainer width="100%" height={140}>
              <LineChart data={progressData} margin={{top:4,right:8,left:-22,bottom:0}}>
                <XAxis dataKey="sem" tick={{fontSize:9,fill:C.dim}} axisLine={false} tickLine={false}/>
                <YAxis domain={[0,100]} tick={{fontSize:9,fill:C.dim}} axisLine={false} tickLine={false}/>
                <Tooltip contentStyle={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,fontSize:11}} formatter={v=>[`${v}%`,"Avance"]}/>
                <Line type="monotone" dataKey="pct" stroke={C.b2} strokeWidth={2.5} dot={{fill:C.b2,r:4,strokeWidth:0}}/>
              </LineChart>
            </ResponsiveContainer>
          </Card>}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:11}}>
            <Card style={{padding:13,background:C.gBg,border:"none"}}>
              <p style={{fontSize:9,fontWeight:800,color:C.green,textTransform:"uppercase",letterSpacing:".09em",marginBottom:4}}>Pagado</p>
              <Mono ch={`USD ${fmt(paid)}`} size={15} color={C.green} weight={900}/>
            </Card>
            <Card style={{padding:13,background:C.aBg,border:"none"}}>
              <p style={{fontSize:9,fontWeight:800,color:C.amber,textTransform:"uppercase",letterSpacing:".09em",marginBottom:4}}>Saldo</p>
              <Mono ch={`USD ${fmt(pending)}`} size={15} color={C.amber} weight={900}/>
              <p style={{fontSize:10,color:C.dim,marginTop:3}}>Proximo: {next?.name || "-"}</p>
            </Card>
          </div>
          {updates[0] && (
            <Card style={{padding:14,cursor:"pointer"}} onClick={()=>setTab("avance")}>
              <p style={{fontSize:10,fontWeight:700,color:C.b2,textTransform:"uppercase",letterSpacing:".08em",marginBottom:3}}>{updates[0].week} - {updates[0].date}</p>
              <p style={{fontSize:14,fontWeight:700,color:C.txt,marginBottom:6}}>{updates[0].title}</p>
              <p style={{fontSize:12,color:C.txt2,lineHeight:1.5}}>{(updates[0].summary||"").slice(0,160)}...</p>
            </Card>
          )}
        </div>
      )}

      {tab==="avance" && (
        <div className="up">
          {canEdit && <button onClick={()=>setShowUpload(true)} className="btn" style={{width:"100%",padding:"12px 14px",marginBottom:11,borderRadius:11,border:"none",background:`linear-gradient(135deg,${C.b2},${C.b3})`,color:"#fff",fontSize:13,fontWeight:800,letterSpacing:".02em",cursor:"pointer",boxShadow:"0 4px 14px rgba(30,58,95,.20)"}}>+ Subir avance semanal (con IA)</button>}
          {showUpload && <Modal title="Subir avance semanal" onClose={()=>{setShowUpload(false);setUpPreview(null);}}>
            <div style={{marginBottom:11}}>
              <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",display:"block",marginBottom:5}}>% Avance general</label>
              <input type="number" min={0} max={100} value={upPct} onChange={e=>setUpPct(Number(e.target.value))} style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:14,fontFamily:"'JetBrains Mono',monospace",fontWeight:700,color:C.b3}}/>
            </div>
            <div style={{marginBottom:11}}>
              <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",display:"block",marginBottom:5}}>Descripcion (la IA lo formatea)</label>
              <textarea value={upDesc} onChange={e=>setUpDesc(e.target.value)} rows={4} placeholder="Ej: completamos OSB del sector norte, marcos DVH en planta baja, falta cubierta sector sur..." style={{width:"100%",padding:"9px 11px",borderRadius:9,border:`1px solid ${C.border}`,fontSize:13,resize:"vertical",lineHeight:1.5}}/>
            </div>
            <div style={{marginBottom:14}}>
              <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",letterSpacing:".09em",display:"block",marginBottom:5}}>Fotos (opcional)</label>
              <input ref={upFileRef} type="file" accept="image/*" multiple onChange={handleUpFiles} style={{display:"none"}}/>
              <button onClick={()=>upFileRef.current?.click()} className="btn" style={{padding:"8px 13px",borderRadius:8,border:`1px dashed ${C.b2}`,background:C.tag,color:C.b2,fontSize:12,fontWeight:700,cursor:"pointer"}}>+ Agregar fotos ({upPhotos.length})</button>
              {upPhotos.length>0 && <div style={{display:"flex",gap:5,marginTop:8,overflowX:"auto"}}>{upPhotos.map((ph,i)=><img key={i} src={ph.url} alt="" style={{height:54,width:74,objectFit:"cover",borderRadius:6,flexShrink:0}}/>)}</div>}
            </div>
            {!upPreview && <button onClick={processUpAI} disabled={upProcessing||!upDesc.trim()} className="btn" style={{width:"100%",padding:"11px 14px",borderRadius:10,border:"none",background:upDesc.trim()?C.b2:C.dim,color:"#fff",fontSize:13,fontWeight:800,cursor:upDesc.trim()?"pointer":"not-allowed",opacity:upProcessing?0.6:1}}>{upProcessing?"Procesando con Claude...":"Generar resumen con IA"}</button>}
            {upPreview && <div>
              <div style={{background:C.bg,borderRadius:10,padding:13,marginBottom:11,border:`1px solid ${C.border}`}}>
                <p style={{fontSize:9,fontWeight:800,color:C.b2,textTransform:"uppercase",letterSpacing:".09em",marginBottom:6}}>Vista previa (editable)</p>
                <input value={upPreview.title} onChange={e=>setUpPreview({...upPreview,title:e.target.value})} style={{width:"100%",padding:"6px 8px",border:`1px solid ${C.border}`,borderRadius:6,fontSize:13,fontWeight:700,marginBottom:7,color:C.txt}}/>
                <textarea value={upPreview.summary} onChange={e=>setUpPreview({...upPreview,summary:e.target.value})} rows={3} style={{width:"100%",padding:"6px 8px",border:`1px solid ${C.border}`,borderRadius:6,fontSize:12,marginBottom:7,resize:"vertical",lineHeight:1.5,color:C.txt}}/>
                <p style={{fontSize:9,fontWeight:800,color:C.green,textTransform:"uppercase",marginTop:6,marginBottom:3}}>Completado:</p>
                {(upPreview.completed||[]).map((it,j)=><p key={j} style={{fontSize:11,color:C.txt}}>* {it}</p>)}
                <p style={{fontSize:9,fontWeight:800,color:C.b2,textTransform:"uppercase",marginTop:6,marginBottom:3}}>Proximos pasos:</p>
                {(upPreview.next||[]).map((it,j)=><p key={j} style={{fontSize:11,color:C.txt}}>* {it}</p>)}
              </div>
              <div style={{display:"flex",gap:8}}>
                <button onClick={()=>setUpPreview(null)} className="btn" style={{flex:1,padding:"10px 12px",borderRadius:9,border:`1px solid ${C.border}`,background:C.card,color:C.txt2,fontSize:12,fontWeight:700,cursor:"pointer"}}>Reintentar</button>
                <button onClick={publishUp} className="btn" style={{flex:2,padding:"10px 12px",borderRadius:9,border:"none",background:C.green,color:"#fff",fontSize:12,fontWeight:800,cursor:"pointer"}}>Publicar al cliente</button>
              </div>
            </div>}
          </Modal>}
          {updates.length === 0 && <Card style={{padding:24,textAlign:"center"}}><p style={{color:C.txt2,fontSize:13}}>Sin actualizaciones cargadas todavia.</p></Card>}
          {updates.map((upd,i)=>(
            <Card key={upd.id} style={{marginBottom:11,overflow:"hidden"}}>
              <div onClick={()=>setEu(eu===i?-1:i)} style={{padding:"14px 17px",cursor:"pointer",display:"flex",justifyContent:"space-between"}}>
                <div>
                  <span style={{fontSize:10,fontWeight:800,color:C.b2,textTransform:"uppercase",letterSpacing:".09em"}}>{upd.week}</span>
                  <p style={{fontSize:13,fontWeight:700,color:C.txt,marginTop:4}}>{upd.title}</p>
                </div>
                <Mono ch={`${upd.progress}%`} size={18} weight={900}/>
              </div>
              {eu===i && <div style={{padding:"0 17px 16px"}}>
                <p style={{fontSize:12,color:C.txt2,lineHeight:1.6,marginBottom:10}}>{upd.summary}</p>
                {(upd.photos||[]).length>0 && <div style={{display:"flex",gap:6,marginBottom:10,overflowX:"auto"}}>{upd.photos.map((ph,j)=><img key={j} src={ph} alt="" style={{height:90,width:130,objectFit:"cover",borderRadius:8,flexShrink:0}}/>)}</div>}
                {(upd.completed||[]).length>0 && <div style={{background:C.gBg,borderRadius:9,padding:"9px 11px",marginBottom:7}}>
                  <p style={{fontSize:9,fontWeight:800,color:C.green,textTransform:"uppercase",letterSpacing:".08em",marginBottom:5}}>Completado</p>
                  {upd.completed.map((it,j)=><p key={j} style={{fontSize:11,color:C.txt,marginBottom:3}}>* {it}</p>)}
                </div>}
                {(upd.next||[]).length>0 && <div style={{background:C.tag,borderRadius:9,padding:"9px 11px"}}>
                  <p style={{fontSize:9,fontWeight:800,color:C.b2,textTransform:"uppercase",letterSpacing:".08em",marginBottom:5}}>Proximos pasos</p>
                  {upd.next.map((it,j)=><p key={j} style={{fontSize:11,color:C.txt,marginBottom:3}}>* {it}</p>)}
                </div>}
              </div>}
            </Card>
          ))}
        </div>
      )}

      {tab==="financiero" && (
        <div className="up">
          <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:9,marginBottom:13}}>
            <Card style={{padding:12,background:C.tag,border:"none"}}>
              <p style={{fontSize:9,fontWeight:800,color:C.b3,textTransform:"uppercase",marginBottom:3}}>Contrato total</p>
              <Mono ch={`USD ${fmt(totalContract)}`} size={13} color={C.b3} weight={900}/>
            </Card>
            <Card style={{padding:12,background:C.aBg,border:"none"}}>
              <p style={{fontSize:9,fontWeight:800,color:C.amber,textTransform:"uppercase",marginBottom:3}}>Ajustado CAC</p>
              <Mono ch={`USD ${fmt(totalContract*(1+cacVar))}`} size={13} color={C.amber} weight={900}/>
              <p style={{fontSize:10,color:C.dim,marginTop:2}}>+{(cacVar*100).toFixed(2)}%</p>
            </Card>
            <Card style={{padding:12,background:C.gBg,border:"none"}}>
              <p style={{fontSize:9,fontWeight:800,color:C.green,textTransform:"uppercase",marginBottom:3}}>Pagado</p>
              <Mono ch={`USD ${fmt(paid)}`} size={13} color={C.green} weight={900}/>
            </Card>
            <Card style={{padding:12,background:C.rBg,border:"none"}}>
              <p style={{fontSize:9,fontWeight:800,color:C.red,textTransform:"uppercase",marginBottom:3}}>Saldo</p>
              <Mono ch={`USD ${fmt(pending)}`} size={13} color={C.red} weight={900}/>
            </Card>
          </div>
          <Card style={{padding:15,marginBottom:13}}>
            <p style={{fontSize:13,fontWeight:800,color:C.txt,marginBottom:13}}>Cuotas por hito</p>
            {milestones.map((m,i)=>(
              <div key={m.id} style={{display:"flex",alignItems:"center",gap:10,paddingBottom:10,marginBottom:10,borderBottom:i<milestones.length-1?`1px dashed ${C.border}`:"none"}}>
                <div style={{width:26,height:26,borderRadius:"50%",background:m.status==="paid"?C.gBg:C.aBg,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,fontSize:11,fontWeight:800,color:m.status==="paid"?C.green:C.amber}}>{m.status==="paid"?"OK":"--"}</div>
                <div style={{flex:1,minWidth:0}}>
                  <p style={{fontSize:12,fontWeight:700,color:C.txt,overflow:"hidden",whiteSpace:"nowrap",textOverflow:"ellipsis"}}>{m.name}</p>
                  <p style={{fontSize:10,color:C.dim}}>{m.status==="paid"?`${m.paidDate} - ${m.certRef}`:"Pendiente"}</p>
                </div>
                <Mono ch={`USD ${fmt(m.usd)}`} size={12} color={m.status==="paid"?C.green:C.amber} weight={800}/>
                {canEdit && m.status!=="paid" && <button onClick={()=>setPayModal(m)} className="btn" style={{padding:"5px 9px",borderRadius:6,border:"none",background:C.green,color:"#fff",fontSize:10,fontWeight:800,cursor:"pointer",letterSpacing:".04em"}}>MARCAR PAGADA</button>}
              </div>
            ))}
          </Card>
          {payModal && <Modal title={`Marcar pagada: ${payModal.name}`} onClose={()=>setPayModal(null)}>
            <div style={{background:C.gBg,borderRadius:9,padding:11,marginBottom:11,border:`1px solid ${C.green}`}}>
              <p style={{fontSize:10,fontWeight:800,color:C.green,textTransform:"uppercase",marginBottom:3}}>Importe a registrar</p>
              <Mono ch={`USD ${fmt(payModal.usd)}`} size={20} color={C.green} weight={900}/>
            </div>
            <p style={{fontSize:11,color:C.txt2,marginBottom:11,lineHeight:1.5}}>Al confirmar se marca la cuota como <strong>pagada</strong>, se registra la fecha de hoy y se emite automaticamente el <strong>Certificado de Avance</strong> en la pestana Planos.</p>
            <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>Nota interna (opcional)</label>
            <textarea value={payNote} onChange={e=>setPayNote(e.target.value)} rows={2} placeholder="Ref. transferencia, banco, etc." style={{width:"100%",padding:"8px 10px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:12,marginBottom:13,resize:"vertical"}}/>
            <div style={{display:"flex",gap:8}}>
              <button onClick={()=>setPayModal(null)} className="btn" style={{flex:1,padding:"10px 12px",borderRadius:9,border:`1px solid ${C.border}`,background:C.card,color:C.txt2,fontSize:12,fontWeight:700,cursor:"pointer"}}>Cancelar</button>
              <button onClick={confirmPay} disabled={paySaving} className="btn" style={{flex:2,padding:"10px 12px",borderRadius:9,border:"none",background:C.green,color:"#fff",fontSize:12,fontWeight:800,cursor:paySaving?"wait":"pointer",opacity:paySaving?0.6:1}}>{paySaving?"Guardando...":"Confirmar y emitir certificado"}</button>
            </div>
          </Modal>}
        </div>
      )}

      {tab==="planos" && (
        <div className="up">
          {documents.length === 0 && <Card style={{padding:24,textAlign:"center"}}><p style={{color:C.txt2,fontSize:13}}>Sin documentos cargados.</p></Card>}
          {documents.map(doc=>(
            <Card key={doc.id} style={{padding:"11px 14px",marginBottom:8,display:"flex",alignItems:"center",gap:10}}>
              <div style={{width:32,height:32,borderRadius:8,background:C.tag,display:"flex",alignItems:"center",justifyContent:"center",fontSize:14,fontWeight:800,color:C.b2}}>{doc.icon}</div>
              <div style={{flex:1,minWidth:0}}>
                <p style={{fontSize:13,fontWeight:700,color:C.txt}}>{doc.name}</p>
                <p style={{fontSize:10,color:C.dim}}>{doc.date} - {doc.size}{doc.ref?` - ${doc.ref}`:""}</p>
              </div>
              <Badge status={doc.status}/>
            </Card>
          ))}
        </div>
      )}

      {tab==="mods" && (
        <div className="up">
          {mods.length === 0 && <Card style={{padding:24,textAlign:"center"}}><p style={{color:C.txt2,fontSize:13}}>Sin modificaciones solicitadas.</p></Card>}
          {mods.map(mod=>(
            <Card key={mod.id} style={{padding:14,marginBottom:9}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <Mono ch={`${mod.id} - ${mod.date}`} size={10} color={C.dim} weight={600}/>
                <Badge status={mod.status}/>
              </div>
              <p style={{fontSize:13,fontWeight:700,color:C.txt,marginBottom:5}}>{mod.title}</p>
              <p style={{fontSize:12,color:C.txt2,lineHeight:1.5,marginBottom:mod.archNote?7:0}}>{mod.description}</p>
              {mod.archNote && <div style={{background:mod.status==="approved"?C.gBg:C.rBg,borderRadius:7,padding:"7px 10px",marginTop:6,borderLeft:`3px solid ${mod.status==="approved"?C.green:C.red}`}}>
                <p style={{fontSize:9,fontWeight:800,color:mod.status==="approved"?C.green:C.red,textTransform:"uppercase",marginBottom:2}}>{mod.status==="approved"?`Aprobada - ${mod.approvalNumber}`:"Rechazada"}</p>
                <p style={{fontSize:11,color:C.txt}}>{mod.archNote}</p>
              </div>}
              {canEdit && (mod.status==="pending"||!mod.status) && <div style={{display:"flex",gap:8,marginTop:10}}>
                <button onClick={()=>setModAction({mod,action:"reject"})} className="btn" style={{flex:1,padding:"7px 10px",borderRadius:7,border:`1px solid ${C.red}`,background:"#fff",color:C.red,fontSize:11,fontWeight:800,cursor:"pointer",letterSpacing:".03em"}}>RECHAZAR</button>
                <button onClick={()=>setModAction({mod,action:"approve"})} className="btn" style={{flex:1,padding:"7px 10px",borderRadius:7,border:"none",background:C.green,color:"#fff",fontSize:11,fontWeight:800,cursor:"pointer",letterSpacing:".03em"}}>APROBAR</button>
              </div>}
            </Card>
          ))}
          {modAction && <Modal title={`${modAction.action==="approve"?"Aprobar":"Rechazar"} modificacion`} onClose={()=>setModAction(null)}>
            <p style={{fontSize:12,color:C.txt,marginBottom:11,lineHeight:1.5}}><strong>{modAction.mod.title}</strong></p>
            <p style={{fontSize:11,color:C.txt2,marginBottom:13,lineHeight:1.5}}>{modAction.mod.description}</p>
            <label style={{fontSize:10,fontWeight:800,color:C.txt2,textTransform:"uppercase",display:"block",marginBottom:5}}>{modAction.action==="approve"?"Nota tecnica (visible al cliente)":"Motivo del rechazo"}</label>
            <textarea value={modNote} onChange={e=>setModNote(e.target.value)} rows={3} placeholder={modAction.action==="approve"?"Aprobado. Sumamos $X al contrato y Y dias al cronograma...":"No es factible porque..."} style={{width:"100%",padding:"8px 10px",border:`1px solid ${C.border}`,borderRadius:8,fontSize:12,marginBottom:13,resize:"vertical",lineHeight:1.5}}/>
            <div style={{display:"flex",gap:8}}>
              <button onClick={()=>setModAction(null)} className="btn" style={{flex:1,padding:"10px 12px",borderRadius:9,border:`1px solid ${C.border}`,background:C.card,color:C.txt2,fontSize:12,fontWeight:700,cursor:"pointer"}}>Cancelar</button>
              <button onClick={confirmModAction} disabled={modSaving} className="btn" style={{flex:2,padding:"10px 12px",borderRadius:9,border:"none",background:modAction.action==="approve"?C.green:C.red,color:"#fff",fontSize:12,fontWeight:800,cursor:modSaving?"wait":"pointer",opacity:modSaving?0.6:1}}>{modSaving?"Guardando...":(modAction.action==="approve"?"Confirmar aprobacion":"Confirmar rechazo")}</button>
            </div>
          </Modal>}
        </div>
      )}
    </div>
  );
};

// ─── ROOT APP ──────────────────────────────────────────────────────────────
export default function App() {
  const [authState, setAuthState] = useState({ user: null, project: null, projects: null });
  const [authMode, setAuthMode] = useState("login");
  const [setPwToken, setSetPwToken] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = async (token) => {
    try {
      const r = await fetch("/api/mi-hogar/me", { headers: { Authorization: `Bearer ${token}` } });
      const data = await r.json();
      if (data.ok) {
        setAuthState({ user: data.user, project: data.project || null, projects: data.projects || null });
        setAuthMode("app");
        return true;
      }
    } catch {}
    clearToken();
    return false;
  };

  useEffect(() => {
    boot();
    const url = new URL(window.location.href);
    const invite = url.searchParams.get("invite");
    const reset = url.searchParams.get("reset");
    if (invite) {
      setSetPwToken(invite);
      setAuthMode("set-password");
      setLoading(false);
      return;
    }
    if (reset) {
      setSetPwToken(reset);
      setAuthMode("set-password");
      setLoading(false);
      return;
    }
    const saved = getToken();
    if (saved) {
      fetchMe(saved).finally(()=>setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = async (user, token) => {
    await fetchMe(token);
  };

  const handleSetPasswordDone = async (user, token) => {
    setSetPwToken(null);
    await fetchMe(token);
  };

  const handleLogout = () => {
    clearToken();
    setAuthState({ user: null, project: null, projects: null });
    setAuthMode("login");
  };

  if (loading) return <Splash/>;

  if (authMode === "set-password" && setPwToken) {
    return <SetPasswordForm token={setPwToken} onDone={handleSetPasswordDone}/>;
  }
  if (authMode === "forgot") {
    return <ForgotPasswordForm onBack={()=>setAuthMode("login")}/>;
  }
  if (authMode !== "app" || !authState.user) {
    return <Login onLogin={handleLogin} onForgot={()=>setAuthMode("forgot")}/>;
  }

  if (authState.user.role === "client" && authState.project) {
    return <ClientDash user={authState.user} project={authState.project} onLogout={handleLogout}/>;
  }
  return <ArchPanel user={authState.user} projects={authState.projects || []} onLogout={handleLogout}/>;
}
