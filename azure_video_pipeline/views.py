import mimetypes

from azure.storage import CloudStorageAccount
from courseware import courses
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from edxval.api import get_video_info, ValVideoNotFoundError, ValInternalError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from student.auth import user_has_role
from student.roles import CourseStaffRole
from .utils import get_media_service_client
from .media_service import AccessPolicyPermissions, LocatorTypes


@login_required
@require_http_methods(["PUT"])
def upload_handler(request, course_id, edx_video_id):
    """
    View to perform media file uploads which bigger then Azure BlockBlob's single upload threshold.

    Uploads up to mentioned threshold are executed directly: browser -> storage-locator-url.
    :param request:
    :return:
    ref: https://docs.microsoft.com/en-us/rest/api/storageservices/put-blob
    """
    try:
        course_key = CourseKey.from_string(course_id)
        course = courses.get_course(course_key)
    except (InvalidKeyError, ValueError):
        raise HttpResponseBadRequest

    try:
        video_info = get_video_info(edx_video_id)
    except (ValVideoNotFoundError, ValInternalError):
        raise HttpResponseBadRequest

    if not user_has_role(request.user, CourseStaffRole(course_key)):
        raise HttpResponseForbidden

    filename = video_info['client_video_id']
    mime_type = mimetypes.guess_type(filename)[0]
    media_services = get_media_service_client(course.org)
    asset = media_services.create_asset(edx_video_id)
    media_services.create_asset_file(asset['Id'], filename, mime_type)
    access_policy = media_services.create_access_policy(
        u'AccessPolicy_{}'.format(filename.split('.')[0]),
        permissions=AccessPolicyPermissions.WRITE
    )
    media_services.create_locator(
        access_policy['Id'],
        asset['Id'],
        locator_type=LocatorTypes.SAS
    )
    storage_client = CloudStorageAccount(media_services.storage_account_name, media_services.storage_key)
    blob_service = storage_client.create_blob_service()
    container_name = 'asset-{}'.format(asset['Id'].split(':')[-1])
    blob_service.put_block_blob_from_file(container_name, filename, request)
    return JsonResponse({'status': 'ok'})
