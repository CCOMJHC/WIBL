echo "Preparing to install PowerShell..."
mkdir /opt/powershell
cd /tmp

platform=$(uname -m)
# MS doesn't always use the correct machine strings when they package PowerShell, so we need to do this...
if [[ "$platform" = "aarch64" ]]; then
  platform=arm64
  sum=006021694a9e0ce962457d23189e3cb88ae030863b221907f8fb891df9497aeb
elif [[ "$platform" = "x86_64" ]]; then
  platform=x64
  sum=36605dc37979de5af2e10783bf70c0ad8150521e81e6d7c9322036ebb897e7fe
else
  echo "Unkown platform $platform, exiting..."
  exit 1
fi

echo "Installing PowerShell for ${platform}..."
wget https://github.com/PowerShell/PowerShell/releases/download/v7.4.2/powershell-7.4.2-linux-${platform}.tar.gz
echo "$sum  powershell-7.4.2-linux-${platform}.tar.gz" > powershell-7.4.2-linux-${platform}.tar.gz.sum
sha256sum -c powershell-7.4.2-linux-${platform}.tar.gz.sum
tar xf powershell-7.4.2-linux-${platform}.tar.gz -C /opt/powershell
echo 'PATH=${PATH}:/opt/powershell' >> /etc/environment
echo 'export PATH=${PATH}:/opt/powershell' >> /etc/profile.d/sh.local
