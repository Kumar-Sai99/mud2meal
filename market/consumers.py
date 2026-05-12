import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id   = self.scope['url_route']['kwargs']['room_id']
        self.room_name = f'chat_{self.room_id}'

        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data    = json.loads(text_data)
        message = data['message'].strip()
        sender  = self.scope['user']

        if not message or not sender.is_authenticated:
            return

        await self.save_message(sender, message)

        await self.channel_layer.group_send(
            self.room_name,
            {
                'type'   : 'chat_message',
                'message': message,
                'sender' : sender.username,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type'   : 'new_message',
            'message': event['message'],
            'sender' : event['sender'],
        }))

    @database_sync_to_async
    def save_message(self, sender, message):
        from .models import ChatRoom, ChatMessage
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            ChatMessage.objects.create(
                room    = room,
                sender  = sender,
                message = message,
            )
        except:
            pass