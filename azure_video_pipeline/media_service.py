# -*- coding: utf-8 -*-
import logging
import mimetypes
from datetime import datetime, timedelta

import re
import requests
from msrestazure.azure_active_directory import ServicePrincipalCredentials
from requests import HTTPError

from .blobs_service import BlobServiceClient

LOGGER = logging.getLogger(__name__)


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
        mime_type = mimetypes.guess_type(self.client_video_id)[0]
        self.create_asset_file(self.asset['Id'], self.client_video_id, mime_type)
        access_policy = self.create_access_policy(
            u'AccessPolicy_{}'.format(self.client_video_id.split('.')[0]),
            permissions=AccessPolicyPermissions.WRITE
        )
        self.create_locator(
            access_policy['Id'],
            self.asset['Id'],
            locator_type=LocatorTypes.SAS
        )

        blob_service = BlobServiceClient(self.storage_account_name, self.storage_key)
        sas_url = blob_service.generate_url(
            asset_id=self.asset['Id'],
            blob_name=self.client_video_id,
            expires_in=expires_in
        )
        return sas_url

    def get_locators_list(self, locator_type=LocatorTypes.OnDemandOrigin):
        url = '{}Locators?$filter=Type eq {}'.format(self.rest_api_endpoint, locator_type)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            locators = response.json().get('value', [])
            return locators
        else:
            response.raise_for_status()

    def get_asset_locator(self, input_asset_id, type):
        url = "{}Assets('{}')/Locators?$filter=Type eq {}".format(self.rest_api_endpoint, input_asset_id, type)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            locators = response.json().get('value', [])
            return locators[0] if locators else None
        else:
            response.raise_for_status()

    def get_asset_files(self, input_asset_id):
        url = "{}Assets('{}')/Files".format(self.rest_api_endpoint, input_asset_id)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files = response.json().get('value', [])
            return files
        else:
            response.raise_for_status()

    def get_asset_by_name(self, asset_name):
        url = "{}Assets".format(self.rest_api_endpoint)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            assets = response.json().get('value', [])
            wanted_asset = filter(lambda a: a['Name'] == asset_name, assets)
            return wanted_asset and wanted_asset[0]
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

    def create_asset_file(self, input_asset_id, file_name, mime_type):
        url = "{}Files".format(self.rest_api_endpoint)
        headers = self.get_headers()
        data = {
            "IsEncrypted": "false",
            "IsPrimary": "false",
            "MimeType": mime_type,
            "Name": file_name,
            "ParentAssetId": input_asset_id
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

    def create_locator(self, access_policy_id, input_asset_id, locator_type):
        url = "{}Locators".format(self.rest_api_endpoint)
        headers = self.get_headers()
        start_time = (datetime.utcnow() - timedelta(minutes=10)).replace(microsecond=0).isoformat()
        data = {
            "AccessPolicyId": access_policy_id,
            "AssetId": input_asset_id,
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

    def create_job(self, input_asset_id, filename, media_processor_id=None):
        """
        Create encode Job on Azure Media Service for input Asset video.

        :param input_asset_id:  AzureMS Asset ID which contains encode target video.
        :param filename: file name to be encoded
        :param media_processor_id: ID of encode processor (defaults to Standard
        ref: https://docs.microsoft.com/en-us/azure/media-services/media-services-encode-asset
        """
        media_processor_name = '-'
        if media_processor_id is None:
            media_processor_props = self.get_media_processor()
            media_processor_id = media_processor_props[u'Id']
            media_processor_name = media_processor_props[u'Name']

        input_asset_url = "{}Assets('{}')".format(self.rest_api_endpoint, input_asset_id)
        output_asset_name = '{} - {} - {}'.format(media_processor_name, input_asset_id, filename)

        url = "{}Jobs".format(self.rest_api_endpoint)
        headers = self.get_headers()
        headers.update({
            "Accept": "application/json;odata=verbose"
        })
        job_config_data = {
            "Name": "AssetEncodeJob:{}".format(input_asset_id),
            "InputMediaAssets": [
                {
                    "__metadata": {
                        "uri": input_asset_url
                    }
                }
            ],
            "Tasks": [
                {
                    "Configuration": "Adaptive Streaming",
                    "MediaProcessorId": media_processor_id,
                    "TaskBody":
                        "<?xml version=\"1.0\" encoding=\"utf-8\"?><taskBody><inputAsset>JobInputAsset(0)"
                        "</inputAsset><outputAsset assetName=\"{}\">JobOutputAsset(0)</outputAsset></taskBody>"
                        .format(output_asset_name)
                }
            ]
        }

        response = requests.post(url, headers=headers, json=job_config_data)
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
