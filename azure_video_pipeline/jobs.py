import logging

from courseware import courses
from django.db import models
from django.dispatch import receiver
from edxval.api import update_video_status
from edxval.models import Video
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from requests import RequestException

from azure_video_pipeline.media_service import MediaServiceClient
from azure_video_pipeline.utils import get_azure_config

LOGGER = logging.getLogger(__name__)


@receiver(models.signals.post_save, sender=Video)
def video_status_update_callback(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Listen to video status updates and set processing job.
    """
    # process video after it is successfully uploaded:
    if not kwargs['created']:
        LOGGER.info('Creating video encode Job on Azure...')
        video = kwargs['instance']
        if video.status == 'upload_completed':
            course_video = video.courses.first()
            course_id = course_video.course_id
            azure_config = {}
            try:
                course_key = CourseKey.from_string(course_id)
                course = courses.get_course(course_key)
                azure_config = get_azure_config(course.org)
            except (InvalidKeyError, ValueError):
                # need to update video status to 'failed' here:
                update_video_status(video.edx_video_id, 'upload_failed')
                LOGGER.exception("Couldn't recognize Organization Azure storage profile.")

            ams_api = MediaServiceClient(azure_config)
            try:
                # create AzureMS video encode Job:
                filename = video.client_video_id
                asset_name = video.edx_video_id

                asset_data = ams_api.get_asset_by_name(asset_name)

                input_asset_id = asset_data and asset_data[u'Id']
                if input_asset_id:
                    job_info = ams_api.create_job(input_asset_id, filename)
                    if u'Created' in job_info['d'].keys():
                        update_video_status(video.edx_video_id, 'transcode_active')
            except RequestException:
                LOGGER.exception("Something went wrong during AzureMS encode Job creation.")
