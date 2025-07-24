#!/usr/bin/env python3
"""
Create a proper deployment package for the Alexa Wine Skill
Includes all Python dependencies required for AWS Lambda
"""

import os
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path

def create_deployment_package():
    """Create a deployment package with all dependencies"""
    print("Creating deployment package with dependencies...")
    
    # Files to include in the deployment package
    files_to_include = [
        'lambda_function.py',
        'config.py', 
        'utils.py',
        'wine_service.py',
        'wine_api_service.py',
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
                print(f"✓ Added {file_name}")
        
        # Install dependencies to package directory
        print("Installing Python dependencies...")
        
        # Create a requirements file without boto3/botocore (provided by Lambda)
        lambda_requirements = [
            'ask-sdk-core==1.19.0',
            'ask-sdk-model==1.82.0', 
            'python-dotenv==1.0.0',
            'requests==2.31.0'
        ]
        
        requirements_path = package_dir / 'requirements_lambda.txt'
        with open(requirements_path, 'w') as f:
            f.write('\n'.join(lambda_requirements))
        
        # Install dependencies
        result = subprocess.run([
            'pip', 'install', '-r', str(requirements_path),
            '--target', str(package_dir),
            '--no-deps'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error installing dependencies: {result.stderr}")
            return None
        
        # Install each dependency individually to handle dependencies properly
        for req in lambda_requirements:
            print(f"Installing {req}...")
            result = subprocess.run([
                'pip', 'install', req,
                '--target', str(package_dir)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Warning: Could not install {req}: {result.stderr}")
        
        # Remove unnecessary files to reduce package size
        for root, dirs, files in os.walk(package_dir):
            # Remove __pycache__ directories
            if '__pycache__' in dirs:
                shutil.rmtree(os.path.join(root, '__pycache__'))
                dirs.remove('__pycache__')
            
            # Remove .pyc files
            for file in files[:]:
                if file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))
                    files.remove(file)
        
        # Create zip file
        zip_path = 'alexa-wine-skill-python-with-deps.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
                    
        print(f"✓ Created deployment package: {zip_path}")
        
        # Get package size
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"Package size: {size_mb:.2f} MB")
        
        return zip_path

if __name__ == '__main__':
    zip_path = create_deployment_package()
    if zip_path:
        print(f"\nDeployment package ready: {zip_path}")
        print("You can now update the Lambda function with:")
        print(f"aws lambda update-function-code --function-name alexa-wine-skill-python-dev-alexaSkill --zip-file fileb://{zip_path} --region us-east-1")
    else:
        print("Failed to create deployment package")
