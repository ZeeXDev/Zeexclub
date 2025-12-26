#Codeflix_Botz
#rohit_1888 on Tg

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)


class LocalStorage:
    """Classe pour gérer le stockage local dans des fichiers JSON"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def _get_file_path(self, collection_name: str) -> Path:
        return self.data_dir / f"{collection_name}.json"
    
    async def load_data(self, collection_name: str) -> Dict:
        """Charge les données d'une collection depuis le fichier JSON"""
        file_path = self._get_file_path(collection_name)
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    async def save_data(self, collection_name: str, data: Dict) -> None:
        """Sauvegarde les données d'une collection dans le fichier JSON"""
        file_path = self._get_file_path(collection_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def insert_one(self, collection_name: str, document: Dict) -> None:
        """Insère un document dans une collection"""
        data = await self.load_data(collection_name)
        doc_id = document.get('_id')
        if doc_id is not None:
            data[str(doc_id)] = document
        await self.save_data(collection_name, data)
    
    async def find_one(self, collection_name: str, query: Dict) -> Optional[Dict]:
        """Trouve un document dans une collection"""
        data = await self.load_data(collection_name)
        
        if '_id' in query:
            doc_id = str(query['_id'])
            return data.get(doc_id)
        
        # Recherche par d'autres champs (simple implémentation)
        for doc in data.values():
            match = True
            for key, value in query.items():
                if doc.get(key) != value:
                    match = False
                    break
            if match:
                return doc
        
        return None
    
    async def update_one(self, collection_name: str, query: Dict, update: Dict, upsert: bool = False) -> None:
        """Met à jour un document dans une collection"""
        data = await self.load_data(collection_name)
        
        doc = await self.find_one(collection_name, query)
        
        if doc:
            doc_id = str(doc['_id'])
            # Appliquer les opérations de mise à jour
            if '$set' in update:
                data[doc_id].update(update['$set'])
            if '$addToSet' in update:
                for key, value in update['$addToSet'].items():
                    if key in data[doc_id]:
                        if value not in data[doc_id][key]:
                            data[doc_id][key].append(value)
                    else:
                        data[doc_id][key] = [value]
            if '$pull' in update:
                for key, value in update['$pull'].items():
                    if key in data[doc_id] and isinstance(data[doc_id][key], list):
                        if value in data[doc_id][key]:
                            data[doc_id][key].remove(value)
        elif upsert and '_id' in query:
            # Créer un nouveau document
            new_doc = {'_id': query['_id']}
            if '$set' in update:
                new_doc.update(update['$set'])
            data[str(query['_id'])] = new_doc
        
        await self.save_data(collection_name, data)
    
    async def delete_one(self, collection_name: str, query: Dict) -> None:
        """Supprime un document d'une collection"""
        data = await self.load_data(collection_name)
        
        if '_id' in query:
            doc_id = str(query['_id'])
            if doc_id in data:
                del data[doc_id]
        
        await self.save_data(collection_name, data)
    
    async def find_all(self, collection_name: str) -> List[Dict]:
        """Récupère tous les documents d'une collection"""
        data = await self.load_data(collection_name)
        return list(data.values())
    
    async def get_all_ids(self, collection_name: str) -> List:
        """Récupère tous les IDs d'une collection"""
        data = await self.load_data(collection_name)
        return [int(doc_id) for doc_id in data.keys() if doc_id.isdigit()]


class Rohit:
    def __init__(self, data_dir: str = "data"):
        self.storage = LocalStorage(data_dir)
        
        # Noms des collections (fichiers JSON)
        self.channel_data_name = 'channels'
        self.admins_data_name = 'admins'
        self.user_data_name = 'users'
        self.banned_user_name = 'banned_user'
        self.autho_user_name = 'autho_user'
        self.del_timer_name = 'del_timer'
        self.fsub_name = 'fsub'
        self.rqst_fsub_name = 'request_forcesub'
        self.rqst_fsub_channel_name = 'request_forcesub_channel'
        self.user_sessions_name = 'user_sessions'  # NOUVEAU

    # USER DATA
    async def present_user(self, user_id: int) -> bool:
        found = await self.storage.find_one(self.user_data_name, {'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int) -> None:
        if not await self.present_user(user_id):
            await self.storage.insert_one(self.user_data_name, {'_id': user_id})

    async def full_userbase(self) -> List[int]:
        return await self.storage.get_all_ids(self.user_data_name)

    async def del_user(self, user_id: int) -> None:
        await self.storage.delete_one(self.user_data_name, {'_id': user_id})

    # ADMIN DATA
    async def admin_exist(self, admin_id: int) -> bool:
        found = await self.storage.find_one(self.admins_data_name, {'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int) -> None:
        if not await self.admin_exist(admin_id):
            await self.storage.insert_one(self.admins_data_name, {'_id': admin_id})

    async def del_admin(self, admin_id: int) -> None:
        if await self.admin_exist(admin_id):
            await self.storage.delete_one(self.admins_data_name, {'_id': admin_id})

    async def get_all_admins(self) -> List[int]:
        return await self.storage.get_all_ids(self.admins_data_name)

    # BAN USER DATA
    async def ban_user_exist(self, user_id: int) -> bool:
        found = await self.storage.find_one(self.banned_user_name, {'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int) -> None:
        if not await self.ban_user_exist(user_id):
            await self.storage.insert_one(self.banned_user_name, {'_id': user_id})

    async def del_ban_user(self, user_id: int) -> None:
        if await self.ban_user_exist(user_id):
            await self.storage.delete_one(self.banned_user_name, {'_id': user_id})

    async def get_ban_users(self) -> List[int]:
        return await self.storage.get_all_ids(self.banned_user_name)

    # AUTO DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int) -> None:
        existing = await self.storage.find_one(self.del_timer_name, {})
        if existing:
            await self.storage.update_one(
                self.del_timer_name,
                {},
                {'$set': {'value': value}}
            )
        else:
            await self.storage.insert_one(self.del_timer_name, {'value': value})

    async def get_del_timer(self) -> int:
        data = await self.storage.find_one(self.del_timer_name, {})
        if data:
            return data.get('value', 600)
        return 0

    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int) -> bool:
        found = await self.storage.find_one(self.fsub_name, {'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int, mode: str = "off") -> None:
        if not await self.channel_exist(channel_id):
            await self.storage.insert_one(
                self.fsub_name, 
                {'_id': channel_id, 'mode': mode}
            )

    async def rem_channel(self, channel_id: int) -> None:
        if await self.channel_exist(channel_id):
            await self.storage.delete_one(self.fsub_name, {'_id': channel_id})

    async def show_channels(self) -> List[int]:
        return await self.storage.get_all_ids(self.fsub_name)

    # Get current mode of a channel
    async def get_channel_mode(self, channel_id: int) -> str:
        data = await self.storage.find_one(self.fsub_name, {'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    # Set mode of a channel
    async def set_channel_mode(self, channel_id: int, mode: str) -> None:
        await self.storage.update_one(
            self.fsub_name,
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT
    async def req_user(self, channel_id: int, user_id: int) -> None:
        try:
            await self.storage.update_one(
                self.rqst_fsub_channel_name,
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")

    async def del_req_user(self, channel_id: int, user_id: int) -> None:
        await self.storage.update_one(
            self.rqst_fsub_channel_name,
            {'_id': channel_id},
            {'$pull': {'user_ids': user_id}}
        )

    async def req_user_exist(self, channel_id: int, user_id: int) -> bool:
        try:
            found = await self.storage.find_one(
                self.rqst_fsub_channel_name,
                {'_id': int(channel_id)}
            )
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

    # ===== NOUVELLES MÉTHODES ADSGRAM =====
    
    async def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Récupère les informations de session d'un utilisateur"""
        return await self.storage.find_one(self.user_sessions_name, {'_id': user_id})

    async def set_free_session(self, user_id: int, duration_hours: int = 20) -> None:
        """Active une session gratuite pour un utilisateur"""
        expiry_time = datetime.now() + timedelta(hours=duration_hours)
        await self.storage.update_one(
            self.user_sessions_name,
            {'_id': user_id},
            {'$set': {
                'has_free_session': True,
                'session_expiry': expiry_time.isoformat(),
                'last_ad_watch': datetime.now().isoformat()
            }},
            upsert=True
        )

    async def has_active_session(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur a une session active"""
        session = await self.get_user_session(user_id)
        if not session or not session.get('has_free_session'):
            return False
        
        expiry = datetime.fromisoformat(session['session_expiry'])
        if datetime.now() > expiry:
            # Session expirée, la désactiver
            await self.remove_free_session(user_id)
            return False
        
        return True

    async def remove_free_session(self, user_id: int) -> None:
        """Supprime la session gratuite d'un utilisateur"""
        await self.storage.update_one(
            self.user_sessions_name,
            {'_id': user_id},
            {'$set': {'has_free_session': False}}
        )

    async def get_session_expiry(self, user_id: int) -> Optional[datetime]:
        """Récupère la date d'expiration de la session"""
        session = await self.get_user_session(user_id)
        if session and session.get('session_expiry'):
            return datetime.fromisoformat(session['session_expiry'])
        return None

    async def can_watch_ad(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur peut regarder une nouvelle pub"""
        session = await self.get_user_session(user_id)
        if not session or not session.get('last_ad_watch'):
            return True
        
        last_watch = datetime.fromisoformat(session['last_ad_watch'])
        time_diff = datetime.now() - last_watch
        
        # Peut regarder une pub si 20h se sont écoulées
        return time_diff >= timedelta(hours=20)


# Initialisation de la base de données
db = Rohit()