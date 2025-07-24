#!/usr/bin/env python3
"""
Simple deployment script for Alexa Wine Skill Python implementation
Creates a deployment package and uploads to AWS Lambda
"""

import os
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path

def create_deployment_package():
    """Create a deployment package for AWS Lambda"""
    print("Creating deployment package...")
    
    # Files to include in the deployment package
    files_to_include = [
        'lambda_function.py',
        'config.py', 
        'utils.py',
        'wine_service.py',
        'wineDatabase.json',
        '.env'
    ]
    
    # Create temporary directory for package
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / 'package'
        package_dir.mkdir()
        
        # Copy source files
        for file_name in files_to_include:
            if os.path.exists(file_name):
                shutil.copy2(file_name, package_dir)
                print(f"Added {file_name}")
        
        # Install dependencies to package directory
        print("Installing dependencies...")
        subprocess.run([
            'pip', 'install', '-r', 'requirements.txt', 
            '--target', str(package_dir),
            '--no-deps'  # Skip boto3/botocore since they're provided by Lambda
        ], check=True)
        
        # Create zip file
        zip_path = 'alexa-wine-skill-python.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
                    
        print(f"Created deployment package: {zip_path}")
        return zip_path

def deploy_to_lambda(zip_path, function_name='alexa-wine-skill-python'):
    """Deploy the package to AWS Lambda"""
    print(f"Deploying to Lambda function: {function_name}")
    
    try:
        # Check if function exists
        result = subprocess.run([
            'aws', 'lambda', 'get-function',
            '--function-name', function_name
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Update existing function
            print("Updating existing function...")
            subprocess.run([
                'aws', 'lambda', 'update-function-code',
                '--function-name', function_name,
                '--zip-file', f'fileb://{zip_path}'
            ], check=True)
        else:
            # Create new function
            print("Creating new function...")
            subprocess.run([
                'aws', 'lambda', 'create-function',
                '--function-name', function_name,
                '--runtime', 'python3.11',
                '--role', 'arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role',
                '--handler', 'lambda_function.lambda_handler',
                '--zip-file', f'fileb://{zip_path}',
                '--timeout', '30',
                '--memory-size', '256'
            ], check=True)
            
        print("Deployment successful!")
        
    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    # Create deployment package
    zip_path = create_deployment_package()
    
    # Deploy to Lambda
    deploy_to_lambda(zip_path)
    
    print("Done!")
