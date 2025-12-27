// webapp/static/js/app.js

const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

let adController;
let sessionData = null;
let countdownInterval = null;

// Initialiser AdsGram
async function initAdsGram() {
    try {
        if (!BLOCK_ID || BLOCK_ID === '') {
            console.error('Block ID AdsGram non configuré');
            return;
        }
        adController = window.Adsgram.init({ blockId: BLOCK_ID });
        console.log('AdsGram initialisé avec succès');
    } catch (error) {
        console.error('Erreur lors de l\'initialisation AdsGram:', error);
    }
}

// Charger les données de session
async function loadSessionData() {
    try {
        const userId = tg.initDataUnsafe?.user?.id;
        
        if (!userId) {
            showMessage('Impossible de récupérer votre ID utilisateur', 'error');
            return;
        }

        const response = await fetch('/api/session', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({
                user_id: userId
            })
        });

        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }

        sessionData = await response.json();
        
        if (sessionData.success) {
            updateUI();
        } else {
            showMessage('Erreur lors du chargement des données', 'error');
        }
    } catch (error) {
        showMessage('Erreur de connexion au serveur', 'error');
        console.error('Erreur loadSessionData:', error);
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('content').style.display = 'block';
    }
}

// Mettre à jour l'interface
function updateUI() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const timeRemaining = document.getElementById('timeRemaining');
    const totalAds = document.getElementById('totalAds');
    const nextAdIn = document.getElementById('nextAdIn');
    const watchAdBtn = document.getElementById('watchAdBtn');
    const buttonInfo = document.getElementById('buttonInfo');

    // Afficher le statut de la session
    if (sessionData.has_active_session) {
        statusDot.classList.add('active');
        statusText.textContent = 'Session Active';
        timeRemaining.textContent = formatTime(sessionData.remaining_seconds);
        
        // Démarrer le compte à rebours
        startCountdown();
    } else {
        statusDot.classList.remove('active');
        statusText.textContent = 'Session Inactive';
        timeRemaining.textContent = '00:00:00';
    }

    // Afficher les statistiques
    totalAds.textContent = sessionData.total_ads_watched || 0;

    // Gérer le bouton de pub
    if (sessionData.can_watch_ad) {
        watchAdBtn.disabled = false;
        buttonInfo.textContent = 'Gagnez 20h d\'accès gratuit';
        nextAdIn.textContent = 'Maintenant';
    } else {
        watchAdBtn.disabled = true;
        const cooldownHours = Math.ceil(sessionData.cooldown_remaining / 3600);
        buttonInfo.textContent = `Prochaine pub disponible dans ${cooldownHours}h`;
        nextAdIn.textContent = cooldownHours + 'h';
    }
}

// Démarrer le compte à rebours
function startCountdown() {
    // Arrêter le compte à rebours précédent s'il existe
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }

    countdownInterval = setInterval(() => {
        if (sessionData && sessionData.remaining_seconds > 0) {
            sessionData.remaining_seconds--;
            document.getElementById('timeRemaining').textContent = 
                formatTime(sessionData.remaining_seconds);
            
            if (sessionData.remaining_seconds <= 0) {
                clearInterval(countdownInterval);
                loadSessionData(); // Recharger les données
            }
        }
    }, 1000);
}

// Formater le temps (HH:MM:SS)
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${pad(hours)}:${pad(minutes)}:${pad(secs)}`;
}

// Ajouter un zéro devant les nombres < 10
function pad(num) {
    return num.toString().padStart(2, '0');
}

// Afficher une pub
async function showAd() {
    if (!adController) {
        showMessage('AdsGram non initialisé. Vérifiez votre configuration.', 'error');
        return;
    }

    try {
        // Feedback haptique
        if (tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('medium');
        }
        
        // Afficher la pub
        await adController.show()
            .then(async () => {
                // Pub vue avec succès - Récompenser l'utilisateur
                const userId = tg.initDataUnsafe?.user?.id;
                
                const response = await fetch('/api/reward', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json' 
                    },
                    body: JSON.stringify({
                        user_id: userId
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    // Feedback de succès
                    if (tg.HapticFeedback) {
                        tg.HapticFeedback.notificationOccurred('success');
                    }
                    
                    showMessage('✅ Session de 20h activée avec succès !', 'success');
                    
                    // Recharger les données après 1 seconde
                    setTimeout(() => {
                        loadSessionData();
                    }, 1000);
                } else {
                    showMessage('❌ ' + (result.error || 'Erreur lors de l\'activation'), 'error');
                }
            })
            .catch((error) => {
                // L'utilisateur a fermé la pub ou erreur
                if (error.code === 'AdNotLoaded') {
                    showMessage('Pub non disponible pour le moment', 'error');
                } else {
                    console.error('Erreur pub:', error);
                }
            });
    } catch (error) {
        console.error('Erreur lors de l\'affichage de la pub:', error);
        showMessage('Une erreur est survenue', 'error');
    }
}

// Afficher un message
function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.className = `message ${type} show`;
    messageDiv.textContent = text;
    
    setTimeout(() => {
        messageDiv.classList.remove('show');
        setTimeout(() => {
            messageDiv.textContent = '';
            messageDiv.className = 'message';
        }, 300);
    }, 3000);
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    initAdsGram();
    loadSessionData();
});

// Nettoyer le compte à rebours lors de la fermeture
window.addEventListener('beforeunload', () => {
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
});