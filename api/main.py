import asyncio
import hmac
import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from .analysis import family_comparison, methylation_summary, wearable_summary
from .combined_demo import demo_profile_order, ensure_combined_demo
from .config import Settings, settings
from .datasets import investigation_calls, records
from .demo import add_demo_methylation, seed_demo, template_file
from .demo_cases import profile_coverage
from .eligibility import investigation_eligibility, investigation_identity
from .methylation_demo import ensure_blood_demo
from .models import (
    ConversationCreate,
    FamilyCreate,
    InvestigationCreate,
    MessageCreate,
    ProfileCreate,
    SessionCreate,
)
from .public_demo import attach_public_methylation, seed_public_demo
from .store import Store, identifier
from .worker import loop


def create_app(config: Settings | None = None, *, embedded_worker: bool | None = None) -> FastAPI:
    config = config or settings
    embedded_worker = config.dna_embedded_worker if embedded_worker is None else embedded_worker
    store = Store(config)

    @asynccontextmanager
    async def lifespan(app):
        stop = asyncio.Event()
        task = asyncio.create_task(loop(store, stop)) if embedded_worker else None
        yield
        stop.set()
        if task:
            await task

    app = FastAPI(title="Helix research workspace", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Last-Event-ID"],
    )

    def session(request: Request) -> dict:
        authorization = request.headers.get("Authorization", "")
        value = (
            store.authenticate(authorization.removeprefix("Bearer "))
            if authorization.startswith("Bearer ")
            else None
        )
        if not value:
            raise HTTPException(401, "Session expired. Reconnect to the workspace.")
        return value

    Session = Annotated[dict, Depends(session)]

    def require_profile(auth, profile_id):
        profile = store.profile(auth["id"], profile_id)
        if not profile:
            raise HTTPException(404, "Profile not found.")
        return profile

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "methylation_required": False,
            "providers": {
                "chat": bool(config.anthropic_api_key),
                "alphagenome": bool(config.alphagenome_api_key),
                "evo2": bool(config.evo2_forward_endpoint),
            },
            "version": "0.1.0",
        }

    @app.get("/api/scientific-contexts")
    async def scientific_contexts(auth: Session):
        from .science import alphagenome_contexts

        if not config.alphagenome_api_key:
            return {"contexts": [], "configured": False}
        cached = store.cached("alphagenome:contexts")
        if cached is not None:
            return {"contexts": cached, "configured": True}
        try:
            contexts = await asyncio.to_thread(alphagenome_contexts, config.alphagenome_api_key)
        except Exception:
            raise HTTPException(
                503, "Could not retrieve supported scientific contexts. No substitute list was used."
            ) from None
        store.cache("alphagenome:contexts", contexts)
        return {"contexts": contexts, "configured": True}

    @app.post("/api/session")
    def create_session(body: SessionCreate, request: Request):
        if not body.demo:
            local = request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}
            permitted = bool(config.dna_access_key) and hmac.compare_digest(
                body.access_key, config.dna_access_key
            )
            if not permitted and not (config.dna_allow_local_workspaces and local):
                raise HTTPException(403, "A workspace access key is required for private uploads.")
        token, workspace = store.session(body.demo)
        seed = seed_public_demo if body.demo_source == "public" else seed_demo
        profiles = seed(store, workspace) if body.demo else []
        if body.demo and body.demo_source == "public":
            profiles = ensure_combined_demo(store, workspace)
        return {
            "token": token,
            "workspace_id": workspace,
            "demo": body.demo,
            "demo_source": body.demo_source if body.demo else None,
            "profiles": profile_coverage(store, workspace, profiles),
        }

    @app.get("/api/profiles")
    def profiles(auth: Session):
        return profile_coverage(store, auth["id"], demo_profile_order(store.profiles(auth["id"])))

    @app.post("/api/demo/combined-profiles")
    def combined_profiles(auth: Session):
        if not auth["demo"] or not any(p.get("public_dataset_key") for p in store.profiles(auth["id"])):
            raise HTTPException(403, "Combined public-source personas are available in the public demo only.")
        return profile_coverage(store, auth["id"], ensure_combined_demo(store, auth["id"]))

    @app.post("/api/profiles", status_code=201)
    def new_profile(body: ProfileCreate, auth: Session):
        if auth["demo"]:
            raise HTTPException(403, "Create a private workspace to add your own data.")
        try:
            ZoneInfo(body.timezone)
        except ZoneInfoNotFoundError:
            raise HTTPException(422, "Use an IANA timezone, such as America/New_York.") from None
        return store.create_profile(auth["id"], {**body.model_dump(), "provenance": "uploaded"})

    @app.patch("/api/profiles/{profile_id}")
    def update_profile(profile_id: str, body: ProfileCreate, auth: Session):
        profile = require_profile(auth, profile_id)
        if auth["demo"]:
            raise HTTPException(403, "Demo profiles are read-only.")
        try:
            ZoneInfo(body.timezone)
        except ZoneInfoNotFoundError:
            raise HTTPException(422, "Invalid IANA timezone.") from None
        with store.connection() as conn:
            conn.execute(
                "UPDATE profiles SET payload=? WHERE id=? AND workspace=?",
                (
                    json.dumps({**body.model_dump(), "provenance": profile["provenance"]}),
                    profile_id,
                    auth["id"],
                ),
            )
        return store.profile(auth["id"], profile_id)

    @app.delete("/api/profiles/{profile_id}", status_code=204)
    def delete_profile(profile_id: str, auth: Session):
        require_profile(auth, profile_id)
        with store.connection() as conn:
            jobs = conn.execute("SELECT id,payload FROM jobs WHERE workspace=?", (auth["id"],)).fetchall()
            for job in jobs:
                payload = json.loads(job["payload"])
                if payload.get("profile_id") == profile_id:
                    if payload.get("source"):
                        Path(payload["source"]).unlink(missing_ok=True)
                    conn.execute("DELETE FROM events WHERE job=?", (job["id"],))
                    conn.execute("DELETE FROM jobs WHERE id=?", (job["id"],))
            conn.execute("DELETE FROM datasets WHERE profile=? AND workspace=?", (profile_id, auth["id"]))
            conn.execute("DELETE FROM profiles WHERE id=? AND workspace=?", (profile_id, auth["id"]))
            conn.execute(
                "DELETE FROM conversations WHERE profile=? AND workspace=?", (profile_id, auth["id"])
            )
            # Molecular cache keys contain workspace-specific information; clear on profile deletion.
            conn.execute("DELETE FROM cache WHERE key LIKE ?", (f"molecular:{auth['id']}:%",))
        shutil.rmtree(store.root / auth["id"] / profile_id, ignore_errors=True)

    @app.get("/api/profiles/{profile_id}/datasets")
    def datasets(profile_id: str, auth: Session):
        require_profile(auth, profile_id)
        return [
            {k: v for k, v in d.items() if k not in {"path", "workspace"}}
            for d in store.datasets(auth["id"], profile_id)
        ]

    @app.post("/api/profiles/{profile_id}/datasets", status_code=202)
    async def upload(
        profile_id: str,
        auth: Session,
        file: UploadFile = File(...),
        kind: str = Form(...),
        metadata: str = Form("{}"),
    ):
        require_profile(auth, profile_id)
        if auth["demo"]:
            raise HTTPException(403, "Use a private workspace for uploads.")
        if kind not in {"genetics", "wearables", "methylation"}:
            raise HTTPException(422, "Unsupported dataset type.")
        try:
            meta = json.loads(metadata)
            if not isinstance(meta, dict):
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(422, "Metadata must be a JSON object.") from None
        meta["provenance"] = "uploaded"
        name = Path(file.filename or "upload.txt").name
        folder = store.root / auth["id"] / profile_id / "imports"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (identifier() + (".gz" if name.endswith(".gz") else ".txt"))
        size = 0
        try:
            with path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > config.max_upload_bytes:
                        raise HTTPException(413, "Upload exceeds the 512 MiB limit.")
                    output.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        job = store.new_job(
            auth["id"],
            "import",
            {"profile_id": profile_id, "kind": kind, "metadata": meta, "filename": name, "source": str(path)},
        )
        return {"job_id": job}

    @app.get("/api/profiles/{profile_id}/variants")
    def variants(profile_id: str, auth: Session, search: str = "", limit: int = Query(100, ge=1, le=500)):
        require_profile(auth, profile_id)
        return [
            {
                **r,
                "investigation": investigation_eligibility(r),
                "investigation_id": investigation_identity(r),
            }
            for r in records(store, auth["id"], profile_id, "genetics", limit=limit, search=search[:100])
        ]

    @app.get("/api/profiles/{profile_id}/wearables")
    def wearables(profile_id: str, auth: Session):
        require_profile(auth, profile_id)
        return wearable_summary(store, auth["id"], profile_id)

    @app.get("/api/profiles/{profile_id}/methylation")
    def methylation(profile_id: str, auth: Session):
        require_profile(auth, profile_id)
        return methylation_summary(store, auth["id"], profile_id)

    @app.post("/api/demo/methylation-report")
    def blood_methylation_demo(auth: Session):
        return {"profile": ensure_blood_demo(store, auth["id"])}

    @app.post("/api/profiles/{profile_id}/demo-methylation")
    def demo_methylation(profile_id: str, auth: Session):
        profile = require_profile(auth, profile_id)
        if (profile.get("public_dataset_key") or profile.get("genetic_sample_key")) == "hg002":
            if not store.datasets(auth["id"], profile_id, "methylation"):
                attach_public_methylation(store, auth["id"], profile_id)
            return methylation_summary(store, auth["id"], profile_id)
        if profile.get("provenance") != "synthetic":
            raise HTTPException(403, "Demo measurements cannot be attached to this profile.")
        if not store.datasets(auth["id"], profile_id, "methylation"):
            add_demo_methylation(store, auth["id"], profile_id)
        return methylation_summary(store, auth["id"], profile_id)

    @app.post("/api/messages", status_code=202)
    def message(body: MessageCreate, auth: Session):
        require_profile(auth, body.profile_id)
        try:
            job, conversation = store.queue_chat(
                auth["id"], body.profile_id, body.question, body.conversation_id
            )
        except LookupError as error:
            raise HTTPException(404, str(error)) from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        return {"job_id": job, "conversation_id": conversation}

    @app.get("/api/profiles/{profile_id}/conversations")
    def conversations(profile_id: str, auth: Session):
        require_profile(auth, profile_id)
        return store.conversations(auth["id"], profile_id)

    @app.post("/api/profiles/{profile_id}/conversations", status_code=201)
    def new_conversation(profile_id: str, body: ConversationCreate, auth: Session):
        require_profile(auth, profile_id)
        return store.new_conversation(auth["id"], profile_id, body.title)

    @app.get("/api/conversations/{conversation_id}")
    def conversation_messages(conversation_id: str, auth: Session, limit: int = Query(200, ge=1, le=1000)):
        try:
            return store.conversation_messages(auth["id"], conversation_id, limit)
        except LookupError:
            raise HTTPException(404, "Chat not found.") from None

    @app.post("/api/messages/{job_id}/retry", status_code=202)
    def retry_message(job_id: str, auth: Session):
        try:
            conversation = store.retry_chat(auth["id"], job_id)
        except LookupError:
            raise HTTPException(404, "Message not found.") from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        return {"job_id": job_id, "conversation_id": conversation}

    @app.post("/api/investigations", status_code=202)
    def investigation(body: InvestigationCreate, auth: Session):
        require_profile(auth, body.profile_id)
        try:
            calls = investigation_calls(store, auth["id"], body.profile_id, body.variant_id)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        if not calls:
            raise HTTPException(422, "This variant is not measured in the selected profile.")
        eligibility = investigation_eligibility(calls[0])
        if not eligibility["eligible"]:
            raise HTTPException(422, eligibility["reason"])
        job = store.new_job(auth["id"], "investigation", body.model_dump())
        return {"job_id": job}

    @app.post("/api/family-comparisons")
    def family(body: FamilyCreate, auth: Session):
        try:
            return family_comparison(store, auth["id"], body.profile_a, body.profile_b)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, auth: Session):
        job = store.job(auth["id"], job_id)
        if not job:
            raise HTTPException(404, "Run not found.")
        return {k: v for k, v in job.items() if k not in {"workspace", "payload"}}

    @app.get("/api/jobs/{job_id}/events")
    async def events(job_id: str, request: Request, auth: Session, after: int = 0):
        if not store.job(auth["id"], job_id):
            raise HTTPException(404, "Run not found.")
        try:
            after = max(after, int(request.headers.get("Last-Event-ID", "0")))
        except ValueError:
            raise HTTPException(422, "Invalid event cursor.") from None

        async def stream():
            cursor = after
            while not await request.is_disconnected():
                for event in store.events(job_id, cursor):
                    cursor = event["id"]
                    yield f"id: {cursor}\nevent: {event['kind']}\ndata: {json.dumps(event)}\n\n"
                job = store.job(auth["id"], job_id)
                if not job or job["status"] in {"completed", "failed"}:
                    break
                yield ": keepalive\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
        )

    @app.get("/api/jobs/{job_id}/export")
    def export(job_id: str, auth: Session):
        job = store.job(auth["id"], job_id)
        if not job:
            raise HTTPException(404, "Run not found.")
        return {
            "job": {k: v for k, v in job.items() if k not in {"payload", "workspace"}},
            "events": store.events(job_id),
        }

    @app.get("/api/templates/{kind}")
    def template(kind: str):
        if kind not in {"genetics", "wearables", "methylation"}:
            raise HTTPException(404)
        name, content = template_file(kind)
        return PlainTextResponse(content, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    return app


app = create_app()


def serve():
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
