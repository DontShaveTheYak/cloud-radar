"""Nox sessions."""

import sys
from textwrap import dedent

import nox

try:
    from nox_poetry import Session, session
except ImportError:
    message = f"""\
    Nox failed to import the 'nox-poetry' package.

    Please install it using the following command:

    {sys.executable} -m pip install nox-poetry"""
    raise SystemExit(dedent(message)) from None

nox.options.sessions = "mypy", "tests"

locations = "src", "tests", "noxfile.py"

default_python = "3.12"

python_versions = ["3.9", "3.10", "3.11", "3.12", "3.13"]


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
    session.install(".")
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
            *session.posargs,
        )
    finally:
        pass
        # if session.interactive:
        #     session.notify("coverage", posargs=[])


@session(python=python_versions)
def mypy(session: Session) -> None:
    """Type-check using mypy."""
    args = session.posargs or locations
    session.run_always("poetry", "install", external=True)
    session.run("mypy", *args)
    if not session.posargs:
        session.run("mypy", f"--python-executable={sys.executable}", "noxfile.py")
