"""Check for updates."""

from github import Github
from packaging import version


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
    gh = Github()
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
