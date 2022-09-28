import tempfile

import nox


nox.options.sessions = "lint", "mypy", "tests"

locations = "src", "tests", "noxfile.py"


def install_with_constraints(session, *args, **kwargs):
    with tempfile.NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--only",
            "dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        session.install("-r", requirements.name, *args, **kwargs)


@nox.session(python="3.9")
def coverage(session):
    """Upload coverage data."""
    install_with_constraints(session)
    session.run("coverage", "xml", "--fail-under=0")
    session.run("codecov", *session.posargs)


@nox.session(python=["3.9", "3.8"])
def tests(session):
    args = session.posargs or ["--cov", "-m", "not e2e"]
    session.run("poetry", "install", "--only", "main", external=True)
    install_with_constraints(
        session,
    )
    session.run("pytest", *args)


@nox.session(python=["3.9", "3.8"])
def lint(session):
    args = session.posargs or locations
    install_with_constraints(session)
    session.run("flake8", *args)


@nox.session(python=["3.9", "3.8"])
def mypy(session):
    args = session.posargs or locations
    install_with_constraints(session)
    session.run("mypy", *args)


@nox.session(python="3.9")
def black(session):
    args = session.posargs or locations
    install_with_constraints(session)
    session.run("black", *args)
