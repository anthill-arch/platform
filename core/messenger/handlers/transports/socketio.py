from anthill.framework.conf import settings
from anthill.framework.core.exceptions import ImproperlyConfigured
from anthill.framework.core.mail.asynchronous import send_mail
from anthill.framework.utils.translation import translate as _
from anthill.framework.handlers.socketio import SocketIOHandler
from anthill.platform.auth.handlers import UserHandlerMixin
from anthill.platform.core.messenger.handlers.client_watchers import MessengerClientsWatcher
from anthill.platform.core.messenger.client.exceptions import ClientError
from anthill.platform.core.messenger.moderators import ModeratedException, moderate_message
from tornado import template
from typing import Optional
import user_agents
import socketio
import logging


logger = logging.getLogger('anthill.application')


class MessengerNamespace(socketio.AsyncNamespace):
    groups = ['__messenger__']  # Global groups. Must starts with `__` for security reason
    direct_group_prefix = '__direct'  # Must starts with `__`
    client_class = None
    is_notify_on_net_status_changed = True
    secure_direct = True
    secure_groups = True
    email_on_incoming_message = True
    clients = MessengerClientsWatcher(user_limit=0)

    ONLINE = 'online'
    OFFLINE = 'offline'

    def create_client(self, user=None):
        if self.client_class is None:
            raise ImproperlyConfigured('Client class is undefined')
        return self.client_class(user=user)

    async def get_client(self, sid):
        session = await self.get_session(sid)
        return session['client']

    async def get_request_handler(self, sid):
        session = await self.get_session(sid)
        return session['request_handler']

    async def send_net_status(self, sid, status: str) -> None:
        allowed = [self.ONLINE, self.OFFLINE]
        if status not in allowed:
            raise ValueError('Status must be in %s' % allowed)
        method = getattr(self, 'on_' + status)
        await method(sid)

    async def build_direct_group_with(self, user_id: str, sid, reverse: bool = False) -> str:
        client = await self.get_client(sid)
        items = [self.direct_group_prefix]
        if reverse:
            items += [user_id, client.get_user_id()]
        else:
            items += [client.get_user_id(), user_id]
        return '.'.join(items)

    async def get_groups(self, sid) -> list:
        client = await self.get_client(sid)
        groups = self.groups or []
        groups += await client.get_groups() or []

        # For testing purposes
        if 'test' not in groups and settings.DEBUG:
            groups.append('test')

        # Personal group
        personal_group = client.create_personal_group()
        if personal_group not in groups:
            groups.append(personal_group)

        return groups

    def get_participants(self, group: str):
        return self.server.manager.get_participants(self.namespace, room=group)

    def enter_groups(self, sid, groups) -> None:
        for group in groups:
            self.enter_room(sid, group)

    def leave_groups(self, sid, groups) -> None:
        for group in groups:
            self.leave_room(sid, group)

    # noinspection PyMethodMayBeStatic
    def retrieve_group(self, data):
        group = data.get('group')
        trusted = data.get('trusted', False)
        if not trusted:
            if group.startswith('__'):  # System group
                raise ValueError('Not valid group name: %s' % group)
        return group

    async def online(self, sid, user_id):
        """Check if user online."""
        client = await self.get_client(sid)
        group = client.create_personal_group(user_id)
        return bool(next(self.get_participants(group), None))

    async def on_connect(self, sid, environ):
        request_handler = environ['tornado.handler']
        session = await self.get_session(sid)

        current_user = request_handler.current_user
        client = self.create_client(user=current_user)
        await client.authenticate()

        session['client'] = client
        session['request_handler'] = request_handler

        self.enter_groups(sid, await self.get_groups(sid))

        if self.is_notify_on_net_status_changed:
            await self.send_net_status(sid, self.ONLINE)

    async def on_disconnect(self, sid):
        if self.is_notify_on_net_status_changed:
            await self.send_net_status(sid, self.OFFLINE)
        self.leave_groups(sid, self.rooms(sid))

    async def on_message(self, sid, data):
        pass

    # Supported messages client can send

    # Client actions

    # GROUPS

    async def on_create_group(self, sid, data):
        client = await self.get_client(sid)
        personal_group = client.create_personal_group()
        group_name = data.get('name')
        group_data = data.get('data')
        content = {
            'user': {
                'id': client.get_user_id()
            }
        }
        try:
            await client.create_group(group_name, group_data)
        except ClientError as e:
            content['error'] = str(e)
            await self.emit('create_group', data=content, room=personal_group)
        else:
            for sid_ in self.get_participants(personal_group):
                self.enter_room(sid_, group_name)
            await self.emit('create_group', data=content, room=group_name)

    async def on_delete_group(self, sid, data):
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        content = {
            'user': {
                'id': client.get_user_id()
            }
        }
        try:
            await client.delete_group(group)
        except ClientError as e:
            content['error'] = str(e)
            personal_group = client.create_personal_group()
            await self.emit('delete_group', data=content, room=personal_group)
        else:
            await self.emit('delete_group', data=content, room=group)
            await self.close_room(room=group)

    async def on_update_group(self, sid, data):
        client = await self.get_client(sid)
        group = self.retrieve_group(data)

    async def on_join_group(self, sid, data):
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        personal_group = client.create_personal_group()
        content = {
            'user': {
                'id': client.get_user_id()
            }
        }
        try:
            await client.join_group(group)
        except ClientError as e:
            content['error'] = str(e)
            await self.emit('join_group', data=content, room=personal_group)
        else:
            for sid_ in self.get_participants(personal_group):
                self.enter_room(sid_, group)
            await self.emit('join_group', data=content, room=group)

    async def on_leave_group(self, sid, data):
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        personal_group = client.create_personal_group()
        content = {
            'user': {
                'id': client.get_user_id()
            }
        }
        try:
            await client.leave_group(group)
        except ClientError as e:
            content['error'] = str(e)
            await self.emit('leave_group', data=content, room=personal_group)
        else:
            for sid_ in self.get_participants(personal_group):
                self.leave_room(sid_, group)
            await self.emit('leave_group', data=content, room=group)

    # /GROUPS

    # MESSAGES

    async def send_email_on_incoming_message(self, data, group, my_client):
        participants = self.get_participants(group)
        clients = [await self.get_client(s) for s in participants]
        clients.remove(my_client)
        recipient_list = (c.user.email for c in clients)
        loader = template.Loader(settings.TEMPLATE_PATH)
        subject = _('New incoming message')
        message = loader.load("incoming_message_email.txt").generate(**data)
        html_message = loader.load("incoming_message_email.html").generate(**data)
        from_email = settings.DEFAULT_FROM_EMAIL
        await send_mail(
            subject, message, from_email, recipient_list,
            fail_silently=False, html_message=html_message)

    async def on_create_message(self, sid, data):
        content_type = data.get('content_type', 'text/plain')
        group = self.retrieve_group(data)
        text = data.get('data')
        event_id = data.get('event_id')
        client = await self.get_client(sid)
        content = {
            'user': {
                'id': client.get_user_id()
            },
            'content_type': content_type,
            'event_id': event_id
        }

        # Moderation
        try:
            await moderate_message(text)
        except ModeratedException as e:
            content['error'] = '\n'.join(e.messages)
            personal_group = client.create_personal_group()
            await self.emit('create_message', data=content, room=personal_group)
            return 'ERR', event_id, '\n'.join(e.messages)
        # /Moderation

        try:
            message_id = await client.create_message(group, {
                'data': data,
                'content_type': content_type
            })
        except ClientError as e:
            content['error'] = str(e)
            personal_group = client.create_personal_group()
            await self.emit('create_message', data=content, room=personal_group)
            return 'ERR', event_id, str(e)
        else:
            content['payload'] = {'id': message_id, 'data': data}
            await self.emit('create_message', data=content, room=group)
            if self.email_on_incoming_message:
                await self.send_email_on_incoming_message(data, group, client)
            return 'OK', event_id, message_id

    async def on_enumerate_group(self, sid, data):
        client = await self.get_client(sid)

    async def on_get_messages(self, sid, data):
        client = await self.get_client(sid)

    async def on_delete_messages(self, sid, data):
        client = await self.get_client(sid)

    async def on_update_messages(self, sid, data):
        client = await self.get_client(sid)

    async def on_read_messages(self, sid, data):
        client = await self.get_client(sid)

    # /MESSAGES

    # /Client actions

    # System actions

    async def on_typing_started(self, sid, data):
        """Typing text message started."""
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        content = {
            'user': {
                'id': client.get_user_id()
            }
        }
        await self.emit('typing_started', data=content, room=group, skip_sid=sid)

    async def on_typing_stopped(self, sid, data):
        """Typing text message stopped."""
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        content = {
            'user': {
                'id': client.get_user_id()
            }
        }
        await self.emit('typing_stopped', data=content, room=group, skip_sid=sid)

    async def on_sending_file_started(self, sid, data):
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        content = {
            'user': {
                'id': client.get_user_id()
            },
            'content_type': None,
            'event_id': None
        }
        await self.emit('sending_file_started', data=content, room=group, skip_sid=sid)

    async def on_sending_file_stopped(self, sid, data):
        client = await self.get_client(sid)
        group = self.retrieve_group(data)
        content = {
            'user': {
                'id': client.get_user_id()
            },
            'event_id': None
        }
        await self.emit('sending_file_stopped', data=content, room=group, skip_sid=sid)

    async def on_online(self, sid):
        request_handler = await self.get_request_handler(sid)
        user_agent = request_handler.request.headers.get('User-Agent')
        user_agent = user_agents.parse(user_agent)
        client = await self.get_client(sid)
        content = {
            'user': {
                'id': client.get_user_id()
            },
            'device': {
                'family': user_agent.device.family,
                'brand': user_agent.device.brand,
                'model': user_agent.device.model
            },
            'os': {
                'family': user_agent.os.family,
                'version': user_agent.os.version_string
            }
        }
        for group in self.rooms(sid):
            await self.emit(self.ONLINE, data=content, room=group, skip_sid=sid)

    async def on_offline(self, sid):
        client = await self.get_client(sid)
        user_id = client.get_user_id()
        content = {
            'user': {
                'id': user_id
            }
        }
        is_online = await self.online(sid, user_id)
        if not is_online:
            for group in self.rooms(sid):
                await self.emit(self.OFFLINE, data=content, room=group, skip_sid=sid)

    # /System actions


class MessengerHandler(UserHandlerMixin, SocketIOHandler):
    def check_origin(self, origin):
        return True
        # TODO: configuration from settings.py
        # return super().check_origin(origin)
