# Instructions for building LogConvert

## Amazon Linux 2023
Use the provided [Dockerfile](Dockerfile) as a starting point for building and running LogConvert
in Amazon Linux 2023 environments (e.g., public.ecr.aws/lambda/python:3.12).

### AMD64
```shell
$ docker buildx build --platform linux/amd64 -t wibl/logconvert:latest ./
```

### ARM64
```shell
$ docker buildx build --platform linux/arm64 -t wibl/logconvert:latest ./
```

## macOS
Use the script [build-logconvert.bash](scripts/macos-build/build-logconvert.bash)
to build LogConvert for M-series (i.e., Apple Silicon, not x86_64) Macs running
macOS 11.0 (Big Sur) and later. 

For example:
```shell
$ ./scripts/macos-build/build-logconvert.bash
...
...
...
$ ls -l logconvert
-rwxr-xr-x  1 wibl  staff  557816 Dec 23 20:50 logconvert*
```

This will build a statically linked binary named `logconvert` and copy it to 
the current directory, which you can run as follows:
```shell
./logconvert -f YDVR -i 00020001.DAT -o 00020001.wibl
```
