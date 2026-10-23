#! /bin/bash
clear
missing_deps=()
dependencies_available=true
if command -v dnf >/dev/null 2>&1; then
    pkg_manager=dnf
elif command -v yum >/dev/null 2>&1; then
    pkg_manager=yum
else
    echo "Neither dnf nor yum was found. Install the dependencies manually, following:"
    echo "https://installer.docs.pyansys.com/version/stable/installer.html"
    exit 1
fi
# Check user input for sudo permission
while true; do
    read -p "Require sudo permission to install this package and the dependencies. Do you want to continue?(Y/N): " user_selection
    if [ "$user_selection" = "Y" ] || [ "$user_selection" = "N" ]; then
        break
    fi
    clear
done
printf "\n"
if [ "$user_selection" = "Y" ]; then
    #Check sudo
    sudo -v >/dev/null 2>&1
    root_check=$?
    if [ $root_check -eq 0 ]; then
        # check zlib
        ls /usr/local/lib/libz.so >/dev/null 2>&1
        ret=$?
        if [ $ret -eq 0 ]; then
            :
        else
            missing_deps+=("zlib")
            dependencies_available=false
        fi
        # check other dependencies
        $pkg_manager group list --installed 2>/dev/null | grep -q 'Development Tools'
        ret=$?
        if [ $ret -eq 0 ]; then
            :
        else
            missing_deps+=("Development Tools")
            dependencies_available=false
        fi
        arr=("wget" "gnome-terminal" "libffi-devel" "openssl-devel" "rpm-build" "sqlite-devel" "sqlite-libs" "libXinerama-devel" "coreutils" "mesa-libGL" "mesa-libEGL" "xcb-util-cursor")
        for x in "${arr[@]}"; do
            c="rpm -qa | grep $x"
            eval $c
            ret=$?
            if [ $ret -eq 0 ]; then
                :
            else
                missing_deps+=("$x")
                dependencies_available=false
            fi
        done
        if [ $dependencies_available = true ]; then
            if ! sudo rpm -iv ansys_python_manager_*.rpm; then
                printf "\nInstallation failed...\n"
                exit 1
            fi
            available=$(cat ~/.bashrc | grep -zoP "# Add alias for Ansys Python Manager \nalias  ansys_python_manager=~/.local/opt/ansys_python_manager/ansys_python_manager" | wc -l)
            echo $available
            if [ $available -lt 1 ]
            then
                echo -e "# Add alias for Ansys Python Manager \nalias  ansys_python_manager=~/.local/opt/ansys_python_manager/ansys_python_manager" | sudo tee -a ~/.bashrc
            fi
            printf "\nInstallation success...\nIt is suggested to restart your machine to begin using the software....\n"
        else
            echo "Missing dependencies..."
            install_script="true"
            packages=""
            install_zlib=false
            install_dev_tools=false
            for x in "${missing_deps[@]}"; do
                if [ "$x" == "zlib" ]; then
                    install_zlib=true
                elif [ "$x" == "Development Tools" ]; then
                    install_dev_tools=true
                else
                    packages="$packages $x"
                fi
            done
            if [ -n "$packages" ]; then
                install_script="$install_script && sudo $pkg_manager install$packages -y"
            fi
            if [ $install_dev_tools = true ]; then
                # dnf5 (Fedora 41+) only accepts the group ID
                install_script="$install_script && { sudo $pkg_manager group install 'Development Tools' -y || sudo $pkg_manager group install development-tools -y; }"
            fi
            sudo $pkg_manager update -y
            if ! eval $install_script; then
                printf "\nFailed to install the dependencies. Installation aborted...\n"
                exit 1
            fi
            if [ $install_zlib = true ]; then
                mkdir ansys-prereq; cd ansys-prereq; wget https://zlib.net/current/zlib.tar.gz; tar xvzf zlib.tar.gz; cd zlib-*; sudo make clean; ./configure; sudo make; sudo make install; cd ../..; rm -rf ansys-prereq;
            fi
            if ! sudo rpm -iv ansys_python_manager_*.rpm; then
                printf "\nInstallation failed...\n"
                exit 1
            fi
            printf "\nInstallation success...\n"
        fi
    else
        echo "You don't have access to sudo. Please try again..."
    fi
else
    printf "Aborting installation....\nUser permission denied.... \n\n"
    echo "Ansys Python Manager and required dependencies require sudo access to install."
fi
