# Setup — Raspberry Pi 4 Model B, 8 GB (deployment / demo machine)

Raspberry Pi OS 64-bit recommended (extra RAM headroom, better
OpenCV/NumPy wheel availability than 32-bit).

**Check your Python version first:** `python3 --version`. Current
Raspberry Pi OS (Debian "trixie") ships **Python 3.13** by default. The
pins in `requirements.txt` are chosen to install on Python 3.11–3.13 —
if your Pi has something outside that range, the packages below may need
bumping (check `pip index versions <package>` for what's available for
your interpreter).

## 1. System packages

PySide6/Qt and OpenCV need a few apt packages on Pi OS that aren't needed
on Windows:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip \
  libgl1 libegl1 libxkbcommon0 libxcb-cursor0 \
  libqt6gui6 libqt6widgets6 libqt6core6
```

(Exact package names can shift between Raspberry Pi OS releases — if
`pip install pyside6` fails to import afterward with a missing `.so`
error, `apt search libqt6` and add whatever it's missing.)

## 2. Clone

```bash
git clone https://github.com/<your-username>/microspot-vision.git ~/microspot-vision
cd ~/microspot-vision
```

## 3. Virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Install dependencies

```bash
pip install -r requirements.txt
```

`picamera2` is deliberately **not** in `requirements.txt` — pip-installing
it pulls in `python-prctl`, which has no prebuilt wheel and fails to build
without the `libcap` system dev headers (confirmed by testing it, not
assumed). It's also not needed until Phase 15 (live camera capture). When
that phase arrives, install it the way Raspberry Pi OS actually supports:

```bash
sudo apt install -y python3-picamera2 --no-install-recommends
```

This also pulls in the matching `libcamera` system bindings, which pip
has no way to provide at all.

## 5. Run

```bash
python run.py
```

## 6. Day-to-day update loop

Never hand-edit the Pi clone. Always pull the latest from GitHub:

```bash
cd ~/microspot-vision
git pull
pip install -r requirements.txt   # only if requirements.txt changed
python run.py
```

## 7. Run tests

```bash
pytest
```

If running over SSH with no attached display:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

To actually see the GUI window during a live demo, run it from the Pi's
own desktop session (not over SSH without X forwarding), or use
`ssh -X` and expect it to be slow.
