#! /bin/bash
clear
missing_deps=()
dependencies_available=true
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
        yum grouplist | grep 'Development Tools'
        ret=$?
        if [ $ret -eq 0 ]; then
            :
        else
            missing_deps+=("Development Tools")
            dependencies_available=false
        fi
        arr=("wget" "libffi-devel" "openssl-devel" "rpm-build" "sqlite-devel" "sqlite-libs" "libXinerama-devel")
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
            sudo rpm -iv ansys_python_manager_*.rpm
            printf "\nInstallation success...\n"
        else
            echo "Missing dependencies..."
            install_script="sudo yum update -y; sudo yum install "
            install_zlib=false
            for x in "${missing_deps[@]}"; do
                if [ $x == "zlib" ]; then
                    install_zlib=true
                else
                    install_script="$install_script $x"
                fi
            done
            install_script="$install_script -y"
            if [ $install_zlib = true ]; then
                install_script="$install_script; mkdir ansys-prereq; cd ansys-prereq; wget https://zlib.net/current/zlib.tar.gz; tar xvzf zlib.tar.gz; cd zlib-*; sudo make clean; ./configure; sudo make; sudo make install; cd ../..; rm -rf ansys-prereq;"
            fi
            eval $install_script
            sudo rpm -iv ansys_python_manager_*.rpm
            printf "\nInstallation success...\n"
        fi
    else
        echo "You don't have access to sudo. Please try again..."
    fi
else
    printf "Aborting installation....\nUser permission denied.... \n\n"
    echo "Ansys Python Manager and required dependencies require sudo access to install."
fi
