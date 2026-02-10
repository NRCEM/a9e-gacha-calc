from functools import lru_cache
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.character import analyze

app = FastAPI(title="A9E Banner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimRequest(BaseModel):
    pity_6: int
    pity_120: int
    rolls: int


@lru_cache(maxsize=512)
def _cached_curve(pity_6: int, pity_120: int, rolls: int):
    return analyze(rolls, pity_6, pity_120)["curve"]


@app.post("/simulate")
def api_simulate(req: SimRequest):
    out = analyze(req.rolls, req.pity_6, req.pity_120)
    out.pop("curve", None)  # keep response small
    return out


@app.post("/series")
def api_series(req: SimRequest):
    return {"character": _cached_curve(req.pity_6, req.pity_120, req.rolls)}
