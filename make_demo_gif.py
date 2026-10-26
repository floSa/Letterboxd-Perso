import os
import time
import subprocess
import shutil
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "docs/assets"
VIDEO_DIR = "docs/assets/temp_video"
GIF_PATH = os.path.join(OUTPUT_DIR, "demo.gif")
MP4_PATH = os.path.join(OUTPUT_DIR, "demo.mp4")
FFMPEG_EXE = r"C:\Program Files\ShareX\ffmpeg.exe"

os.makedirs(OUTPUT_DIR, exist_ok=True)
if os.path.exists(VIDEO_DIR):
    shutil.rmtree(VIDEO_DIR)
os.makedirs(VIDEO_DIR, exist_ok=True)

def run():
    print("=== Étape 1 : Enregistrement vidéo Playwright haute fluidité (Octobre 2026) ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True
        )
        context = browser.new_context(
            viewport={"width": 1180, "height": 740},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1180, "height": 740}
        )
        page = context.new_page()

        # Curseur souris réaliste haute visibilité avec effet d'onde au clic
        page.add_init_script("""
            window.addEventListener('DOMContentLoaded', () => {
                const cursor = document.createElement('div');
                cursor.id = 'virtual-mouse';
                cursor.innerHTML = `
                    <svg width="30" height="30" viewBox="0 0 30 30" fill="none" style="filter: drop-shadow(2px 3px 4px rgba(0,0,0,0.8));">
                        <path d="M4 3L26 14L15 18L10 28L4 3Z" fill="#ffffff" stroke="#0f172a" stroke-width="2.2" stroke-linejoin="round"/>
                        <circle cx="5" cy="4" r="3" fill="#f59e0b"/>
                    </svg>
                    <div id="click-ripple" style="
                        position: absolute;
                        top: 0px;
                        left: 0px;
                        width: 32px;
                        height: 32px;
                        border-radius: 50%;
                        background: rgba(16, 185, 129, 0.65);
                        transform: scale(0);
                        pointer-events: none;
                        transition: transform 0.3s ease-out, opacity 0.3s ease-out;
                        opacity: 0;
                    "></div>
                `;
                cursor.style.position = 'fixed';
                cursor.style.top = '0';
                cursor.style.left = '0';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '9999999';
                cursor.style.transform = 'translate(-50px, -50px)';
                document.body.appendChild(cursor);

                window.currentMouseX = 250;
                window.currentMouseY = 150;

                window.setMousePos = (x, y) => {
                    window.currentMouseX = x;
                    window.currentMouseY = y;
                    cursor.style.transform = `translate(${x}px, ${y}px)`;
                };

                window.triggerClickEffect = () => {
                    const ripple = document.getElementById('click-ripple');
                    if (ripple) {
                        ripple.style.transition = 'none';
                        ripple.style.transform = 'scale(0)';
                        ripple.style.opacity = '1';
                        setTimeout(() => {
                            ripple.style.transition = 'transform 0.35s ease-out, opacity 0.35s ease-out';
                            ripple.style.transform = 'scale(2.2)';
                            ripple.style.opacity = '0';
                        }, 25);
                    }
                };

                // Défilement fluide progressif pas-à-pas
                window.smoothStepScroll = async (selector, dx, dy, steps = 24, delayMs = 20) => {
                    const target = selector === 'window' ? window : document.querySelector(selector);
                    if (!target) return;
                    for (let i = 0; i < steps; i++) {
                        if (selector === 'window') {
                            window.scrollBy(dx / steps, dy / steps);
                        } else {
                            target.scrollBy(dx / steps, dy / steps);
                        }
                        await new Promise(r => setTimeout(r, delayMs));
                    }
                };
            });
        """)

        # Fonctions d'assistance pour le pilotage fluide
        def glide_mouse(target_selector, steps=18, pause_after=0.3):
            el = page.wait_for_selector(target_selector)
            box = el.bounding_box()
            if not box:
                return el
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2

            cur = page.evaluate("() => ({ x: window.currentMouseX || 250, y: window.currentMouseY || 150 })")
            sx, sy = cur["x"], cur["y"]

            for i in range(1, steps + 1):
                t = i / steps
                # Ease out quad pour un mouvement naturel
                ease = 1 - (1 - t) * (1 - t)
                x = sx + (target_x - sx) * ease
                y = sy + (target_y - sy) * ease
                page.evaluate(f"window.setMousePos({x}, {y})")
                time.sleep(0.02)

            time.sleep(pause_after)
            return el

        def click_with_mouse(target_selector, pause_after=0.6):
            el = glide_mouse(target_selector, steps=18, pause_after=0.25)
            page.evaluate("window.triggerClickEffect()")
            el.click()
            time.sleep(pause_after)

        def smooth_scroll_window(dy, steps=25, delay_ms=20):
            page.evaluate(f"window.smoothStepScroll('window', 0, {dy}, {steps}, {delay_ms})")
            time.sleep((steps * delay_ms) / 1000 + 0.3)

        def smooth_scroll_element(selector, dx, steps=25, delay_ms=20):
            page.evaluate(f"window.smoothStepScroll('{selector}', {dx}, 0, {steps}, {delay_ms})")
            time.sleep((steps * delay_ms) / 1000 + 0.3)

        print("1. Ouverture de l'application sur Octobre 2026...")
        page.goto("http://localhost:8080")
        page.wait_for_selector(".movie-row", timeout=10000)
        time.sleep(1.2)

        # 2. Défilement vertical pour explorer les sorties de la semaine
        print("2. Défilement vertical fluide dans la semaine...")
        smooth_scroll_window(350, steps=24, delay_ms=20)
        time.sleep(0.8)
        smooth_scroll_window(-350, steps=24, delay_ms=20)
        time.sleep(0.6)

        # 3. Noter le 1er film : 3 étoiles
        print("3. Notation 3 étoiles sur le 1er film...")
        star3 = ".movie-row:first-child .rating-widget:first-of-type .star-unit:nth-child(3) .click-half.right"
        click_with_mouse(star3, pause_after=0.9)

        # 4. Noter le même film : 4 cœurs
        print("4. Priorité 4 cœurs sur le même film...")
        heart4 = ".movie-row:first-child .rating-widget:nth-of-type(2) .star-unit:nth-child(4) .click-half.right"
        click_with_mouse(heart4, pause_after=0.9)

        # 5. Marquer la possession sur le même film (cible verte)
        print("5. Marquer le film comme possédé...")
        owned_btn = ".movie-row:first-child .btn-owned-target"
        click_with_mouse(owned_btn, pause_after=1.0)

        # 6. Bascule en vue Mois (Octobre 2026)
        print("6. Passage à la vue Mois...")
        click_with_mouse('.scale-btn[data-scale="month"]', pause_after=1.2)
        page.wait_for_selector(".carousel-block", timeout=5000)

        # 7. Défilement horizontal fluide dans le carrousel du mois
        print("7. Défilement horizontal fluide dans le carrousel du mois...")
        glide_mouse(".carousel-block:first-child .carousel-track", steps=15, pause_after=0.3)
        # Faire glisser les cartes vers la gauche (scroll vers la droite de 480px)
        smooth_scroll_element(".carousel-block:first-child .carousel-track", 480, steps=28, delay_ms=22)
        time.sleep(0.9)
        # Faire revenir doucement les cartes
        smooth_scroll_element(".carousel-block:first-child .carousel-track", -480, steps=28, delay_ms=22)
        time.sleep(0.8)

        # 8. Bascule en vue Année (2026)
        print("8. Passage à la vue Année...")
        click_with_mouse('.scale-btn[data-scale="year"]', pause_after=1.2)
        page.wait_for_selector(".carousel-block", timeout=5000)

        # 9. Défilement dans la vue Année (vertical sur les mois et horizontal sur un carrousel)
        print("9. Défilements dans la vue Année...")
        smooth_scroll_window(360, steps=24, delay_ms=20)
        time.sleep(0.8)
        smooth_scroll_window(-360, steps=24, delay_ms=20)
        time.sleep(0.6)
        # Défilement horizontal dans un mois
        smooth_scroll_element(".carousel-block:first-child .carousel-track", 450, steps=26, delay_ms=22)
        time.sleep(0.8)
        smooth_scroll_element(".carousel-block:first-child .carousel-track", -450, steps=26, delay_ms=22)
        time.sleep(0.8)

        # 10. Onglet Ma Sélection (Watchlist)
        print("10. Consultation de l'onglet Ma Sélection...")
        click_with_mouse('.nav-tab[data-tab="watchlist"]', pause_after=1.6)

        # 11. Onglet Films Vus
        print("11. Consultation de l'onglet Films Vus...")
        click_with_mouse('.nav-tab[data-tab="watched"]', pause_after=1.6)

        # 12. Retour final sur Sorties Cinéma
        print("12. Retour sur Sorties Cinéma...")
        click_with_mouse('.nav-tab[data-tab="triage"]', pause_after=1.8)

        # Fermeture et enregistrement de la vidéo
        browser.close()

    print("=== Étape 2 : Conversion vidéo haute fidélité avec ffmpeg ===")
    video_files = [os.path.join(VIDEO_DIR, f) for f in os.listdir(VIDEO_DIR) if f.endswith(".webm")]
    if not video_files:
        raise RuntimeError("Aucun fichier vidéo capturé !")
    src_video = video_files[0]
    print(f"Vidéo source capturée : {src_video}")

    # 1. Copie / conversion MP4
    cmd_mp4 = [
        FFMPEG_EXE, "-y", "-i", src_video,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
        MP4_PATH
    ]
    subprocess.run(cmd_mp4, check=True)
    print(f"Vidéo MP4 enregistrée : {MP4_PATH}")

    # 2. Conversion GIF ultra-fluide (12 fps, palettegen adaptative 128 couleurs)
    # Filtre bayer 3 pour un tramage très propre sans grain excessif
    filter_complex = "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3"
    cmd_gif = [
        FFMPEG_EXE, "-y", "-i", src_video,
        "-vf", filter_complex,
        GIF_PATH
    ]
    subprocess.run(cmd_gif, check=True)

    gif_size = os.path.getsize(GIF_PATH) / (1024 * 1024)
    print(f"\nSUCCESS : GIF généré avec succès dans {GIF_PATH} ({gif_size:.2f} Mo)")

    # Nettoyage vidéo temporaire
    shutil.rmtree(VIDEO_DIR)

if __name__ == "__main__":
    run()
