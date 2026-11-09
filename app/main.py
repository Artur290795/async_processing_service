from fastapi import FastAPI

from app.api.routes import payments_router

app = FastAPI(title="Async Payment Processing Service", version="0.1.0")
app.include_router(payments_router)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
