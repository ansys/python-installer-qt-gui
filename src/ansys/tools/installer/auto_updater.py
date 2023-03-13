"""Check for updates."""

from github import Github
from packaging import version

# Readonly on this repo
# This repository will be released to the public, there's no issue with this token.
# Exp Mon, Jan 1 2024, should be able to use public unauth by then
READ_ONLY_PAT = (
    "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"
)


def query_gh_latest_release():
    """Check GitHub for updates.

    Compares the current version with the version on GitHub.

    Returns the version of the latest release and the download url of
    the executable installer.

    Returns
    -------
    str
        Tag of the latest version.

    str
        Url of the latest release installer.

    """
    gh = Github(READ_ONLY_PAT)
    repo = gh.get_repo(f"pyansys/python-installer-qt-gui")

    # Get the latest release and its tag name
    latest_release = repo.get_latest_release()
    latest_version_tag = latest_release.tag_name

    download_asset = None
    for asset in latest_release.get_assets():
        if asset.name.endswith(".exe"):
            download_asset = asset

    download_url = None if download_asset is None else download_asset.url

    return version.parse(latest_version_tag), download_url
