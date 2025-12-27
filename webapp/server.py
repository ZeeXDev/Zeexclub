# webapp/server.py
# Serveur Flask pour la WebApp AdsGram avec fichiers séparés

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sys
import os
import asyncio

# Ajouter le chemin parent pour importer database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import db
from config import ADSGRAM_BLOCK_ID

# Définir explicitement les chemins pour Flask
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
CORS(app)

# Helper pour exécuter les fonctions async
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

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
        session = run_async(db.get_user_session(user_id))
        has_active = run_async(db.has_active_session(user_id))
        can_watch = run_async(db.can_watch_ad(user_id))
        
        remaining_time = run_async(db.get_session_remaining_time(user_id))
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/reward', methods=['POST'])
def reward_session():
    """Récompense l'utilisateur après avoir vu une pub"""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id requis'}), 400
    
    try:
        # Vérifier si l'utilisateur peut regarder une pub
        can_watch = run_async(db.can_watch_ad(user_id))
        
        if not can_watch:
            return jsonify({
                'success': False,
                'error': 'Cooldown actif, réessayez plus tard'
            }), 400
        
        # Ajouter 20h de session
        session_data = run_async(db.add_session_time(user_id, hours=20))
        
        return jsonify({
            'success': True,
            'message': '20h de session ajoutées',
            'session_expiry': session_data.get('session_expiry'),
            'total_ads_watched': session_data.get('total_ads_watched')
        })
    
    except Exception as e:
        print(f"Erreur dans reward_session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['POST'])
def admin_stats():
    """Admin: Statistiques globales"""
    data = request.json
    admin_id = data.get('admin_id')
    
    if not admin_id:
        return jsonify({'error': 'admin_id requis'}), 400
    
    try:
        # Vérifier que c'est un admin
        is_admin = run_async(db.admin_exist(admin_id))
        if not is_admin:
            return jsonify({'error': 'Non autorisé'}), 403
        
        stats = run_async(db.get_ads_stats())
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        print(f"Erreur dans admin_stats: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Serveur WebApp AdsGram démarré")
    print("=" * 50)
    print(f"📁 Template folder: {template_dir}")
    print(f"📁 Static folder: {static_dir}")
    print(f"📺 Block ID: {ADSGRAM_BLOCK_ID if ADSGRAM_BLOCK_ID else 'NON CONFIGURÉ ⚠️'}")
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
    # debug=True pour voir les erreurs en développement
    app.run(host='0.0.0.0', port=5000, debug=True)