# Gate Appointment System (Component 4): how it works and how to run it on another computer

## 1. How the system works

Roles are a demo switch in the top bar (Driver / Gate admin). It is not login security.

| Step | Who | What happens | Page |
|---|---|---|---|
| 1 | Driver | Checks the forecast for each hour (Normal / Busy / Congested) and the trucks already booked on each gate | Gate Status |
| 2 | Driver | Picks an hour and enters truck, container, carrier and cargo type. Weather, carrier reliability and vessel delay are derived | Request Appointment |
| 3 | System | Scores no-show risk, picks the slot (overbooking rule) and the gate (lane), predicts clearance time, saves the request as **awaiting approval** | (automatic) |
| 4 | Gate admin | Approves, or rejects with a reason the driver will see | Approvals |
| 5 | Driver | Document upload **unlocks only after approval**. Each upload is OCR-checked against the booking and its template; submitting re-scores risk | Upload Documents |
| 6 | Driver | Follows the trip live: gate, lane status, queue, expected entry, delays, notices | My Trip |
| 7 | System | A disruption, lane closure or rebalance moves the driver to another gate and/or adds a delay notice, each with the reason | (automatic) |
| 8 | Gate officer | Picks a gate, checks each truck in, then completes the gate process (or marks a no-show) | Gate Desk |

The models behind it:
- **Congestion forecast** (SARIMAX, one per lane): hourly queue per lane.
- **Clearance time** (XGBoost): minutes a truck needs at the gate.
- **No-show / late** (XGBoost + SHAP): calibrated probability, used by the overbooking rule.
- **Decision layer**: expected-arrivals overbooking, lane choice, PuLP/CBC re-optimization.
- **OCR**: RapidOCR reads documents; a template per document type decides whether each is complete.

Detail: `README.md` in this folder (endpoints, rules, limits) and `ml-models/gate/README.md` (training).

## 2. What the other computer needs

| Need | Version | Notes |
|---|---|---|
| Git | any | to clone the repo |
| Python | 3.10 or newer (tested on 3.13) | with `pip` |
| Node.js | 20 or newer (tested on 23) | includes `npm` |
| Browser | Edge or Chrome | |
| Internet | optional | only for the live weather forecast. Without it the system uses a seasonal prior and still works |
| PostgreSQL | optional | not needed for demos. Without it data is held in memory |

No GPU, no dataset files and no training are needed. The trained models and the forecast are already in the repository
(`backend/gate/models/` and `backend/gate/data/`). About 1 GB of disk covers the Python and Node packages.

Do **not** copy `.env` files or the CSV datasets between computers; they are not in git.

## 3. Install

```bash
git clone https://github.com/tharindunanayakkara9/Final-Research.git
cd Final-Research
git checkout feature/c4-gate
```
(The team repo `IsuJayasinghe/Final-Research` has the same branch.)

Backend (first terminal):
```bash
cd backend/gate
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```
Wait for `Application startup complete` (the first start also loads the OCR model, which can take 10 to 30 seconds).
Check `http://127.0.0.1:8000/`. It should show `"status":"ok"` and `"storage":"memory"`.

Frontend (second terminal):
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

Keep these two ports. The frontend calls the backend at `http://localhost:8000`, and the backend only accepts the
frontend from `http://localhost:5173`.

## 4. Add the demo data

Open a third terminal. The backend must be running. Use `127.0.0.1` (not `localhost`) on Windows, because `localhost` adds
about 2 seconds per request.

**a) A busy gate (60 realistic bookings for tomorrow):**
```bash
cd backend/gate
python tools/seed_demo_bookings.py
```
Options: `--date 2026-10-20`, `--count 100`, `--risky-share 0.3`, `--url http://127.0.0.1:8000`.
Bookings are sent through the real API, so risk, overbooking and lane choice all apply. Some are auto-confirmed and the
rest wait for the gate admin. In the app, switch to **Gate admin**, open **Approvals** and press *Approve all low-risk*.
The busiest hour shows on **Gate Status**.

**b) Three different appointments for the OCR demo:**
```bash
python tools/make_demo_appointments.py                 # documents only: you book and approve live (see section 5)
python tools/make_demo_appointments.py --book --approve   # also book the three and approve them
```
This is the only document generator. It writes a separate set of made-up documents for each of three appointments,
**drawn in the layout of the real forms** (grids, tables, a ticked check box, a numbered driving licence card; no real
logos or photos), into `backend/gate/sample_documents/appointments/`. Without `--book` it only writes the files.

**Every run makes new values**: truck IDs, container numbers, booking and seal numbers, drivers, goods, shippers and
vessels. At the end it prints a table of exactly what to type when you book (the same values are in each folder's
`README.txt`), for example:
```
  folder       truck      container    carrier    type       cargo   hour
  1_clean      TRK-47417  GESU9228151  Carrier-E  standard   export  11:00
  2_hazardous  TRK-68873  HLCU1367529  Carrier-B  hazardous  import  10:00
  3_reefer     TRK-57109  SEGU0981739  Carrier-G  reefer     export  14:00
```
Other options: `--date YYYY-MM-DD` (default tomorrow; the documents are dated for it, so book that date), `--out DIR`,
`--url http://127.0.0.1:8000`, `--seed N` (the seed is printed on every run; use it to get exactly the same documents
again, for example to rehearse), and `--fixed` (the original fixed set, shown in the table below).

What stays the same on every run is each appointment's **story**, so the demo always works the same way:

| | 1_clean | 2_hazardous | 3_reefer |
|---|---|---|---|
| Cargo | ordinary goods (T-shirts, tea, tiles or gloves) | fuel or chemical (petroleum, methanol, sodium hydroxide or acetone) | alcohol (wine, whisky or beer) |
| Customs risk read by OCR | **low** | **medium** | **high** |
| Carrier | a reliable one | Carrier-B (the least reliable) | another carrier |
| Vessel read by OCR | on time | **delayed** (3 or 5 h) | **delayed** (3 or 5 h) |
| Documents needed | 6 | 7 (dangerous goods declaration) | 7 (reefer certificate) |
| Faulty files to try first | none | `vgm__PROBLEM_wrong_container`, `gate_pass__PROBLEM_expired` | `seal_photo__PROBLEM_no_seal_number`, `driver_docs__PROBLEM_incomplete`, `gate_pass__PROBLEM_blurry` |

With `--fixed` the values are always: `TRK-81001` / `MSCU5382047` (Carrier-A, 08:00), `TRK-81002` / `HLCU2745198`
(Carrier-B, 10:00) and `TRK-81003` / `OOLU6198420` (Carrier-C, 13:00), and after fixing and submitting the no-show risks
and clearance times were about 8% / 8 min, 22% / 31 min and 11% / 30 min (they shift slightly with the date and weather).

How to demo one appointment:
1. In **Driver** mode open **My Trip** (or Upload Documents) and enter the truck ID printed for that appointment.
2. Open **Upload Documents**. The approved appointment is selected.
3. Upload each `__PROBLEM_` file into its slot (the file name starts with the slot). Each is flagged with the exact
   reason: a wrong container number, an expired permit, a missing seal number, missing licence details, or an
   unreadable image.
4. Upload the file with the same slot name (`vgm.png`, `gate_pass.png`, ...) to replace it. It clears.
5. Upload the remaining documents until it shows 6 / 6 or 7 / 7 cleared, then press *Submit documents*.
6. Compare the three: customs risk (low, medium, high), the vessel delay, no-show risk and clearance time all differ
   because the documents differ. That is the proof that the models read the real document content.

The tests (`tests/test_demo_appointments.py`) generate 24 different random sets and read many of them with OCR, so a
change that breaks this demo fails the tests.

**c) Your own real documents.** The OCR reads the layouts of real photographed forms, not only the generated ones: a
booking confirmation, a customs declaration (CUSDEC) with numbered boxes, a terminal gate pass with a grid and barcode,
a VGM declaration with a weights table and tick boxes, a container and seal verification report, and a driving licence
with the vehicle registration certificate (JPG, PNG or PDF; see "How the OCR reads real forms" in `README.md`). To try
a set of your own:
1. Make a booking whose **truck ID, container ID and date** are the ones printed on the documents (for example truck
   `TRK-80579`, container `MAEU3483419`, the appointment date on the gate pass), then approve it as gate admin.
2. In Upload Documents, upload each file into its slot. The container, the date and the pass's validity window are
   checked against the booking. A slot outside the pass's time window is a warning, not an error.
3. After *Submit documents* any detail that disagrees between documents (for example a different booking number on the
   VGM and the booking confirmation) is listed under "Please confirm".
Photographs should be flat, sharp and well lit. Names are shown as the OCR returned them, often without spaces.
The special cargo certificate (hazardous or reefer bookings only) is drawn as a plain titled card, because no real
sample of it was available.

**d) Resetting.** With no database, a backend restart clears all bookings. Seed again after restarting.

## 5. A 10 minute walkthrough

1. **Driver** mode: Gate Status, pick tomorrow, *Show busiest hour* (congested), then pick a quiet hour.
2. Request Appointment with the hazardous appointment's values from the table the tool printed (truck, container,
   Carrier-B, hazardous, import, tomorrow, its hour; see section 4b). The request shows "waiting for the gate admin".
   (If you ran `make_demo_appointments.py --book --approve`, these bookings already exist: skip to step 4.)
3. Upload Documents is locked. Switch to **Gate admin**, open Approvals and approve the request.
4. Back to **Driver**: My Trip shows the approval. Upload `vgm__PROBLEM_wrong_container.png` first to show a document
   being flagged, then the 7 good documents from `sample_documents/appointments/2_hazardous/`, and submit.
5. Compare with `1_clean` and `3_reefer`: customs risk, vessel delay and risk differ because the documents differ.
6. **Gate admin**: Gate Allocation, close the driver's gate for 3 hours ("crane breakdown"). Slot Optimization, inject a
   4 hour vessel delay and an 80% queue spike.
7. **Driver**: My Trip shows the new gate, the longer wait and the reasons under Updates.
8. **Gate admin**: Gate Desk, pick that gate and open *Show booking and documents* on the truck: the full booking and every
   uploaded document (status, what was read, problems). Then *Check in*, then *Complete gate process*. The driver sees it complete.
9. Model Results: the evidence for each model (see `ml-models/gate/reports/`).

## 6. Optional: PostgreSQL instead of memory

1. Apply the team schema (`database/schema/`), then `database/migrations/001`, `002`, `003` in order.
2. Copy `backend/gate/.env.example` to `backend/gate/.env` and set `DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/smart_port_management`.
3. Restart the backend. `GET /` should now say `"storage":"postgresql"`.

Never commit `.env`. Tell the group before running migrations on a shared database.

## 7. Check it works

```bash
cd backend/gate
python -m pytest -q          # about 1.5 minutes; PostgreSQL tests are skipped without a database
cd ../../frontend
npm run lint
npm run build
```
Interactive API docs: `http://127.0.0.1:8000/docs`.

## 8. Common problems

| Problem | Fix |
|---|---|
| `address already in use` on port 8000 | An older backend is still running. Stop it, or use `--port 8001` and change `API_BASE_URL` in `frontend/src/lib/gateApi.js` |
| Page says "Could not reach the gate appointment service" | The backend is not running, or it is not on port 8000 |
| The browser shows CORS errors | The frontend is not on port 5173. Free that port or edit `allow_origins` in `main.py` |
| `&&` is a parser error in PowerShell 5.1 | Put the commands on separate lines or separate them with `;` |
| Gate pass flagged as expired or the documents do not match | Regenerate the sample documents for the booking's date (section 4b) |
| OCR returns 503 | `rapidocr_onnxruntime` or `pymupdf` did not install. Rerun `pip install -r requirements.txt` |
| Slow seeding on Windows | Use `--url http://127.0.0.1:8000` (the default) |
| Weather says "seasonal prior" | No internet, or the date is more than 16 days ahead. This is expected |

## 9. Honest limits
Training data is synthetic. The vessel schedule is simulated until Component 1 is connected (`VESSEL_API_URL`). The
customs risk table is illustrative. The Driver / Gate admin switch has no authentication. Lane closures and disruptions
are held in memory.

## 10. Optional: retraining the models
Not needed to run the system. The raw CSVs are not in git; see `ml-models/gate/README.md` for the files to place in
`ml-models/gate/data/raw/` and the training scripts. The congestion training is slow and very large on disk.
