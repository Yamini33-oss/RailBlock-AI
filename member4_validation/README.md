# KAVACH BIE - Member 4: Conflict Detection and Operational Validation

> **Academic demonstration only.** This project is not approved, certified or
> safe for real railway operations. All train schedules are **synthetic
> (made-up) data** and are **not** real Indian Railways schedules.

## 1. Project purpose
KAVACH BIE is a railway maintenance optimization project. **Member 3**
recommends a maintenance date and time. **Member 4 (this module)** checks
whether that proposed window breaks the project's operational rules.

## 2. Member 4's responsibilities
For a proposed window the module checks:
- Train movements on the affected track section.
- Overlap between train schedules and the maintenance window.
- Whether the window is long enough for the required duration.
- Whether each required resource exists and is available.
- Whether the schedule data itself is valid.

It returns `VALID` (all checks pass) or `CONFLICT` (one or more checks fail),
plus the reasons.

## 3. Technology
Python, FastAPI, Uvicorn, Pydantic, CSV files, pytest. No Node.js, MongoDB or
paid services; works offline after installing the packages.

## 4. Folder structure
```
member4-validation/
    main.py              <- all validation logic (standard library only)
    api.py               <- FastAPI web API (wraps main.py)
    train_schedule.csv   <- synthetic train movements
    resources.csv        <- simplified resource availability
    requirements.txt
    README.md
    .gitignore
    tests/
        __init__.py
        test_validation.py
```

## 5. Setup on Windows
1. Install Python 3.10 or newer from https://www.python.org/downloads/ and tick
   **"Add python.exe to PATH"** during installation. Check with `python --version`.
2. Extract the ZIP. In VS Code choose **File > Open Folder** and open the
   `member4-validation` folder (the one containing `main.py`).
3. Open the VS Code terminal (**Terminal > New Terminal**).
4. Create a virtual environment:
   ```
   python -m venv .venv
   ```
5. Activate it.
   - Command Prompt: `.venv\Scripts\activate.bat`
   - PowerShell: `.venv\Scripts\Activate.ps1`

   PowerShell may block activation because of its execution policy ("running
   scripts is disabled on this system"). If so, switch the terminal to
   **Command Prompt** (the drop-down next to the `+` in the VS Code terminal)
   and use the Command Prompt command instead.
   When active, you will see `(.venv)` at the start of the prompt.
6. Install dependencies:
   ```
   python -m pip install -r requirements.txt
   ```

## 6. Run the automated tests
```
python -m pytest -v
```
All tests should pass. They use temporary CSV files, so your data files are
never changed.

## 7. Start the server
```
python -m uvicorn api:app --reload
```
Open the interactive documentation: **http://127.0.0.1:8000/docs**
(use "Try it out" on `POST /validate`). Stop the server with `Ctrl+C`.

Optional: `python main.py` prints one example validation without a server.

## 8. Submit a sample request
`POST http://127.0.0.1:8000/validate` with this JSON body:
```json
{
  "track_section": "SEC-01",
  "start_time": "2026-10-15 13:00",
  "end_time": "2026-10-15 14:00",
  "required_duration_minutes": 60,
  "required_resources": ["Maintenance Team", "Repair Equipment"]
}
```
Rules: times use `YYYY-MM-DD HH:MM`; the end must be later than the start;
the duration must be a whole number greater than zero (not 60.5 or true).

### Example CONFLICT response (abridged)
```json
{
  "status": "CONFLICT",
  "track_section": "SEC-01",
  "start_time": "2026-10-15 13:00",
  "end_time": "2026-10-15 14:00",
  "required_duration_minutes": 60,
  "window_duration_minutes": 60,
  "affected_trains": ["T101"],
  "reasons": [
    "Train T101 (Express Alpha) runs 2026-10-15 13:15 to 2026-10-15 13:45 and overlaps the proposed maintenance window"
  ],
  "resource_results": [
    {"resource_name": "Maintenance Team", "status": "AVAILABLE", "message": "Resource 'Maintenance Team' is available"},
    {"resource_name": "Repair Equipment", "status": "AVAILABLE", "message": "Resource 'Repair Equipment' is available"}
  ],
  "invalid_schedule_records": [],
  "invalid_resource_records": [],
  "note": "Academic demonstration using synthetic data. Not approved or certified for real railway operations."
}
```

### Example VALID response
Same request but `"start_time": "2026-10-15 08:00"`, `"end_time": "2026-10-15 09:00"`:
```json
{
  "status": "VALID",
  "track_section": "SEC-01",
  "start_time": "2026-10-15 08:00",
  "end_time": "2026-10-15 09:00",
  "required_duration_minutes": 60,
  "window_duration_minutes": 60,
  "affected_trains": [],
  "reasons": [],
  "resource_results": [ "...both AVAILABLE..." ],
  "invalid_schedule_records": [],
  "invalid_resource_records": [],
  "note": "Academic demonstration using synthetic data. Not approved or certified for real railway operations."
}
```

## 9. How to read the results
| Field | Meaning |
|---|---|
| `status` | `VALID` = every implemented check passed. `CONFLICT` = at least one failed. |
| `reasons` | Plain-language list of what failed (empty when VALID). |
| `affected_trains` | IDs of trains on that section that overlap the window. |
| `window_duration_minutes` | Length of the proposed window. |
| `resource_results[].status` | `AVAILABLE`, `UNAVAILABLE`, `NOT_FOUND` (not in resources.csv) or `INVALID_DATA`. |
| `invalid_schedule_records` | Bad CSV rows (line number, train ID, problems). |

**Overlap rule:** a train conflicts when
`maintenance_start < train_end AND train_start < maintenance_end`.
A train ending exactly when maintenance starts, or starting exactly when it
ends, is **not** an overlap. Only trains on the requested track section count.

**Fail-closed behaviour (never a false VALID):**
- Any invalid train-schedule row makes the result `CONFLICT`.
- A track section that does not appear in `train_schedule.csv` (for example a
  typo like `SEC-1`) gives `CONFLICT`, because it cannot be checked.
- A window shorter than `required_duration_minutes` gives `CONFLICT`
  (HTTP 200) with the two durations shown.

**HTTP status codes**
- `200` - validation finished (`VALID` or `CONFLICT`).
- `422` - malformed request (body `{"status": "INVALID_REQUEST", "errors": [...]}`).
- `500` - a CSV file is missing/unreadable/lacks columns
  (`{"status": "DATA_FILE_ERROR", ...}`) or an unexpected internal error
  (`{"status": "INTERNAL_ERROR", ...}`). It never returns a fake `VALID`.

## 10. Common errors and fixes
| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python with "Add to PATH" ticked, then reopen VS Code. |
| PowerShell: "running scripts is disabled" | Use Command Prompt and `.venv\Scripts\activate.bat`. |
| `No module named fastapi` / `pytest` | Activate `.venv`, then run `python -m pip install -r requirements.txt`. |
| `No module named main` / `api` | Open the folder that directly contains `main.py` and run commands there. |
| Port 8000 already in use | Stop the other server, or add `--port 8001`. |
| 422 response | Read the `errors` list; fix the field named in it. |
| 500 `DATA_FILE_ERROR` | The CSV is missing, empty, or lacks a required column - the message says which. |

## 11. For Member 3 (calls the API)
Start this server, then send the recommended window to `/validate`:
```python
import requests

reply = requests.post("http://127.0.0.1:8000/validate", json={
    "track_section": "SEC-01",
    "start_time": "2026-10-15 08:00",
    "end_time": "2026-10-15 09:00",
    "required_duration_minutes": 60,
    "required_resources": ["Maintenance Team", "Repair Equipment"],
})
if reply.status_code == 200:
    result = reply.json()
    print(result["status"], result["reasons"])
else:
    print("Problem:", reply.status_code, reply.json())
```
(`pip install requests` first, or call `main.validate_maintenance(...)` directly
if you share a Python project.) Always check `status_code` before reading `status`.

## 12. For Member 5 (React website)
```javascript
const response = await fetch("http://127.0.0.1:8000/validate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    track_section: "SEC-01",
    start_time: "2026-10-15 08:00",
    end_time: "2026-10-15 09:00",
    required_duration_minutes: 60,
    required_resources: ["Maintenance Team"],
  }),
});
const data = await response.json();
if (response.ok) { /* show data.status and data.reasons */ }
else { /* 422 -> data.errors, 500 -> data.detail */ }
```
A browser on another address (such as `http://localhost:3000`) is blocked by
CORS unless the API allows it. CORS is **not** enabled in this version; agree
with your team before adding it, or use a proxy in the React dev server.

## 13. Limitations
- Train schedules are **synthetic demonstration data**, not real timetables.
- Resource availability is a **simple flag in `resources.csv`**. It is **not**
  date- or time-specific.
- Only the checks listed above are implemented (no signalling, speed limits,
  crew rules, weather, etc.).
- Section names are matched by exact text (ignoring capitals and spaces).
- This is a student project: **not** official, certified, or safe for real
  railway operations.

## 14. Editing the data
Keep the CSV columns exactly as they are. Times are `YYYY-MM-DD HH:MM`.
`available` accepts `true/false`, `yes/no`, `y/n`, `1/0`. Bad rows are reported,
and they make validation return `CONFLICT` until fixed.
