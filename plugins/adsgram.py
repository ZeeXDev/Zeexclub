from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    WebAppInfo,
    CallbackQuery,
    Message
)
from database.database import db
from config import ADSGRAM_BLOCK_ID, FREE_SESSION_DURATION, OWNER_ID
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def create_adsgram_button(user_id: int):
    """Crée le bouton pour ouvrir la WebApp AdsGram avec user_id"""
    if not ADSGRAM_BLOCK_ID:
        logger.error("ADSGRAM_BLOCK_ID n'est pas configuré!")
        return None
    
    # On ajoute le user_id dans l'URL pour le passer à AdsGram
    webapp_url = f"https://api.adsgram.ai/adv?blockId={ADSGRAM_BLOCK_ID}&tg_id={user_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📺 Regarder une pub (20h gratuit)", 
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton("❌ Annuler", callback_data="cancel_ad")]
    ])


async def check_session_and_prompt(client: Client, user_id: int, message: Message):
    """
    Vérifie la session et prompt l'utilisateur si nécessaire
    Retourne (has_access: bool, status_msg: str)
    """
    
    # Le propriétaire a toujours accès
    if user_id == OWNER_ID:
        return True, None
    
    # Vérifier si l'utilisateur a une session active
    has_session = await db.has_active_session(user_id)
    
    if has_session:
        # L'utilisateur a une session active
        expiry = await db.get_session_expiry(user_id)
        time_left = expiry - datetime.now()
        hours = int(time_left.total_seconds() / 3600)
        minutes = int((time_left.total_seconds() % 3600) / 60)
        
        return True, f"✅ Session active encore {hours}h {minutes}min"
    
    # Pas de session active, vérifier si peut regarder une pub
    can_watch = await db.can_watch_ad(user_id)
    
    if not can_watch:
        session = await db.get_user_session(user_id)
        if session and session.get('last_ad_watch'):
            last_watch = datetime.fromisoformat(session['last_ad_watch'])
            next_watch = last_watch + timedelta(hours=FREE_SESSION_DURATION)
            time_until = next_watch - datetime.now()
            hours = int(time_until.total_seconds() / 3600)
            minutes = int((time_until.total_seconds() % 3600) / 60)
            
            await message.reply_text(
                f"⏳ <b>Tu as déjà regardé une pub récemment.</b>\n\n"
                f"Prochaine pub disponible dans : <b>{hours}h {minutes}min</b>",
                quote=True
            )
            return False, None
    
    # Demander à l'utilisateur de regarder une pub
    keyboard = create_adsgram_button(user_id)
    if keyboard:
        await message.reply_text(
            "🔒 <b>Accès limité</b>\n\n"
            "Pour accéder à ce fichier, tu dois regarder une courte publicité.\n"
            f"Tu recevras <b>{FREE_SESSION_DURATION} heures</b> d'accès gratuit après avoir regardé la pub ! 🎉\n\n"
            "👇 Clique sur le bouton ci-dessous :",
            reply_markup=keyboard,
            quote=True
        )
    else:
        await message.reply_text(
            "❌ <b>Erreur de configuration</b>\n\n"
            "AdsGram n'est pas configuré correctement. Contacte l'administrateur.",
            quote=True
        )
    
    return False, None


@Client.on_callback_query(filters.regex("^cancel_ad$"))
async def cancel_ad_callback(client: Client, callback: CallbackQuery):
    """Gère l'annulation de la visualisation de pub"""
    await callback.message.delete()
    await callback.answer("❌ Annulé", show_alert=False)


@Client.on_callback_query(filters.regex("^check_session$"))
async def check_session_callback(client: Client, callback: CallbackQuery):
    """Vérifie le statut de la session de l'utilisateur"""
    user_id = callback.from_user.id
    
    has_session = await db.has_active_session(user_id)
    
    if has_session:
        expiry = await db.get_session_expiry(user_id)
        time_left = expiry - datetime.now()
        hours = int(time_left.total_seconds() / 3600)
        minutes = int((time_left.total_seconds() % 3600) / 60)
        
        await callback.answer(
            f"✅ Session active encore {hours}h {minutes}min",
            show_alert=True
        )
    else:
        can_watch = await db.can_watch_ad(user_id)
        if can_watch:
            await callback.answer(
                "❌ Pas de session active. Regarde une pub pour en obtenir une !",
                show_alert=True
            )
        else:
            session = await db.get_user_session(user_id)
            if session and session.get('last_ad_watch'):
                last_watch = datetime.fromisoformat(session['last_ad_watch'])
                next_watch = last_watch + timedelta(hours=FREE_SESSION_DURATION)
                time_until = next_watch - datetime.now()
                hours = int(time_until.total_seconds() / 3600)
                minutes = int((time_until.total_seconds() % 3600) / 60)
                
                await callback.answer(
                    f"⏳ Prochaine pub disponible dans {hours}h {minutes}min",
                    show_alert=True
                )


# Handler pour les données de la WebApp (après visualisation de la pub)
@Client.on_message(filters.web_app_data)
async def handle_webapp_data(client: Client, message: Message):
    """Traite les données reçues de la WebApp AdsGram"""
    try:
        user_id = message.from_user.id
        
        logger.info(f"WebApp data reçue de l'utilisateur {user_id}: {message.web_app_data.data}")
        
        # AdsGram envoie les données après la visualisation réussie
        # On active la session gratuite
        await db.set_free_session(user_id, FREE_SESSION_DURATION)
        
        await message.reply_text(
            "✅ <b>Merci d'avoir regardé la pub !</b>\n\n"
            f"🎉 Tu as maintenant <b>{FREE_SESSION_DURATION} heures</b> d'accès gratuit !\n"
            "Tu peux maintenant accéder à tous les fichiers.\n\n"
            "💡 Renvoie le lien du fichier pour y accéder.",
            quote=True
        )
        
        logger.info(f"Session activée pour l'utilisateur {user_id}")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement WebApp data: {e}")
        await message.reply_text(
            "❌ Une erreur s'est produite. Réessaie plus tard.",
            quote=True
        )


# Commande pour vérifier le statut de la session
@Client.on_message(filters.command("session") & filters.private)
async def session_status(client: Client, message: Message):
    """Affiche le statut de la session de l'utilisateur"""
    user_id = message.from_user.id
    
    has_session = await db.has_active_session(user_id)
    
    if has_session:
        expiry = await db.get_session_expiry(user_id)
        time_left = expiry - datetime.now()
        hours = int(time_left.total_seconds() / 3600)
        minutes = int((time_left.total_seconds() % 3600) / 60)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Actualiser", callback_data="check_session")]
        ])
        
        await message.reply_text(
            f"✅ <b>Session active</b>\n\n"
            f"⏱ Temps restant : <b>{hours}h {minutes}min</b>\n"
            f"📅 Expire le : <code>{expiry.strftime('%d/%m/%Y à %H:%M')}</code>",
            reply_markup=keyboard,
            quote=True
        )
    else:
        can_watch = await db.can_watch_ad(user_id)
        
        if can_watch:
            keyboard = create_adsgram_button(user_id)
            await message.reply_text(
                "❌ <b>Pas de session active</b>\n\n"
                f"Regarde une pub pour obtenir <b>{FREE_SESSION_DURATION}h</b> d'accès gratuit !",
                reply_markup=keyboard,
                quote=True
            )
        else:
            session = await db.get_user_session(user_id)
            if session and session.get('last_ad_watch'):
                last_watch = datetime.fromisoformat(session['last_ad_watch'])
                next_watch = last_watch + timedelta(hours=FREE_SESSION_DURATION)
                time_until = next_watch - datetime.now()
                hours = int(time_until.total_seconds() / 3600)
                minutes = int((time_until.total_seconds() % 3600) / 60)
                
                await message.reply_text(
                    f"⏳ <b>Session expirée</b>\n\n"
                    f"Prochaine pub disponible dans : <b>{hours}h {minutes}min</b>",
                    quote=True
                )