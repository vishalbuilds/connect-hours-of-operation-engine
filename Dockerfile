FROM public.ecr.aws/lambda/python:3.11

# Install dependencies 
COPY src/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code 
COPY src/ ${LAMBDA_TASK_ROOT}/

# Build arguments and labels
ARG build=local-dev
LABEL build=$build \
      image="connect-hours-of-operation"


# Environment configuration
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}" 

# Default CMD for Lambda runtime 
CMD ["lambda_handler.lambda_handler"]