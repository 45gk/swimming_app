from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WorkoutRecord(Base):
    __tablename__ = "workouts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ended_at: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    total_distance_m: Mapped[float | None] = mapped_column(Float)
    pool_length_m: Mapped[float | None] = mapped_column(Float)
    total_energy_kcal: Mapped[float | None] = mapped_column(Float)
    source_name: Mapped[str | None] = mapped_column(String)
    location_type: Mapped[str | None] = mapped_column(String)
    raw_metadata: Mapped[str] = mapped_column(Text, nullable=False)

    measurements: Mapped[list["MeasurementRecord"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan"
    )


class MeasurementRecord(Base):
    __tablename__ = "measurements"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workout_id: Mapped[str] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ended_at: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String)
    source_name: Mapped[str | None] = mapped_column(String)

    workout: Mapped[WorkoutRecord] = relationship(back_populates="measurements")
