# INSLIB

Python binding of [INSLIB](https://github.com/jnz/INSLIB), a portable C11
library for 3D navigation state estimation: a 15/18-state error-state Kalman
filter fusing IMU, GNSS, magnetometer, barometer and local position, plus
standalone AHRS/ARS attitude filters and a baro/accel vertical channel, run
side by side with automatic mode arbitration.

The wheel ships the compiled C library, the Python side is a thin `ctypes`
layer over it, with no required dependencies.

## Install

```sh
pip install inslib
```

Wheels exist for Linux x86_64, aarch64 and armv7l (64- and 32-bit Raspberry
Pi OS included), Windows x64 and ARM64, and macOS Intel and Apple silicon.
Anywhere else (a Pi Zero/1, for example), install from a checkout of the
repository with `pip install -e python/`, which needs a C compiler.

The import name is `INSLIB`. Optional extras: `inslib[mavlink]` (MAVLink
telemetry), `inslib[replay]` (the YAML-configured CSV runner `inslib-run`).

## Quick start

```python
import math
from INSLIB import Navigator, Config

D2R = math.pi / 180.0
lat, lon, h = 48.1372 * D2R, 11.5756 * D2R, 520.0

nav = Navigator(Config(auto_init=True))
dt = 0.01                                    # 100 Hz IMU
for k in range(1, 1201):
    t_us = int(k * dt * 1e6)
    nav.imu(t_us, dt, acc=(0.0, 0.0, -9.81), gyr=(0.0, 0.0, 0.0))
    if k % 100 == 0:                         # 1 Hz GNSS fix
        nav.gnss_pos_llh((lat, lon, h), var_ned=(4.0, 4.0, 4.0))
    nav.update()                             # run the filter for this epoch
    sol = nav.solution()

print(sol.mode, sol.lat_rad / D2R, sol.lon_rad / D2R, sol.alt_m)
```

Conventions: body frame FRD, navigation frame NED, Hamilton quaternion
`[w, x, y, z]`, time in int64 microseconds, angles in radians.

## Documentation

- [Python tutorial](https://github.com/jnz/INSLIB/blob/main/tutorial/python_tutorial.md)
- [Manual (PDF)](https://github.com/jnz/INSLIB/blob/main/doc/INSLIB_manual.pdf)
- [Changelog](https://github.com/jnz/INSLIB/blob/main/CHANGELOG.md)

The replay, post-processing GUI and calibration tools live in the
repository's `tools/` directory, not in this package.

## License

AGPL-3.0-or-later.
