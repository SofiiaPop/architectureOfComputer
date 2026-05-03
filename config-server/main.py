import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI()

registry: Dict[str, List[str]] = {}


class RegisterRequest(BaseModel):
    service_name: str
    url: str


@app.post("/register")
def register(req: RegisterRequest):
    registry.setdefault(req.service_name, [])
    if req.url not in registry[req.service_name]:
        registry[req.service_name].append(req.url)
    print(f"[config-server] Registered {req.service_name} -> {req.url}")
    print(f"[config-server] Registry state: {registry}")
    return {"status": "ok"}


@app.get("/services/{service_name}")
def get_service(service_name: str):
    urls = registry.get(service_name)
    if not urls:
        raise HTTPException(status_code=404, detail=f"No instances for {service_name}")
    return {"service_name": service_name, "urls": urls}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))