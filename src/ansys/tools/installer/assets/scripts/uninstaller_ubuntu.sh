echo "Uninstalling Ansys Python Manager......."
sleep 3

rm -rf ${HOME}/.local/share/icons/pyansys_icon.svg
rm -rf ${HOME}/.local/share/applications/ansys_python_manager.desktop
rm -rf ${HOME}/.local/usr/share/doc/ansys-python-manager

rm -rf ${HOME}/.local/opt/ansys_python_manager
