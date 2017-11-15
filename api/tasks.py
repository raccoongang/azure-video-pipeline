import time

from celery.task import task
from celery.utils.log import get_task_logger

from .media_service import MediaServicesManagementClient, PermissionsAccessPolicy, TypesLocators

LOGGER = get_task_logger(__name__)


@task()
def monitoring_job(job_id, settings_azure):
    LOGGER.info('Start monitoring_job job_id - {}'.format(job_id))
    media_services = MediaServicesManagementClient(settings_azure)

    while True:
        job = media_services.get_job(job_id)
        state = job['State']
        LOGGER.info('monitoring_job state - {}, job_id - {}'.format(state, job_id))

        if int(state) == 3:
            output_media_assets = media_services.get_output_media_assets(job_id)
            LOGGER.info('monitoring_job create locator OnDemandOrigin asset_id - {}'.format(output_media_assets['Id']))
            policy_name = u'AccessPolicy_Test'
            access_policy = media_services.create_access_policy(
                policy_name,
                duration_in_minutes=60 * 24 * 365 * 10,
                permissions=PermissionsAccessPolicy.READ
            )
            media_services.create_locator(
                access_policy['Id'],
                output_media_assets['Id'],
                type=TypesLocators.OnDemandOrigin
            )
            break

        if int(state) > 3:
            break

        time.sleep(30)
