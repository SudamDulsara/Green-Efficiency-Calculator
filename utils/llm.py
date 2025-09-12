import os, json
from openai import OpenAI

_client = None
def _client_ok():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

def call_json(system_prompt: str, user_prompt: str, model: str|None=None, temperature: float=0.2):
    client = _client_ok()
    model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role":"system","content":system_prompt},
                  {"role":"user","content":user_prompt}],
        response_format={"type":"json_object"},
    )
    txt = resp.choices[0].message.content
    try:
        return json.loads(txt)
    except Exception:
        resp2 = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[{"role":"system","content":system_prompt},
                      {"role":"user","content":user_prompt + "\n\nReturn ONLY valid JSON."}],
            response_format={"type":"json_object"},
        )
        return json.loads(resp2.choices[0].message.content)
    
def call_text(system_prompt: str, user_prompt: str, model: str|None=None, temperature: float=0.2):
    client = _client_ok()
    model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role":"system","content":system_prompt},
                  {"role":"user","content":user_prompt}],
    )
    return resp.choices[0].message.content
