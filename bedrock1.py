# bedrock1.py
import json
import re
import time
from s3_utils import list_files_in_s3, get_file_content_from_s3, save_tf_file_to_s3, get_text_from_pdf
from botocore.exceptions import ClientError
import boto3
from flask.cli import load_dotenv
import os 

load_dotenv()
bedrock_client = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name='ap-northeast-2',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)
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

        # pdf_key = select_pdf_key(file_key)
        # pdf_text = get_text_from_pdf(bucket_name, file_key)
        # if not pdf_text:
        #     continue

        input= (
            f"Provide only the minimal GCP Terraform code required to replicate the configuration in this AWS file ({file_key}). "
            f"Return only the essential GCP code in a code block using this format:\n\n```hcl\n<code_here>\n```.\n\n{content}"
        )

        # request_payload = {
        #     "inputText": input_text,
        #     "textGenerationConfig": {
        #         "maxTokenCount": 3072,
        #         "stopSequences": [],
        #         "temperature": 0.3,
        #         "topP": 0.7
        #     }
        # }

        try:
            response = bedrock_client.retrieve_and_generate(
                input = {
                    'text' : input,
                },
                retrieveAndGenerateConfiguration = {
                    'knowledgeBaseConfiguration':{
                        'knowledgeBaseId': 'WR0HLFPBYD',
                        'modelArn': 'arn:aws:bedrock:ap-northeast-2:055937727491:inference-profile/apac.anthropic.claude-3-sonnet-20240229-v1:0'
                    },
                    'type':'KNOWLEDGE_BASE'
                }
            )
            model_response = response["output"]["text"]
            # full_response_text = model_response.get('results', [{}])[0].get('outputText', "")
            match = re.search(r"```hcl\n(.*?)\n```", model_response, re.DOTALL)
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
