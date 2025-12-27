#Codeflix_Botz
#rohit_1888 on Tg

import motor, asyncio
import motor.motor_asyncio
import time
import pymongo, os
from config import DB_URI, DB_NAME
from bot import Bot
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

logging.basicConfig(level=logging.INFO)


class Rohit:

    def __init__(self, DB_URI, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
        self.database = self.dbclient[DB_NAME]

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.del_timer_data = self.database['del_timer']
        self.fsub_data = self.database['fsub']   
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.user_sessions = self.database['user_sessions']  # NOUVEAU pour AdsGram


    # USER DATA
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        return

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return


    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            return

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            return

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    # BAN USER DATA
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})
            return

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            return

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    # AUTO DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int):        
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})

    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 600)
        return 0


    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})
            return

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})
            return

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    
    # Get current mode of a channel
    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    # Set mode of a channel
    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT

    # Add the user to the set of users for a specific channel
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")


    # Method 2: Remove a user from the channel set
    async def del_req_user(self, channel_id: int, user_id: int):
        # Remove the user from the set of users for the channel
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )

    # Check if the user exists in the set of the channel's users
    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False  


    # Method to check if a channel exists using show_channels
    async def reqChannel_exist(self, channel_id: int):
        # Get the list of all channel IDs from the database
        channel_ids = await self.show_channels()
        
        # Check if the given channel_id is in the list of channel IDs
        if channel_id in channel_ids:
            return True
        else:
            return False


    # ========== GESTION DES SESSIONS ADSGRAM (NOUVEAU) ==========
    
    async def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Récupère les données de session d'un utilisateur"""
        return await self.user_sessions.find_one({'_id': user_id})
    
    async def has_active_session(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur a une session active"""
        session = await self.get_user_session(user_id)
        if not session:
            return False
        
        expiry = session.get('session_expiry')
        if not expiry:
            return False
        
        # Convertir la string en datetime si nécessaire
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)
        
        return datetime.now() < expiry
    
    async def add_session_time(self, user_id: int, hours: int = 20) -> Dict:
        """Ajoute du temps de session à un utilisateur"""
        session = await self.get_user_session(user_id)
        now = datetime.now()
        
        if session and await self.has_active_session(user_id):
            # Prolonger la session existante
            current_expiry = session.get('session_expiry')
            if isinstance(current_expiry, str):
                current_expiry = datetime.fromisoformat(current_expiry)
            new_expiry = current_expiry + timedelta(hours=hours)
        else:
            # Créer une nouvelle session
            new_expiry = now + timedelta(hours=hours)
        
        session_data = {
            '_id': user_id,
            'session_expiry': new_expiry.isoformat(),
            'last_ad_watch': now.isoformat(),
            'total_ads_watched': session.get('total_ads_watched', 0) + 1 if session else 1,
            'updated_at': now.isoformat()
        }
        
        await self.user_sessions.update_one(
            {'_id': user_id},
            {'$set': session_data},
            upsert=True
        )
        
        return session_data
    
    async def get_session_remaining_time(self, user_id: int) -> Optional[timedelta]:
        """Retourne le temps restant de la session"""
        session = await self.get_user_session(user_id)
        if not session:
            return None
        
        expiry = session.get('session_expiry')
        if not expiry:
            return None
        
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)
        
        now = datetime.now()
        if now >= expiry:
            return timedelta(0)
        
        return expiry - now
    
    async def can_watch_ad(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur peut regarder une pub (cooldown de 20h)"""
        session = await self.get_user_session(user_id)
        if not session:
            return True
        
        last_watch = session.get('last_ad_watch')
        if not last_watch:
            return True
        
        if isinstance(last_watch, str):
            last_watch = datetime.fromisoformat(last_watch)
        
        cooldown_end = last_watch + timedelta(hours=20)
        return datetime.now() >= cooldown_end
    
    async def get_all_sessions(self) -> List[Dict]:
        """Récupère toutes les sessions (pour l'admin)"""
        return await self.user_sessions.find({}).to_list(None)
    
    async def reset_user_session(self, user_id: int) -> None:
        """Reset la session d'un utilisateur"""
        await self.user_sessions.delete_one({'_id': user_id})
    
    async def get_ads_stats(self) -> Dict:
        """Statistiques globales des pubs"""
        sessions = await self.get_all_sessions()
        total_watches = sum(s.get('total_ads_watched', 0) for s in sessions)
        active_sessions = sum(1 for s in sessions if await self.has_active_session(s['_id']))
        
        return {
            'total_ads_watched': total_watches,
            'active_sessions': active_sessions,
            'total_users_with_sessions': len(sessions)
        }


db = Rohit(DB_URI, DB_NAME)