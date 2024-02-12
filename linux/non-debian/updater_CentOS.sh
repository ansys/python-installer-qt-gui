#! /bin/bash

while true; do
    read -p "Require sudo permission to update & install the package. Do you want to continue?(Y/N): " user_selection
    if [ "$user_selection" = "Y" ] || [ "$user_selection" = "N" ]; then
        break
    fi
    clear
done
if [ "$user_selection" = "Y" ]; then
    sudo rpm -iv ansys_python_manager_*.rpm
else
    printf "Aborting installation....\nUser permission denied.... \n\n"
    echo "Ansys Python Manager and required dependencies require sudo access to install."
fi