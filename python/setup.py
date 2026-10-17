"""Build hook of the INSLIB wheel: compiles libINSLIB next to the package.

All metadata lives in pyproject.toml. This file only adds what setuptools
cannot express there: the shared library that ``_core.py`` loads with
ctypes. It is a plain C library (no Python C API), so it is built with a
direct compiler call instead of a setuptools Extension, and the wheel is
tagged ``py3-none-<platform>``: one wheel per platform serves every
Python version.

The source list and the KFCore limits are read from the top-level
Makefile (SUITE_SRC, KFCORE_SRC, KFCORE_LIMITS), so the wheel and
``make pylib`` cannot drift apart. That needs the full repository
checkout, which is why only wheels are published, no sdist.

Compiler: ``$CC`` if set, else gcc on Windows (MinGW-w64, MSVC lacks the
automatic symbol export) and cc elsewhere.

(c) Jan Zwiener (jan@zwiener.org)
"""

import os
import re
import shlex
import shutil
import subprocess
import sys

from setuptools import Command, setup
from setuptools.command.build import build
from setuptools.dist import Distribution

try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:  # setuptools < 70.1 ships it in the wheel package
    from wheel.bdist_wheel import bdist_wheel

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

if sys.platform == "win32":
    _LIBNAME = "libINSLIB.dll"
elif sys.platform == "darwin":
    _LIBNAME = "libINSLIB.dylib"
else:
    _LIBNAME = "libINSLIB.so"


def _makefile_vars(*names):
    """Read single-line ``NAME := value`` assignments from the Makefile."""
    path = os.path.join(_ROOT, "Makefile")
    if not os.path.exists(path):
        raise RuntimeError(
            "INSLIB's Makefile not found at %s. The wheel builds from the "
            "full repository checkout (python/ inside it)." % path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    values = {}
    for name in names:
        m = re.search(r"^%s\s*:=\s*(.*)$" % re.escape(name), text, re.M)
        if not m:
            raise RuntimeError("Makefile has no '%s :=' line" % name)
        values[name] = m.group(1).split()
    return values


class build_inslib(Command):
    """Compile the C library into the package (``build_lib`` or in place)."""

    description = "compile libINSLIB (ctypes shared library)"
    user_options = []

    def initialize_options(self):
        self.build_lib = None
        self.editable_mode = False

    def finalize_options(self):
        self.set_undefined_options("build", ("build_lib", "build_lib"))

    def _target(self):
        if self.editable_mode:
            return os.path.join(_HERE, "INSLIB", _LIBNAME)
        return os.path.join(self.build_lib, "INSLIB", _LIBNAME)

    def _license(self):
        return os.path.join(os.path.dirname(self._target()), "LICENSE")

    def get_outputs(self):
        return [self._target()] if self.editable_mode else             [self._target(), self._license()]

    def get_output_mapping(self):
        return {}

    def get_source_files(self):
        return []

    def run(self):
        mk = _makefile_vars("SUITE_SRC", "KFCORE_SRC", "KFCORE_LIMITS")
        srcs = [os.path.join(_ROOT, p) for p in
                mk["SUITE_SRC"] + mk["KFCORE_SRC"]]
        srcs.append(os.path.join(_HERE, "csrc", "ins_capi.c"))
        missing = [p for p in srcs if not os.path.exists(p)]
        if missing:
            raise RuntimeError(
                "missing C sources (KFCore submodule not initialized? run "
                "git submodule update --init):\n  " + "\n  ".join(missing))

        cc = shlex.split(os.environ.get("CC", "")) or \
            ["gcc" if sys.platform == "win32" else "cc"]
        target = self._target()
        if shutil.which(cc[0]) is None:
            if self.editable_mode and os.path.exists(target):
                self.warn("no C compiler '%s', keeping the existing %s"
                          % (cc[0], target))
                return
            raise RuntimeError(
                "C compiler '%s' not found. Set CC or install gcc/clang."
                % cc[0])

        incs = ["src", "KFCore/c", "KFCore/c/navigation_tools", "KFCore/tests"]
        cmd = cc + ["-std=c11", "-O2", "-D_GNU_SOURCE", "-fPIC", "-shared"]
        cmd += mk["KFCORE_LIMITS"]
        cmd += ["-I" + os.path.join(_HERE, "csrc")]
        cmd += ["-I" + os.path.join(_ROOT, p) for p in incs]
        cmd += srcs
        if sys.platform == "win32":
            # No libgcc DLL dependency next to the wheel's DLL.
            cmd.append("-static-libgcc")
        cmd += ["-lm", "-o", target]

        os.makedirs(os.path.dirname(target), exist_ok=True)
        self.announce(" ".join(cmd), level=2)
        subprocess.check_call(cmd)
        if not self.editable_mode:
            # The AGPL text travels with every wheel. It lives at the
            # repository root, outside the project directory that PEP 639
            # license-files may point into.
            shutil.copyfile(os.path.join(_ROOT, "LICENSE"), self._license())


class build_with_lib(build):
    sub_commands = build.sub_commands + [("build_inslib", None)]


class bdist_wheel_platform(bdist_wheel):
    """Platform wheel without a Python ABI tag (ctypes, no C extension)."""

    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        _, _, plat = super().get_tag()
        return "py3", "none", plat


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


setup(
    distclass=BinaryDistribution,
    cmdclass={
        "build": build_with_lib,
        "build_inslib": build_inslib,
        "bdist_wheel": bdist_wheel_platform,
    },
)
