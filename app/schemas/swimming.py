from pydantic import BaseModel


class ImportResponse(BaseModel):
    status: str
    swimming_workouts_found: int
    measurements_found: int
    filename: str


class WorkoutResponse(BaseModel):
    id: str
    activity_type: str
    started_at: str
    ended_at: str
    duration_seconds: float
    total_distance_m: float | None
    pool_length_m: float | None
    total_energy_kcal: float | None
    source_name: str | None
    location_type: str | None
    raw_metadata: str


class MeasurementStatsResponse(BaseModel):
    type: str
    avg_value: float
    min_value: float
    max_value: float
    sample_count: int


class SummaryResponse(BaseModel):
    workout_count: int
    total_distance_m: float
    average_distance_m: float | None
    average_pace_seconds_per_100m: float | None
    average_duration_seconds: float | None
    measurement_stats: list[MeasurementStatsResponse]
    note: str


class LengthSampleResponse(BaseModel):
    length_index: int
    distance_m: float
    duration_seconds: float
    stroke_count: float | None


class TrainingSessionResponse(BaseModel):
    workout_id: str
    started_at: str
    distance_m: float | None
    duration_seconds: float
    pace_seconds_per_100m: float | None
    average_heart_rate_bpm: float | None
    heart_rate_samples: int
    stroke_count: float | None
    pool_length_m: float | None
    lengths_recorded: int
    length_series: list[LengthSampleResponse]
    recorded_moving_time_seconds: float | None
    estimated_moving_pace_seconds_per_100m: float | None
    average_strokes_per_length: float | None
    average_swolf: float | None
    pace_fade_first_to_last_quarter_percent: float | None
    stroke_change_first_to_last_quarter_percent: float | None
    heart_rate_early_late_change_bpm: float | None
    unattributed_duration_seconds: float | None
    between_length_gaps_seconds: list[float]
    location_type: str | None


class WeeklyTrainingResponse(BaseModel):
    week_start: str
    distance_m: float
    sessions: int


class TrainingInsightResponse(BaseModel):
    kind: str
    title: str
    detail: str
    evidence: dict[str, object]


class DataCoverageResponse(BaseModel):
    workouts_with_distance: int
    workouts_missing_distance: int
    workouts_missing_duration: int
    heart_rate_samples: int
    stroke_count_available: bool
    limitations: list[str]


class TrainingAnalysisResponse(BaseModel):
    session_count: int
    sessions: list[TrainingSessionResponse]
    weekly_training: list[WeeklyTrainingResponse]
    insights: list[TrainingInsightResponse]
    data_coverage: DataCoverageResponse
