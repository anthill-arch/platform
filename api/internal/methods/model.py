from anthill.framework.utils.asynchronous import thread_pool_exec as future_exec
from ..core import as_internal, InternalAPI
from typing import Optional


def get_model_class(model_name: str):
    from anthill.framework.apps import app
    return app.get_model(model_name)


async def get_model_query(model_name: str,
                          page: int = 1,
                          page_size: int = 0,
                          in_list: Optional[list] = None,
                          identifier_name: str = 'id',
                          **filter_data):
    model = get_model_class(model_name)
    query = model.query.filter_by(**filter_data)
    if page_size:
        query = query.limit(page_size)
        if page:
            query = query.offset((page - 1) * page_size)
    if in_list:
        identifier = getattr(model, identifier_name)
        query = query.filter(identifier.in_(in_list))
    return query


async def get_model_object(model_name: str,
                           object_id: str,
                           identifier_name: str = 'id'):
    query = await get_model_query(model_name, **{identifier_name: object_id})
    return await future_exec(query.one)


def deserialize_data(model, **data):
    from anthill.framework.db import db

    if isinstance(model, str):
        model = get_model_class(model)

    model_schema = getattr(model, '__marshmallow__')
    obj = model_schema.load(data, session=db.session)
    return obj


@as_internal()
async def model_version(api: InternalAPI,
                        model_name: str,
                        object_id: str,
                        version: int,
                        identifier_name: str = 'id',
                        **options):
    obj = await get_model_object(model_name, object_id, identifier_name)
    return await future_exec(obj.versions.get, version)


@as_internal()
async def model_recover(api: InternalAPI,
                        model_name: str,
                        object_id: str,
                        version: int,
                        identifier_name: str = 'id',
                        **options) -> None:
    obj = await get_model_object(model_name, object_id, identifier_name)
    version = await future_exec(obj.versions.get, version)
    await future_exec(version.revert)


@as_internal()
async def model_history(api: InternalAPI,
                        model_name: str,
                        object_id: str,
                        identifier_name: str = 'id',
                        **options):
    obj = await get_model_object(model_name, object_id, identifier_name)
    return obj.versions


@as_internal()
async def get_model(api: InternalAPI,
                    model_name: str,
                    object_id: str,
                    identifier_name: str = 'id',
                    **options):
    obj = await get_model_object(model_name, object_id, identifier_name)
    return obj.dump()


@as_internal()
async def get_models(api: InternalAPI,
                     model_name: str,
                     filter_data: Optional[dict] = None,
                     in_list: Optional[list] = None,
                     identifier_name: str = 'id',
                     page: int = 1,
                     page_size: int = 0,
                     **options):
    model = get_model_class(model_name)
    query = await get_model_query(
        model_name=model_name,
        page=page,
        page_size=page_size,
        in_list=in_list,
        identifier_name=identifier_name,
        **(filter_data or {})
    )
    objects = await future_exec(query.all)
    return model.dump_many(objects)


@as_internal()
async def update_or_create_model(api: InternalAPI,
                                 model_name: str,
                                 data: dict,
                                 **options):
    obj = deserialize_data(model_name, **data)
    obj = await future_exec(obj.save)
    return obj.dump()


@as_internal()
async def delete_model(api: InternalAPI,
                       model_name: str,
                       object_id: str,
                       identifier_name: str = 'id',
                       **options):
    obj = await get_model_object(model_name, object_id, identifier_name)
    await future_exec(obj.delete)
