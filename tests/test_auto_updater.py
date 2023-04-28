import os

from packaging.version import Version

from ansys.tools.installer.auto_updater import query_gh_latest_release


def test_query_gh_latest_release():
    latest_version_tag, download_url = query_gh_latest_release(
        token=os.getenv("GITHUB_TOKEN", None)
    )

    ver = latest_version_tag
    assert isinstance(ver, Version)
    assert "http" in download_url
