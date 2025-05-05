# Base container images for running WIBL in Docker
This page describes how to build WIBL base container imagers for running WIBL
in Docker or other container runtime environments. The following steps
assum you are using [Docker Desktop](https://www.docker.com/products/docker-desktop/).

## Build
To build, do the following:
```shell
$ docker buildx build \
  --platform linux/amd64,linux/arm64 --builder=desktop-linux \
  -t ghcr.io/ccomjhc/wibl:1.1.0-amazonlinux -t ghcr.io/ccomjhc/wibl:1.1.0 \
  cloud/AWS
```

> Note: If you don't have a builder named `desktop-linux`, run `docker buildx ls`
> to find the name of your builder.

> Note: For now, we tag this image both as `1.1.0-amazonlinux` and 
> `1.1.0`. In the future we may plan to build a version of the that is
> not based on Amazon Linux.

To push, first store your GitHub container registry personal access token to
an environment variable named `CR_PAT`, then login:
```shell
$ echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

> For more info on pushing images, see [here](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#pushing-container-images)

Then push:
```shell
$ docker image push --all-tags ghcr.io/ccomjhc/wibl
```
