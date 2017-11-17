from azure.storage import CloudStorageAccount
from azure.storage.blob import BlobSharedAccessPermissions

from azure_video_pipeline.utils import get_shared_access_policy


class BlobServiceClient(object):

    def __init__(self, account_name, account_key):
        storage_client = CloudStorageAccount(account_name, account_key)
        self.blob_service = storage_client.create_blob_service()

    def generate_url(self, asset_id, blob_name, expires_in):
        sas_policy = get_shared_access_policy(BlobSharedAccessPermissions.WRITE, expires_in)
        container_name = 'asset-{}'.format(asset_id.split(':')[-1])
        sas_token = self.blob_service.generate_shared_access_signature(container_name, blob_name, sas_policy)
        sas_url = self.blob_service.make_blob_url(container_name, blob_name, sas_token=sas_token)
        return sas_url
