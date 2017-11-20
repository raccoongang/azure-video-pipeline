import mimetypes

from azure.storage import CloudStorageAccount
from courseware import courses
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_http_methods
from edxval.api import get_video_info, ValInternalError, ValVideoNotFoundError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from student.auth import user_has_role
from student.roles import CourseStaffRole

from .media_service import AccessPolicyPermissions, LocatorTypes
from .utils import get_media_service_client


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
    except (InvalidKeyError, ValueError) as exc:
        return HttpResponseBadRequest(exc.message)

    try:
        video_info = get_video_info(edx_video_id)
    except (ValVideoNotFoundError, ValInternalError) as exc:
        return HttpResponseBadRequest(exc.message)

    if not user_has_role(request.user, CourseStaffRole(course_key)):
        return HttpResponseForbidden(_("Staff only."))

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
