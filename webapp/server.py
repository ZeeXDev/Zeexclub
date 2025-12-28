# webapp/server.py
# Serveur Flask pour la WebApp AdsGram avec fichiers séparés

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sys
import os

# Ajouter le chemin parent pour importer database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ADSGRAM_BLOCK_ID, DB_URI, DB_NAME

# Import asyncio
import asyncio
import motor.motor_asyncio

# Définir explicitement les chemins pour Flask
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
CORS(app)

# Connexion MongoDB directe pour la WebApp
client = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = client[DB_NAME]
user_sessions = database['user_sessions']


# Helper pour exécuter les fonctions async SANS fermer le loop
def run_async(coro):
    """Exécute une coroutine de manière sûre"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        return result
    except Exception as e:
        print(f"Error in run_async: {e}")
        return None
    finally:
        try:
            loop.close()
        except:
            pass


# ========== FONCTIONS DATABASE (copie simplifiée) ==========

async def get_user_session(user_id: int):
    """Récupère la session d'un utilisateur"""
    try:
        return await user_sessions.find_one({'_id': user_id})
    except Exception as e:
        print(f"Error getting session: {e}")
        return None


async def has_active_session(user_id: int):
    """Vérifie si la session est active"""
    try:
        session = await get_user_session(user_id)
        if not session:
            return False
        
        expiry = session.get('session_expiry')
        if not expiry:
            return False
        
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)
        
        return datetime.now() < expiry
    except Exception as e:
        print(f"Error checking active session: {e}")
        return False


async def get_session_remaining_time(user_id: int):
    """Temps restant de session"""
    try:
        session = await get_user_session(user_id)
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
    except Exception as e:
        print(f"Error getting remaining time: {e}")
        return None


async def can_watch_ad(user_id: int):
    """Vérifie si l'utilisateur peut regarder une pub"""
    try:
        session = await get_user_session(user_id)
        if not session:
            return True
        
        last_watch = session.get('last_ad_watch')
        if not last_watch:
            return True
        
        if isinstance(last_watch, str):
            last_watch = datetime.fromisoformat(last_watch)
        
        cooldown_end = last_watch + timedelta(hours=20)
        return datetime.now() >= cooldown_end
    except Exception as e:
        print(f"Error checking ad cooldown: {e}")
        return True


async def add_session_time(user_id: int, hours: int = 20):
    """Ajoute du temps de session"""
    try:
        session = await get_user_session(user_id)
        now = datetime.now()
        
        if session and await has_active_session(user_id):
            current_expiry = session.get('session_expiry')
            if isinstance(current_expiry, str):
                current_expiry = datetime.fromisoformat(current_expiry)
            new_expiry = current_expiry + timedelta(hours=hours)
        else:
            new_expiry = now + timedelta(hours=hours)
        
        session_data = {
            '_id': user_id,
            'session_expiry': new_expiry.isoformat(),
            'last_ad_watch': now.isoformat(),
            'total_ads_watched': session.get('total_ads_watched', 0) + 1 if session else 1,
            'updated_at': now.isoformat()
        }
        
        await user_sessions.update_one(
            {'_id': user_id},
            {'$set': session_data},
            upsert=True
        )
        
        return session_data
    except Exception as e:
        print(f"Error adding session time: {e}")
        return None


# ========== ROUTES ==========

@app.route('/')
def index():
    """Page principale de la WebApp"""
    return render_template('index.html', block_id=ADSGRAM_BLOCK_ID)


@app.route('/api/session', methods=['POST'])
def get_session():
    """Récupère les informations de session d'un utilisateur"""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id requis'}), 400
    
    try:
        session = run_async(get_user_session(user_id))
        has_active = run_async(has_active_session(user_id))
        can_watch = run_async(can_watch_ad(user_id))
        
        remaining_time = run_async(get_session_remaining_time(user_id))
        remaining_seconds = int(remaining_time.total_seconds()) if remaining_time else 0
        
        # Calculer le temps avant la prochaine pub
        cooldown_remaining = 0
        if session and not can_watch:
            last_watch = session.get('last_ad_watch')
            if last_watch:
                if isinstance(last_watch, str):
                    last_watch = datetime.fromisoformat(last_watch)
                cooldown_end = last_watch + timedelta(hours=20)
                cooldown_remaining = int((cooldown_end - datetime.now()).total_seconds())
                if cooldown_remaining < 0:
                    cooldown_remaining = 0
        
        return jsonify({
            'success': True,
            'has_active_session': has_active,
            'remaining_seconds': remaining_seconds,
            'can_watch_ad': can_watch,
            'cooldown_remaining': cooldown_remaining,
            'total_ads_watched': session.get('total_ads_watched', 0) if session else 0,
            'session_expiry': session.get('session_expiry') if session else None
        })
    
    except Exception as e:
        print(f"Erreur dans get_session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reward', methods=['POST'])
def reward_session():
    """Récompense l'utilisateur après avoir vu une pub"""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id requis'}), 400
    
    try:
        # Vérifier si l'utilisateur peut regarder une pub
        can_watch = run_async(can_watch_ad(user_id))
        
        if not can_watch:
            return jsonify({
                'success': False,
                'error': 'Cooldown actif, réessayez plus tard'
            }), 400
        
        # Ajouter 20h de session
        session_data = run_async(add_session_time(user_id, hours=20))
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'ajout de la session'
            }), 500
        
        return jsonify({
            'success': True,
            'message': '20h de session ajoutées',
            'session_expiry': session_data.get('session_expiry'),
            'total_ads_watched': session_data.get('total_ads_watched')
        })
    
    except Exception as e:
        print(f"Erreur dans reward_session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Serveur WebApp AdsGram démarré")
    print("=" * 50)
    print(f"📁 Template folder: {template_dir}")
    print(f"📁 Static folder: {static_dir}")
    print(f"📺 Block ID: {ADSGRAM_BLOCK_ID if ADSGRAM_BLOCK_ID else 'NON CONFIGURÉ ⚠️'}")
    print(f"🗄️  Database: {DB_NAME}")
    print("=" * 50)
    print(f"🌐 Accéder à: http://localhost:5000")
    print("=" * 50)
    
    if not ADSGRAM_BLOCK_ID:
        print("\n⚠️  ATTENTION: Block ID AdsGram non configuré!")
        print("Définissez la variable ADSGRAM_BLOCK_ID dans config.py\n")
    
    # Vérifier que les dossiers existent
    if not os.path.exists(template_dir):
        print(f"❌ ERREUR: Le dossier templates/ n'existe pas à {template_dir}")
    if not os.path.exists(static_dir):
        print(f"❌ ERREUR: Le dossier static/ n'existe pas à {static_dir}")
    
    # Démarrer le serveur Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)