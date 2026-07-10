
import boto3
from botocore.exceptions import NoCredentialsError

# 1. Configure your MinIO credentials and endpoint
MINIO_ENDPOINT = "http://localhost:9000"  # Replace with your MinIO server port
ACCESS_KEY = "admin"      # Your MinIO Root User/Access Key
SECRET_KEY = "password123"      # Your MinIO Root Password/Secret Key
BUCKET_NAME = "mys3bucket"          # The bucket you already created

# 2. Initialize the boto3 S3 client pointing to MinIO
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    # MinIO doesn't strictly require a region, but boto3 expects one
    region_name='us-east-1' 
)

# 3. Test the connection by uploading a sample file
try:

    for bucket in s3_client.list_buckets():
        print(bucket)
        print(bucket)  # The name of the bucket.
        print(bucket)

        


    #for bucket in s3_client.list_buckets()['Buckets']:   
    #    for key,value in bucket.items():
    #        print(key,value)
    
    """
    # Create a dummy local file to upload
    with open("test.txt", "w") as f:
        f.write("Hello MinIO from Boto3!")

    print(f"Uploading 'test.txt' to bucket '{BUCKET_NAME}'...")
    
    s3_client.upload_file(
        Filename="test.txt", 
        Bucket=BUCKET_NAME, 
        Key="uploaded_test.txt"  # The name the file will have in MinIO
    )
    
    print("Upload successful!")
    """
except Exception as e:
    print(f"An error occurred: {e}")

