"""FastAPI app: chat widget endpoint + health check."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .agent import steps
from .memory import store

app = FastAPI(title="Operator Intake Agent")


class ChatIn(BaseModel):
    lead_id: str
    message: str


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/chat")
async def chat(inp: ChatIn):
    reply = await steps.handle_message(inp.lead_id, inp.message)
    return {"reply": reply}


@app.get("/lead/{lead_id}")
async def lead(lead_id: str):
    return await store.get_lead(lead_id)


@app.get("/", response_class=HTMLResponse)
async def widget():
    return """
    <html><body style="font-family:sans-serif;max-width:480px;margin:40px auto">
    <h2>Chat with us</h2>
    <div id="log" style="border:1px solid #ccc;height:300px;overflow:auto;padding:8px"></div>
    <input id="msg" style="width:80%" placeholder="Hi, I need..."/>
    <button onclick="send()">Send</button>
    <script>
    const leadId = 'demo-' + Math.floor(Math.random()*1e6);
    async function send(){
      const m = document.getElementById('msg'); const log = document.getElementById('log');
      log.innerHTML += '<p><b>You:</b> ' + m.value + '</p>';
      const r = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({lead_id: leadId, message: m.value})});
      const j = await r.json();
      log.innerHTML += '<p><b>Agent:</b> ' + j.reply + '</p>'; m.value='';
    }
    </script></body></html>
    """
