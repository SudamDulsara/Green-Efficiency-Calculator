from agents.intake_agent import normalize

def run_workflow(input_payload: dict) -> dict:
    data = normalize(input_payload)