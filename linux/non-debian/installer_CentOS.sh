mkdir ansys-prereq;
cd ansys-prereq;
sudo yum update -y
sudo yum groupinstall 'Development Tools' -y
sudo yum install wget libffi-devel openssl-devel rpm-build sqlite-devel sqlite-libs libXinerama-devel -y;
wget https://zlib.net/current/zlib.tar.gz;
tar xvzf zlib.tar.gz;
cd zlib-*;
./configure;
sudo make;
sudo make install;
cd ../..;
rm -rf ansys-prereq;
sudo rpm -iv ansys_python_manager_*.rpm