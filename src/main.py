"""FastAPI app: chat widget endpoint + health check."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .agent import steps
from .memory import store
from .evolus import client as evolus
from .config import settings

app = FastAPI(title="Operator Intake Agent")


class ChatIn(BaseModel):
    lead_id: str
    message: str


@app.get("/healthz")
async def healthz():
    """Liveness plus non-secret integration status."""
    return {"ok": True,
            "model": {"stub": settings.vllm_stub, "name": settings.vllm_model},
            "evolus": evolus.status(),
            "memory": settings.memory_backend}


@app.post("/chat")
async def chat(inp: ChatIn):
    reply = await steps.handle_message(inp.lead_id, inp.message)
    return {"reply": reply}


@app.get("/lead/{lead_id}")
async def lead(lead_id: str):
    return await store.get_lead(lead_id)


@app.get("/lead/{lead_id}/timeline")
async def timeline(lead_id: str):
    return await store.get_timeline(lead_id)


@app.get("/", response_class=HTMLResponse)
async def widget():
    return """
    <html><body style="font-family:sans-serif;max-width:480px;margin:40px auto">
    <h2>Chat with us</h2>
    <div id="log" style="border:1px solid #ccc;height:300px;overflow:auto;padding:8px"></div>
    <input id="msg" style="width:80%" placeholder="Hi, I need..."
      onkeydown="if(event.key==='Enter')send()"/>
    <button onclick="send()">Send</button>
    <script>
    const leadId = 'demo-' + Math.floor(Math.random()*1e6);
    function add(who, text){
      const p = document.createElement('p'), b = document.createElement('b');
      b.textContent = who + ': '; p.appendChild(b); p.appendChild(document.createTextNode(text));
      const log = document.getElementById('log'); log.appendChild(p); log.scrollTop = log.scrollHeight;
    }
    async function send(){
      const m = document.getElementById('msg'); const text = m.value.trim();
      if(!text) return; add('You', text); m.value = '';
      const r = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({lead_id: leadId, message: text})});
      const j = await r.json(); add('Agent', j.reply);
    }
    </script></body></html>
    """
