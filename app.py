# app.py
import os
from flask import Flask, jsonify, request
from flask.cli import load_dotenv
from terraform_executer import apply_terraform
from bedrock1 import lambda_handler

load_dotenv()
app = Flask(__name__)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


@app.route("/api/bedrock/username", methods=["POST"])
def user_name():
    if request.is_json:
        user_email = request.json.get('user_email')
        platform = request.json.get('platform')

        # Terraform 변환 및 실행
        lambda_handler(user_email, platform)
        return {
            'statusCode': 200,
            'body': f"All Terraform files for {user_email} have been processed and applied."
        }
    else:
        return jsonify({"error": "Request must be JSON"}), 400

@app.route("/api/terraform/confirm", methods=["POST"])
def apply_terraform_endpoint():
    if request.is_json:
        user_email = request.json.get('user_email')
        platform = request.json.get('platform')

        # Terraform 적용 함수 호출
        apply_terraform(user_email, platform)

        return {
            'statusCode': 200,
            'body': f"Terraform applied for {platform}."
        }
    else:
        return jsonify({"error": "Request must be JSON"}), 400

if __name__ == "__main__":
    app.run(debug=True)
