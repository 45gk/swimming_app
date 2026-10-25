from dataclasses import dataclass
@dataclass(frozen=True)
class Workout:
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


@dataclass(frozen=True)
class Measurement:
    id: str
    workout_id: str
    type: str
    started_at: str
    ended_at: str
    value: float
    unit: str | None
    source_name: str | None


@dataclass(frozen=True)
class ParsedHealthExport:
    workouts: list[Workout]
    measurements: list[Measurement]


