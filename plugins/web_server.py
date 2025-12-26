from aiohttp import web
from database.database import db
from config import FREE_SESSION_DURATION
import logging

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running"})

@routes.get("/adsgram/reward")
async def adsgram_reward_handler(request):
    """
    Endpoint appelé par AdsGram quand un utilisateur termine une pub
    URL à configurer sur AdsGram: https://ton-domaine.com/adsgram/reward?userid=[userId]
    """
    try:
        # Récupérer l'user_id depuis les paramètres de l'URL
        user_id = request.query.get('userid')
        
        if not user_id:
            logger.error("AdsGram reward: userid manquant")
            return web.json_response(
                {"status": "error", "message": "userid required"},
                status=400
            )
        
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"AdsGram reward: userid invalide: {user_id}")
            return web.json_response(
                {"status": "error", "message": "invalid userid"},
                status=400
            )
        
        # Vérifier si l'utilisateur peut regarder une pub
        can_watch = await db.can_watch_ad(user_id)
        
        if not can_watch:
            logger.warning(f"AdsGram reward: utilisateur {user_id} a déjà une session récente")
            return web.json_response(
                {"status": "error", "message": "session already active"},
                status=429
            )
        
        # Activer la session gratuite
        await db.set_free_session(user_id, FREE_SESSION_DURATION)
        
        logger.info(f"✅ AdsGram: Session activée pour l'utilisateur {user_id}")
        
        # Répondre à AdsGram que tout s'est bien passé
        return web.json_response({
            "status": "success",
            "message": "reward granted",
            "user_id": user_id,
            "duration_hours": FREE_SESSION_DURATION
        })
        
    except Exception as e:
        logger.error(f"Erreur dans adsgram_reward_handler: {e}")
        return web.json_response(
            {"status": "error", "message": str(e)},
            status=500
        )

async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app