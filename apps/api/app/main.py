from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routers import (
    admin,
    audits,
    chain,
    datasets,
    samples,
    evidence,
    model_versions,
    organizations,
    projects,
    training_rounds,
    training_tasks,
)

app = FastAPI(title="AI 模型训练过程可信审计平台接口")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(projects.router)
app.include_router(organizations.router)
app.include_router(datasets.router)
app.include_router(training_tasks.router)
app.include_router(training_rounds.router)
app.include_router(model_versions.router)
app.include_router(audits.router)
app.include_router(evidence.router)
app.include_router(chain.router)
app.include_router(samples.router)
app.include_router(admin.router)
