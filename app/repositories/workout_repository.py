from dataclasses import asdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import MeasurementRecord, WorkoutRecord
from app.domain.entities import Measurement, Workout


class WorkoutRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_import(self, workouts: list[Workout], measurements: list[Measurement]) -> None:
        if workouts:
            statement = insert(WorkoutRecord).values([asdict(workout) for workout in workouts])
            self.session.execute(statement.on_conflict_do_nothing(index_elements=[WorkoutRecord.id]))
        if measurements:
            statement = insert(MeasurementRecord).values([asdict(measurement) for measurement in measurements])
            self.session.execute(statement.on_conflict_do_nothing(index_elements=[MeasurementRecord.id]))
        self.session.commit()

    def list_workouts(self, limit: int) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(WorkoutRecord).order_by(WorkoutRecord.started_at.desc()).limit(limit)
        ).all()
        return [self._workout_dict(row) for row in rows]

    def get_workouts_and_measurement_stats(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        workout_rows = self.session.scalars(
            select(WorkoutRecord).order_by(WorkoutRecord.started_at)
        ).all()
        stats_statement = select(
            MeasurementRecord.type,
            func.avg(MeasurementRecord.value).label("avg_value"),
            func.min(MeasurementRecord.value).label("min_value"),
            func.max(MeasurementRecord.value).label("max_value"),
            func.count(MeasurementRecord.id).label("sample_count"),
        ).group_by(MeasurementRecord.type).order_by(MeasurementRecord.type)
        stats = [dict(row) for row in self.session.execute(stats_statement).mappings().all()]
        return [self._workout_dict(row) for row in workout_rows], stats

    def get_analysis_data(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        workouts = self.session.scalars(
            select(WorkoutRecord).order_by(WorkoutRecord.started_at)
        ).all()
        measurements = self.session.scalars(
            select(MeasurementRecord).order_by(MeasurementRecord.started_at)
        ).all()
        return (
            [self._workout_dict(row) for row in workouts],
            [
                {
                    "id": row.id,
                    "workout_id": row.workout_id,
                    "type": row.type,
                    "started_at": row.started_at,
                    "ended_at": row.ended_at,
                    "value": row.value,
                    "unit": row.unit,
                    "source_name": row.source_name,
                }
                for row in measurements
            ],
        )

    @staticmethod
    def _workout_dict(workout: WorkoutRecord) -> dict[str, Any]:
        return {
            "id": workout.id,
            "activity_type": workout.activity_type,
            "started_at": workout.started_at,
            "ended_at": workout.ended_at,
            "duration_seconds": workout.duration_seconds,
            "total_distance_m": workout.total_distance_m,
            "pool_length_m": workout.pool_length_m,
            "total_energy_kcal": workout.total_energy_kcal,
            "source_name": workout.source_name,
            "location_type": workout.location_type,
            "raw_metadata": workout.raw_metadata,
        }
