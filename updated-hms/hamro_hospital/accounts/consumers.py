import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.groups_to_join = [f'user_{user.id}']
        role = getattr(user, 'role', '')
        if role:
            self.groups_to_join.append(f'role_{role}')
        for group in self.groups_to_join:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        for group in getattr(self, 'groups_to_join', []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notify(self, event):
        await self.send(text_data=json.dumps(event.get('payload', {})))
