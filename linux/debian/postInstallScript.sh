envsubst < ${HOME}/.local/share/applications/ansys_python_manager_prebuid.desktop > ${HOME}/.local/share/applications/ansys_python_manager.desktop
rm -rf ${HOME}/.local/share/applications/ansys_python_manager_prebuid.desktop

envsubst < ${HOME}/.local/opt/ansys_python_manager/scripts/uninstall_prebuid.sh > ${HOME}/.local/opt/ansys_python_manager/scripts/uninstall.sh
rm -rf ${HOME}/.local/opt/ansys_python_manager/scripts/uninstall_prebuid.sh