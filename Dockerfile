FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

# The kagglehub cache defaults to /root/.cache/kagglehub (since the image builds as root)
#  but the AWS Lambda function runs as sbx_user1051, which can't read /root/ so we need
#  to place somewhere that is accessible by sbx_user1051.
ENV KAGGLEHUB_CACHE='/opt/.cache/kagglehub'

COPY .env .env.public pyproject.toml install lambda_function.py model.py ${LAMBDA_TASK_ROOT}
COPY lib ${LAMBDA_TASK_ROOT}/lib

RUN ${LAMBDA_TASK_ROOT}/install

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.lambda_handler" ]