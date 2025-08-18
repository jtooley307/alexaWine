import boto3
import json
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
REGION = os.getenv('AWS_REGION', 'us-west-2')
TABLE_PREFIX = os.getenv('DYNAMODB_TABLE_PREFIX', 'wine_skill_')
POLICY_NAME = f"{TABLE_PREFIX}dynamodb_policy"
ROLE_NAME = f"{TABLE_PREFIX}lambda_role"

# Initialize AWS clients
iam = boto3.client('iam', region_name=REGION)
dynamodb = boto3.client('dynamodb', region_name=REGION)

# IAM Policy Document for DynamoDB access
POLICY_DOCUMENT = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:DescribeTable"
            ],
            "Resource": []
        }
    ]
}

# Trust relationship for Lambda service
TRUST_RELATIONSHIP = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

def get_table_arns():
    """Get ARNs of all DynamoDB tables with the specified prefix."""
    try:
        response = dynamodb.list_tables()
        table_names = [name for name in response['TableNames'] if name.startswith(TABLE_PREFIX)]
        
        # Get table ARNs
        table_arns = []
        for table_name in table_names:
            table = dynamodb.describe_table(TableName=table_name)
            table_arns.append(table['Table']['TableArn'])
        
        return table_arns
    except ClientError as e:
        print(f"Error getting table ARNs: {e}")
        return []

def create_iam_role():
    """Create IAM role for Lambda with necessary permissions."""
    try:
        # Check if role already exists
        try:
            role = iam.get_role(RoleName=ROLE_NAME)
            print(f"IAM role {ROLE_NAME} already exists.")
            return role['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            pass
        
        # Create the IAM role
        print(f"Creating IAM role: {ROLE_NAME}")
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST_RELATIONSHIP),
            Description='IAM role for Wine Skill Lambda functions to access DynamoDB',
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'AlexaWineSkill'
                },
            ]
        )
        
        # Attach basic Lambda execution policy
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Create and attach DynamoDB access policy
        table_arns = get_table_arns()
        if table_arns:
            policy_doc = POLICY_DOCUMENT.copy()
            policy_doc['Statement'][0]['Resource'] = table_arns
            
            # Create policy
            policy = iam.create_policy(
                PolicyName=POLICY_NAME,
                PolicyDocument=json.dumps(policy_doc),
                Description='Policy for accessing Wine Skill DynamoDB tables',
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'AlexaWineSkill'
                    },
                ]
            )
            
            # Attach policy to role
            iam.attach_role_policy(
                RoleName=ROLE_NAME,
                PolicyArn=policy['Policy']['Arn']
            )
            
            print(f"Created and attached policy {POLICY_NAME} to role {ROLE_NAME}")
        
        return role['Role']['Arn']
        
    except ClientError as e:
        print(f"Error creating IAM role: {e}")
        raise

def main():
    try:
        print("Setting up IAM role and permissions for Wine Skill...")
        
        # Create IAM role and get its ARN
        role_arn = create_iam_role()
        
        print("\nIAM setup complete!")
        print(f"Role ARN: {role_arn}")
        print("\nMake sure to update your Lambda function's execution role with this ARN:")
        print(f"{role_arn}")
        
    except Exception as e:
        print(f"Error setting up IAM: {e}")
        raise

if __name__ == "__main__":
    main()
