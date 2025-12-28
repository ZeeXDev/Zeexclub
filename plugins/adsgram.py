# plugins/adsgram.py
# Module AdsGram pour gérer les sessions gratuites

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from database.database import db
from config import ADSGRAM_BLOCK_ID, FREE_SESSION_DURATION
from datetime import datetime, timedelta
import os

# URL de ta WebApp (automatique selon l'environnement)
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://zeexclub-1.onrender.com")

async def check_session_and_prompt(client: Client, user_id: int, message):
    """
    Vérifie si l'utilisateur a une session active
    Retourne (has_access: bool, status_message: str)
    """
    try:
        has_session = await db.has_active_session(user_id)
        
        if has_session:
            # L'utilisateur a une session active
            remaining_time = await db.get_session_remaining_time(user_id)
            if remaining_time:
                hours = int(remaining_time.total_seconds() / 3600)
                minutes = int((remaining_time.total_seconds() % 3600) / 60)
                status_msg = f"✅ Session active: {hours}h {minutes}min restantes"
                return True, status_msg
        
        # Pas de session active - Afficher le message de pub
        can_watch = await db.can_watch_ad(user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📺 Regarder une pub (20h gratuit)", 
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
            [InlineKeyboardButton(
                "📊 Mes sessions", 
                callback_data="check_session"
            )]
        ])
        
        if can_watch:
            text = (
                "⏰ **Session Expirée**\n\n"
                "Pour accéder à ce fichier, vous devez avoir une session active.\n\n"
                "🎬 Regardez une pub pour obtenir **20 heures** d'accès gratuit !"
            )
        else:
            session = await db.get_user_session(user_id)
            if session:
                last_watch = datetime.fromisoformat(session['last_ad_watch'])
                next_available = last_watch + timedelta(hours=FREE_SESSION_DURATION)
                hours_left = int((next_available - datetime.now()).total_seconds() / 3600)
                
                text = (
                    "⏰ **Session Expirée**\n\n"
                    f"Vous pourrez regarder une nouvelle pub dans **{hours_left}h**.\n\n"
                    "En attendant, consultez vos sessions."
                )
            else:
                text = (
                    "⏰ **Aucune Session Active**\n\n"
                    "Regardez une pub pour obtenir 20h d'accès gratuit !"
                )
        
        await message.reply_text(text, reply_markup=keyboard)
        return False, None
    
    except Exception as e:
        print(f"[ADSGRAM ERROR] check_session_and_prompt: {e}")
        # En cas d'erreur, on laisse passer l'utilisateur pour ne pas bloquer
        return True, "⚠️ Erreur de vérification de session"


@Client.on_callback_query(filters.regex("^check_session$"))
async def check_session_callback(client: Client, callback_query: CallbackQuery):
    """Callback pour vérifier la session"""
    user_id = callback_query.from_user.id
    
    try:
        session = await db.get_user_session(user_id)
        has_active = await db.has_active_session(user_id)
        
        if not session:
            text = (
                "❌ **Aucune Session**\n\n"
                "Vous n'avez jamais regardé de pub.\n"
                "Cliquez sur le bouton ci-dessous pour commencer !"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📺 Regarder une pub", 
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )],
                [InlineKeyboardButton("« Retour", callback_data="start")]
            ])
        else:
            remaining_time = await db.get_session_remaining_time(user_id)
            can_watch = await db.can_watch_ad(user_id)
            
            if has_active and remaining_time:
                hours = int(remaining_time.total_seconds() / 3600)
                minutes = int((remaining_time.total_seconds() % 3600) / 60)
                status = f"✅ Active ({hours}h {minutes}min restantes)"
            else:
                status = "❌ Expirée"
            
            if can_watch:
                next_ad = "Maintenant !"
            else:
                last_watch = datetime.fromisoformat(session['last_ad_watch'])
                next_available = last_watch + timedelta(hours=FREE_SESSION_DURATION)
                hours_left = int((next_available - datetime.now()).total_seconds() / 3600)
                next_ad = f"Dans {hours_left}h"
            
            text = (
                f"📊 **Vos Sessions**\n\n"
                f"Status: {status}\n"
                f"🎬 Pubs vues: {session.get('total_ads_watched', 0)}\n"
                f"⏰ Prochaine pub: {next_ad}"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📺 Gérer mes sessions", 
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )],
                [InlineKeyboardButton("« Retour", callback_data="start")]
            ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    
    except Exception as e:
        print(f"[ADSGRAM ERROR] check_session_callback: {e}")
        await callback_query.answer("❌ Erreur lors de la récupération des données", show_alert=True)


@Client.on_message(filters.command("mysession") & filters.private)
async def my_session_command(client: Client, message):
    """Commande pour voir sa session"""
    user_id = message.from_user.id
    
    try:
        session = await db.get_user_session(user_id)
        has_active = await db.has_active_session(user_id)
        
        if not session:
            await message.reply_text(
                "❌ **Aucune Session**\n\n"
                "Vous n'avez jamais regardé de pub.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "📺 Commencer", 
                        web_app=WebAppInfo(url=WEBAPP_URL)
                    )]
                ])
            )
            return
        
        remaining_time = await db.get_session_remaining_time(user_id)
        can_watch = await db.can_watch_ad(user_id)
        
        if has_active and remaining_time:
            hours = int(remaining_time.total_seconds() / 3600)
            minutes = int((remaining_time.total_seconds() % 3600) / 60)
            status = f"✅ Active ({hours}h {minutes}min)"
        else:
            status = "❌ Expirée"
        
        if can_watch:
            next_ad = "Maintenant !"
        else:
            last_watch = datetime.fromisoformat(session['last_ad_watch'])
            next_available = last_watch + timedelta(hours=FREE_SESSION_DURATION)
            hours_left = int((next_available - datetime.now()).total_seconds() / 3600)
            next_ad = f"Dans {hours_left}h"
        
        text = (
            f"📊 **Vos Sessions**\n\n"
            f"Status: {status}\n"
            f"🎬 Pubs vues: {session.get('total_ads_watched', 0)}\n"
            f"⏰ Prochaine pub: {next_ad}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📺 Gérer mes sessions", 
                web_app=WebAppInfo(url=WEBAPP_URL)
            )]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
    
    except Exception as e:
        print(f"[ADSGRAM ERROR] my_session_command: {e}")
        await message.reply_text("❌ Erreur lors de la récupération de votre session")


# ========== COMMANDES ADMIN ==========

@Client.on_message(filters.command("givesession") & filters.private)
async def give_session_admin(client: Client, message):
    """Admin: Donner une session à un utilisateur"""
    admin_id = message.from_user.id
    
    try:
        if not await db.admin_exist(admin_id):
            await message.reply_text("❌ Accès refusé.")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text(
                "❌ Usage: `/givesession USER_ID [HOURS]`\n"
                "Exemple: `/givesession 123456789 24`"
            )
            return
        
        target_user_id = int(parts[1])
        hours = int(parts[2]) if len(parts) > 2 else FREE_SESSION_DURATION
        
        session_data = await db.add_session_time(target_user_id, hours=hours)
        
        await message.reply_text(
            f"✅ **Session Ajoutée**\n\n"
            f"👤 User: `{target_user_id}`\n"
            f"⏰ Durée: {hours}h\n"
            f"🎬 Total pubs: {session_data['total_ads_watched']}"
        )
    
    except ValueError:
        await message.reply_text("❌ Format invalide. Les IDs et heures doivent être des nombres.")
    except Exception as e:
        print(f"[ADSGRAM ERROR] give_session_admin: {e}")
        await message.reply_text(f"❌ Erreur lors de l'ajout de la session: {str(e)}")


@Client.on_message(filters.command("removesession") & filters.private)
async def remove_session_admin(client: Client, message):
    """Admin: Supprimer la session d'un utilisateur"""
    admin_id = message.from_user.id
    
    try:
        if not await db.admin_exist(admin_id):
            await message.reply_text("❌ Accès refusé.")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text(
                "❌ Usage: `/removesession USER_ID`\n"
                "Exemple: `/removesession 123456789`"
            )
            return
        
        target_user_id = int(parts[1])
        await db.reset_user_session(target_user_id)
        
        await message.reply_text(
            f"✅ **Session Supprimée**\n\n"
            f"👤 User: `{target_user_id}`"
        )
    
    except ValueError:
        await message.reply_text("❌ Format invalide. L'ID doit être un nombre.")
    except Exception as e:
        print(f"[ADSGRAM ERROR] remove_session_admin: {e}")
        await message.reply_text(f"❌ Erreur: {str(e)}")


@Client.on_message(filters.command("sessionstats") & filters.private)
async def session_stats_admin(client: Client, message):
    """Admin: Stats des sessions"""
    admin_id = message.from_user.id
    
    try:
        if not await db.admin_exist(admin_id):
            await message.reply_text("❌ Accès refusé.")
            return
        
        stats = await db.get_ads_stats()
        
        text = (
            "📊 **Statistiques Sessions**\n\n"
            f"🎬 Total pubs vues: {stats['total_ads_watched']}\n"
            f"✅ Sessions actives: {stats['active_sessions']}\n"
            f"👥 Users avec sessions: {stats['total_users_with_sessions']}"
        )
        
        await message.reply_text(text)
    
    except Exception as e:
        print(f"[ADSGRAM ERROR] session_stats_admin: {e}")
        await message.reply_text(f"❌ Erreur: {str(e)}")