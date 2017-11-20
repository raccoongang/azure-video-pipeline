from django.conf import settings
from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',
    url(
        r'^videos/upload_handler/{}/(?P<edx_video_id>[\w-]+)/$'.format(settings.COURSE_ID_PATTERN),
        'azure_video_pipeline.views.upload_handler',
        name='video-upload-handler'
    ),
)
