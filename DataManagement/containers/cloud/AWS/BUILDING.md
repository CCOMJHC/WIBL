# Base container images for running WIBL in Docker
This page describes how to build WIBL base container imagers for running WIBL
in Docker or other container runtime environments.

## Build
To build, do the following:
```shell
$ docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/wibl/python:1.0.3-amazonlinux -t ghcr.io/wibl/python:1.0.3
```

> Note: For now, we tag this image both as `1.0.3-amazonlinux` and 
> `:1.0.3`. In the future we may plan to build a version of the that is
> not based on Amazon Linux.

To push, first store your GitHub container registry personal access token to
an environment variable named `CR_PAT`, then login:
```shell
$ echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

> For more info on pushing images, see [here](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#pushing-container-images)

Then push:
```shell
$ docker image push --all-tags ghcr.io/wibl/python
```
