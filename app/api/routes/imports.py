from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_database
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.swimming import ImportResponse
from app.services.apple_health_importer import InvalidHealthExport, extract_xml, parse_export

router = APIRouter(prefix="/api", tags=["data"])


@router.post("/import", response_model=ImportResponse)
async def import_health_export(
    request: Request,
    filename: str = Query(default="export.xml"),
    connection: Session = Depends(get_database),
) -> ImportResponse:
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Request body is empty.")
    try:
        xml_bytes = extract_xml(payload, filename)
        parsed = parse_export(xml_bytes)
    except InvalidHealthExport as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    WorkoutRepository(connection).add_import(parsed.workouts, parsed.measurements)
    return ImportResponse(
        status="imported",
        swimming_workouts_found=len(parsed.workouts),
        measurements_found=len(parsed.measurements),
        filename=filename,
    )
