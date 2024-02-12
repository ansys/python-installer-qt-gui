sudo yum update -y
sudo yum install binutils rpm-build fontconfig-devel freetype-devel libX11-devel libX11-xcb libXext-devel libXfixes-devel libXi-devel libXrender-devel libxcb-devel xcb-util-keysyms xcb-util xcb-util-image xcb-util-wm xcb-util-renderutil libXcursor-devel libglvnd-glx libxshmfence-devel libXrandr-devel libxkbcommon-devel libXinerama-devel libxkbcommon-x11 xorg-x11-drivers mesa-libGL mesa-libEGL mesa-dri-drivers python3-pip python3-qt5 gtk3-devel gnome-terminal dbus-x11 -y

sudo yum install ruby -y
sudo gem install fpm

cd ../..

python3 -m pip install pip -U
python3 -m pip install -e .[freeze]

python3 -m PyInstaller frozen.spec

mkdir -p package_Fedora/opt
mkdir -p package_Fedora/usr/share/applications
mkdir -p package_Fedora/usr/share/icons/hicolor/scalable/apps
cp -r dist/ansys_python_manager package_Fedora/opt/ansys_python_manager
cp src/ansys/tools/installer/assets/pyansys_icon.svg package_Fedora/usr/share/icons/hicolor/scalable/apps/pyansys_icon.svg
cp linux/non-debian/ansys_python_manager.desktop package_Fedora/usr/share/applications
find package_Fedora/opt/ansys_python_manager -type f -exec chmod 644 -- {} +
find package_Fedora/opt/ansys_python_manager -type d -exec chmod 755 -- {} +
find package_Fedora/usr/share -type f -exec chmod 644 -- {} +
chmod +x package_Fedora/opt/ansys_python_manager/ansys_python_manager
version=`cat ./src/ansys/tools/installer/VERSION`
echo $version
fpm -C package_Fedora -s dir -t rpm -n "ansys_python_manager" -v $version -p ansys_python_manager_Fedora.rpm -n "ansys_python_manager" --description "Ansys application to manage Python on the workstation." --url "https://installer.docs.pyansys.com/version/dev/installer.html" --maintainer "ANSYS, Inc. <pyansys.core@ansys.com>"
cp ./linux/non-debian/installer_CentOS.sh installer_Fedora.sh
cp ./linux/non-debian/updater_CentOS.sh updater_Fedora.sh
zip -r ./linux/manual_build/Ansys-Python-Manager_linux_fedora_v$version.zip ansys_python_manager_Fedora.rpm installer_Fedora.sh updater_Fedora.sh

rm ansys_python_manager_Fedora.rpm
rm -rf package_Fedora
rm -rf dist/ansys_python_manager
rm -rf installer_Fedora.sh
rm -rf updater_Fedora.sh