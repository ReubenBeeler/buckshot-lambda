#!/bin/bash

# context block for preventing TOCTOU
{
	set -e

	if [[ -f ".env" ]]; then
		source .env
	fi

	ARCH=linux/arm64 # Dockerfile base image requires linux/arm64

	echo "Building container $LOCAL_IMAGE_NAME..."
	docker buildx build --platform $ARCH --provenance=false -t $LOCAL_IMAGE_NAME . --progress=plain --no-cache

	echo "Running container $LOCAL_IMAGE_NAME..."
	# docker run --rm --platform $ARCH -p 9000:8080 -it --entrypoint "/bin/bash" $LOCAL_IMAGE_NAME
	docker run --rm --platform $ARCH -p 9000:8080 -it $LOCAL_IMAGE_NAME

	# Test it with
	# curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"test": true}'

	exit 0
}