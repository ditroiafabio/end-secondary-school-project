import pygame
import assets as assets_module

KEY_INTERACT    = pygame.K_f  # touche pour interagir avec un PNJ
INTERACT_RADIUS = 80          # distance max en pixels pour pouvoir parler au PNJ
ANIM_FPS        = 8           # frames d'animation jouées par seconde


# -------------------------------------------------------
# PNJ renard - guide principal du joueur
# -------------------------------------------------------

class NPC(pygame.sprite.Sprite):
    def __init__(self, x, y, name="PNJ", dialogue=None):
        super().__init__()

        self.name     = name
        self.dialogue = dialogue or ["Appuyez sur SHIFT pour faire un dash !"]  # dialogue par défaut

        # on charge les deux animations : repos et discussion
        self._anim_idle    = assets_module.assets.fox.idle
        self._anim_talk    = assets_module.assets.fox.talk
        self._current_anim = self._anim_idle  # on commence en mode repos
        self._frame_index  = 0.0
        self._anim_speed   = ANIM_FPS

        self.image = self._current_anim[0]  # première frame de l'animation
        self.rect  = self.image.get_rect()
        self.rect.midbottom = (x, y)  # le bas-centre du sprite à la position donnée

        # zone de détection autour du PNJ (plus large que son sprite pour faciliter l'approche)
        self.interact_rect = self.rect.inflate(INTERACT_RADIUS * 2, INTERACT_RADIUS)

        self.in_range    = False  # True si le joueur est assez proche pour parler
        self.talking     = False  # True si le dialogue est ouvert
        self._line_index = 0      # index de la ligne de dialogue actuellement affichée


    def _set_anim(self, frames):
        # change d'animation seulement si ce n'est pas déjà la bonne (évite les redémarrages inutiles)
        if frames is not self._current_anim:
            self._current_anim = frames
            self._frame_index  = 0.0

    def _advance_anim(self, dt):
        # avance l'animation en fonction du temps écoulé
        self._frame_index += self._anim_speed * dt
        if self._frame_index >= len(self._current_anim):
            self._frame_index = 0.0  # on repart à la première frame (boucle)
        self.image = self._current_anim[int(self._frame_index)]

        # on recentre le rect car les frames peuvent avoir des tailles légèrement différentes
        prev = self.rect.midbottom
        self.rect = self.image.get_rect()
        self.rect.midbottom = prev


    def update(self, player_hitbox, dt=1/60):
        # on vérifie si le joueur est dans la zone de détection
        self.in_range = self.interact_rect.colliderect(player_hitbox)

        if not self.in_range and self.talking:
            self.close_dialogue()  # si le joueur s'éloigne, on ferme automatiquement le dialogue

        # on choisit l'animation selon l'état
        self._set_anim(self._anim_talk if self.talking else self._anim_idle)
        self._advance_anim(dt)

        # on recalcule la zone d'interaction car le rect peut avoir bougé
        self.interact_rect = self.rect.inflate(INTERACT_RADIUS * 2, INTERACT_RADIUS)

    def handle_event(self, event):
        # on réagit seulement à la touche d'interaction quand le joueur est proche
        if event.type != pygame.KEYDOWN or event.key != KEY_INTERACT:
            return
        if not self.in_range:
            return
        if not self.talking:
            self.open_dialogue()  # premier appui : on ouvre le dialogue
        else:
            self._next_line()     # appuis suivants : on passe à la ligne suivante

    def open_dialogue(self):
        self.talking     = True
        self._line_index = 0  # on recommence toujours depuis la première ligne

    def _next_line(self):
        self._line_index += 1
        if self._line_index >= len(self.dialogue):
            self.close_dialogue()  # plus de lignes → on ferme le dialogue

    def close_dialogue(self):
        self.talking     = False
        self._line_index = 0


    def draw(self, screen, camera, font):
        # si une caméra est fournie, on applique son décalage ; sinon on dessine directement
        draw_rect = camera.apply(self.rect) if camera else self.rect
        screen.blit(self.image, draw_rect)

        if self.talking:
            self._draw_dialogue_bubble(screen, draw_rect, font)
        elif self.in_range:
            self._draw_prompt(screen, draw_rect, font)  # invite à interagir si le joueur est proche

    def _draw_prompt(self, screen, draw_rect, font):
        # petit texte au-dessus du PNJ pour signaler qu'on peut interagir
        surf = font.render("[F]  Parler", True, (255, 230, 80))
        screen.blit(surf, surf.get_rect(midbottom=(draw_rect.centerx, draw_rect.top - 6)))

    def _draw_dialogue_bubble(self, screen, draw_rect, font):
        if self._line_index >= len(self.dialogue):
            return

        text  = self.dialogue[self._line_index]
        tsurf = font.render(text, True, (20, 20, 20))  # texte sombre sur fond blanc

        PAD = 12  # marge interne de la bulle
        bw  = tsurf.get_width()  + PAD * 2
        bh  = tsurf.get_height() + PAD * 2
        bx  = draw_rect.centerx - bw // 2  # centré au-dessus du PNJ
        by  = draw_rect.top - bh - 14      # 14px au-dessus du sprite

        # fond blanc semi-transparent avec bordure grise
        bubble = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (255, 255, 255, 230), bubble.get_rect(), border_radius=8)
        pygame.draw.rect(bubble, (80, 80, 80, 200),   bubble.get_rect(), 2, border_radius=8)
        screen.blit(bubble, (bx, by))
        screen.blit(tsurf,  (bx + PAD, by + PAD))  # texte centré dans la bulle

        # petite pointe triangulaire qui pointe vers le PNJ
        tip_x = draw_rect.centerx
        tip_y = draw_rect.top - 4
        pygame.draw.polygon(screen, (255, 255, 255),
                            [(tip_x - 8, tip_y - 10), (tip_x + 8, tip_y - 10), (tip_x, tip_y)])

        # indicateur "suite" si il reste des lignes à lire
        if self._line_index < len(self.dialogue) - 1:
            more = font.render("▶", True, (120, 120, 120))
            screen.blit(more, (bx + bw - more.get_width() - 6, by + bh - more.get_height() - 4))


# -------------------------------------------------------
# PNJ soldat - dialogue différent, pas d'animation de discussion
# -------------------------------------------------------

class Soldier(pygame.sprite.Sprite):
    def __init__(self, x, y, name="Soldat", dialogue=None):
        super().__init__()

        self.name     = name
        self.dialogue = dialogue or ["Comment passer au-dessus ?..."]

        # le soldat n'a qu'une animation idle, pas d'animation de dialogue
        self._anim_idle    = assets_module.assets.soldier.idle
        self._current_anim = self._anim_idle
        self._frame_index  = 0.0
        self._anim_speed   = ANIM_FPS

        self.image = self._current_anim[0]
        self.rect  = self.image.get_rect()
        self.rect.midbottom = (x, y)

        self.interact_rect = self.rect.inflate(INTERACT_RADIUS * 2, INTERACT_RADIUS)

        self.in_range    = False
        self.talking     = False
        self._line_index = 0

    def _advance_anim(self, dt):
        # même logique que pour le renard
        self._frame_index += self._anim_speed * dt
        if self._frame_index >= len(self._current_anim):
            self._frame_index = 0.0
        self.image = self._current_anim[int(self._frame_index)]
        prev = self.rect.midbottom
        self.rect = self.image.get_rect()
        self.rect.midbottom = prev

    def update(self, player_hitbox, dt=1/60):
        self.in_range = self.interact_rect.colliderect(player_hitbox)
        if not self.in_range and self.talking:
            self.close_dialogue()
        self._advance_anim(dt)
        self.interact_rect = self.rect.inflate(INTERACT_RADIUS * 2, INTERACT_RADIUS)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key != KEY_INTERACT:
            return
        if not self.in_range:
            return
        if not self.talking:
            self.open_dialogue()
        else:
            self._next_line()

    def open_dialogue(self):
        self.talking     = True
        self._line_index = 0

    def _next_line(self):
        self._line_index += 1
        if self._line_index >= len(self.dialogue):
            self.close_dialogue()

    def close_dialogue(self):
        self.talking     = False
        self._line_index = 0

    def draw(self, screen, camera, font):
        draw_rect = camera.apply(self.rect) if camera else self.rect
        screen.blit(self.image, draw_rect)

        if self.talking:
            self._draw_dialogue_bubble(screen, draw_rect, font)
        elif self.in_range:
            # invite à interagir (même style que le renard)
            surf = font.render("[F]  Parler", True, (255, 230, 80))
            screen.blit(surf, surf.get_rect(midbottom=(draw_rect.centerx, draw_rect.top - 6)))

    def _draw_dialogue_bubble(self, screen, draw_rect, font):
        if self._line_index >= len(self.dialogue):
            return
        text  = self.dialogue[self._line_index]
        tsurf = font.render(text, True, (20, 20, 20))
        PAD   = 12
        bw    = tsurf.get_width()  + PAD * 2
        bh    = tsurf.get_height() + PAD * 2
        bx    = draw_rect.centerx - bw // 2
        by    = draw_rect.top - bh - 14

        bubble = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(bubble, (255, 255, 255, 230), bubble.get_rect(), border_radius=8)
        pygame.draw.rect(bubble, (80, 80, 80, 200),   bubble.get_rect(), 2, border_radius=8)
        screen.blit(bubble, (bx, by))
        screen.blit(tsurf,  (bx + PAD, by + PAD))

        # pointe de la bulle vers le bas
        tip_x = draw_rect.centerx
        tip_y = draw_rect.top - 4
        pygame.draw.polygon(screen, (255, 255, 255),
                            [(tip_x - 8, tip_y - 10), (tip_x + 8, tip_y - 10), (tip_x, tip_y)])

        if self._line_index < len(self.dialogue) - 1:
            more = font.render("▶", True, (120, 120, 120))
            screen.blit(more, (bx + bw - more.get_width() - 6, by + bh - more.get_height() - 4))