from pyrogram import Client, filters
from pyrogram.types import Message
from database.database import db
from config import FREE_SESSION_DURATION
from helper_func import admin
from datetime import datetime

@Client.on_message(filters.command("givesession") & admin)
async def give_session(client: Client, message: Message):
    """Donne une session gratuite à un utilisateur (admin only)"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ <b>Usage:</b> <code>/givesession &lt;user_id&gt; [durée_en_heures]</code>\n\n"
            f"<i>Durée par défaut: {FREE_SESSION_DURATION}h</i>"
        )
        return
    
    try:
        user_id = int(message.command[1])
        duration = int(message.command[2]) if len(message.command) > 2 else FREE_SESSION_DURATION
        
        await db.set_free_session(user_id, duration)
        
        await message.reply_text(
            f"✅ <b>Session accordée !</b>\n\n"
            f"👤 Utilisateur: <code>{user_id}</code>\n"
            f"⏱ Durée: <b>{duration}h</b>"
        )
    except ValueError:
        await message.reply_text("❌ <b>Erreur:</b> ID utilisateur ou durée invalide")
    except Exception as e:
        await message.reply_text(f"❌ <b>Erreur:</b> <code>{e}</code>")


@Client.on_message(filters.command("removesession") & admin)
async def remove_session(client: Client, message: Message):
    """Supprime la session d'un utilisateur (admin only)"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ <b>Usage:</b> <code>/removesession &lt;user_id&gt;</code>"
        )
        return
    
    try:
        user_id = int(message.command[1])
        
        # Vérifier si l'utilisateur a une session
        has_session = await db.has_active_session(user_id)
        
        if not has_session:
            await message.reply_text(
                f"ℹ️ L'utilisateur <code>{user_id}</code> n'a pas de session active."
            )
            return
        
        await db.remove_free_session(user_id)
        
        await message.reply_text(
            f"✅ <b>Session supprimée !</b>\n\n"
            f"👤 Utilisateur: <code>{user_id}</code>"
        )
    except ValueError:
        await message.reply_text("❌ <b>Erreur:</b> ID utilisateur invalide")
    except Exception as e:
        await message.reply_text(f"❌ <b>Erreur:</b> <code>{e}</code>")


@Client.on_message(filters.command("checksession") & admin)
async def check_user_session(client: Client, message: Message):
    """Vérifie la session d'un utilisateur spécifique (admin only)"""
    if len(message.command) < 2:
        await message.reply_text(
            "❌ <b>Usage:</b> <code>/checksession &lt;user_id&gt;</code>"
        )
        return
    
    try:
        user_id = int(message.command[1])
        
        has_session = await db.has_active_session(user_id)
        
        if has_session:
            expiry = await db.get_session_expiry(user_id)
            time_left = expiry - datetime.now()
            hours = int(time_left.total_seconds() / 3600)
            minutes = int((time_left.total_seconds() % 3600) / 60)
            
            session = await db.get_user_session(user_id)
            last_watch = datetime.fromisoformat(session['last_ad_watch'])
            
            await message.reply_text(
                f"✅ <b>Session active</b>\n\n"
                f"👤 Utilisateur: <code>{user_id}</code>\n"
                f"⏱ Temps restant: <b>{hours}h {minutes}min</b>\n"
                f"📅 Expire le: <code>{expiry.strftime('%d/%m/%Y à %H:%M')}</code>\n"
                f"🕐 Dernière pub vue: <code>{last_watch.strftime('%d/%m/%Y à %H:%M')}</code>"
            )
        else:
            session = await db.get_user_session(user_id)
            if session and session.get('last_ad_watch'):
                last_watch = datetime.fromisoformat(session['last_ad_watch'])
                await message.reply_text(
                    f"❌ <b>Pas de session active</b>\n\n"
                    f"👤 Utilisateur: <code>{user_id}</code>\n"
                    f"🕐 Dernière pub vue: <code>{last_watch.strftime('%d/%m/%Y à %H:%M')}</code>"
                )
            else:
                await message.reply_text(
                    f"ℹ️ L'utilisateur <code>{user_id}</code> n'a jamais regardé de pub."
                )
                
    except ValueError:
        await message.reply_text("❌ <b>Erreur:</b> ID utilisateur invalide")
    except Exception as e:
        await message.reply_text(f"❌ <b>Erreur:</b> <code>{e}</code>")


@Client.on_message(filters.command("sessionstats") & admin)
async def session_stats(client: Client, message: Message):
    """Affiche les statistiques des sessions (admin only)"""
    try:
        # Récupérer tous les utilisateurs
        all_users = await db.full_userbase()
        
        active_sessions = 0
        expired_sessions = 0
        no_sessions = 0
        
        for user_id in all_users:
            has_session = await db.has_active_session(user_id)
            if has_session:
                active_sessions += 1
            else:
                session = await db.get_user_session(user_id)
                if session and session.get('last_ad_watch'):
                    expired_sessions += 1
                else:
                    no_sessions += 1
        
        total = len(all_users)
        
        await message.reply_text(
            f"📊 <b>Statistiques des sessions</b>\n\n"
            f"👥 Total utilisateurs: <code>{total}</code>\n"
            f"✅ Sessions actives: <code>{active_sessions}</code> ({active_sessions*100//total if total > 0 else 0}%)\n"
            f"⏳ Sessions expirées: <code>{expired_sessions}</code> ({expired_sessions*100//total if total > 0 else 0}%)\n"
            f"❌ Jamais de pub: <code>{no_sessions}</code> ({no_sessions*100//total if total > 0 else 0}%)"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ <b>Erreur:</b> <code>{e}</code>")