import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_aws_credentials():
    """Check if AWS credentials are properly configured."""
    print("Checking AWS credentials...")
    
    # Check environment variables
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'us-west-2')
    
    if not access_key or not secret_key:
        print("AWS credentials not found in environment variables.")
        return False
    
    print(f"AWS Region: {region}")
    print("AWS credentials found in environment variables.")
    return True

def test_dynamodb_connection():
    """Test connection to DynamoDB."""
    print("\nTesting DynamoDB connection...")
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.client('dynamodb')
        
        # List tables to test the connection
        response = dynamodb.list_tables(Limit=5)
        print("Successfully connected to DynamoDB!")
        
        # Print existing tables (if any)
        if 'TableNames' in response and response['TableNames']:
            print("\nExisting tables:")
            for table in response['TableNames']:
                print(f"- {table}")
        else:
            print("\nNo tables found in this region.")
            
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        print(f"\nError connecting to DynamoDB: {error_code}")
        print(f"Message: {error_message}")
        
        if error_code == 'UnrecognizedClientException':
            print("\nPossible issues:")
            print("1. Invalid AWS access key or secret key")
            print("2. Missing or incorrect AWS region")
            print("3. AWS credentials have expired")
            print("\nPlease check your AWS credentials and try again.")
        
        return False

def main():
    print("AWS Credentials Setup")
    print("=" * 40)
    
    # Check if credentials are set
    if not check_aws_credentials():
        print("\nPlease set your AWS credentials in the .env file:")
        print("AWS_ACCESS_KEY_ID=your_access_key")
        print("AWS_SECRET_ACCESS_KEY=your_secret_key")
        print("AWS_REGION=us-west-2")
        return
    
    # Test DynamoDB connection
    if test_dynamodb_connection():
        print("\nAWS credentials are properly configured!")
    else:
        print("\nFailed to connect to DynamoDB. Please check your credentials and try again.")

if __name__ == "__main__":
    main()
