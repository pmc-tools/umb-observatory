echo 'Downloading Modest (targetplatform = ${TARGETPLATFORM})';
mkdir tmp; cd tmp;
if [ "${TARGETPLATFORM}" = "linux/amd64" ] ; then
  echo 'Installing Modest for linux/amd64';
  wget wget "https://www.modestchecker.net/Downloads/Modest-Toolset-$(wget -qO- https://www.modestchecker.net/Downloads/Version.txt)-linux-x64.zip"
elif [ "${TARGETPLATFORM}" = "linux/arm64" ] ; then
  echo 'Installing Modest for linux/arm64';
  wget wget "https://www.modestchecker.net/Downloads/Modest-Toolset-$(wget -qO- https://www.modestchecker.net/Downloads/Version.txt)-linux-arm64.zip"
else
  echo "Unknown targetplatform ${TARGETPLATFORM}"
  exit 1
fi
unzip *.zip ;
rm *.zip ;
mv Modest /opt/Modest
cd .. ;
rm -rf tmp ;