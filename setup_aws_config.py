import os
import configparser
from pathlib import Path

def setup_aws_credentials():
    """Guide the user through setting up AWS credentials."""
    print("AWS Credentials Setup")
    print("=" * 40)
    print("\nThis script will help you set up your AWS credentials.")
    print("You'll need your AWS Access Key ID and Secret Access Key.")
    print("If you don't have these, get them from the AWS IAM console.\n")
    
    # Get AWS credentials from user
    aws_access_key_id = input("Enter your AWS Access Key ID: ").strip()
    aws_secret_access_key = input("Enter your AWS Secret Access Key: ").strip()
    aws_region = input("Enter your preferred AWS region [us-west-2]: ").strip() or "us-west-2"
    
    # Create AWS directory if it doesn't exist
    aws_dir = Path.home() / ".aws"
    aws_dir.mkdir(exist_ok=True, mode=0o700)
    
    # Create or update credentials file
    config = configparser.ConfigParser()
    credentials_path = aws_dir / "credentials"
    
    if credentials_path.exists():
        config.read(credentials_path)
    
    if 'default' not in config:
        config['default'] = {}
    
    config['default']['aws_access_key_id'] = aws_access_key_id
    config['default']['aws_secret_access_key'] = aws_secret_access_key
    
    with open(credentials_path, 'w') as f:
        config.write(f)
    
    # Set secure permissions
    credentials_path.chmod(0o600)
    
    # Create or update config file
    config = configparser.ConfigParser()
    config_path = aws_dir / "config"
    
    if config_path.exists():
        config.read(config_path)
    
    if 'default' not in config:
        config['default'] = {}
    
    config['default']['region'] = aws_region
    config['default']['output'] = 'json'
    
    with open(config_path, 'w') as f:
        config.write(f)
    
    # Set secure permissions
    config_path.chmod(0o600)
    
    print("\nAWS credentials have been configured successfully!")
    print(f"Credentials file: {credentials_path}")
    print(f"Config file: {config_path}")
    print("\nYou can now run the DynamoDB setup script.")

if __name__ == "__main__":
    setup_aws_credentials()
