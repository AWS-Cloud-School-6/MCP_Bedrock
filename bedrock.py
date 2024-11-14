import json
import re
import time
from s3_utils import list_files_in_s3, get_file_content_from_s3, save_tf_file_to_s3, get_text_from_pdf
from botocore.exceptions import ClientError
import boto3

bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
bucket_name = 'aiwa-terraform'

def lambda_handler(user_email, platform):
    folder_path = f"users/{user_email}/aws"
    files = list_files_in_s3(bucket_name, folder_path)

    if not files:
        print("No files found, returning 404 status.")
        return {
            'statusCode': 404,
            'body': f'No files found for the specified user and platform: {platform}'
        }

    for file_key in files:
        content = get_file_content_from_s3(bucket_name, file_key)
        if not content:
            continue

        pdf_key = select_pdf_key(file_key)
        pdf_text = get_text_from_pdf(bucket_name, pdf_key)
        if not pdf_text:
            continue

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

        try:
            response = bedrock_client.invoke_model(
                modelId="amazon.titan-text-premier-v1:0",
                body=json.dumps(request_payload),
                contentType='application/json',
                accept='application/json'
            )
            model_response = json.loads(response['body'].read())
            full_response_text = model_response.get('results', [{}])[0].get('outputText', "")
            match = re.search(r"```hcl\n(.*?)\n```", full_response_text, re.DOTALL)
            response_text = match.group(1) if match else ""

            gcp_file_key = file_key.replace('aws', 'gcp')
            save_tf_file_to_s3(bucket_name, gcp_file_key, response_text)

        except ClientError as e:
            print(f"Error: {e} - Failed for file '{file_key}'. Skipping.")
        time.sleep(5)

def select_pdf_key(file_key):
    if 'eip' in file_key.lower():
        return 'rag/eip.pdf'
    elif 'vpc' in file_key.lower():
        return 'rag/vpc.pdf'
    elif 'subnet' in file_key.lower():
        return 'rag/subnet.pdf'
    elif 'route-table' in file_key.lower():
        return 'rag/route-table.pdf'
    else:
        return 'rag/rag_full.pdf'
