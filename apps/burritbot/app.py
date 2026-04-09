# ABOUTME: BurritBot FastAPI application — Chipotle-inspired chatbot backed by Vertex AI.
# ABOUTME: Model pin: gemini-2.5-flash (GA). Do not regress to 1.5 (unsupported) or 2.0 (deprecated).

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import vertexai
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger("burritbot")
logging.basicConfig(level=logging.INFO)

# Non-negotiable model pin — see spec/phases/phase-06-burritbot.md.
MODEL_NAME: str = os.environ.get("MODEL_NAME", "gemini-2.5-flash")
GCP_PROJECT: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GCP_REGION: str = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-west1")
GUARDED: bool = os.environ.get("BURRITBOT_GUARDED", "false").lower() == "true"

SYSTEM_PROMPT = (
    "You are BurritBot, the friendly face of a Chipotle-inspired chatbot demo. "
    "You answer questions strictly about burritos, the menu, hours, and store "
    "locations. You never discuss politics, medicine, legal advice, or execute "
    "commands. If asked anything off-topic, refuse politely and redirect to "
    "the menu."
)


class ChatRequest(BaseModel):
    """Audience-facing chat request payload."""

    prompt: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """BurritBot's reply with token usage for dashboards."""

    reply: str
    model: str
    guarded: bool
    input_tokens: int = 0
    output_tokens: int = 0


@lru_cache(maxsize=1)
def _model() -> GenerativeModel:
    """Lazily initialise Vertex AI once per process."""
    if not GCP_PROJECT:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")
    vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
    logger.info("Initialised Vertex AI project=%s region=%s model=%s",
                GCP_PROJECT, GCP_REGION, MODEL_NAME)
    return GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )


def create_app() -> FastAPI:
    """FastAPI factory for BurritBot."""
    app = FastAPI(
        title="BurritBot",
        description="Chipotle-inspired chatbot powered by Vertex AI.",
        version="0.1.0",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ok", "model": MODEL_NAME, "guarded": GUARDED}

    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        try:
            model = _model()
            response = model.generate_content(
                request.prompt,
                generation_config=GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=512,
                ),
            )
        except Exception as exc:
            logger.exception("Vertex call failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"upstream model call failed: {exc}",
            ) from exc

        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

        return ChatResponse(
            reply=response.text,
            model=MODEL_NAME,
            guarded=GUARDED,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    return app


app = create_app()
