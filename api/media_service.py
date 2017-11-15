# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import re

from msrestazure.azure_active_directory import ServicePrincipalCredentials
import requests
from requests import HTTPError


class TypesLocators(object):
    SAS = 1
    OnDemandOrigin = 2


class PermissionsAccessPolicy(object):
    NONE = 0
    READ = 1
    WRITE = 2
    DELETE = 3


class MediaServicesManagementClient(object):

    def __init__(self, settings_azure):
        """
        Create a MediaServicesManagementClient instance.

        :param settings_azure: (dict) initialization parameters
        """
        self.rest_api_endpoint = settings_azure.pop('rest_api_endpoint')
        host = re.findall('[https|http]://(\w+.+)/api/', self.rest_api_endpoint, re.M)
        self.host = host[0] if host else None
        self.credentials = ServicePrincipalCredentials(**settings_azure)

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'DataServiceVersion': '1.0',
            'MaxDataServiceVersion': '3.0',
            'Accept': 'application/json',
            'Accept-Charset': 'UTF-8',
            'x-ms-version': '2.15',
            'Host': self.host,
            'Authorization': '{} {}'.format(self.credentials.token['token_type'],
                                            self.credentials.token['access_token'])
        }

    def get_list_locators(self, type=TypesLocators.OnDemandOrigin):
        url = '{}Locators?$filter=Type eq {}'.format(self.rest_api_endpoint, type)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            locators = response.json().get('value', [])
            return locators
        else:
            response.raise_for_status()

    def get_locator_for_asset(self, asset_id, type):
        url = "{}Assets('{}')/Locators?$filter=Type eq {}".format(self.rest_api_endpoint, asset_id, type)
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            locators = response.json().get('value', [])
            return locators[0] if locators else None
        else:
            response.raise_for_status()

    def get_files_for_asset(self, asset_id):
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

    def create_access_policy(self, policy_name, duration_in_minutes=120, permissions=PermissionsAccessPolicy.NONE):
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

    def create_locator(self, access_policy_id, asset_id, type):
        url = "{}Locators".format(self.rest_api_endpoint)
        headers = self.get_headers()
        start_time = (datetime.utcnow() - timedelta(minutes=10)).replace(microsecond=0).isoformat()
        data = {
            "AccessPolicyId": access_policy_id,
            "AssetId": asset_id,
            "StartTime": start_time,
            "Type": type
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
