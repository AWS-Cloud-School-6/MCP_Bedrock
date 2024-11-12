import json
import re
import boto3
import time
from io import BytesIO
from pypdf import PdfReader
from botocore.exceptions import ClientError

# S3 및 Bedrock 클라이언트 생성
s3 = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

from flask import Flask, jsonify, request

app = Flask(__name__) 

@app.route("/api/bedrock/username", methods=["POST"])
def user_name(): 
     if request.is_json:  # Check if the request contains JSON
        user = request.json.get('user_email')
        lambda_handler(user)
        return {
            'statusCode': 200,
            'body': "All Terraform files have been processed and saved to the GCP folder in S3."
         }
     else:
        return jsonify({"error": "Request must be JSON"}), 400
        
    
def list_files_in_s3(bucket_name, folder_path):
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path)
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append(obj['Key'])
        print(f"Files found in S3 bucket '{bucket_name}' with prefix '{folder_path}': {files}")
        return [file for file in files if not (file.endswith("main.tf") or file.endswith("terraform.tfvars") or file.endswith("terraform.tfstate"))]
    except Exception as e:
        print(f"Error listing files in S3: {str(e)}")
        return None

def get_file_content_from_s3(bucket_name, file_key):
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        content = response["Body"].read().decode('utf-8')
        print(f"Content retrieved from file '{file_key}' in S3 bucket '{bucket_name}'")
        return content
    except Exception as e:
        print(f"Error fetching file from S3: {str(e)}")
        return None

def get_text_from_pdf(bucket_name, pdf_key):
    try:
        response = s3.get_object(Bucket=bucket_name, Key=pdf_key)
        pdf_content = response["Body"].read()
        pdf_reader = PdfReader(BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        print(f"Text extracted from PDF '{pdf_key}' in S3 bucket '{bucket_name}'")
        return text
    except Exception as e:
        print(f"Error fetching or reading PDF file from S3: {str(e)}")
        return None

def select_pdf_key(file_key):
    """파일명에 따라 적절한 RAG PDF 경로를 반환합니다."""
    if 'eip' in file_key.lower():
        return 'rag/eip.pdf'
    elif 'vpc' in file_key.lower():
        return 'rag/vpc.pdf'
    elif 'subnet' in file_key.lower():
        return 'rag/subnet.pdf'
    elif 'route-table' in file_key.lower():
        return 'rag/route-table.pdf'
    else:
        return 'rag/rag_full.pdf'  # 기본 파일

def save_tf_file_to_s3(bucket_name, file_key, content):
    try:
        s3.put_object(Bucket=bucket_name, Key=file_key, Body=content)
        print(f"File '{file_key}' saved to S3 bucket '{bucket_name}'")
    except Exception as e:
        print(f"Error saving file to S3: {str(e)}")

def lambda_handler(event):
    bucket_name = 'aiwa-terraform'
    user_email = event
    platform = 'aws'
    file_delay = 5  # 각 파일 처리 후 5초 지연

    print(f"Starting Lambda function with user_email: {user_email}, platform: {platform}")

    # AWS 폴더에서 각 .tf 파일 가져오기
    folder_path = f"users/{user_email}/{platform.lower()}/"
    files = list_files_in_s3(bucket_name, folder_path)

    if not files:
        print("No files found, returning 404 status.")
        return { 
            'statusCode': 404,
            'body': f'No files found for the specified user and platform: {platform}'
        }

    # 각 .tf 파일을 Bedrock 모델에 개별 요청 보내기
    for file_key in files:
        print(f"Processing file: {file_key}")
        content = get_file_content_from_s3(bucket_name, file_key)
        
        if not content:
            print(f"Skipping empty file: {file_key}")
            continue

        # 파일명에 맞는 PDF 파일 경로 선택 및 PDF 텍스트 가져오기
        pdf_key = select_pdf_key(file_key)
        pdf_text = get_text_from_pdf(bucket_name, pdf_key)
        
        if not pdf_text:
            print(f"PDF file for {file_key} could not be retrieved or is empty.")
            continue

        # Bedrock 모델 요청 payload 생성
        input_text = (
    f"Use the following context from the PDF document to accurately convert AWS Terraform code to GCP. "
    f"Make sure to keep all resource names, like 'name-vpc', exactly as they appear in the AWS code and RAG context:\n\n"
    f"{pdf_text}\n\n"
    f"Now, provide only the minimal GCP Terraform code required to replicate the configuration in this AWS file ({file_key}). "
    f"Return only the essential GCP code in a code block using this format:\n\n```hcl\n<code_here>\n```.\n\n{content}"
)


        request_payload = {
            "inputText": input_text,
            "textGenerationConfig": {
                "maxTokenCount": 3072,
                "stopSequences": [],
                "temperature": 0.3,
                "topP": 0.7
            }
        }
        
        # Bedrock 모델 호출
        try:
            print(f"Invoking model for file '{file_key}'")
            response = bedrock_client.invoke_model(
                modelId="amazon.titan-text-premier-v1:0",
                body=json.dumps(request_payload),
                contentType='application/json',
                accept='application/json'
            )
            model_response = json.loads(response['body'].read())
            print("Model Response:", model_response)
            full_response_text = model_response.get('results', [{}])[0].get('outputText', "")
            
            # ```hcl와 ``` 사이의 내용만 추출
            match = re.search(r"```hcl\n(.*?)\n```", full_response_text, re.DOTALL)
            response_text = match.group(1) if match else ""
            
            if not response_text:
                print("Warning: Extracted response text is empty")

            # GCP 폴더에 동일한 파일명으로 저장
            gcp_file_key = file_key.replace(f"{platform.lower()}", "gcp")
            save_tf_file_to_s3(bucket_name, gcp_file_key, response_text)
            print(f"Successfully processed and saved file '{file_key}'")

        except ClientError as e:
            print(f"Error: {e} - Failed for file '{file_key}'. Skipping.")

        # 각 파일 처리 후 추가 지연 시간
        print(f"Waiting {file_delay} seconds before processing the next file...")
        time.sleep(file_delay)

    print("All files processed. Lambda function execution complete.")
    
if __name__ == "__main__": 
    app.run(debug=True)

