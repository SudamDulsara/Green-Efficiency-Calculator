# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict

from workflow import run_workflow  # v1 linear
from coordinator import run_agentic  # v2 agentic

app = FastAPI(title="Green Efficiency Calculator API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RawPayload(BaseModel):
    payload: Dict[str, Any]

@app.get("/")
def health():
    return {"ok": True, "version": "2.0"}

@app.post("/run_workflow")
def run_workflow_endpoint(req: RawPayload):
    return run_workflow(req.payload)

@app.post("/agentic")
def run_agentic_endpoint(req: RawPayload):
    """
    Agentic v2: optional keys:
      - region: str (for tariff lookup)
      - bill_text: str (raw text pasted from bill; optional)
      - other intake fields...
    """
    return run_agentic(req.payload)
