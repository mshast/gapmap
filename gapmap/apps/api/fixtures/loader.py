"""Load package-safe demo fixture assets."""

from importlib.resources import files

from gapmap.apps.api.contracts import DemoFixtureResponse


def load_demo_fixture() -> DemoFixtureResponse:
    root = files("gapmap.apps.api.fixtures")
    return DemoFixtureResponse(
        resume_text=root.joinpath("demo_resume.txt").read_text(encoding="utf-8").strip(),
        job_description=root.joinpath("demo_job_description.txt")
        .read_text(encoding="utf-8")
        .strip(),
    )
