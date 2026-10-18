import pygame
import assets
from entities_properties import EntityProperties  # propriétés de chaque entité (vitesse, HP, etc.)


class Slime(pygame.sprite.Sprite):  # le slime hérite de Sprite pour pouvoir être dans un Group pygame

    def __init__(self, x, y, left_x=None, right_x=None):
        super().__init__()  # obligatoire pour que pygame.sprite.Sprite fonctionne correctement

        self.props      = EntityProperties.SLIME_GREEN  # dictionnaire avec toutes les stats du slime
        self.anim_speed = self.props["anim_speed"]       # vitesse de défilement des frames d'animation
        self.move_speed = self.props["move_speed"]       # vitesse de déplacement horizontal

        # on commence avec l'animation de marche, à la première frame
        self.animation_list = assets.assets.slime_green.walk
        self.frame_index    = 0
        self.image          = self.animation_list[0]  # image actuelle affichée à l'écran

        # état initial : le slime part vers la droite
        self.state        = 'right'
        self.facing_right = True
        self.on_ground    = False  # mis à jour par le système de collision dans main.py

        # vecteur de déplacement : x est géré ici, y est géré par la gravité dans main.py
        self.direction = pygame.math.Vector2(self.move_speed, 0)

        # rect = rectangle graphique pour afficher le sprite
        self.rect            = self.image.get_rect()
        self.rect.bottomleft = (x, y)  # on place le bas-gauche du sprite à la position donnée

        # hitbox = rectangle de collision (peut être plus petit que le sprite)
        hw = self.props["hitbox_width"]
        hh = self.props["hitbox_height"]
        self.hitbox           = pygame.Rect(0, 0, hw, hh)
        self.hitbox.midbottom = self.rect.midbottom  # on aligne la hitbox avec le bas du sprite

        # bornes de patrouille : le slime fait demi-tour quand il les atteint
        self.left_x  = left_x  if left_x  is not None else x - 200  # par défaut 200px à gauche
        self.right_x = right_x if right_x is not None else x + 200  # par défaut 200px à droite

        # points de vie
        self.max_hp = self.props["max_hp"]
        self.hp     = self.max_hp  # le slime commence avec tous ses HP

        # knockback : recul appliqué quand le slime prend un coup
        self.is_knocked      = False
        self.knockback_timer = 0                          # timestamp auquel le knockback se termine
        self.knockback_vel   = pygame.math.Vector2(0, 0) # vitesse de recul (x et y)

        self.is_hurt  = False   # True pendant l'animation de dégât
        self.is_dying = False   # True quand les HP tombent à 0


    # -----------------------------------------------------------
    # synchronisation rect / hitbox
    # -----------------------------------------------------------

    def _sync_rect_from_hitbox(self):
        # le rect graphique doit toujours coller à la hitbox (c'est la hitbox qui fait autorité)
        self.rect.midbottom = self.hitbox.midbottom

    def _set_walk_anim(self):
        # remet l'animation de marche depuis le début (utilisé après un demi-tour ou fin de hurt)
        self.animation_list = assets.assets.slime_green.walk
        self.frame_index    = 0


    # -----------------------------------------------------------
    # gestion des dégâts
    # -----------------------------------------------------------

    def take_damage(self, amount, knockback_dir):
        if self.is_dying:
            return  # on ignore les coups sur un slime déjà en train de mourir
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self._start_death()
        else:
            self._start_hurt(knockback_dir)

    def _start_hurt(self, knockback_dir):
        self.is_hurt        = True
        self.frame_index    = 0
        self.animation_list = assets.assets.slime_green.hurt  # on passe sur l'anim de dégât
        self.anim_speed     = self.props["hurt_anim_speed"]   # plus rapide que l'anim de marche

        # on applique le knockback : déplacement forcé dans la direction du coup
        self.is_knocked      = True
        self.knockback_timer = pygame.time.get_ticks() + self.props["knockback_duration"]  # heure de fin du knockback
        self.knockback_vel.x = knockback_dir * self.props["knockback_x"]  # recul horizontal
        self.knockback_vel.y = self.props["knockback_y"]  # petit saut vers le haut (valeur négative)

    def _start_death(self):
        self.is_dying       = True
        self.is_hurt        = False
        self.is_knocked     = False
        self.direction.x    = 0   # le slime s'arrête complètement de bouger
        self.frame_index    = 0
        self.animation_list = assets.assets.slime_green.death
        self.anim_speed     = self.props["death_anim_speed"]


    # -----------------------------------------------------------
    # déplacement (direction.y est géré par main.py, pas ici)
    # -----------------------------------------------------------

    def prepare_move(self):
        if self.is_dying:
            self.direction.x = 0  # mort = immobile
            return

        if self.is_knocked:
            self.direction.x = self.knockback_vel.x  # pendant le knockback, on ignore la patrouille
            return

        # demi-tour quand on atteint une des bornes de patrouille
        if self.state == 'right' and self.hitbox.right >= self.right_x:
            self.state        = 'left'
            self.facing_right = False
            self._set_walk_anim()
        elif self.state == 'left' and self.hitbox.left <= self.left_x:
            self.state        = 'right'
            self.facing_right = True
            self._set_walk_anim()

        # vitesse positive si on va à droite, négative si on va à gauche
        self.direction.x = self.move_speed if self.state == 'right' else -self.move_speed

    def check_knockback_end(self):
        # vérifie si la durée du knockback est écoulée
        if self.is_knocked and pygame.time.get_ticks() >= self.knockback_timer:
            self.is_knocked       = False
            self.knockback_vel.xy = 0, 0  # on remet la vitesse de recul à zéro
            if self.is_hurt:
                # le knockback est fini, on sort aussi de l'état hurt et on reprend la marche
                self.is_hurt    = False
                self.anim_speed = self.props["anim_speed"]
                self._set_walk_anim()


    # -----------------------------------------------------------
    # animation
    # -----------------------------------------------------------

    def animate(self):
        self.frame_index += self.anim_speed  # on avance dans la liste de frames

        if self.is_dying:
            if self.frame_index >= len(self.animation_list):
                # animation de mort terminée : on réduit la hitbox à zéro et on supprime le sprite du Group
                self.hitbox.width  = 0
                self.hitbox.height = 0
                self.kill()  # méthode pygame qui retire le sprite de tous les groupes
                return
        else:
            if self.frame_index >= len(self.animation_list):
                self.frame_index = 0  # pour les autres animations, on boucle

        self.image = self.animation_list[int(self.frame_index)]
        if not self.facing_right:
            # on retourne horizontalement le sprite quand le slime va à gauche
            self.image = pygame.transform.flip(self.image, True, False)


    # -----------------------------------------------------------
    # barre de vie affichée au-dessus du slime
    # -----------------------------------------------------------

    def draw_health_bar(self, screen, camera=None):
        if self.is_dying:
            return  # pas de barre de vie sur un slime en train de mourir
        bar_w = self.props["hitbox_width"] + 10  # légèrement plus large que la hitbox
        bar_h = 6
        ref   = camera.apply(self.rect) if camera else self.rect  # position à l'écran (avec ou sans caméra)
        x     = ref.centerx - bar_w // 2  # centré horizontalement sur le slime
        y     = ref.top - 12              # 12 pixels au-dessus du sprite

        pygame.draw.rect(screen, (80, 80, 80),  (x, y, bar_w, bar_h))                              # fond gris (HP manquants)
        pygame.draw.rect(screen, (220, 30, 30), (x, y, int(bar_w * self.hp / self.max_hp), bar_h)) # barre rouge (HP restants)
        pygame.draw.rect(screen, (30, 30, 30),  (x, y, bar_w, bar_h), 1)                           # contour noir (épaisseur 1px)


    # -----------------------------------------------------------
    # mise à jour appelée chaque frame par le Group
    # -----------------------------------------------------------

    def update(self):
        self.check_knockback_end()   # on vérifie si le knockback est terminé
        self.prepare_move()          # on calcule direction.x selon l'état
        self.animate()               # on avance l'animation et on met à jour self.image
        self._sync_rect_from_hitbox() # on aligne le rect graphique sur la hitbox

    def draw(self, screen, camera=None):
        draw_rect = camera.apply(self.rect) if camera else self.rect
        screen.blit(self.image, draw_rect)    # on affiche le sprite
        self.draw_health_bar(screen, camera)  # on affiche la barre de vie par-dessus
        # pygame.draw.rect(screen, (0, 255, 0), camera.apply(self.hitbox) if camera else self.hitbox, 2)  # debug hitbox (désactivé)