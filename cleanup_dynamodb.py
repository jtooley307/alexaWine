import boto3
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
dynamodb = boto3.client('dynamodb', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)

def delete_tables():
    """Delete all DynamoDB tables with the specified prefix."""
    try:
        # List all tables
        response = dynamodb.list_tables()
        
        # Filter tables by prefix
        table_names = [name for name in response['TableNames'] if name.startswith(TABLE_PREFIX)]
        
        if not table_names:
            print("No tables found with the specified prefix.")
            return
        
        # Delete each table
        for table_name in table_names:
            try:
                print(f"Deleting table: {table_name}")
                dynamodb.delete_table(TableName=table_name)
                
                # Wait for the table to be deleted
                waiter = dynamodb.get_waiter('table_not_exists')
                waiter.wait(TableName=table_name)
                print(f"Table {table_name} deleted successfully.")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print(f"Table {table_name} does not exist.")
                else:
                    print(f"Error deleting table {table_name}: {e}")
                    raise
    
    except ClientError as e:
        print(f"Error listing/deleting tables: {e}")
        raise

def detach_policy_from_role(policy_arn):
    """Detach a policy from a role."""
    try:
        iam.detach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn=policy_arn
        )
        print(f"Detached policy {policy_arn} from role {ROLE_NAME}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"Policy {policy_arn} is not attached to role {ROLE_NAME}")
        else:
            print(f"Error detaching policy {policy_arn}: {e}")
            raise

def delete_iam_resources():
    """Delete IAM role and policy."""
    # Get the policy ARN
    policy_arn = None
    try:
        response = iam.list_policies(Scope='Local')
        for policy in response['Policies']:
            if policy['PolicyName'] == POLICY_NAME:
                policy_arn = policy['Arn']
                break
    except ClientError as e:
        print(f"Error listing policies: {e}")
        return
    
    # Detach policy from role if it exists
    if policy_arn:
        # First, detach the policy from the role
        try:
            detach_policy_from_role(policy_arn)
            
            # Delete the policy
            iam.delete_policy(PolicyArn=policy_arn)
            print(f"Deleted policy: {policy_arn}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                print(f"Policy {POLICY_NAME} does not exist.")
            else:
                print(f"Error deleting policy {POLICY_NAME}: {e}")
    
    # Delete the IAM role
    try:
        # First, detach any remaining policies
        try:
            response = iam.list_attached_role_policies(RoleName=ROLE_NAME)
            for policy in response['AttachedPolicies']:
                iam.detach_role_policy(
                    RoleName=ROLE_NAME,
                    PolicyArn=policy['PolicyArn']
                )
                print(f"Detached policy {policy['PolicyName']} from role {ROLE_NAME}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                print(f"Error detaching policies from role {ROLE_NAME}: {e}")
                return
        
        # Delete the role
        iam.delete_role(RoleName=ROLE_NAME)
        print(f"Deleted IAM role: {ROLE_NAME}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"Role {ROLE_NAME} does not exist.")
        else:
            print(f"Error deleting role {ROLE_NAME}: {e}")

def main():
    try:
        print("Starting cleanup of DynamoDB and IAM resources...")
        
        # Delete DynamoDB tables
        print("\nDeleting DynamoDB tables...")
        delete_tables()
        
        # Delete IAM resources
        print("\nDeleting IAM resources...")
        delete_iam_resources()
        
        print("\nCleanup complete!")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        raise

if __name__ == "__main__":
    main()
