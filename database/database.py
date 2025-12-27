#Codeflix_Botz
#rohit_1888 on Tg

import asyncio
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import os

logging.basicConfig(level=logging.INFO)

# Configuration MongoDB
MONGODB_URI = os.environ.get("DB_URI", "")
DB_NAME = os.environ.get("DB_NAME", "Cluster0")


class Rohit:
    def __init__(self):
        # Connexion MongoDB
        if MONGODB_URI:
            self.client = AsyncIOMotorClient(MONGODB_URI)
            self.db = self.client[DB_NAME]
        else:
            raise Exception("DB_URI non configuré dans les variables d'environnement")
        
        # Collections MongoDB
        self.users = self.db['users']
        self.admins = self.db['admins']
        self.banned_users = self.db['banned_users']
        self.channels = self.db['channels']
        self.settings = self.db['settings']
        self.request_fsub = self.db['request_forcesub']
        self.user_sessions = self.db['user_sessions']  # NOUVEAU pour AdsGram

    # USER DATA
    async def present_user(self, user_id: int) -> bool:
        found = await self.users.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int) -> None:
        if not await self.present_user(user_id):
            await self.users.insert_one({'_id': user_id})

    async def full_userbase(self) -> List[int]:
        users = await self.users.find({}).to_list(None)
        return [user['_id'] for user in users]

    async def del_user(self, user_id: int) -> None:
        await self.users.delete_one({'_id': user_id})

    # ADMIN DATA
    async def admin_exist(self, admin_id: int) -> bool:
        found = await self.admins.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int) -> None:
        if not await self.admin_exist(admin_id):
            await self.admins.insert_one({'_id': admin_id})

    async def del_admin(self, admin_id: int) -> None:
        await self.admins.delete_one({'_id': admin_id})

    async def get_all_admins(self) -> List[int]:
        admins = await self.admins.find({}).to_list(None)
        return [admin['_id'] for admin in admins]

    # BAN USER DATA
    async def ban_user_exist(self, user_id: int) -> bool:
        found = await self.banned_users.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int) -> None:
        if not await self.ban_user_exist(user_id):
            await self.banned_users.insert_one({'_id': user_id})

    async def del_ban_user(self, user_id: int) -> None:
        await self.banned_users.delete_one({'_id': user_id})

    async def get_ban_users(self) -> List[int]:
        banned = await self.banned_users.find({}).to_list(None)
        return [user['_id'] for user in banned]

    # AUTO DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int) -> None:
        await self.settings.update_one(
            {'_id': 'del_timer'},
            {'$set': {'value': value}},
            upsert=True
        )

    async def get_del_timer(self) -> int:
        data = await self.settings.find_one({'_id': 'del_timer'})
        return data.get('value', 600) if data else 0

    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int) -> bool:
        found = await self.channels.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int, mode: str = "off") -> None:
        if not await self.channel_exist(channel_id):
            await self.channels.insert_one({'_id': channel_id, 'mode': mode})

    async def rem_channel(self, channel_id: int) -> None:
        await self.channels.delete_one({'_id': channel_id})

    async def show_channels(self) -> List[int]:
        channels = await self.channels.find({}).to_list(None)
        return [channel['_id'] for channel in channels]

    async def get_channel_mode(self, channel_id: int) -> str:
        data = await self.channels.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str) -> None:
        await self.channels.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT
    async def req_user(self, channel_id: int, user_id: int) -> None:
        try:
            await self.request_fsub.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")

    async def del_req_user(self, channel_id: int, user_id: int) -> None:
        await self.request_fsub.update_one(
            {'_id': channel_id},
            {'$pull': {'user_ids': user_id}}
        )

    async def req_user_exist(self, channel_id: int, user_id: int) -> bool:
        try:
            found = await self.request_fsub.find_one({'_id': int(channel_id)})
            if found:
                user_ids = found.get('user_ids', [])
                return int(user_id) in user_ids
            return False
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False

    async def reqChannel_exist(self, channel_id: int) -> bool:
        channel_ids = await self.show_channels()
        return channel_id in channel_ids

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


# Initialisation de la base de données
db = Rohit()