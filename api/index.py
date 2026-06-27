from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import time
import random
import string

try:
    from upstash_redis import Redis
    redis_client = Redis(
        url=os.environ.get("UPSTASH_REDIS_REST_URL", ""),
        token=os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
    )
    USE_REDIS = bool(os.environ.get("UPSTASH_REDIS_REST_URL"))
except Exception:
    redis_client = None
    USE_REDIS = False

# Fallback in-memory store for local dev
_memory_store = {}

app = FastAPI(title="When Can We Meet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    title: str
    dates: List[str]          # ISO date strings, e.g. "2024-06-01"
    host_name: str


class VoteRequest(BaseModel):
    participant_name: str
    selected_dates: List[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_id(n=8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _kv_get(key: str):
    if USE_REDIS:
        val = redis_client.get(key)
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        return json.loads(val)
    return _memory_store.get(key)


def _kv_set(key: str, value, ex: int = 60 * 60 * 24 * 30):
    if USE_REDIS:
        redis_client.set(key, json.dumps(value), ex=ex)
    else:
        _memory_store[key] = value


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "redis": USE_REDIS}


@app.post("/api/rooms")
def create_room(body: CreateRoomRequest):
    room_id = _gen_id()
    room = {
        "id": room_id,
        "title": body.title,
        "dates": body.dates,
        "host_name": body.host_name,
        "participants": {},
        "created_at": int(time.time()),
    }
    _kv_set(f"room:{room_id}", room)
    return {"room_id": room_id, "room": room}


@app.get("/api/rooms/{room_id}")
def get_room(room_id: str):
    room = _kv_get(f"room:{room_id}")
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@app.post("/api/rooms/{room_id}/vote")
def vote(room_id: str, body: VoteRequest):
    room = _kv_get(f"room:{room_id}")
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    name = body.participant_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")

    # Validate dates belong to room
    valid = set(room["dates"])
    selected = [d for d in body.selected_dates if d in valid]

    room["participants"][name] = selected
    _kv_set(f"room:{room_id}", room)

    # Compute tallies
    tally = _compute_tally(room)
    return {"participants": room["participants"], "tally": tally}


@app.get("/api/rooms/{room_id}/results")
def get_results(room_id: str):
    room = _kv_get(f"room:{room_id}")
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    tally = _compute_tally(room)
    return {
        "title": room["title"],
        "dates": room["dates"],
        "participants": room["participants"],
        "tally": tally,
        "best_dates": _best_dates(tally),
    }


def _compute_tally(room: dict) -> dict:
    tally = {d: 0 for d in room["dates"]}
    for selected in room["participants"].values():
        for d in selected:
            if d in tally:
                tally[d] += 1
    return tally


def _best_dates(tally: dict) -> List[str]:
    if not tally:
        return []
    max_votes = max(tally.values())
    if max_votes == 0:
        return []
    return [d for d, v in tally.items() if v == max_votes]


# ── Vercel handler ────────────────────────────────────────────────────────────
handler = Mangum(app, lifespan="off")
