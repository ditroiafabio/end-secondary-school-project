import pygame
from settings import *
import assets
from entities_properties import EntityProperties


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.props = EntityProperties.PLAYER  # toutes les stats du joueur en un seul endroit

        # --- animation ---
        self.animation_list = assets.assets.player.idle  # on commence par l'animation idle
        self.frame_index    = 0
        self.image          = self.animation_list[self.frame_index]

        # --- états du joueur ---
        self.status           = 'idle'
        self.facing_right     = True    # True = regarde à droite, False = regarde à gauche
        self.on_ground        = False   # mis à jour par le système de collision
        self.on_wall_left     = False
        self.on_wall_right    = False
        self.is_run_attacking = False   # True si on attaque en courant (animation différente)

        # coyote time : quelques frames de grâce pour sauter juste après avoir quitté une plateforme
        self.coyote_time   = 0
        self.COYOTE_FRAMES = 6   # environ 100ms à 60fps

        # --- physique ---
        self.direction  = pygame.math.Vector2(0, 0)  # vecteur de déplacement (x et y)
        self.anim_speed = self.props["anim_speed"]

        # --- dash ---
        self.is_dashing      = False
        self.dash_start_time = 0
        self.last_dash_time  = -self.props["dash_cooldown"]  # valeur initiale qui autorise un dash immédiat
        self.dash_direction  = 0   # +1 = droite, -1 = gauche

        # --- attaque ---
        self.is_attacking = False

        # --- vie ---
        self.max_hp = self.props["max_hp"]
        self.hp     = self.max_hp

        # --- invincibilité et mort ---
        self.is_hurt       = False
        self.hurt_timer    = 0
        self.last_hit_time = -self.props["iframe_duration"]  # permet d'être touché dès le début
        self.is_dying      = False

        # rect = zone d'affichage du sprite ; hitbox = zone de collision (plus petite)
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)

        hw = self.props["hitbox_width"]
        hh = self.props["hitbox_height"]
        self.hitbox = pygame.Rect(0, 0, hw, hh)
        self.hitbox.midbottom = self.rect.midbottom

        self.checkpoint = (x, y)  # position de respawn, mise à jour à chaque checkpoint touché


    def _sync_rect_from_hitbox(self):
        # aligne le rect graphique sur la hitbox en compensant l'espace vide en bas du sprite
        offset = self.props["empty_space_bottom"]
        self.rect.midbottom = (self.hitbox.centerx, self.hitbox.bottom + offset)

    def is_invincible(self):
        # retourne True si le joueur est encore dans sa période d'invincibilité après un coup
        return pygame.time.get_ticks() - self.last_hit_time < self.props["iframe_duration"]

    def take_damage(self, amount):
        if self.is_invincible() or self.is_dying:
            return  # on ignore les dégâts si déjà invincible ou en train de mourir
        self.hp -= amount
        self.last_hit_time = pygame.time.get_ticks()  # démarre la période d'invincibilité

        if self.hp <= 0:
            self.hp = 0
            self._start_death()
        else:
            self._start_hurt()

    def _start_hurt(self):
        self.is_hurt      = True
        self.is_attacking = False  # l'attaque est annulée quand on prend un coup
        self.frame_index  = 0
        self.hurt_timer   = pygame.time.get_ticks() + self.props["hurt_duration"]

    def _start_death(self):
        self.is_dying     = True
        self.is_hurt      = False
        self.is_attacking = False
        self.is_dashing   = False
        self.direction.xy = 0, 0  # on stoppe tout mouvement
        self.frame_index  = 0

    def get_direction_from_mouse(self):
        # détermine si le joueur doit aller à gauche ou à droite selon la position de la souris
        mouse_x, _ = pygame.mouse.get_pos()
        diff_x     = mouse_x - self.hitbox.centerx
        if abs(diff_x) > 10:  # zone morte de 10px pour éviter les micro-vibrations
            return 1 if diff_x > 0 else -1
        return 0  # souris trop proche : pas de mouvement

    def get_input(self):
        if self.is_dying:
            self.direction.x = 0
            return

        # pendant une attaque normale on ne peut pas bouger (sauf si c'est une attaque en course)
        if self.is_attacking and not self.is_run_attacking:
            self.direction.x = 0
            return

        keys = pygame.key.get_pressed()
        if not self.is_dashing:
            if keys[KEY_MOVE]:  # Z maintenu
                mouse_dir = self.get_direction_from_mouse()
                if mouse_dir != 0:
                    self.direction.x  = mouse_dir
                    self.facing_right  = (self.direction.x > 0)  # on oriente le sprite
                else:
                    self.direction.x = 0
            else:
                self.direction.x = 0  # aucune touche = arrêt

    def handle_event(self, event):
        if self.is_dying:
            return

        if event.type == pygame.KEYDOWN:
            # --- saut ---
            if event.key == KEY_JUMP and not self.is_attacking:
                if self.on_ground or self.coyote_time > 0:
                    self.direction.y  = self.props["jump_force"]  # saut normal
                    self.coyote_time  = 0
                elif self.on_wall_right:
                    self.wall_jump(-1)  # wall jump : on pousse vers la gauche
                elif self.on_wall_left:
                    self.wall_jump(1)   # wall jump : on pousse vers la droite

            # --- dash ---
            if event.key == KEY_DASH and not self.is_attacking:
                now = pygame.time.get_ticks()
                if now - self.last_dash_time >= self.props["dash_cooldown"] and not self.is_dashing:
                    self.start_dash()

            # --- attaque ---
            if event.key == KEY_ATTACK and not self.is_dashing and not self.is_attacking:
                self.start_attack()

    def wall_jump(self, side):
        # side = +1 pour sauter vers la droite, -1 pour sauter vers la gauche
        self.direction.x  = side * self.props["wall_jump_force_x"]
        self.direction.y  = self.props["wall_jump_force_y"]
        self.facing_right = (side == 1)

    def start_dash(self):
        self.is_dashing      = True
        self.dash_start_time = pygame.time.get_ticks()
        self.last_dash_time  = self.dash_start_time
        self.direction.y     = 0  # on annule la gravité pour que le dash soit parfaitement horizontal

        mouse_dir = self.get_direction_from_mouse()
        if mouse_dir != 0:
            self.dash_direction = mouse_dir
            self.facing_right   = (self.dash_direction > 0)
        else:
            # si la souris est trop proche, on dashe dans la direction où on regarde déjà
            self.dash_direction = 1 if self.facing_right else -1

    def start_attack(self):
        self.is_attacking     = True
        self.is_run_attacking = abs(self.direction.x) > 0.1  # en mouvement = attaque en course
        self.frame_index      = 0  # on repart du début de l'animation d'attaque

    def check_dash_end(self):
        if self.is_dashing:
            if pygame.time.get_ticks() - self.dash_start_time > self.props["dash_duration"]:
                self.is_dashing = False  # durée écoulée → fin du dash

    def check_hurt_end(self):
        if self.is_hurt and pygame.time.get_ticks() >= self.hurt_timer:
            self.is_hurt     = False
            self.frame_index = 0  # on repart de la première frame de l'animation suivante

    def get_status(self):
        # détermine l'état courant pour choisir la bonne animation (ordre de priorité important)
        if self.is_dying:
            self.status = 'death'
        elif self.is_hurt:
            self.status = 'hurt'
        elif self.is_attacking:
            self.status = 'attack'
        elif self.is_dashing or abs(self.direction.x) > 0.1:
            self.status = 'run'
        else:
            self.status = 'idle'

    def animate(self):
        self.get_status()
        a = assets.assets.player  # raccourci vers les assets du joueur

        if self.status == 'death':
            self.animation_list = a.death_right if self.facing_right else a.death_left
            self.frame_index   += self.anim_speed
            if self.frame_index >= len(self.animation_list):
                # animation terminée → on respawn au dernier checkpoint
                self.frame_index = len(self.animation_list) - 1
                self._do_respawn()

        elif self.status == 'hurt':
            self.animation_list = a.hurt_right if self.facing_right else a.hurt_left
            self.frame_index   += self.anim_speed
            if self.frame_index >= len(self.animation_list):
                self.frame_index = 0  # boucle sur l'animation de douleur

        elif self.status == 'attack':
            if self.is_run_attacking:
                self.animation_list = a.run_attack_right if self.facing_right else a.run_attack_left
            else:
                self.animation_list = a.attack_right if self.facing_right else a.attack_left
            self.frame_index += self.anim_speed
            if self.frame_index >= len(self.animation_list):
                # l'attaque ne boucle pas : elle se termine automatiquement à la fin de l'animation
                self.frame_index      = 0
                self.is_attacking     = False
                self.is_run_attacking = False

        elif self.status == 'run':
            self.animation_list = a.run_right if self.facing_right else a.run_left
            self.frame_index   += self.anim_speed
            if self.frame_index >= len(self.animation_list):
                self.frame_index = 0

        else:  # idle
            self.animation_list = a.idle
            self.frame_index   += self.anim_speed
            if self.frame_index >= len(self.animation_list):
                self.frame_index = 0

        self.image = self.animation_list[int(self.frame_index)]

    def _do_respawn(self):
        # remet le joueur à vie complète au dernier checkpoint atteint
        self.hp           = self.max_hp
        self.is_dying     = False
        self.is_hurt      = False
        self.is_attacking = False
        self.is_dashing   = False
        self.direction.xy = 0, 0
        self.frame_index  = 0
        self.last_hit_time = -self.props["iframe_duration"]  # l'invincibilité repart à zéro
        self.hitbox.midbottom = self.checkpoint
        self._sync_rect_from_hitbox()

    def set_checkpoint(self, x, y):
        self.checkpoint = (x, y)  # mémorise la nouvelle position de respawn

    def update(self):
        self.get_input()
        self.check_dash_end()
        self.check_hurt_end()

        # coyote time : on décompte tant qu'on est dans les airs
        if self.on_ground:
            self.coyote_time = self.COYOTE_FRAMES  # on recharge les frames de grâce
        elif self.coyote_time > 0:
            self.coyote_time -= 1  # on consomme une frame de grâce

        self.animate()
        self._sync_rect_from_hitbox()

    def draw(self, screen, camera=None):
        # clignotement pendant l'invincibilité : on saute une frame sur deux toutes les 100ms
        if self.is_invincible() and not self.is_dying:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                return  # on n'affiche pas le joueur cette frame

        draw_rect = camera.apply(self.rect) if camera else self.rect
        screen.blit(self.image, draw_rect)
        # pygame.draw.rect(screen, (255, 0, 0), self.hitbox, 2)