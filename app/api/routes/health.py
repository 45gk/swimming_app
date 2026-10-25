from fastapi import APIRouter

router = APIRouter(tags=["general"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
