# Buckshot Lambda

This is an AWS Lambda function for validating images from the Raspberry Pi based on the presence of wildlife using SpeciesNet inference.

## AWS Lambda Files

```
lambda.py			# AWS Lambda event handler
create_layer.sh		# Auto-creates lambda_layer.zip
lambda_layer.zip	# AWS Lambda layer for lambda.py dependencies
```

## Technical Difficulties

- layer.zip
- missing os.memfd_create with venvs created by uv due to compilation bugs (pyenv venv works fine)
- uv trying to resolve dependency versions to fit ALL platforms, not just the target platform
- uv force wheels only with no-build = true to avoid compilation on edge devices (compilation is fine on local docker build for certain packages)
- uv is for better environment management and faster docker builds but need to install to system packages (put this in design choices)
- speciesnet isn't designed for execution on edge devices.
  - wheels are missing for some versions/architectures leading to compilation of complicated packages like numpy==1.26.4 (which edge devices often can't handle). And, even when wheels are available for the 'right architecture', they contain illegal CPU instructions for the raspi. The pure-python libs can be compiled fine but there are numerous missing implicit dependencies for C libraries such as numpy and ml-dtypes (it's nontrivial to install all of them automatically)
  - PyTorch and other dependencies are huge and generally slow on edge devices -- requires docker container for AWS Lambda deployment instead of just a zip file.
  - It uses opencv-python instead of opencv-python-headless, requiring manual package override (given they import to the same namespace) which has no right to work, but it fortunately does. I tried uv arg `[tool.uv.sources] \n opencv-python = { package = "opencv-python-headless" }`, but it doesn't exist -- no such tool to tell uv to replace one package with another so you have to resort to exclude and then add manual dependency that hopefully gets resolved correctly in place of the original dependency
- speciesnet depends on pkg_resource and therefore setuptools<81.0.0 (or is it <82 ?), which was somehow installed with incompatible version alongside speciesnet (although speciesnet lists the constraint...), which led to confusing errors (especially when uv would sometimes install a compatible version and sometimes not)
- uv package resolution isn't great because it limits itself to 3 options (highest, lowest, lowest-direct) that do not take into account certain factors afaik like no wheels or platform and ultimately fail even when a compatible solution exists
- speciesnet not working at all on 3.14, but I switch to 3.13 not realizing that speciesnet doesn't officially support 3.13 (but uv doesn't tell me that), so I get ALL SORTS of dependency resolution problems -> missing wheels -> compilation problems on minimal containers

## TODOs

- Migrate validation to end-of-day batch
- Include bounding boxes in the S3 object metadata and conditionally render the bounding boxes in the frontend
