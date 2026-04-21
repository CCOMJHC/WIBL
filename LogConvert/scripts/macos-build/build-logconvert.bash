#!/usr/bin/env bash
set -eu -o pipefail
CONTENT_ROOT=$(realpath "$(dirname $0)/../..")

# Install cmake ~3.31.6, something before version 4, so that we can support 
# cmake_minimum_required(VERSION 3.0)
PATH=/Applications/CMake.app/Contents/bin:${PATH}
export PATH

export BUILD_ROOT="${CONTENT_ROOT}/build-deps/macOS"
export INSTALL_ROOT="${BUILD_ROOT}/install"
mkdir -p ${INSTALL_ROOT}


# Install NMEA200 library
pushd ${BUILD_ROOT}
wget https://github.com/ttlappalainen/NMEA2000/archive/5b7b9fc3ccc18e30ebfba92da6486cffc6251595.tar.gz -O NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595.tar.gz
echo "3e4c10fc0652619f87a4e66d00fabd7bd9def12d33144bacdc8b63192258aef8  NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595.tar.gz" > NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595.tar.gz.sum
sha256sum -c NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595.tar.gz.sum
tar xf NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595.tar.gz
cd NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595 
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_IGNORE_PREFIX_PATH='/opt/homebrew;/usr/local' \
	-DCMAKE_OSX_ARCHITECTURES='arm64' \
	-DCMAKE_OSX_DEPLOYMENT_TARGET='11.0' \
	-DBUILD_SHARED_LIBS=OFF \
	-DCMAKE_CXX_FLAGS='-Wno-error=vla' \
	-B build -S .
cmake --build build -j $(nproc)
export N2K_INCLUDE="${BUILD_ROOT}/NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595/src"
export N2K_LIB="${BUILD_ROOT}/NMEA2000-5b7b9fc3ccc18e30ebfba92da6486cffc6251595/build/src/libnmea2000.a"

# Boost 1.83
pushd ${BUILD_ROOT}
wget https://archives.boost.io/release/1.83.0/source/boost_1_83_0.tar.bz2
echo "6478edfe2f3305127cffe8caf73ea0176c53769f4bf1585be237eb30798c3b8e  boost_1_83_0.tar.bz2" > boost_1_83_0.tar.bz2.sum
sha256sum -c boost_1_83_0.tar.bz2.sum
tar xf boost_1_83_0.tar.bz2
cd boost_1_83_0
export SDKROOT=$(xcrun --show-sdk-path)
./bootstrap.sh --prefix=${INSTALL_ROOT} \
	--with-libraries='program_options' \
	--with-toolset=clang
cat > user-config.jam <<-EOF
using clang : arm64 : clang++ -arch arm64 -mmacosx-version-min=11.0 ;
EOF
./b2 --user-config=user-config.jam \
    toolset=clang-arm64 \
    architecture=arm \
    address-model=64 \
    link=static \
    threading=multi \
    runtime-link=static \
    variant=release \
    cxxflags="-std=c++11 -mmacosx-version-min=11.0" \
    linkflags="-mmacosx-version-min=11.0" \
    --stagedir=stage-arm64 \
    install

# Build LogConvert
pushd "${CONTENT_ROOT}"
cmake -G Ninja -Wno-dev -DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_IGNORE_PREFIX_PATH='/opt/homebrew;/usr/local' \
	-DCMAKE_OSX_ARCHITECTURES='arm64' \
	-DCMAKE_OSX_DEPLOYMENT_TARGET='11.0' \
	-DCMAKE_PREFIX_PATH=${INSTALL_ROOT} \
	-DCMAKE_INSTALL_PREFIX=${CONTENT_ROOT} \
	-DBoost_USE_STATIC_RUNTIME=ON \
	-B build -S . \
  -DN2K_INCLUDE=${N2K_INCLUDE} -DN2K_LIB=${N2K_LIB}
cmake --build build -j $(nproc) --target install
cp build/bin/logconvert .
