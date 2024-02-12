# Copyright (C) 2023 - 2024 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Check for updates."""

from github import Github
from packaging import version


def query_gh_latest_release(token=None):
    """Check GitHub for updates.

    Compares the current version with the version on GitHub.

    Returns the version of the latest release and the download url of
    the executable installer.

    Parameters
    ----------
    token : str, optional
        Token to perform the request. Not necessary, only used on testing
        to avoid reaching API request limit.

    Returns
    -------
    str
        Tag of the latest version.

    str
        Url of the latest release installer.

    """
    gh = Github(login_or_token=token)
    repo = gh.get_repo(f"ansys/python-installer-qt-gui")

    # Get the latest release and its tag name
    latest_release = repo.get_latest_release()
    latest_version_tag = latest_release.tag_name

    download_asset = None
    for asset in latest_release.get_assets():
        if asset.name.endswith(".exe"):
            download_asset = asset

    download_url = None if download_asset is None else download_asset.url

    return version.parse(latest_version_tag), download_url
