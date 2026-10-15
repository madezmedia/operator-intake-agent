# Demo script — stub mode, one booked lead

A 2–3 minute take. One lead, from the first chat message through a booked appointment. No `.env`, no Evolus key, no GPU.

Record against a checkout of this repo. If a `.env` is present and sets `VLLM_STUB=false`, the replies below will not match. For this take, use a clean tree and leave stub mode on.

The stub answers only when the wording hits its rules. Send the four customer lines **exactly**, one at a time, and wait for each reply. Do not refresh the page mid-take. A refresh mints a new lead id and the booking you just made stays on the old one.

Target length: about 2 minutes 30 seconds once the server is up. The first image build can run before you hit record.

---

## 0:00 — Start the stack (about 20 seconds on camera)

In a terminal, from the repo root:

```bash
docker compose up --build
```

Leave that terminal visible. Wait until the `agent` log shows Uvicorn running on port 8000. Redis must be healthy first; compose waits for that.

In a second terminal:

```bash
curl -sS -D - http://localhost:8000/health
```

Say this while it returns: “Liveness is up. No credentials.”

On screen:

- Status line `HTTP/1.1 200 OK`
- Body `{"ok":true}`

Then confirm this is the stub, still with Evolus offline:

```bash
curl -sS http://localhost:8000/healthz
```

Read these fields out loud:

- `"ok": true`
- `"model": {"stub": true, "name": "Qwen/Qwen2.5-7B-Instruct"}`
- `"evolus": {"configured": false, ...}`
- `"memory": "redis"`

If `stub` is not `true`, stop. Do not record the live model path with this script.

---

## 0:20 — Open the chat and copy the lead id (about 20 seconds)

In the browser, open:

http://localhost:8000

The page title in the body is **Chat with us**. The box placeholder is `Hi, I need...`. There is a **Send** button. Enter sends too.

The page picks a lead id when it loads (`demo-` plus a number) and does not print it. Before you type the first message:

1. Open DevTools (F12).
2. Click **Console**.
3. Type `leadId` and press Enter.
4. Copy the string it prints, for example `demo-482193`.

Keep that value. You will paste it into the two curls at the end.

Narrator line: “Pretend it is 9 p.m. and the AC just died. The office is closed. This chat is the front desk.”

---

## 0:40 — Message 1, intake (about 20 seconds)

Click the input. Type exactly:

```text
Hi, my AC stopped blowing cold air
```

Press Enter.

The agent reply is:

```text
[stub] Got it, thanks. What's your name and phone?
```

The `[stub]` prefix is intentional. Say: “That prefix means the rule-based stand-in is answering. The tools behind it are the real ones.”

What just happened: the message matched an AC job, so the agent saved the service on this lead and asked only for what is still missing.

---

## 1:00 — Message 2, the facts (about 25 seconds)

Type exactly:

```text
I'm Dana Brooks, 704-555-0142, zip 28205, tomorrow if possible
```

Press Enter.

The agent reply is:

```text
[stub] Got it. Want me to book you in?
```

Say: “Name, phone, ZIP, and tomorrow are on the lead now. It did not ask for any of them again.”

---

## 1:25 — Message 3, qualify and offer slots (about 25 seconds)

Type exactly:

```text
Can you book me in?
```

Press Enter.

The agent reply starts with:

```text
[stub] Great, you're all set to book. Open slots:
```

and then three labels. They are the next weekday windows at 9:00 AM, 11:00 AM, and 1:00 PM Eastern, like `Fri Oct 16, 9:00 AM`. The calendar date depends on the day you record. Read the three labels the agent actually printed. Do not substitute your own times.

Under the hood the score is 90 (phone, service, name, preferred time, ZIP). The bar is 60, so this lead can book.

---

## 1:50 — Message 4, book the first window (about 20 seconds)

Type exactly:

```text
The first one sounds good
```

Press Enter.

The agent reply is:

```text
[stub] You're booked for LABEL. We'll text a reminder.
```

`LABEL` is the first of the three labels from the previous reply. Read it back.

Say: “Booked. Same lead. Nobody re-asked the phone number, the ZIP, or what was broken.”

---

## 2:10 — Show the shared record (about 25 seconds)

Back in the second terminal, paste the lead id from the console. Replace `LEAD_ID` below.

```bash
curl -sS http://localhost:8000/lead/LEAD_ID
```

Point at:

- `name`: `Dana Brooks`
- `phone`: `704-555-0142`
- `zip`: `28205`
- `service`: the first customer message (it contains “AC”)
- `preferred_time`: `tomorrow`
- `score`: `90`
- `qualified`: `true`
- `stage`: `followup`
- `booking.label`: the same window the agent just confirmed
- `evolus_status`: `skipped`

Then the timeline:

```bash
curl -sS http://localhost:8000/lead/LEAD_ID/timeline
```

Scroll so these `kind` values are visible: `intake`, `qualification`, `booking`, `evolus`. The Evolus line says the workflow was skipped. That is the offline path. The appointment is still booked.

Closing line, to camera:

“Every step was a separate turn. They all used one lead record, so the booking step already knew Dana. Judges can run this with `docker compose up --build` and `GET /health`. The live AMD numbers and the Evolus workspace come on when the owner’s `.env` is in place.”

Stop. Do not open a real Evolus console in this take unless that smoke has already been done off camera. This script stays on the stub.

---

## If a reply does not match

| What you see | What to do |
|---|---|
| Health is not 200 | Wait for Uvicorn, then run the health curl again. |
| `healthz` shows `"stub": false` | You are on the live model. Stop. Start from a tree with no `.env`, or with `VLLM_STUB=true`. |
| Agent asks for name and phone again after message 2 | The second line was edited. Send it again exactly, including `I'm Dana Brooks`. |
| No slot list after message 3 | The line must contain “book”. Send `Can you book me in?` |
| The booked time is not the first label you were just offered, or the reply says the slot is unavailable | Redis still has bookings from an earlier take. Stop the stack with `docker compose down -v`, start again, and begin at message 1. |
| Page was refreshed | Copy the new `leadId` from the console and start at message 1. |

---

## Shot list

1. Terminal: `docker compose up --build`, then the 200 from `/health`.
2. Terminal: `/healthz` with stub true and Evolus not configured.
3. Browser: the four messages and the four `[stub]` replies, uninterrupted.
4. Terminal: `/lead/LEAD_ID` and `/lead/LEAD_ID/timeline`, with the booking and `evolus_status` of `skipped` in frame.
