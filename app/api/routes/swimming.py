from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_database
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.swimming import SummaryResponse, TrainingAnalysisResponse, WorkoutResponse
from app.services.swim_analysis import build_summary, build_training_analysis

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/workouts", response_model=list[WorkoutResponse])
def list_workouts(
    limit: int = Query(default=100, ge=1, le=500),
    connection: Session = Depends(get_database),
) -> list[dict[str, Any]]:
    return WorkoutRepository(connection).list_workouts(limit)


@router.get("/summary", response_model=SummaryResponse)
def summary(connection: Session = Depends(get_database)) -> dict[str, Any]:
    workouts, measurement_stats = WorkoutRepository(connection).get_workouts_and_measurement_stats()
    return build_summary(workouts, measurement_stats)


@router.get("/analysis", response_model=TrainingAnalysisResponse)
def training_analysis(connection: Session = Depends(get_database)) -> dict[str, Any]:
    workouts, measurements = WorkoutRepository(connection).get_analysis_data()
    return build_training_analysis(workouts, measurements)
