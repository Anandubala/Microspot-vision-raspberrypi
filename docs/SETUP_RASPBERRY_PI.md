# Setup — Raspberry Pi 4 Model B, 8 GB (deployment / demo machine)

Raspberry Pi OS 64-bit recommended (extra RAM headroom, better
OpenCV/NumPy wheel availability than 32-bit).

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

This installs `picamera2` here (it's `sys_platform == "linux"` in
`requirements.txt`) even though Phase 1 doesn't use it yet — it's for
Phase 15 (live camera capture).

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
