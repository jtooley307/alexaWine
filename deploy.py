#!/usr/bin/env python3
"""
Simple deployment script for Alexa Wine Skill Python implementation
Creates a deployment package and uploads to AWS Lambda
"""

import os
import sys
import zipfile
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    # Fallback if python-dotenv is not installed locally; no-op
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

def create_deployment_package():
    """Create a deployment package for AWS Lambda"""
    print("Creating deployment package...")
    
    # Load env early to control optional deps and file inclusion
    load_dotenv()
    use_opensearch = (os.getenv('USE_OPENSEARCH', 'false').lower() == 'true')
    use_vector = (os.getenv('USE_VECTOR_SEARCH', 'false').lower() == 'true')

    # Files to include in the deployment package
    files_to_include = [
        'lambda_function.py',
        'config.py', 
        'utils.py',
        'card_utils.py',
        'apl_utils.py',
        'wine_service.py',
        'wine_api_service.py',
        'wine_dynamodb_service.py',
        'wineDatabase.json',
        '.env'
    ]
    # Include OpenSearch helper only if enabled
    if use_opensearch:
        files_to_include.append('opensearch_search.py')
    
    # Create temporary directory for package
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / 'package'
        package_dir.mkdir()
        
        # Copy source files with detailed logging
        print("\nIncluding files in deployment package:")
        for file_name in files_to_include:
            src_path = Path(file_name)
            if src_path.exists():
                dest_path = package_dir / file_name
                # Create parent directories if they don't exist
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
                print(f"✓ Added {file_name} ({src_path.absolute()})")
            else:
                print(f"✗ Missing {file_name} - This may cause runtime errors!")

        # Recursively include APL documents directory
        apl_dir = Path('apl')
        if apl_dir.exists() and apl_dir.is_dir():
            print("\nIncluding APL documents (apl/**):")
            for root, dirs, files in os.walk(apl_dir):
                for file in files:
                    src_path = Path(root) / file
                    rel = src_path.relative_to(Path('.'))
                    dest_path = package_dir / rel
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    print(f"✓ Added {rel}")
        
        # Install minimal runtime dependencies to package directory (keep ZIP small)
        print("\nInstalling minimal runtime dependencies...")
        minimal_packages = [
            'ask-sdk-core==1.19.0',
            'ask-sdk-model==1.82.0',
            'python-dotenv==1.0.0',
            'requests==2.31.0',
            # Note: boto3/botocore provided by AWS Lambda runtime; do NOT vendor
        ]
        # Only include OpenSearch client libs when explicitly enabled
        if use_opensearch or use_vector:
            minimal_packages += [
                'opensearch-py==2.5.0',
                'requests-aws4auth==1.2.3'
            ]
        for pkg in minimal_packages:
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', pkg,
                    '--target', str(package_dir),
                    '--upgrade',
                    '--no-cache-dir'
                ], check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            except subprocess.CalledProcessError as e:
                print(f"\nERROR installing dependency: {pkg}")
                if e.stdout:
                    print(f"STDOUT:\n{e.stdout}")
                if e.stderr:
                    print(f"STDERR:\n{e.stderr}")
                raise
        
        # Verify wineDatabase.json is in the package
        db_path = package_dir / 'wineDatabase.json'
        if db_path.exists():
            print(f"\nVerifying wineDatabase.json...")
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                    wine_count = len(db.get('wines', []))
                    print(f"✓ wineDatabase.json is valid and contains {wine_count} wines")
            except Exception as e:
                print(f"✗ Error reading wineDatabase.json: {str(e)}")
        else:
            print("\n✗ ERROR: wineDatabase.json is missing from the deployment package!")
        
        # Install additional required packages
        additional_packages = [
            'ask_sdk_runtime',  # Required by ask-sdk-core
            'typing_extensions'  # Required by ask-sdk-core
        ]
        
        for pkg in additional_packages:
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', pkg,
                    '--target', str(package_dir),
                    '--upgrade'
                ], check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            except subprocess.CalledProcessError as e:
                print(f"\nERROR installing dependency: {pkg}")
                if e.stdout:
                    print(f"STDOUT:\n{e.stdout}")
                if e.stderr:
                    print(f"STDERR:\n{e.stderr}")
                raise
        
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

def wait_for_lambda_update(function_name: str, region: str, timeout_sec: int = 120):
    """Poll Lambda LastUpdateStatus until Successful/Failed or timeout."""
    import time
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            r = subprocess.run([
                'aws','lambda','get-function-configuration',
                '--function-name', function_name,
                '--region', region,
                '--query','LastUpdateStatus','--output','text'
            ], capture_output=True, text=True, check=True)
            status = (r.stdout or '').strip()
            print(f"LastUpdateStatus={status}")
            if status in ('Successful','Failed'):
                return status
        except subprocess.CalledProcessError:
            pass
        time.sleep(3)
    raise RuntimeError('Timed out waiting for Lambda update to finish')

def get_aws_account_id():
    """Get the AWS account ID"""
    try:
        sts_result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
            capture_output=True, text=True, check=True
        )
        return sts_result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting AWS account ID: {e}")
        print("Please make sure you have AWS credentials configured and have run 'aws configure'")
        raise

def deploy_to_lambda(zip_path, function_name=None, region=None):
    """Deploy the package to AWS Lambda"""
    # Load .env so os.getenv picks up local config
    load_dotenv()
    # Resolve region from environment or default
    region = region or os.getenv('AWS_REGION', 'us-west-2')
    # Resolve function name; allow override via env var
    function_name = function_name or os.getenv('LAMBDA_FUNCTION_NAME') or 'alexa-wine-skill-python-dev-alexaSkill'
    print(f"\nDeploying to Lambda function: {function_name} (region: {region})")
    
    # Get AWS account ID
    account_id = get_aws_account_id()
    if not account_id:
        print("Failed to get AWS account ID. Make sure you have AWS credentials configured.")
        return
    
    # Role ARN (allow override via env var)
    default_role = f"arn:aws:iam::{account_id}:role/service-role/alexaWine-dev-us-east-1-lambdaRole"
    role_arn = os.getenv('LAMBDA_ROLE_ARN', default_role)
    print(f"Using IAM role: {role_arn}")
    
    # Prepare env file path early to avoid reference before assignment
    env_file = Path('env_vars.json')
    
    # Check if function exists
    function_exists = False
    try:
        subprocess.run(
            ['aws', 'lambda', 'get-function', '--function-name', function_name, '--region', region],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        function_exists = True
        print(f"Updating existing function: {function_name}")
    except subprocess.CalledProcessError:
        print(f"Creating new function: {function_name}")
    
    # Deploy the function
    try:
        if function_exists:
            # Update function code
            update_cmd = [
                'aws', 'lambda', 'update-function-code',
                '--function-name', function_name,
                '--zip-file', f'fileb://{zip_path}',
                '--region', region,
                '--publish'  # Publish a new version
            ]
            result = subprocess.run(update_cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            
            # Wait for code update to finish to avoid ResourceConflict on config
            wait_for_lambda_update(function_name, region)

            # Update function configuration (preserve existing environment variables)
            # 1) Fetch existing env
            get_env_cmd = [
                'aws', 'lambda', 'get-function-configuration',
                '--function-name', function_name,
                '--region', region,
                '--query', 'Environment.Variables', '--output', 'json'
            ]
            existing_env = {}
            try:
                r = subprocess.run(get_env_cmd, check=True, capture_output=True, text=True)
                existing_env = json.loads(r.stdout or '{}') or {}
            except subprocess.CalledProcessError:
                existing_env = {}

            # 2) Merge overrides from local environment (do not drop existing keys)
            overrides = {
                # Avoid reserved keys (AWS_*, LAMBDA_*)
                'PYTHONPATH': existing_env.get('PYTHONPATH', ''),
            }
            # Pass-through commonly used variables if present
            for key in [
                # General (do NOT include AWS_REGION to avoid reserved keys)
                'LOG_LEVEL', 'ALEXA_SKILL_ID',
                # DynamoDB
                'USE_DYNAMODB', 'DYNAMODB_TABLE_PREFIX',
                # Wine API
                'WINE_API_BASE_URL',
                # OpenSearch flags
                'USE_OPENSEARCH', 'USE_VECTOR_SEARCH', 'USE_HYBRID_SEARCH',
                'OPENSEARCH_ENDPOINT', 'OPENSEARCH_REGION', 'OPENSEARCH_INDEX', 'OPENSEARCH_USE_IAM',
                # Embeddings (Bedrock for prod)
                'EMBED_PROVIDER', 'EMBED_DIM', 'BEDROCK_REGION', 'BEDROCK_EMBEDDING_MODEL_ID',
                # Bedrock NLG
                'USE_BEDROCK_NLG', 'BEDROCK_TEXT_MODEL_ID',
                # Visual assets
                'CARD_LOGO_URL'
            ]:
                val = os.getenv(key)
                if val is not None:
                    overrides[key] = val

            # Filter out any accidental reserved keys
            reserved_prefixes = ('AWS_', 'LAMBDA_')
            merged_env = existing_env.copy()
            merged_env.update({k: v for k, v in overrides.items() if not k.startswith(reserved_prefixes)})

            env_vars = {'Variables': merged_env}
            with open(env_file, 'w') as f:
                json.dump(env_vars, f)

            config_cmd = [
                'aws', 'lambda', 'update-function-configuration',
                '--function-name', function_name,
                '--runtime', 'python3.11',
                '--handler', 'lambda_function.lambda_handler',
                '--timeout', '30',
                '--memory-size', '256',
                '--region', region,
                '--environment', f'file://{env_file.absolute()}'
            ]
            result = subprocess.run(config_cmd, check=True, capture_output=True, text=True)
            print("Updated function configuration (env preserved and merged):")
            print(result.stdout)
        else:
            # Create new function
            # Create environment variables JSON file if not exists
            if not env_file.exists():
                env_vars = {
                    'Variables': {
                        'LAMBDA_TASK_ROOT': '.',
                        'PYTHONPATH': ''
                    }
                }
                with open(env_file, 'w') as f:
                    json.dump(env_vars, f)
                    
            create_cmd = [
                'aws', 'lambda', 'create-function',
                '--function-name', function_name,
                '--runtime', 'python3.11',
                '--role', role_arn,
                '--handler', 'lambda_function.lambda_handler',
                '--zip-file', f'fileb://{zip_path}',
                '--region', region,
                '--timeout', '30',
                '--memory-size', '256',
                '--environment', f'file://{env_file.absolute()}'
            ]
            result = subprocess.run(create_cmd, check=True, capture_output=True, text=True)
            print("Created new function:")
            print(result.stdout)
        
        # Add permission for Alexa to invoke the function
        try:
            print("\nAdding permission for Alexa to invoke the function...")
            permission_cmd = [
                'aws', 'lambda', 'add-permission',
                '--function-name', function_name,
                '--statement-id', 'alexa-skills-kit-trigger',
                '--action', 'lambda:InvokeFunction',
                '--principal', 'alexa-appkit.amazon.com',
                '--region', region
            ]
            result = subprocess.run(permission_cmd, check=True, capture_output=True, text=True)
            print("Alexa permission added:")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Note: Could not add Alexa permission (may already exist): {e.stderr}")
        
        print("\nDeployment successful!")
        print(f"Function ARN: arn:aws:lambda:{region}:{account_id}:function:{function_name}")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError deploying Lambda function:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    
    return True

if __name__ == '__main__':
    # Create deployment package
    zip_path = create_deployment_package()
    
    # Deploy to Lambda
    deploy_to_lambda(zip_path)
    
    print("Done!")
