import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id   = self.scope['url_route']['kwargs']['room_id']
        self.room_name = f'chat_{self.room_id}'

        # join room group
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )
        await self.accept()

        # send last 20 messages on connect
        messages = await self.get_messages()
        for msg in messages:
            await self.send(text_data=json.dumps({
                'type'     : 'old_message',
                'message'  : msg['message'],
                'sender'   : msg['sender'],
                'timestamp': msg['timestamp'],
            }))

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

        # save to database
        await self.save_message(sender, message)

        # broadcast to room
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
    def get_messages(self):
        try:
            room     = ChatRoom.objects.get(pk=self.room_id)
            messages = ChatMessage.objects.filter(
                room=room
            ).select_related('sender').order_by('-timestamp')[:20]
            return [
                {
                    'message'  : m.message,
                    'sender'   : m.sender.username,
                    'timestamp': m.timestamp.strftime('%I:%M %p'),
                }
                for m in reversed(list(messages))
            ]
        except:
            return []

    @database_sync_to_async
    def save_message(self, sender, message):
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            ChatMessage.objects.create(
                room    = room,
                sender  = sender,
                message = message,
            )
        except:
            pass