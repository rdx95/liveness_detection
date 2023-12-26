import boto3
from botocore.exceptions import NoCredentialsError

class DigitalOceanSpacesClient:
    def __init__(self, access_key, secret_key, space_name, space_region):
        self.access_key = access_key
        self.secret_key = secret_key
        self.space_name = space_name
        self.space_region = space_region
        session = boto3.session.Session() # type: ignore
        self.client = session.client('s3',
                                  region_name=self.space_region,
                                  endpoint_url=f'https://{self.space_region}.digitaloceanspaces.com',
                                  aws_access_key_id=self.access_key,
                                  aws_secret_access_key=self.secret_key)

    def upload_file(self, local_file_path, remote_file_name):
        try:
            self.client.upload_file(local_file_path, self.space_name, remote_file_name)
            return True;
        except NoCredentialsError:
            print("Credentials not available. Make sure to provide valid access and secret keys.")
            return False;
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False