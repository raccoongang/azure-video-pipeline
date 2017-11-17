from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(
        r'^videos/upload/(?P<asset_id>\w+)/(?P<client_video_id>\w+)/(?P<expires_in>\w+)/$',
        'azure_video_pipeline.media_service.upload_handler',
        name='video-upload-handler'
    ),
)
