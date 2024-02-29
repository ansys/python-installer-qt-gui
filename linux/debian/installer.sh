#! /bin/bash
clear
missing_deps=()
dependencies_available=true
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
arr=("libffi-dev" "libssl-dev" "build-essential" "libsqlite3-dev" "libxcb-xinerama0")
for x in "${arr[@]}"; do
    c="dpkg -s $x >/dev/null 2>&1"
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
    dpkg -x ./ansys_python_manager.deb ${HOME}/.local
    ./postInstallScript.sh
    printf "\nInstallation success...\n"
else
    echo "Missing dependencies..."
    while true; do
        read -p "Require sudo permission to install dependencies. Do you want to install?(Y/N): " user_selection
        if [ "$user_selection" = "Y" ] || [ "$user_selection" = "N" ]; then
            break
        fi
        clear
    done
    printf "\n"
    if [ "$user_selection" = "Y" ]; then
        sudo -v >/dev/null 2>&1
        root_check=$?
        if [ $root_check -eq 0 ]; then
            install_script="sudo apt-get update -y; "
            install_zlib=false
            for x in "${missing_deps[@]}"; do
                if [ $x == "zlib" ]; then
                    install_zlib=true
                else
                    install_script="$install_script sudo apt-get install $x -y;"
                fi
            done
            if [ $install_zlib = true ]; then
                install_script="$install_script rm -rf ansys-prereq/ ; mkdir -p ansys-prereq; cd ansys-prereq; wget https://zlib.net/current/zlib.tar.gz; tar xvzf zlib.tar.gz; cd zlib-*; make clean; ./configure; make; sudo make install; cd ../..; rm -rf ansys-prereq;"
            fi
            eval $install_script
            dpkg -x ./ansys_python_manager.deb ${HOME}/.local
            ./postInstallScript.sh
            printf "\nInstallation success...\n"
        else
            echo "You don't have access to sudo. Please try again..."
        fi
    else
        printf "Install below mentioned dependencies to proceed installation.... \n"
        for x in "${missing_deps[@]}"; do
            echo "$x"
        done
        printf "Dependencies installation required sudo access.\n"
        echo -e '\e]8;;https://installer.docs.pyansys.com/version/stable/installer.html\aFollow prerequisites in this link\e]8;;\a'
    fi
fi
