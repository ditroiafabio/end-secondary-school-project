import pygame
import sys
import os
from settings import *
from database import init_db, get_top10

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # dossier racine du projet


# -------------------------------------------------------
# couleurs utilisées dans tous les écrans du menu
# -------------------------------------------------------

C_BG      = (12,  14,  23)   # fond principal très sombre
C_BG2     = (20,  24,  40)   # fond légèrement plus clair (boutons, séparateurs)
C_ACCENT  = (220, 160,  40)  # doré pour les titres et éléments mis en avant
C_ACCENT2 = (180, 100,  20)  # version plus sombre de l'accent (hover des boutons)
C_TEXT    = (240, 230, 210)  # blanc cassé pour le texte courant
C_MUTED   = (120, 115, 100)  # gris pour les éléments secondaires
C_GOLD    = (255, 215,   0)  # couleur 1ère place du classement
C_SILVER  = (192, 192, 192)  # couleur 2ème place
C_BRONZE  = (205, 127,  50)  # couleur 3ème place


def lerp_color(a, b, t):
    # interpolation linéaire entre deux couleurs RGB selon t (0.0 = couleur a, 1.0 = couleur b)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def draw_text_centered(surface, text, font, color, cx, cy):
    # dessine du texte centré sur le point (cx, cy)
    surf = font.render(text, True, color)
    surface.blit(surf, surf.get_rect(center=(cx, cy)))


# -------------------------------------------------------
# bouton réutilisable avec effet de survol animé
# -------------------------------------------------------

class Button:
    ANIM_SPEED = 0.12   # vitesse de la transition hover (interpolation)
    ICON_SIZE  = 28     # hauteur cible de l'icône en pixels

    def __init__(self, text, cx, cy, w=260, h=54, icon=None):
        self.text    = text
        self.rect    = pygame.Rect(0, 0, w, h)
        self.rect.center = (cx, cy)  # on centre le bouton sur les coordonnées données
        self.hover_t = 0.0   # progression de l'animation hover (0 = normal, 1 = survolé)
        self.click_t = 0.0   # progression de l'animation de clic (flash blanc)

        if icon is not None:
            # on redimensionne l'icône pour qu'elle fasse exactement ICON_SIZE de hauteur
            iw, ih    = icon.get_size()
            scale     = self.ICON_SIZE / ih
            self.icon = pygame.transform.scale(icon, (int(iw * scale), self.ICON_SIZE))
        else:
            self.icon = None

    def update(self, mx, my):
        # on fait glisser hover_t vers 1 si la souris est dessus, vers 0 sinon
        hovered       = self.rect.collidepoint(mx, my)
        target        = 1.0 if hovered else 0.0
        self.hover_t += (target - self.hover_t) * self.ANIM_SPEED
        if self.click_t > 0:
            self.click_t = max(0, self.click_t - 0.08)  # le flash de clic s'estompe progressivement

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.click_t = 1.0  # déclenche le flash
                return True
        return False

    def draw(self, surface, font):
        t = self.hover_t

        # couleurs interpolées selon l'état de hover
        bg         = lerp_color(C_BG2,  C_ACCENT2, t)
        border_col = lerp_color(C_MUTED, C_ACCENT,  t)
        text_col   = lerp_color(C_TEXT,  C_BG,      t)

        if self.click_t > 0:
            # flash blanc au moment du clic
            flash = int(self.click_t * 255)
            bg    = tuple(min(255, bg[i] + flash // 3) for i in range(3))

        # ombre portée décalée de 4px vers le bas
        shadow_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 80), shadow_surf.get_rect(), border_radius=8)
        surface.blit(shadow_surf, (self.rect.x + 4, self.rect.y + 4))

        pygame.draw.rect(surface, bg,         self.rect, border_radius=8)  # fond du bouton
        pygame.draw.rect(surface, border_col, self.rect, 2, border_radius=8)  # bordure (2px)

        # petit reflet en haut du bouton pour un effet légèrement brillant
        highlight = pygame.Rect(self.rect.x + 4, self.rect.y + 2, self.rect.w - 8, 2)
        pygame.draw.rect(surface, lerp_color((60, 60, 60), C_ACCENT, t), highlight)

        if self.icon is not None:
            PAD    = 14  # marge entre le bord gauche et l'icône
            icon_x = self.rect.x + PAD
            icon_y = self.rect.centery - self.icon.get_height() // 2  # centré verticalement
            surface.blit(self.icon, (icon_x, icon_y))
            text_surf = font.render(self.text, True, text_col)
            # texte affiché à droite de l'icône avec un petit espace
            surface.blit(text_surf, (icon_x + self.icon.get_width() + 10,
                                     self.rect.centery - text_surf.get_height() // 2))
        else:
            draw_text_centered(surface, self.text, font, text_col,
                               self.rect.centerx, self.rect.centery)


# -------------------------------------------------------
# fond animé avec des étoiles qui tombent doucement
# -------------------------------------------------------

class Background:
    def __init__(self):
        import random
        # on génère 80 étoiles avec des propriétés aléatoires
        self.stars = [
            {
                "x":     random.randint(0, SCREEN_WIDTH),
                "y":     random.randint(0, SCREEN_HEIGHT),
                "r":     random.uniform(0.5, 2.0),    # rayon en pixels
                "speed": random.uniform(0.1, 0.4),    # vitesse de chute
                "alpha": random.randint(60, 200)       # transparence
            }
            for _ in range(80)
        ]

    def update(self):
        import random
        for s in self.stars:
            s["y"] += s["speed"]  # l'étoile descend
            if s["y"] > SCREEN_HEIGHT:
                # quand elle sort par le bas, on la remet en haut à une position X aléatoire
                s["y"] = 0
                s["x"] = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface):
        surface.fill(C_BG)  # fond sombre de base

        # dégradé en bas de l'écran : lignes horizontales légèrement plus claires
        for i in range(80):
            pygame.draw.line(surface, C_BG2, (0, SCREEN_HEIGHT - i), (SCREEN_WIDTH, SCREEN_HEIGHT - i))

        # dessin de chaque étoile comme un petit cercle semi-transparent
        for s in self.stars:
            ss = pygame.Surface((int(s["r"] * 2 + 2), int(s["r"] * 2 + 2)), pygame.SRCALPHA)
            pygame.draw.circle(ss, (*C_TEXT, s["alpha"]), (int(s["r"] + 1), int(s["r"] + 1)), int(s["r"]))
            surface.blit(ss, (s["x"], s["y"]))


# -------------------------------------------------------
# écran du menu principal (logo + boutons)
# -------------------------------------------------------

class MainMenu:
    def __init__(self, screen, fonts, bg):
        self.screen = screen
        self.fonts  = fonts
        self.bg     = bg
        self.alpha  = 0   # opacité pour le fondu d'entrée (0 = noir, 255 = visible)

        cx = SCREEN_WIDTH // 2

        # chargement et redimensionnement du logo
        logo_raw  = pygame.image.load(os.path.join(BASE_DIR, "assets", "Logo.png")).convert()
        lw, lh    = logo_raw.get_size()
        self.logo = pygame.transform.scale(logo_raw, (int(lw * min(1.0, 250/lh)), int(lh * min(1.0, 250/lh))))

        def load_icon(name):
            return pygame.image.load(os.path.join(BASE_DIR, "assets", "Menu", name)).convert()

        # deux boutons principaux avec leur icône respective
        self.btn_play = Button("JOUER",      cx, 360, icon=load_icon("Controller.png"))
        self.btn_rank = Button("CLASSEMENT", cx, 440, icon=load_icon("Ranking.png"))

    def handle_event(self, event):
        if self.btn_play.is_clicked(event): return "pseudo"    # on passe à l'écran de saisie du pseudo
        if self.btn_rank.is_clicked(event): return "ranking"   # on affiche le classement
        return None

    def update(self):
        mx, my = pygame.mouse.get_pos()
        self.btn_play.update(mx, my)
        self.btn_rank.update(mx, my)
        self.alpha = min(255, self.alpha + 8)  # fondu d'entrée progressif

    def draw(self):
        cx = SCREEN_WIDTH // 2
        self.screen.blit(self.logo, self.logo.get_rect(center=(cx, 140)))

        # ligne décorative + point sous le logo
        sep_y = self.logo.get_rect(center=(cx, 140)).bottom + 20
        pygame.draw.line(self.screen, C_ACCENT, (cx - 90, sep_y), (cx + 90, sep_y), 1)
        pygame.draw.circle(self.screen, C_ACCENT, (cx, sep_y), 4)

        self.btn_play.draw(self.screen, self.fonts["btn"])
        self.btn_rank.draw(self.screen, self.fonts["btn"])
        draw_text_centered(self.screen, "v0.1.0", self.fonts["tiny"], C_MUTED, cx, SCREEN_HEIGHT - 18)

        # superposition noire semi-transparente pour le fondu d'entrée
        if self.alpha < 255:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(255 - self.alpha)
            self.screen.blit(ov, (0, 0))


# -------------------------------------------------------
# écran de saisie du pseudo avant de lancer la partie
# -------------------------------------------------------

class PseudoScreen:
    MAX_LEN = 16  # nombre maximum de caractères autorisés dans le pseudo

    def __init__(self, screen, fonts, bg):
        self.screen = screen
        self.fonts  = fonts
        self.bg     = bg
        self.pseudo = ""  # texte saisi par le joueur, vide au départ
        self.alpha  = 0

        cx = SCREEN_WIDTH // 2
        self.btn_ok   = Button("VALIDER ▶", cx, 520, w=220, h=50)
        self.btn_back = Button("← RETOUR",  cx, 590, w=220, h=46)

        # curseur clignotant dans la boite de saisie
        self.cursor_visible = True
        self.cursor_timer   = 0

        self.input_rect = pygame.Rect(cx - 200, 380, 400, 60)  # boite de saisie centrée

    def handle_event(self, event):
        if self.btn_back.is_clicked(event):
            return "main"  # retour au menu principal

        # validation par bouton ou par la touche Entrée
        if self.btn_ok.is_clicked(event) or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        ):
            if self.pseudo.strip():  # on refuse les pseudos vides ou composés uniquement d'espaces
                return ("goto_tutorial", self.pseudo.strip())

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.pseudo = self.pseudo[:-1]  # supprime le dernier caractère
            elif len(self.pseudo) < self.MAX_LEN:
                # on accepte seulement les caractères imprimables (lettres, chiffres, symboles)
                if event.unicode.isprintable() and event.unicode != "":
                    self.pseudo += event.unicode

        return None

    def update(self):
        mx, my = pygame.mouse.get_pos()
        self.btn_ok.update(mx, my)
        self.btn_back.update(mx, my)
        self.alpha = min(255, self.alpha + 10)

        # le curseur alterne toutes les 500ms grâce au timestamp pygame
        if pygame.time.get_ticks() % 1000 < 500:
            self.cursor_visible = True
        else:
            self.cursor_visible = False

    def draw(self):
        cx = SCREEN_WIDTH // 2

        draw_text_centered(self.screen, "ENTREZ VOTRE PSEUDO", self.fonts["heading"], C_ACCENT, cx, 200)

        pygame.draw.line(self.screen, C_ACCENT2, (cx - 150, 230), (cx + 150, 230), 1)  # ligne déco

        draw_text_centered(self.screen, "Votre nom apparaîtra dans le classement",
                           self.fonts["sub"], C_MUTED, cx, 260)

        # la bordure de la boite devient dorée si le joueur a commencé à taper
        border_col = C_ACCENT if self.pseudo else C_MUTED
        pygame.draw.rect(self.screen, C_BG2,       self.input_rect, border_radius=8)
        pygame.draw.rect(self.screen, border_col,  self.input_rect, 2, border_radius=8)

        # affichage du texte avec le curseur clignotant (| ou espace)
        txt      = self.pseudo + ("|" if self.cursor_visible else " ")
        txt_surf = self.fonts["btn"].render(txt, True, C_TEXT)
        self.screen.blit(txt_surf, txt_surf.get_rect(center=self.input_rect.center))

        self.btn_ok.draw(self.screen,   self.fonts["btn"])
        self.btn_back.draw(self.screen, self.fonts["btn"])

        if self.alpha < 255:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(255 - self.alpha)
            self.screen.blit(ov, (0, 0))


# -------------------------------------------------------
# écran des instructions affiché avant le début de la partie
# -------------------------------------------------------

class TutorialScreen:
    IMG_PATH = os.path.join(BASE_DIR, "assets", "Instructions", "Instructions.png")

    def __init__(self, screen, fonts, bg, pseudo):
        self.screen = screen
        self.fonts  = fonts
        self.pseudo = pseudo  # on conserve le pseudo pour le transmettre au jeu quand on démarre

        # chargement et mise à l'échelle de l'image pour remplir l'écran sans déformation
        raw    = pygame.image.load(self.IMG_PATH).convert_alpha()
        rw, rh = raw.get_size()
        scale  = min(SCREEN_WIDTH / rw, SCREEN_HEIGHT / rh)
        self.image    = pygame.transform.scale(raw, (int(rw * scale), int(rh * scale)))
        self.img_rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

    def handle_event(self, event):
        # n'importe quelle touche ou clic lance le jeu
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            return ("start", self.pseudo)
        return None

    def update(self):
        pass  # rien à mettre à jour sur cet écran

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.image, self.img_rect)


# -------------------------------------------------------
# écran du classement (top 10 des meilleurs temps)
# -------------------------------------------------------

class RankingScreen:
    def __init__(self, screen, fonts, bg):
        self.screen   = screen
        self.fonts    = fonts
        self.bg       = bg
        self.alpha    = 0
        self.btn_back = Button("← RETOUR", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80, w=220, h=46)
        self.scores   = get_top10()  # chargement des scores depuis la base de données

    def handle_event(self, event):
        if self.btn_back.is_clicked(event):
            return "main"
        return None

    def update(self):
        self.btn_back.update(*pygame.mouse.get_pos())
        self.alpha = min(255, self.alpha + 10)

    def draw(self):
        cx = SCREEN_WIDTH // 2

        draw_text_centered(self.screen, "CLASSEMENT", self.fonts["heading"], C_ACCENT, cx, 80)
        pygame.draw.line(self.screen, C_ACCENT2, (cx - 200, 115), (cx + 200, 115), 1)

        if not self.scores:
            draw_text_centered(self.screen, "Aucun score enregistré", self.fonts["sub"], C_MUTED, cx, 300)
        else:
            colors = [C_GOLD, C_SILVER, C_BRONZE]  # couleurs spéciales pour le podium

            for i, (pseudo, temps) in enumerate(self.scores):
                y   = 160 + i * 60                        # chaque ligne espacée de 60px
                col = colors[i] if i < 3 else C_TEXT      # or/argent/bronze pour le podium, blanc sinon

                # rang (#1, #2, ...)
                rang_surf = self.fonts["btn"].render(f"#{i+1}", True, col)
                self.screen.blit(rang_surf, rang_surf.get_rect(midright=(cx - 180, y)))

                # pseudo du joueur
                pseudo_surf = self.fonts["btn"].render(pseudo, True, col)
                self.screen.blit(pseudo_surf, pseudo_surf.get_rect(midleft=(cx - 150, y)))

                # temps converti en format mm:ss.cc
                mins      = int(temps) // 60
                secs      = int(temps) % 60
                cents     = int((temps - int(temps)) * 100)
                temps_str  = f"{mins:02d}:{secs:02d}.{cents:02d}"
                temps_surf = self.fonts["btn"].render(temps_str, True, col)
                self.screen.blit(temps_surf, temps_surf.get_rect(midright=(cx + 250, y)))

                # ligne de séparation entre chaque entrée (sauf après la dernière)
                if i < len(self.scores) - 1:
                    pygame.draw.line(self.screen, C_BG2, (cx - 260, y + 30), (cx + 260, y + 30), 1)

        self.btn_back.draw(self.screen, self.fonts["btn"])

        if self.alpha < 255:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(255 - self.alpha)
            self.screen.blit(ov, (0, 0))


# -------------------------------------------------------
# écran générique "à venir" pour les fonctionnalités non encore développées
# -------------------------------------------------------

class PlaceholderScreen:
    def __init__(self, screen, fonts, bg, title):
        self.screen   = screen
        self.fonts    = fonts
        self.title    = title
        self.btn_back = Button("← RETOUR", SCREEN_WIDTH // 2, 450, w=200, h=46)
        self.alpha    = 0

    def handle_event(self, event):
        if self.btn_back.is_clicked(event):
            return "main"
        return None

    def update(self):
        self.btn_back.update(*pygame.mouse.get_pos())
        self.alpha = min(255, self.alpha + 10)

    def draw(self):
        cx = SCREEN_WIDTH // 2
        draw_text_centered(self.screen, self.title,    self.fonts["heading"], C_ACCENT, cx, 200)
        draw_text_centered(self.screen, "( à venir )", self.fonts["sub"],    C_MUTED,  cx, 280)
        self.btn_back.draw(self.screen, self.fonts["btn"])

        if self.alpha < 255:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(255 - self.alpha)
            self.screen.blit(ov, (0, 0))


# -------------------------------------------------------
# gestionnaire de tous les écrans du menu
# coordonne la navigation entre les différents écrans
# -------------------------------------------------------

class MenuManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mon Jeu — Menu")
        self.clock  = pygame.time.Clock()

        init_db()  # crée la base de données et ses tables si elles n'existent pas encore

        # toutes les polices utilisées dans les menus
        self.fonts = {
            "title":   pygame.font.SysFont("Georgia", 72, bold=True),
            "heading": pygame.font.SysFont("Georgia", 36, bold=True),
            "btn":     pygame.font.SysFont("Georgia", 22, bold=True),
            "sub":     pygame.font.SysFont("Georgia", 16),
            "tiny":    pygame.font.SysFont("Georgia", 13),
        }

        self.bg = Background()
        self._build_screens()
        self.current = "main"  # on commence toujours sur le menu principal

    def _build_screens(self):
        # crée ou recrée tous les écrans standards (sans le tutoriel qui nécessite un pseudo)
        self._screens = {
            "main":    MainMenu(self.screen, self.fonts, self.bg),
            "pseudo":  PseudoScreen(self.screen, self.fonts, self.bg),
            "ranking": RankingScreen(self.screen, self.fonts, self.bg),
        }

    def _build_tutorial(self, pseudo):
        # crée l'écran de tutoriel uniquement quand on a le pseudo du joueur
        self._screens["tutorial"] = TutorialScreen(self.screen, self.fonts, self.bg, pseudo)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                result = self._screens[self.current].handle_event(event)
                if result is None:
                    continue

                if isinstance(result, tuple) and result[0] == "start":
                    return result  # on retourne ("start", pseudo) à main.py pour lancer le jeu

                if isinstance(result, tuple) and result[0] == "goto_tutorial":
                    self._build_tutorial(result[1])  # on construit le tutoriel avec le pseudo saisi
                    self.current = "tutorial"
                    continue

                # navigation simple : on change juste l'écran courant
                self.current = result
                self._build_screens()
                self.current = result

            self.bg.update()
            self._screens[self.current].update()
            self.bg.draw(self.screen)
            self._screens[self.current].draw()
            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    menu   = MenuManager()
    result = menu.run()
    if result:
        print(f"Go ! pseudo={result[1]}")