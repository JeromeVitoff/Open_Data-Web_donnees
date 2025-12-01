# model/alerts.py
"""
Module de gestion des alertes email pour AurorAlerte.
Envoie des notifications quand les conditions d'observation sont favorables.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd


def send_aurora_alert_email(
    recipient_email: str,
    kp_value: float,
    location: str,
    score: float,
    cloud_pct: float = None,
    dark_flag: int = None,
    smtp_config: dict = None,
    min_kp: int = None  # ← NOUVEAU PARAMÈTRE
) -> tuple[bool, str]:
    """
    Envoie une alerte email quand les conditions d'aurores sont favorables.
    
    Args:
        recipient_email: Email du destinataire
        kp_value: Indice Kp actuel (0-9)
        location: Nom de la localisation
        score: Score de probabilité (0-1)
        cloud_pct: Pourcentage de couverture nuageuse (optionnel)
        dark_flag: 1 si nuit, 0 si jour (optionnel)
        smtp_config: Configuration SMTP (serveur, port, identifiants)
        min_kp: Kp minimum calculé pour cette localisation (optionnel)
    
    Returns:
        (success: bool, message: str) - Tuple avec succès et message
    
    Usage:
        >>> success, msg = send_aurora_alert_email(
        ...     "user@example.com", 6.5, "Stockholm", 0.82,
        ...     cloud_pct=15.0, dark_flag=1, min_kp=4,
        ...     smtp_config={...}
        ... )
        >>> print(msg)
        "Email envoyé avec succès !"
    """
    
    if not smtp_config:
        return False, "Configuration SMTP manquante"
    
    try:
        # Déterminer l'intensité de l'alerte
        if score >= 0.7:
            emoji = "🟢"
            status = "EXCELLENT"
            color = "#2e8540"  # Vert
        elif score >= 0.4:
            emoji = "🟡"
            status = "BON"
            color = "#e3b505"  # Jaune
        else:
            emoji = "🔴"
            status = "MOYEN"
            color = "#c0392b"  # Rouge
        
        # Calculer le ciel dégagé si cloud_pct fourni
        clear_pct = 100 - cloud_pct if cloud_pct is not None else None
        
        # Message personnalisé selon le Kp minimum
        kp_info_html = ""
        kp_info_text = ""
        
        if min_kp is not None:
            if min_kp <= 2:
                kp_message = f"🎉 Excellente nouvelle ! Votre localisation est idéale pour observer les aurores (Kp minimum : {min_kp}). Vous en verrez souvent !"
            elif min_kp <= 5:
                kp_message = f"✅ Bonne localisation ! Les aurores sont régulièrement visibles ici (Kp minimum : {min_kp})."
            elif min_kp <= 7:
                kp_message = f"⚠️ Les aurores sont rares à cette latitude (Kp minimum : {min_kp}). Profitez de cette occasion !"
            else:
                kp_message = f"🔴 Événement exceptionnel ! Les aurores sont très rares ici (Kp minimum : {min_kp}). Ne manquez pas ce spectacle unique !"
            
            kp_info_html = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; border-radius: 3px;">
                <p style="margin: 0;"><strong>📍 Information sur votre localisation :</strong></p>
                <p style="margin: 10px 0 0 0;">{kp_message}</p>
            </div>
            """
            
            kp_info_text = f"\n📍 Information : {kp_message}\n"
        
        # Construire le message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🌌 Alerte Aurores ! Kp = {kp_value:.1f} à {location}'
        msg['From'] = smtp_config['sender_email']
        msg['To'] = recipient_email
        
        # Corps de l'email en HTML
        html_body = f"""
        <html>
          <head>
            <style>
              body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
              }}
              .header {{
                background-color: {color};
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
              }}
              .content {{
                padding: 20px;
                background-color: #f9f9f9;
              }}
              .status-box {{
                background-color: white;
                padding: 15px;
                border-left: 4px solid {color};
                margin: 20px 0;
                border-radius: 3px;
              }}
              .metric {{
                display: inline-block;
                margin: 10px 20px 10px 0;
              }}
              .metric-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
              }}
              .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: {color};
              }}
              .tips {{
                background-color: #e8f4f8;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
              }}
              .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: {color};
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
              }}
              .footer {{
                text-align: center;
                padding: 20px;
                font-size: 12px;
                color: #666;
              }}
            </style>
          </head>
          <body>
            <div class="header">
              <h1>🌌 ALERTE AURORES BORÉALES !</h1>
              <p style="font-size: 18px; margin: 10px 0;">Conditions {status} détectées</p>
            </div>
            
            <div class="content">
              <p style="font-size: 16px;">
                <strong>📍 Localisation :</strong> {location}
              </p>
              
              {kp_info_html}
              
              <div class="status-box">
                <h2 style="margin-top: 0; color: {color};">{emoji} Statut : {status}</h2>
                
                <div class="metric">
                  <div class="metric-label">Indice Kp Actuel</div>
                  <div class="metric-value">{kp_value:.1f}<span style="font-size: 14px; color: #666;"> / 9</span></div>
                </div>
                
                {f'''
                <div class="metric">
                  <div class="metric-label">Kp Minimum Requis</div>
                  <div class="metric-value">{min_kp}<span style="font-size: 14px; color: #666;"> / 9</span></div>
                </div>
                ''' if min_kp is not None else ''}
                
                <div class="metric">
                  <div class="metric-label">Score de Probabilité</div>
                  <div class="metric-value">{score:.2f}<span style="font-size: 14px; color: #666;"> / 1.0</span></div>
                </div>
                
                {f'''
                <div class="metric">
                  <div class="metric-label">Ciel Dégagé</div>
                  <div class="metric-value">{clear_pct:.0f}<span style="font-size: 14px; color: #666;">%</span></div>
                </div>
                ''' if clear_pct is not None else ''}
                
                {f'''
                <div class="metric">
                  <div class="metric-label">Obscurité</div>
                  <div class="metric-value">{'🌙 Nuit' if dark_flag == 1 else '☀️ Jour'}</div>
                </div>
                ''' if dark_flag is not None else ''}
              </div>
              
              <div class="tips">
                <h3 style="margin-top: 0;">💡 Conseils d'Observation</h3>
                <ul>
                  <li><strong>Meilleure période :</strong> Entre 22h et 2h du matin (heure locale)</li>
                  <li><strong>Lieu idéal :</strong> Trouvez un endroit sombre, loin des lumières de la ville</li>
                  <li><strong>Direction :</strong> Regardez vers le nord</li>
                  <li><strong>Patience :</strong> Les aurores apparaissent souvent par vagues, restez vigilant</li>
                  <li><strong>Photo :</strong> Utilisez un trépied, ISO 1600-3200, pose longue 5-15 secondes</li>
                </ul>
                
                {'''
                <p style="margin-bottom: 0;"><strong>⚠️ Note :</strong> 
                {'Vérifiez les prévisions nuageuses avant de sortir.' if clear_pct and clear_pct < 70 else 
                 'Le ciel est dégagé, conditions parfaites !' if clear_pct and clear_pct >= 70 else 
                 'Vérifiez la météo locale avant de sortir.'}
                </p>
                ''' if clear_pct is not None else ''}
              </div>
              
              <div style="text-align: center;">
                <a href="http://localhost:8501" class="button">
                  Voir le Dashboard Complet
                </a>
              </div>
            </div>
            
            <div class="footer">
              <p><strong>AurorAlerte</strong> - Dashboard de surveillance des aurores boréales</p>
              <p>Vous recevez cet email car vous avez activé les alertes automatiques dans AurorAlerte.</p>
              <p style="font-size: 11px; color: #999;">
                {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
              </p>
            </div>
          </body>
        </html>
        """
        
        # Ajouter version texte simple (fallback)
        text_body = f"""
        🌌 ALERTE AURORES BORÉALES !
        
        Conditions {status} détectées à {location}
        {kp_info_text}
        📊 Données actuelles :
        - Indice Kp actuel : {kp_value:.1f} / 9
        {f'- Kp minimum requis : {min_kp} / 9' if min_kp is not None else ''}
        - Score de Probabilité : {score:.2f} / 1.0
        {f'- Ciel Dégagé : {clear_pct:.0f}%' if clear_pct is not None else ''}
        {f'- Obscurité : {"Nuit" if dark_flag == 1 else "Jour"}' if dark_flag is not None else ''}
        
        💡 Conseils :
        - Sortez entre 22h et 2h du matin
        - Trouvez un endroit sombre
        - Regardez vers le nord
        - Soyez patient !
        
        Voir le dashboard : https://web-production-ff2d6.up.railway.app/
        
        ---
        AurorAlerte - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} UTC
        """
        
        # Attacher les deux versions
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Connexion au serveur SMTP et envoi
        with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
            server.starttls()
            server.login(smtp_config['sender_email'], smtp_config['sender_password'])
            server.send_message(msg)
        
        return True, f"Email envoyé avec succès à {recipient_email}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "Erreur d'authentification SMTP. Vérifiez votre email et mot de passe."
    except smtplib.SMTPException as e:
        return False, f"Erreur SMTP : {str(e)}"
    except Exception as e:
        return False, f"Erreur inattendue : {str(e)}"


def should_send_alert(
    kp_value: float,
    kp_threshold: float,
    last_alert_time: pd.Timestamp = None,
    cooldown_hours: float = 1.0
) -> bool:
    """
    Détermine si une alerte doit être envoyée.
    
    Args:
        kp_value: Indice Kp actuel
        kp_threshold: Seuil Kp pour déclencher l'alerte
        last_alert_time: Timestamp de la dernière alerte envoyée
        cooldown_hours: Heures à attendre entre deux alertes
    
    Returns:
        True si une alerte doit être envoyée, False sinon
    
    Usage:
        >>> should_send_alert(6.5, 5.0, None, 1.0)
        True
        >>> last = pd.Timestamp.now()
        >>> should_send_alert(6.5, 5.0, last, 1.0)  # Immédiatement après
        False
    """
    # Vérifier si Kp dépasse le seuil
    if kp_value is None or kp_value < kp_threshold:
        return False
    
    # Si première alerte
    if last_alert_time is None:
        return True
    
    # Vérifier le cooldown
    now = pd.Timestamp.now()
    time_since_last = (now - last_alert_time).total_seconds() / 3600  # En heures
    
    return time_since_last >= cooldown_hours


def validate_email(email: str) -> bool:
    """
    Valide le format d'une adresse email.
    
    Args:
        email: Adresse email à valider
    
    Returns:
        True si le format est valide, False sinon
    
    Usage:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# ============================================
# EXEMPLE D'UTILISATION
# ============================================

if __name__ == "__main__":
    # Configuration de test
    test_config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': 'votre_email@gmail.com',
        'sender_password': 'votre_mot_de_passe_app'
    }
    
    # Test d'envoi AVEC le Kp minimum
    success, message = send_aurora_alert_email(
        recipient_email="destinataire@example.com",
        kp_value=6.5,
        location="Stockholm, Suède",
        score=0.82,
        cloud_pct=15.0,
        dark_flag=1,
        smtp_config=test_config,
        min_kp=4  # ← NOUVEAU
    )
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")