from ..core import as_internal, InternalAPI
from typing import Optional


@as_internal()
def test(api: InternalAPI, **options):
    return {'method': 'test', 'service': api.service.name}


@as_internal()
def ping(api: InternalAPI, **options):
    return {'message': 'pong', 'service': api.service.name}


@as_internal()
def doc(api: InternalAPI, **options):
    return {'methods': ', '.join(api.methods)}


@as_internal()
def get_service_metadata(api: InternalAPI, **options):
    return api.service.app.metadata


@as_internal()
def reload(api: InternalAPI, **options):
    import tornado.autoreload
    # noinspection PyProtectedMember
    tornado.autoreload._reload()


@as_internal()
async def update(api: InternalAPI, version: Optional[str], **options):
    update_manager = api.service.update_manager
    await update_manager.update(version)
