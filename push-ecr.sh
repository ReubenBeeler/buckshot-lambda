#!/bin/bash

set -e

if [[ -f ".env" ]]; then
	source .env
fi

if [[ -z "$AWS_REGION" ]]; then
	echo 'error: you must set environment variable AWS_REGION to the region containing the ECR repository' >&2
	exit -1
fi

if [[ -z "$AWS_ACCOUNT_ID" ]]; then
	AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
fi

# aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker tag "$LOCAL_IMAGE_NAME" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_IMAGE_NAME"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_IMAGE_NAME"