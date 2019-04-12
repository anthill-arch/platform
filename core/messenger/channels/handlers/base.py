from anthill.platform.core.messenger.channels.exceptions import InvalidChannelLayerError


class ChannelHandlerMixin:
    groups = None

    async def get_groups(self) -> list:
        """Returns group names."""
        return self.groups or []

    async def channel_receive_callback(self) -> None:
        """Channel messages listener callback."""
        if self.channel_receive:
            while True:
                message = await self.channel_receive()
                await self.on_channel_message(message)

    async def on_channel_message(self, message: dict) -> None:
        """Receives message from current channel."""

    async def on_message(self, message: str) -> None:
        """Receives message from client."""
        await super().on_message(message)

    async def send_to_channel(self, channel: str, message: dict) -> None:
        """Sends the given message to the given channel."""
        try:
            await self.channel_layer.send(channel, message)
        except AttributeError:
            raise InvalidChannelLayerError("BACKEND is not configured or doesn't support groups")

    async def send_to_group(self, group: str, message: dict) -> None:
        """Sends the given message to the given group."""
        try:
            await self.channel_layer.group_send(group, message)
        except AttributeError:
            raise InvalidChannelLayerError("BACKEND is not configured or doesn't support groups")

    async def send_to_global_groups(self, message: dict) -> None:
        global_groups = self.groups or []
        for group in global_groups:
            await self.send_to_group(group, message)

    async def group_add(self, group: str) -> None:
        await self.channel_layer.group_add(group, self.channel_name)

    async def group_discard(self, group: str) -> None:
        await self.channel_layer.group_discard(group, self.channel_name)
