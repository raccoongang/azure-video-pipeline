# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import mimetypes
import re
from azure.storage.blob.blockblobservice import BlockBlobService
from django.core.urlresolvers import reverse

from msrestazure.azure_active_directory import ServicePrincipalCredentials
import requests
from requests import HTTPError

from azure_video_pipeline.utils import get_media_service_client
from .blobs_service import BlobServiceClient


class LocatorTypes(object):
    SAS = 1
    OnDemandOrigin = 2


class AccessPolicyPermissions(object):
    NONE = 0
    READ = 1
    WRITE = 2
    DELETE = 3


class MediaServiceClient(object):
    """
    Client to consume Azure Media service API.
    """
    RESOURCE = 'https://rest.media.azure.net'

    def __init__(self, azure_config):
        """
        Create a MediaServiceClient instance.

        :param azure_config: (dict) initialization parameters
        """
        self.rest_api_endpoint = azure_config.pop('rest_api_endpoint')
        self.storage_account_name = azure_config.pop('storage_account_name')
        self.storage_key = azure_config.pop('storage_key')
        host = re.findall('[https|http]://(\w+.+)/api/', self.rest_api_endpoint, re.M)
        self.host = host[0] if host else None
        self.credentials = ServicePrincipalCredentials(resource=self.RESOURCE, **azure_config)
        self.asset = {}
        self.client_video_id = ''

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'DataServiceVersion': '1.0',
            'MaxDataServiceVersion': '3.0',
            'Accept': 'application/json',
            'Accept-Charset': 'UTF-8',
            'x-ms-version': '2.15',
            'Host': self.host,
            'Authorization': '{} {}'.format(
                self.credentials.token['token_type'],
                self.credentials.token['access_token']
            )
        }

    def set_metadata(self, metadata_name, value):
        setattr(self, metadata_name, value)

    def generate_url(self, expires_in, *args, **kwargs):
        """
        Guide all Azure uploads to handler.

        :param asset_id:
        :param blob_name:
        :param expires_in:
        :return:
        """
        return reverse('video-upload-handler', kwargs={
            'asset_id': self.asset,
            'client_video_id': self.client_video_id,
            'expires_in': expires_in
        })

    def get_locators_list(self, locator_type=LocatorTypes.OnDemandOrigin):
        url = '{}Locators?$filter=Type eq {}'.format(self.rest_api_endpoint, locator_type)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            locators = response.json().get('value', [])
            return locators
        else:
            response.raise_for_status()

    def get_asset_locator(self, asset_id, type):
        url = "{}Assets('{}')/Locators?$filter=Type eq {}".format(self.rest_api_endpoint, asset_id, type)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            locators = response.json().get('value', [])
            return locators[0] if locators else None
        else:
            response.raise_for_status()

    def get_asset_files(self, asset_id):
        url = "{}Assets('{}')/Files".format(self.rest_api_endpoint, asset_id)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files = response.json().get('value', [])
            return files
        else:
            response.raise_for_status()

    def create_asset(self, asset_name):
        url = "{}Assets".format(self.rest_api_endpoint)
        headers = self.get_headers()
        data = {'Name': asset_name}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            response.raise_for_status()

    def create_asset_file(self, asset_id, file_name, mime_type):
        url = "{}Files".format(self.rest_api_endpoint)
        headers = self.get_headers()
        data = {
            "IsEncrypted": "false",
            "IsPrimary": "false",
            "MimeType": mime_type,
            "Name": file_name,
            "ParentAssetId": asset_id
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            response.raise_for_status()

    def create_access_policy(self, policy_name, duration_in_minutes=120, permissions=AccessPolicyPermissions.NONE):
        url = "{}AccessPolicies".format(self.rest_api_endpoint)
        headers = self.get_headers()
        data = {
            "Name": policy_name,
            "DurationInMinutes": duration_in_minutes,
            "Permissions": permissions
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            response.raise_for_status()

    def create_locator(self, access_policy_id, asset_id, locator_type):
        url = "{}Locators".format(self.rest_api_endpoint)
        headers = self.get_headers()
        start_time = (datetime.utcnow() - timedelta(minutes=10)).replace(microsecond=0).isoformat()
        data = {
            "AccessPolicyId": access_policy_id,
            "AssetId": asset_id,
            "StartTime": start_time,
            "Type": locator_type
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            response.raise_for_status()

    def get_media_processor(self, name='Media Encoder Standard'):
        url = "{}MediaProcessors()?$filter=Name eq '{}'".format(self.rest_api_endpoint, name)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            try:
                media_processor = response.json().get('value', [])[0]
            except IndexError:
                http_error_msg = '%s Response: %s for url: %s' % (response.status_code, response.json(), response.url)
                raise HTTPError(http_error_msg)
            return media_processor
        else:
            response.raise_for_status()

    def create_job(self, asset_id, media_processor_id, filename):
        url_asset = "{}Assets('{}')".format(self.rest_api_endpoint, asset_id)
        asset_name = '{} - Media Encoder'.format(filename)
        url = "{}Jobs".format(self.rest_api_endpoint)
        headers = self.get_headers()
        headers.update({
            "Accept": "application/json;odata=verbose"
        })
        data = {
            "Name": "JobAssets-{}".format(asset_id),
            "InputMediaAssets": [
                {
                    "__metadata": {
                        "uri": url_asset
                    }
                }
            ],
            "Tasks": [
                {
                    "Configuration": "Adaptive Streaming",
                    "MediaProcessorId": media_processor_id,
                    "TaskBody": "<?xml version=\"1.0\" encoding=\"utf-8\"?><taskBody><inputAsset>JobInputAsset(0)"
                                "</inputAsset><outputAsset assetName=\"{}\">JobOutputAsset(0)</outputAsset></taskBody>"
                        .format(asset_name)
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            response.raise_for_status()

    def get_job(self, job_id):
        url = "{}Jobs('{}')".format(self.rest_api_endpoint, job_id)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            job = response.json()
            return job
        else:
            response.raise_for_status()

    def get_output_media_assets(self, job_id):
        url = "{}Jobs('{}')/OutputMediaAssets".format(self.rest_api_endpoint, job_id)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            asset = response.json().get('value', [])[0]
            return asset
        else:
            response.raise_for_status()


def upload_handler(request, asset_id, client_video_id, expires_in):
    """
    View to perform media file uploads which bigger then Azure BlockBlob's single upload threshold.

    Uploads up to mentioned threshold are executed directly: browser -> storage-locator-url.
    :param request:
    :return:
    ref: https://docs.microsoft.com/en-us/rest/api/storageservices/put-blob
    """

    # get_current_organization? via kwarg?
    media_service = get_media_service_client(organization)

    mime_type = mimetypes.guess_type(media_service.client_video_id)[0]
    media_service.create_asset_file(asset_id, client_video_id, mime_type)
    access_policy = media_service.create_access_policy(
        u'AccessPolicy_{}'.format(client_video_id.split('.')[0]),
        permissions=AccessPolicyPermissions.WRITE
    )
    media_service.create_locator(
        access_policy['Id'],
        asset_id,
        locator_type=LocatorTypes.SAS
    )

    blob_service = BlobServiceClient(media_service.storage_account_name, media_service.storage_key)
    upload_url = blob_service.generate_url(
        asset_id=asset_id,
        blob_name=client_video_id,
        expires_in=expires_in
    )


    # custom proxy fileUploadHandler
    # https://docs.djangoproject.com/en/1.8/topics/http/file-uploads/#upload-handlers

    # if uploaded file's size < BlockBlobService.MAX_SINGLE_PUT_SIZE:
    # make PUT_BLOB request (https://docs.microsoft.com/en-us/rest/api/storageservices/put-blob)
    # else:
    # make sequence of PUT_BLOCK's (https://docs.microsoft.com/en-us/rest/api/storageservices/put-block),
    # collect block IDs,
    # finally: commit PUT_BLOCK_LIST with block IDs to commit.

