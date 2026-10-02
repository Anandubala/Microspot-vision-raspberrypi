# Setup — Windows (development machine)

Tested with Python 3.11+ (Phase 1 was built/verified against Python 3.12).

## 1. Clone

```powershell
git clone https://github.com/<your-username>/microspot-vision.git C:\Users\<you>\projects\microspot-vision
cd C:\Users\<you>\projects\microspot-vision
```

## 2. Virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

`picamera2` is not in `requirements.txt` at all (not just skipped on
Windows) — see `docs/SETUP_RASPBERRY_PI.md` for why and how it'll be
installed via apt when Phase 15 needs it. Nothing in the app imports it at
module load time without a guard (see `app/acquisition/camera.py`), so the
app runs fine without it on either machine.

## 4. Run

```powershell
python run.py
```

A window titled "MicroSpot Vision v1.0.0" should open. File > Open Image
to load a JPG/PNG/BMP/TIFF and confirm it displays.

## 5. Run tests

```powershell
pytest
```

Expect all tests to pass. If Qt complains about no display/platform plugin
in a headless CI context, set:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest
```

## Notes

- No Windows-only paths, drive letters, or libraries are used anywhere in
  `app/` — every path goes through `pathlib` and is built relative to the
  project root (`app/config/settings.py`).
- If OpenCV or PySide6 fail to install, upgrade pip first:
  `python -m pip install --upgrade pip`.
