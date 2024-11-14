import os

import boto3
from io import BytesIO
from pypdf import PdfReader

s3 = boto3.client('s3')

def list_files_in_s3(bucket_name, folder_path):
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)

    # 제외할 파일명 목록
    excluded_files = {"main.tf", "terraform.tfvars", "terraform.tfstate"}

    # 파일 필터링 조건 수정
    files = [
        obj['Key'] for obj in response.get('Contents', [])
        if not obj['Key'].endswith('/') and obj['Key'].split('/')[-1] not in excluded_files
    ]

    print("Filtered files in S3 under the specified path:")
    for file in files:
        print(f" - {file}")

    return files

def get_file_content_from_s3(bucket_name, file_key):
    response = s3.get_object(Bucket=bucket_name, Key=file_key)
    return response["Body"].read().decode('utf-8')

def save_tf_file_to_s3(bucket_name, file_key, content):
    # 저장하려는 파일이 제외 파일 목록에 있는지 확인
    excluded_files = {"main.tf", "terraform.tfvars", "terraform.tfstate"}
    if file_key.split('/')[-1] in excluded_files:
        print(f"Skipping save for excluded file '{file_key}'")
        return

    # 제외된 파일이 아니면 저장
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=content)
    print(f"File '{file_key}' saved to S3 bucket '{bucket_name}'")

def get_text_from_pdf(bucket_name, pdf_key):
    response = s3.get_object(Bucket=bucket_name, Key=pdf_key)
    pdf_content = response["Body"].read()
    pdf_reader = PdfReader(BytesIO(pdf_content))
    text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
    return text

def download_file_from_s3(bucket_name, file_key, download_path):
    try:
        s3.download_file(bucket_name, file_key, download_path)
        print(f"Downloaded '{file_key}' from S3 bucket '{bucket_name}' to '{download_path}'")
    except Exception as e:
        print(f"Error downloading file from S3: {str(e)}")


def download_all_files_from_s3(bucket_name, folder_path, local_dir):
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)
    files = [obj['Key'] for obj in response.get('Contents', []) if not obj['Key'].endswith('/')]

    print("All files in S3 under the specified path:")
    for file_key in files:
        file_name = file_key.split('/')[-1]

        # credential.json은 key 디렉토리에, 나머지는 local_dir에 저장
        if file_name == "credential.json":
            download_path = os.path.join(local_dir, "key", file_name)
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
        else:
            download_path = os.path.join(local_dir, file_name)

        print(f"Attempting to download: {file_key} to {download_path}")
        try:
            s3.download_file(bucket_name, file_key, download_path)
            print(f"Successfully downloaded: {file_key} to {download_path}")
        except Exception as e:
            print(f"Error downloading file from S3: {str(e)}")

    return files

