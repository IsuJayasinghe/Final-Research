# Component 4 — Gate Appointment API

FastAPI service for the AI-Powered Gate Appointment System. Routes live in an
`APIRouter` (`router.py`) so the shared backend can mount them later; `main.py`
runs the component standalone.

## What it does
1. **Model 2** scores each booking: P(on time / late / no-show), with SHAP reasons (`noshow.py`).
2. **Overbooking rule** (`scheduler.py`): a slot may exceed capacity while *expected arrivals*
   (sum of 1 - no-show risk) stay within capacity, up to a hard cap (`GATE_MAX_OVERBOOK`).
3. **Model 1** forecasts every lane; the lowest-queue lane and the cheapest nearby slot are chosen.
4. **Clearance model** predicts time at the gate; the booking is saved with its reasons (`service.py`).
5. **Re-optimization**: after a vessel delay / queue spike only unconfirmed bookings are reshuffled with an
   integer program (PuLP/CBC); confirmed bookings stay fixed and every move is explained.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/appointments` | Score risk, pick slot (overbooking rule) and lane, predict clearance, save |
| GET | `/api/appointments` | List saved appointments |
| GET | `/api/appointments/{id}/events` | Audit trail of assignments, moves and status changes |
| POST | `/api/appointments/{id}/confirm` / `/cancel` | Lifecycle |
| POST | `/api/reoptimize` | Apply a disruption (vessel delay hours, queue spike %, window, start) and re-optimize |
| DELETE | `/api/disruption` | Clear the active disruption |
| GET | `/api/slots?date=` | Hourly slot load: bookings, expected arrivals, capacity, forecast wait |
| GET | `/api/model-metrics` | Evaluation reports for the UI results page |
| POST | `/api/documents/check` | OCR one uploaded document (image/PDF): classify, extract fields, validate against the booking |
| GET | `/api/appointments/{id}/documents` | OCR verdicts recorded for an appointment |
| POST | `/api/appointments/{id}/documents/submit` | Count cleared vs missing/flagged documents and re-score no-show risk and clearance time |
| GET | `/api/documents/required?container_type=` | Required document slots for a container type |
| POST | `/api/assign-appointment` | Original single-shot lane+slot assignment (no persistence) |
| POST | `/api/predict-clearance` | Clearance-time model on its own |
| GET | `/api/congestion?at=` | Per-lane forecast queue and wait for a chosen hour |

## Customs risk and missing documents are derived, not typed
A booking is created without them (`POST /api/appointments` leaves `customs_risk_flag` / `missing_documents` out;
passing explicit values is still allowed for simulations). Until the documents are read:
- the no-show and clearance predictions are the **average over the typical document situation** from the training
  data (customs risk 72% low / 20% medium / 8% high; 75% / 15% / 7% / 3% for 0-3 missing documents), and
  the explanation lists only drivers that are actually known;
- the appointment stores both values as *unknown* (NULL), not as zero.

On submitting the documents (below) the OCR verdicts fix both: **missing documents** = required documents that are not
`cleared`, and **customs risk** = the CUSDEC's assessment (HS-chapter table: tobacco, alcohol, arms, explosives,
precious goods and art are high; fuels, chemicals, pharmaceuticals, machinery, electrical equipment and vehicles are
medium; other goods low; a missing HS code or declaration number raises the level). The table in
`documents.py` is illustrative; a real deployment would use the customs authority's own risk profile.
If no customs declaration was checked, customs risk stays unknown.

## OCR document checking (`documents.py`)
Uploads are read with **RapidOCR** (ONNX, pip-only - no Tesseract install); digital PDFs use their text
layer, scanned PDFs are rendered then OCR'd. Each file then goes through:
1. **classify** into one of the 7 slots (booking confirmation, CUSDEC, gate pass, VGM, container/seal, driver and
   vehicle, special cargo) with weighted keywords;
2. **extract** container number (ISO 6346 check digit, O/0-style OCR repair), seal, VGM weight, booking no., truck,
   plate, licence, UN number, set-point temperature, dates;
3. **validate** against the booking: container must match, truck/date on the gate pass, VGM weight plausible
   (1,000-40,000 kg), seal present, UN number for hazardous, set point for reefer, wrong-slot detection, low
   OCR confidence -> `unreadable`;
4. **verdict**: `cleared` / `flagged` / `unreadable` with errors and warnings.

On **submit**, flagged or missing documents become the appointment's `missing_documents` count, no-show risk and
clearance time are re-scored by the models, the extracted fields are saved to `gate.gate_submissions`, and the
change is logged as a `DOCUMENTS_CHECKED` event. Files are processed in memory and never stored.

Demo files: `python tools/make_sample_documents.py [dir] [YYYY-MM-DD]` writes good and faulty sample documents
(git-ignored, dated tomorrow by default) for container `CSQU3054383`, truck `TRK-80579`, including customs
declarations of low, medium, high and incomplete risk (`cusdec*.png`).

## Storage
By default bookings live in memory. To save them in the shared PostgreSQL database:
1. Apply `database/migrations/001_gate_appointment_predictions.sql` (additive; adds prediction columns,
   `gate.gate_appointment_events` and the six `GATE-n` lanes) and then `002_gate_appointment_conditions.sql`
   (weather and vessel-delay columns).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` (never commit `.env`).
`GET /` reports the active `storage` (`memory` or `postgresql`).

## Tests
```bash
python -m pytest tests -q                    # memory repository
TEST_DATABASE_URL=postgresql://... python -m pytest tests -q   # also runs the PostgreSQL contract tests
```

## Run
```bash
cd backend/gate
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```
Docs at `http://localhost:8000/docs`. Models are produced by `ml-models/gate/`.

## Known limits
- Forecast covers one week after the training cutoff; a chosen date maps onto it by hour-of-week.
- Wait time = forecast queue x 5.5 min (no separate model).
- OCR runs on clear scans and photos of printed text; handwriting and heavily degraded images are flagged as
  unreadable rather than guessed. Classification is keyword-based (no trained document classifier).
- Document verdicts are held in the running process until submitted (submission itself is saved).
- A disruption is held in the running process (cleared by `DELETE /api/disruption` or a restart).
- Slot capacity (`GATE_SLOT_CAPACITY`, default 6 for demos) is configurable; the evaluation uses 16.
