# Base image
FROM python:3.9-slim


ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
# Set environment variables
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

# 필요한 패키지 설치
RUN apt-get update && \
    apt-get install -y wget unzip

# Terraform 버전 설정 (필요한 버전으로 변경 가능)
ENV TERRAFORM_VERSION=1.5.7

# Terraform 다운로드 및 설치
RUN wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip


# Set working directory
WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the application port
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
