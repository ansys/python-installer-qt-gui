from ansys.tools.installer import __version__


def test_pkg_version():
    assert isinstance(__version__, str)
