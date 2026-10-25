import io
import json
import zipfile
from bisect import bisect_left
from datetime import datetime
from itertools import islice
from pathlib import Path
from xml.etree import ElementTree as ET

from app.domain.entities import Measurement, ParsedHealthExport, Workout


class InvalidHealthExport(ValueError):
    pass


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_swimming(activity_type: str) -> bool:
    return "swim" in activity_type.lower()


def extract_xml(payload: bytes, filename: str) -> bytes:
    if zipfile.is_zipfile(io.BytesIO(payload)):
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                export_names = [name for name in archive.namelist() if Path(name).name.lower() == "export.xml"]
                if not export_names:
                    raise InvalidHealthExport("ZIP archive does not contain export.xml.")
                return archive.read(export_names[0])
        except zipfile.BadZipFile as exc:
            raise InvalidHealthExport("Invalid ZIP archive.") from exc
    if not filename.lower().endswith(".xml"):
        raise InvalidHealthExport("Provide export.xml or the Apple Health export ZIP.")
    return payload


def parse_export(xml_bytes: bytes) -> ParsedHealthExport:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise InvalidHealthExport("The file is not a valid Apple Health export XML.") from exc

    workouts: list[Workout] = []
    measurements: list[Measurement] = []
    supported_metrics = ("HeartRate", "DistanceSwimming", "SwimmingStrokeCount", "ActiveEnergyBurned")
    records: list[tuple[datetime, datetime, ET.Element]] = []
    for record in root.iter("Record"):
        kind = record.get("type", "")
        if not any(metric in kind for metric in supported_metrics):
            continue
        record_start, record_end = _date(record.get("startDate")), _date(record.get("endDate"))
        if record_start and record_end:
            records.append((record_start, record_end, record))
    records.sort(key=lambda item: item[0])
    record_starts = [item[0] for item in records]
    for node in root.iter("Workout"):
        activity = node.get("workoutActivityType", "")
        if not _is_swimming(activity):
            continue
        start, end = _date(node.get("startDate")), _date(node.get("endDate"))
        if not start or not end:
            continue
        source_name = node.get("sourceName")
        workout_id = f"{source_name or ''}:{node.get('startDate', '')}:{node.get('endDate', '')}"
        metadata = {item.get("key", ""): item.get("value", "") for item in node.findall("MetadataEntry")}
        pool_length_m = None
        lap_length = metadata.get("HKLapLength", "").split()
        if lap_length:
            try:
                pool_length_m = float(lap_length[0])
                if len(lap_length) > 1 and lap_length[1].lower() in {"yd", "yard", "yards"}:
                    pool_length_m *= 0.9144
            except ValueError:
                pool_length_m = None
        distance_m: float | None = None
        energy_kcal: float | None = None
        for statistic in node.findall("WorkoutStatistics"):
            kind = statistic.get("type", "")
            amount = statistic.get("sum") or statistic.get("average")
            if amount is None:
                continue
            if "DistanceSwimming" in kind:
                distance_m = float(amount) * (1000 if statistic.get("unit") == "km" else 1)
            elif "ActiveEnergyBurned" in kind:
                energy_kcal = float(amount)
        duration = float(node.get("duration", "0"))
        if node.get("durationUnit") == "min":
            duration *= 60
        workouts.append(Workout(
            id=workout_id,
            activity_type=activity,
            started_at=start.isoformat(),
            ended_at=end.isoformat(),
            duration_seconds=duration,
            total_distance_m=distance_m,
            pool_length_m=pool_length_m,
            total_energy_kcal=energy_kcal,
            source_name=source_name,
            location_type=metadata.get("HKSwimmingLocationType"),
            raw_metadata=json.dumps(metadata),
        ))
        record_index = bisect_left(record_starts, start)
        for record_start, record_end, record in islice(records, record_index, None):
            if record_start > end:
                break
            if record_end > end:
                continue
            kind = record.get("type", "")
            value = record.get("value")
            if value is None:
                continue
            record_source = record.get("sourceName")
            measurements.append(Measurement(
                id=f"{record_source or ''}:{kind}:{record.get('startDate', '')}",
                workout_id=workout_id,
                type=kind,
                started_at=record_start.isoformat(),
                ended_at=record_end.isoformat(),
                value=float(value),
                unit=record.get("unit"),
                source_name=record_source,
            ))
    return ParsedHealthExport(workouts=workouts, measurements=measurements)
