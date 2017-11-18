from django.core.urlresolvers import reverse


class BlobServiceClient(object):

    def __init__(self):
        self.edx_video_id = ''
        self.course_key = ''

    def set_metadata(self, metadata_name, value):
        setattr(self, metadata_name, value)

    def generate_url(self, *args, **kwargs):
        """
        Guide all Azure uploads to handler.
        """
        return reverse('video-upload-handler', kwargs={
            'course_id': self.course_key,
            'edx_video_id': self.edx_video_id
        })
