"""Nox sessions."""

import sys
from pathlib import Path
from textwrap import dedent

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "tomllib/tomli not found. Run nox with Python 3.11+ or install 'tomli'."
        ) from exc

import nox

try:
    from nox_poetry import Session, session
except ImportError:
    message = f"""\
    Nox failed to import the 'nox-poetry' package.

    Please install it using the following command:

    {sys.executable} -m pip install nox-poetry"""
    raise SystemExit(dedent(message)) from None

with Path("pyproject.toml").open("rb") as _f:
    _config = tomllib.load(_f)["tool"]["cloud-radar"]

python_versions: list[str] = _config["python-versions"]

nox.options.sessions = ("tests",)


# @session(python=default_python)
# def coverage(session: Session) -> None:
#     """Produce the coverage report."""
#     args = session.posargs or ["report"]

#     session.install("coverage[toml]")

#     if not session.posargs and any(Path().glob(".coverage.*")):
#         session.run("coverage", "combine")

#     session.run("coverage", *args)


@session(python=python_versions)
def tests(session: Session) -> None:
    """Run the test suite."""
    session.install(".[e2e]")
    session.install("coverage[toml]", "pytest", "pygments", "pytest-mock")
    try:
        session.run(
            "coverage",
            "run",
            "--parallel",
            "-m",
            "pytest",
            "-m",
            "not e2e",
            "tests",
            "examples",
            *session.posargs,
        )
    finally:
        pass
        # if session.interactive:
        #     session.notify("coverage", posargs=[])
