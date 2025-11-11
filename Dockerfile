FROM public.ecr.aws/lambda/python:3.13

# RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*
# RUN yum install -y git && yum clean all
RUN microdnf install -y git && microdnf clean all

COPY .  ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir -r requirements.txt

CMD ["main.lambda_handler"]
