from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel
from typing import List
import json, os, time, random, string, urllib.request, urllib.error

REDIS_URL   = os.environ.get("UPSTASH_REDIS_REST_URL", "").rstrip("/")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
USE_REDIS   = bool(REDIS_URL and REDIS_TOKEN)

_memory_store = {}

def _redis(command: list):
    url  = f"{REDIS_URL}/{'/'.join(str(c) for c in command)}"
    req  = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=4) as r:
        return json.loads(r.read())["result"]

def _kv_get(key: str):
    if USE_REDIS:
        val = _redis(["GET", key])
        return json.loads(val) if val else None
    return _memory_store.get(key)

def _kv_set(key: str, value, ex: int = 60*60*24*30):
    if USE_REDIS:
        encoded = urllib.request.quote(json.dumps(value, ensure_ascii=False))
        _redis(["SET", key, encoded, "EX", ex])
    else:
        _memory_store[key] = value

def _gen_id(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

app = FastAPI(title="Whenly API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

class CreateRoomRequest(BaseModel):
    title: str
    dates: List[str]
    host_name: str

class VoteRequest(BaseModel):
    participant_name: str
    selected_dates: List[str]

@app.get("/api/health")
def health():
    return {"status": "ok", "redis": USE_REDIS,
            "url_set": bool(REDIS_URL), "token_set": bool(REDIS_TOKEN)}

@app.post("/api/rooms")
def create_room(body: CreateRoomRequest):
    room_id = _gen_id()
    room = {"id": room_id, "title": body.title, "dates": body.dates,
            "host_name": body.host_name, "participants": {},
            "created_at": int(time.time())}
    _kv_set(f"room:{room_id}", room)
    return {"room_id": room_id, "room": room}

@app.get("/api/rooms/{room_id}")
def get_room(room_id: str):
    room = _kv_get(f"room:{room_id}")
    if not room:
        raise HTTPException(404, "Room not found")
    return room

@app.post("/api/rooms/{room_id}/vote")
def vote(room_id: str, body: VoteRequest):
    room = _kv_get(f"room:{room_id}")
    if not room:
        raise HTTPException(404, "Room not found")
    name = body.participant_name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    valid = set(room["dates"])
    room["participants"][name] = [d for d in body.selected_dates if d in valid]
    _kv_set(f"room:{room_id}", room)
    return {"participants": room["participants"], "tally": _tally(room)}

@app.get("/api/rooms/{room_id}/results")
def get_results(room_id: str):
    room = _kv_get(f"room:{room_id}")
    if not room:
        raise HTTPException(404, "Room not found")
    t = _tally(room)
    return {"title": room["title"], "dates": room["dates"],
            "participants": room["participants"],
            "tally": t, "best_dates": _best(t)}

def _tally(room):
    t = {d: 0 for d in room["dates"]}
    for sel in room["participants"].values():
        for d in sel:
            if d in t: t[d] += 1
    return t

def _best(tally):
    if not tally: return []
    m = max(tally.values())
    return [] if m == 0 else [d for d, v in tally.items() if v == m]

handler = Mangum(app, lifespan="off")