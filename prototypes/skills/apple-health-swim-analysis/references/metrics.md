# Swim metrics used by the prototype

- **Whole-workout pace:** workout duration divided by workout distance, expressed per 100 m. It can include pauses.
- **Recorded-length pace:** sum of timed swimming-length durations divided by the distance represented by those lengths, expressed per 100 m. It covers only lengths with usable time records.
- **Unattributed duration:** `max(0, workout duration - timed-length duration)`. Do not label it as rest unless another source confirms rest intervals.
- **Length gap:** the non-negative time between the end of one length record and the start of the next. It can reflect rest, omitted records, or timing behavior.
- **Strokes per length:** use only a stroke sample paired to the same start timestamp as a valid pool-length distance record.
- **SWOLF:** timed length seconds plus strokes for the same paired length. Average only across complete pairs and report the pool length.
- **Early/late comparison:** compare the first and final quarters of at least eight valid lengths. Give both group averages and percent change; this is a within-session description.
- **Heart-rate summary:** distinguish workout-level summary values from time-series samples. For early/late shift, compare the first and final 20% of the sample time span when there are at least ten samples; report the actual averages or their difference and sample count.
- **Distance source:** prefer an explicit workout summary. If absent, a sum of swim distance records may be used only when those records represent the workout's distance; label it as sample-derived.
