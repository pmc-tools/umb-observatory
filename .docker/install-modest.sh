echo 'Downloading Modest (targetplatform = ${TARGETPLATFORM})';
mkdir tmp; cd tmp;
wget https://www.modestchecker.net/Downloads/Modest-umb-all.zip ;
unzip Modest-umb-all.zip ;
rm Modest-umb-all.zip ;
ls
if [ "${TARGETPLATFORM}" = "linux/x64" ] ; then
  echo 'Installing Modest for linux/x64';
  tar xvf Modest-linux-x64.tar.xz;
else
  echo 'Installing Modest for linux/arm64';
  tar xvf Modest-linux-arm64.tar.xz ;
fi
mv Modest /opt/Modest
cd .. ;
rm -rf tmp ;