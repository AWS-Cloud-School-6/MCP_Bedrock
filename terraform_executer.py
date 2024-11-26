# terraform_executer.py
import os
import subprocess
from s3_utils import download_all_files_from_s3
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
bucket_name = 'aiwa-terraform'

def apply_terraform(user_email, platform):
    # S3 경로 및 로컬 디렉토리 설정
    s3_folder_path = f"users/{user_email}/{platform}"
    local_dir = f"/tmp/{user_email}/terraform"
    key_dir = os.path.join(local_dir, "key")
    os.makedirs(local_dir, exist_ok=True)
    os.makedirs(key_dir, exist_ok=True)

    # S3에서 모든 파일 다운로드
    download_all_files_from_s3(bucket_name, s3_folder_path, local_dir)
    print("All files have been downloaded successfully.")

    # 환경 변수 설정 (key 폴더의 credential.json 경로 설정)
    credential_file_path = os.path.join(key_dir, "credential.json")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_file_path
    print(f"GOOGLE_APPLICATION_CREDENTIALS set to {credential_file_path}")

    # 다운로드된 파일 목록 출력
    print("Downloaded files in local_dir:")
    print(os.listdir(local_dir))

    # Terraform 명령어 실행
    try:
        subprocess.run(["terraform", "init"], cwd=local_dir, check=True)
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=local_dir, check=True)
        print("Terraform 실행 성공")
    except subprocess.CalledProcessError as e:
        print(f"Terraform 실행 오류: {e}")
