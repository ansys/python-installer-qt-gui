from PySide6 import QtWidgets

def test_main_window_header(gui):
    assert isinstance(gui.menu_heading, QtWidgets.QLabel)

    # verify image loaded
    pixmap = gui.menu_heading.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()

