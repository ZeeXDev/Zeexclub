import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from plugins.adsgram import check_session_and_prompt  # NOUVELLE LIGNE

BAN_SUPPORT = f"{BAN_SUPPORT}"

async def determine_media_type(msg):
    """Détermine le type de média et retourne l'action appropriée"""
    if msg.video:
        return ChatAction.UPLOAD_VIDEO
    elif msg.document:
        return ChatAction.UPLOAD_DOCUMENT
    elif msg.photo:
        return ChatAction.UPLOAD_PHOTO
    elif msg.audio:
        return ChatAction.UPLOAD_AUDIO
    else:
        return ChatAction.TYPING

async def send_with_progress(client, message, msg):
    """Envoie le média avec la bonne action et gestion des erreurs"""
    try:
        # Détermine l'action appropriée
        action = await determine_media_type(msg)
        await client.send_chat_action(message.chat.id, action)
        
        # Prépare la légende
        original_caption = msg.caption.html if msg.caption else ""
        caption = f"{original_caption}\n\n{CUSTOM_CAPTION}" if CUSTOM_CAPTION else original_caption
        
        # Envoie le média
        sent_msg = await msg.copy(
            chat_id=message.from_user.id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=msg.reply_markup if not DISABLE_CHANNEL_BUTTON else None,
            protect_content=PROTECT_CONTENT
        )
        await asyncio.sleep(0.9)
        return sent_msg
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await send_with_progress(client, message, msg)
    except Exception as e:
        print(f"Erreur lors de l'envoi: {e}")
        return None

@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    banned_users = await db.get_ban_users()  
    if user_id in banned_users:  
        return await message.reply_text(  
            "<b>⛔️ Tu as été banni du bot.</b>\n\n"  
            "<i>Contacte le support si tu penses que c'est une erreur.</i>",  
            reply_markup=InlineKeyboardMarkup(  
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]]  
            )  
        )  
    
    if not await is_subscribed(client, user_id):  
        return await not_joined(client, message)  

    FILE_AUTO_DELETE = await db.get_del_timer()  

    if not await db.present_user(user_id):  
        try:  
            await db.add_user(user_id)  
        except:  
            pass  

    text = message.text  
    if len(text) > 7:  
        try:  
            base64_string = text.split(" ", 1)[1]  
        except IndexError:  
            return  

        # ===== NOUVELLE LOGIQUE ADSGRAM =====
        # Vérifier la session AdsGram AVANT de décoder
        has_access, status_msg = await check_session_and_prompt(client, user_id, message)
        
        if not has_access:
            # L'utilisateur n'a pas accès, le message de pub a déjà été envoyé
            return
        # ===== FIN NOUVELLE LOGIQUE =====

        string = await decode(base64_string)  
        argument = string.split("-")  

        ids = []  
        if len(argument) == 3:  
            try:  
                start = int(int(argument[1]) / abs(client.db_channel.id))  
                end = int(int(argument[2]) / abs(client.db_channel.id))  
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))  
            except Exception as e:  
                print(f"Error decoding IDs: {e}")  
                return  

        elif len(argument) == 2:  
            try:  
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]  
            except Exception as e:  
                print(f"Error decoding ID: {e}")  
                return  

        temp_msg = await message.reply("<b>⏳ Préparation des médias...</b>")  
        try:  
            messages = await get_messages(client, ids)  
        except Exception as e:  
            await message.reply_text("❌ Erreur lors de la récupération des médias")  
            print(f"Error getting messages: {e}")  
            return  
        finally:  
            await temp_msg.delete()  

        sent_messages = []  

        for msg in messages:  
            sent_msg = await send_with_progress(client, message, msg)  
            if sent_msg:  
                sent_messages.append(sent_msg)  

        # ===== AFFICHER LE STATUT DE SESSION =====
        if status_msg and sent_messages:
            await message.reply_text(f"<b>{status_msg}</b>")
        # ===== FIN AFFICHAGE STATUT =====

        if FILE_AUTO_DELETE > 0 and sent_messages:  
            notification_msg = await message.reply(  
                f"<b>❗️ IMPORTANT ❗️\n\n⚠️ Ce(s) fichier(s) sera(ont) supprimé(s) dans {get_exp_time(FILE_AUTO_DELETE)} (pour cause de droits d'auteurs)\n\n📌 Veuillez la(es) transférez pour ne pas la(es) perdre(s)..</b>"  
            )  

            await asyncio.sleep(FILE_AUTO_DELETE)  

            for snt_msg in sent_messages:      
                try:      
                    await snt_msg.delete()    
                except Exception as e:  
                    print(f"Error deleting message {snt_msg.id}: {e}")  

            try:  
                reload_url = (  
                    f"https://t.me/{client.username}?start={message.command[1]}"  
                    if message.command and len(message.command) > 1  
                    else None  
                )  
                keyboard = InlineKeyboardMarkup(  
                    [[InlineKeyboardButton("🔄 Récupérer à nouveau", url=reload_url)]]  
                ) if reload_url else None  

                await notification_msg.edit(  
                    "<b>🗑️ Le(s) média(s) a/ont été supprimé(s) !</b>\n\n"  
                    "<i>Cliquez ci-dessous pour les récupérer à nouveau</i>",  
                    reply_markup=keyboard  
                )  
            except Exception as e:  
                print(f"Error updating notification: {e}")  
    else:  
        reply_markup = InlineKeyboardMarkup(  
            [  
                [InlineKeyboardButton("📢 Chaîne Officielle", url="https://t.me/WorldZPrime")],  
                [  
                    InlineKeyboardButton("ℹ️ À Propos", callback_data="about"),  
                    InlineKeyboardButton("❓ Aide", callback_data="help")  
                ],
                [InlineKeyboardButton("📺 Ma Session", callback_data="check_session")]  # NOUVEAU BOUTON
            ]  
        )  
        await message.reply_photo(  
            photo=START_PIC,  
            caption=START_MSG.format(  
                first=message.from_user.first_name,  
                last=message.from_user.last_name,  
                username=None if not message.from_user.username else '@' + message.from_user.username,  
                mention=message.from_user.mention,  
                id=message.from_user.id  
            ),  
            reply_markup=reply_markup,  
            message_effect_id=5104841245755180586  
        )  

chat_data_cache = {}

async def not_joined(client: Client, message: Message):
    temp = await message.reply("<b><i>Vérification en cours...</i></b>")

    user_id = message.from_user.id  
    buttons = []  
    count = 0  

    try:  
        all_channels = await db.show_channels()  
        for total, chat_id in enumerate(all_channels, start=1):  
            mode = await db.get_channel_mode(chat_id)  

            await message.reply_chat_action(ChatAction.TYPING)  

            if not await is_sub(client, user_id, chat_id):  
                try:  
                    if chat_id in chat_data_cache:  
                        data = chat_data_cache[chat_id]  
                    else:  
                        data = await client.get_chat(chat_id)  
                        chat_data_cache[chat_id] = data  

                    name = data.title  

                    if mode == "on" and not data.username:  
                        invite = await client.create_chat_invite_link(  
                            chat_id=chat_id,  
                            creates_join_request=True,  
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None  
                        )  
                        link = invite.invite_link  
                    else:  
                        if data.username:  
                            link = f"https://t.me/{data.username}"  
                        else:  
                            invite = await client.create_chat_invite_link(  
                                chat_id=chat_id,  
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None)  
                            link = invite.invite_link  

                    buttons.append([InlineKeyboardButton(text=name, url=link)])  
                    count += 1  
                    await temp.edit(f"<b>🔍 Vérification {count}/{len(all_channels)}...</b>")  

                except Exception as e:  
                    print(f"Error with chat {chat_id}: {e}")  
                    return await temp.edit(  
                        f"<b><i>❌ Erreur technique</i></b>\n"  
                        f"<i>Contactez @ZeeXDevBot</i>\n\n"  
                        f"<code>Raison: {e}</code>"  
                    )  

        try:  
            buttons.append([  
                InlineKeyboardButton(  
                    text='🔄 Vérifier à nouveau',  
                    url=f"https://t.me/{client.username}?start={message.command[1]}"  
                )  
            ])  
        except IndexError:  
            pass  

        await message.reply_photo(  
            photo=FORCE_PIC,  
            caption=FORCE_MSG.format(  
                first=message.from_user.first_name,  
                last=message.from_user.last_name,  
                username=None if not message.from_user.username else '@' + message.from_user.username,  
                mention=message.from_user.mention,  
                id=message.from_user.id  
            ),  
            reply_markup=InlineKeyboardMarkup(buttons),  
        )  

    except Exception as e:  
        print(f"Final Error: {e}")  
        await temp.edit(  
            f"<b><i>❌ Erreur critique</i></b>\n"  
            f"<i>Contactez @ZeeXDevBot</i>\n\n"  
            f"<code>Détails: {e}</code>"  
        )

@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Fermer", callback_data="close")]])
    await message.reply(text=CMD_TXT, reply_markup=reply_markup, quote=True)