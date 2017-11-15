from django.db import models
from django.utils.translation import ugettext_lazy as _

from organizations.models import Organization


class AzureOrgProfile(models.Model):
    """
    Azure services API-related extensions for Organization.
    """
    organization = models.OneToOneField(Organization)
    client_id = models.CharField(
        max_length=255,
        help_text=_('The client ID of the Azure AD application')
    )
    client_secret = models.CharField(
        max_length=255,
        help_text=_('The client key of the Azure AD application')
    )
    tenant = models.CharField(
        max_length=255,
        help_text=_('The Azure AD tenant domain where the Azure AD application resides')
    )
    rest_api_endpoint = models.URLField(
        max_length=255,
        help_text=_('The REST API endpoint of the Azure Media service account')
    )
    storage_account_name = models.CharField(
        max_length=255,
        help_text=_('Azure Blobs service storage account name')
    )
    storage_key = models.CharField(
        max_length=255,
        help_text=_('Azure Blobs service storage account key')
    )
