import pygame
import sys
import os
from settings import *  # les constantes
import assets #gestion assets
from player import Player #gestion jouer
from enemy import Slime #gestion ennemi
from menu import MenuManager #menu
from tilemap import TileMap, EndZoneManager #gestion de la map
from npc import NPC, Soldier # gestion des pnjs
from database import init_db, save_score, get_top10  # fonctions pour la base de données

#chemins vers les fichiers
# chemins absolus parce que les soucis d'avant m'ont rendu fou
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))  # dossier où se trouve ce fichier
MAP_PATH     = os.path.join(BASE_DIR, "Maps", "Map.tmx")  # chemin vers la carte du jeu
END_IMG_PATH = os.path.join(BASE_DIR, "assets", "End", "End.png")  # image de fin


# -------------------------------------------------------
# gestion des collisions entre un personnage et les plateformes
# on sépare les déplacements horizontal et vertical pour éviter les bugs de coin
# -------------------------------------------------------

def move_and_collide(hitbox, dx, dy, platforms):
    # dictionnaire qui va retenir ce qui s'est passé pendant le déplacement
    flags = {"on_ground": False, "on_wall_left": False, "on_wall_right": False, "hit_ceiling": False}

    # --- déplacement horizontal ---
    hitbox.x += int(dx)  # on déplace d'abord sur l'axe X
    for plat in platforms:
        if hitbox.colliderect(plat.rect):  # si on touche une plateforme
            if dx > 0:  # on allait vers la droite on est bloqué à gauche du mur
                hitbox.right = plat.rect.left
                flags["on_wall_right"] = True
            elif dx < 0:  # on allait vers la gauche on est bloqué à droite du mur
                hitbox.left = plat.rect.right
                flags["on_wall_left"] = True

    # --- déplacement vertical ---
    hitbox.y += int(dy)  # ensuite on déplace sur l'axe Y
    for plat in platforms:
        if hitbox.colliderect(plat.rect):
            if dy > 0:  # on tombait on est posé sur le sol
                hitbox.bottom = plat.rect.top
                flags["on_ground"] = True
            elif dy < 0:  # on sautait on a touché un plafond
                hitbox.top = plat.rect.bottom
                flags["hit_ceiling"] = True

    return flags  # on renvoie ce qui s'est passé pour que l'appelant puisse réagir


# -------------------------------------------------------
# classe principale qui gère toute la partie en cours
# -------------------------------------------------------

class Game:
    def __init__(self, pseudo="Joueur"):
        pygame.init()  # initialisation de tous les modules pygame
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))  # création de la fenêtre
        pygame.display.set_caption("ThreadRunner")
        self.clock = pygame.time.Clock()  # horloge pour limiter les FPS

        self.pseudo = pseudo  # nom du joueur, sera enregistré dans la base de données

        assets.load_assets()  # chargement de toutes les images du jeu
        init_db()  # initialisation de la base de données (création des tables si nécessaire)

        # polices d'écriture pour l'interface utilisateur
        self.ui_font       = pygame.font.SysFont("Georgia", 22, bold=True)
        self.ui_font_small = pygame.font.SysFont("Georgia", 18)
        self.ui_font_big   = pygame.font.SysFont("Georgia", 32, bold=True)

        self.attacked_enemies = set()  # ensemble des ennemis déjà touchés pendant l'attaque en cours
        self.player = Player(100, 560)  # création du joueur à la position de départ

        # --- HUD (affichage des coeurs de vie) ---
        self.heart_states     = ['full'] * self.player.max_hp  # état de chaque coeur : 'full', 'losing' ou 'empty'
        self.heart_anim_index = [0.0] * self.player.max_hp     # avancement de l'animation de perte de vie
        self.prev_hp          = self.player.max_hp              # HP du joueur au tour précédent (pour détecter les dégâts)
        self.HEART_ANIM_SPEED = 0.12                            # vitesse de l'animation des coeurs

        # --- chronomètre ---
        self.chrono_start = pygame.time.get_ticks()  # on note l'heure de départ en millisecondes
        self.chrono_stop  = None   # tant que c'est None, le chrono tourne ; sinon c'est l'heure d'arrêt
        self.temps_final  = None   # temps en secondes à la fin du niveau, calculé une seule fois

        self._load_map(MAP_PATH)  # chargement de la carte et des entités


    def _load_map(self, tmx_path):
        # charge la carte depuis le fichier .tmx (format Tiled)
        self.tilemap   = TileMap(tmx_path)
        self.platforms = self.tilemap.platforms   # liste de toutes les plateformes solides
        self.enemies   = pygame.sprite.Group()    # groupe de tous les ennemis actifs
        self.attacked_enemies.clear()             # réinitialise la liste des ennemis déjà frappés

        # position de départ par défaut, au cas où il n'y a pas de checkpoint dans la carte
        spawn_x, spawn_y = 100, 560
        if self.tilemap.checkpoints:
            cp      = self.tilemap.checkpoints[0]  # on prend le premier checkpoint de la carte
            spawn_x = cp.centerx
            spawn_y = cp.bottom

        # on place le joueur au point de spawn
        self.player.hitbox.midbottom = (spawn_x, spawn_y)
        self.player._sync_rect_from_hitbox()        # on met à jour le rect graphique depuis la hitbox
        self.player.set_checkpoint(spawn_x, spawn_y) # on mémorise ce point comme dernier checkpoint
        self.player.direction.xy = 0, 0              # on annule tout mouvement résiduel

        self.checkpoint_rects = self.tilemap.checkpoints  # liste de tous les checkpoints de la carte
        # EndZoneManager surveille les zones de fin et appellera _on_end quand le joueur y entre
        self.end_manager = EndZoneManager(self.tilemap.end_zones, on_level_complete=self._on_end)

        self.npcs  = pygame.sprite.Group()  # PNJ normaux (dialogues, etc.)
        self.npcs2 = pygame.sprite.Group()  # soldats (type de PNJ différent)
        self._spawn_entities()              # on crée tous les ennemis et PNJ

        # on réinitialise l'affichage des coeurs avec les HP actuels du joueur
        self.heart_states     = ['full'] * self.player.max_hp
        self.heart_anim_index = [0.0] * self.player.max_hp
        self.prev_hp          = self.player.hp


    def _spawn_entities(self):
        # crée les PNJ et ennemis aux positions définies dans la carte
        for x, y in self.tilemap.npc_spawns:
            self.npcs.add(NPC(x, y))
        for x, y in self.tilemap.npc_spawns2:
            self.npcs2.add(Soldier(x, y))
        # les données des ennemis incluent aussi les bornes gauche/droite de leur patrol
        for data in self.tilemap.enemy_spawns:
            self.enemies.add(Slime(data["x"], data["y"], left_x=data["left_x"], right_x=data["right_x"]))


    # -------------------------------------------------------
    # chronomètre : lecture et affichage
    # -------------------------------------------------------

    def _get_chrono(self):
        # retourne le nombre de secondes écoulées depuis le début
        if self.chrono_stop is not None:
            # le chrono est arrêté, on calcule la durée figée
            return (self.chrono_stop - self.chrono_start) / 1000
        # le chrono tourne encore, on calcule depuis maintenant
        return (pygame.time.get_ticks() - self.chrono_start) / 1000

    def _format_chrono(self, t):
        # convertit un nombre de secondes en chaîne lisible "mm:ss.cc"
        mins  = int(t) // 60         # minutes entières
        secs  = int(t) % 60          # secondes restantes
        cents = int((t - int(t)) * 100)  # centièmes de seconde
        return f"{mins:02d}:{secs:02d}.{cents:02d}"  # format avec zéros à gauche

    def _draw_chrono(self):
        t    = self._get_chrono()
        txt  = self._format_chrono(t)
        surf = self.ui_font_big.render(txt, True, C_CHRONO)

        # on positionne le chrono en haut à droite de l'écran
        x = SCREEN_WIDTH - surf.get_width() - 20
        y = 15

        # fond semi-transparent pour que le texte soit lisible sur n'importe quel fond
        bg = pygame.Surface((surf.get_width() + 16, surf.get_height() + 8), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 140), bg.get_rect(), border_radius=6)  # 140/255 = ~55% opaque
        self.screen.blit(bg, (x - 8, y - 4))   # fond légèrement décalé pour le padding
        self.screen.blit(surf, (x, y))           # texte par-dessus


    # -------------------------------------------------------
    # gestion de la fin du niveau
    # -------------------------------------------------------

    def _on_end(self):
        # appelé par EndZoneManager quand le joueur atteint la zone de fin
        self.chrono_stop = pygame.time.get_ticks()  # on fige le chrono
        self.temps_final = self._get_chrono()        # on calcule le temps final
        save_score(self.pseudo, self.temps_final)    # on sauvegarde en base de données
        self._show_end_screen()

    def _show_end_screen(self):
        # affiche l'image de félicitations/fin en la redimensionnant pour qu'elle rentre dans l'écran
        raw    = pygame.image.load("assets/Instructions/Message de fin.png").convert_alpha()
        rw, rh = raw.get_size()
        scale  = min(SCREEN_WIDTH / rw, SCREEN_HEIGHT / rh)  # facteur de zoom qui garde les proportions
        img    = pygame.transform.scale(raw, (int(rw * scale), int(rh * scale)))
        rect   = img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))  # centré dans la fenêtre

        # boucle d'attente : on reste sur l'image jusqu'à ce que le joueur appuie sur une touche
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False  # n'importe quelle touche ou clic passe à la suite
            self.screen.fill((0, 0, 0))
            self.screen.blit(img, rect)
            pygame.display.flip()
            self.clock.tick(FPS)

        self._show_score_screen()  # on passe ensuite à l'écran de classement

    def _show_score_screen(self):
        scores = get_top10()  # récupère les 10 meilleurs temps depuis la BDD

        # bouton pour quitter l'écran de score et retourner au menu
        btn_continuer = _SimpleButton("CONTINUER ▶", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90,
                                      w=260, h=54, font=self.ui_font)

        running = True
        while running:
            mx, my = pygame.mouse.get_pos()  # position de la souris pour le hover du bouton
            btn_continuer.update(mx, my)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if btn_continuer.is_clicked(event):
                    running = False  # le joueur a cliqué sur continuer

            self.screen.fill(C_SCORE_BG)

            cx = SCREEN_WIDTH // 2  # centre horizontal de l'écran, utilisé pour centrer tous les éléments

            # titre du classement
            titre = self.ui_font_big.render("CLASSEMENT", True, C_ACCENT)
            self.screen.blit(titre, titre.get_rect(centerx=cx, top=40))
            pygame.draw.line(self.screen, C_ACCENT2, (cx - 200, 90), (cx + 200, 90), 1)  # ligne décorative

            # affiche le temps du joueur actuel en évidence
            mon_temps = self._format_chrono(self.temps_final)
            sub = self.ui_font.render(f"Votre temps : {mon_temps}", True, C_ACCENT)
            self.screen.blit(sub, sub.get_rect(centerx=cx, top=105))

            # couleurs spéciales pour le podium (or, argent, bronze)
            colors_podium = [C_GOLD, C_SILVER, C_BRONZE]

            for i, (pseudo, temps) in enumerate(scores):
                y   = 165 + i * 56  # chaque ligne est espacée de 56 pixels
                col = colors_podium[i] if i < 3 else C_TEXT  # podium coloré, reste en blanc cassé

                # on surligne la ligne du joueur actuel avec un fond rectangulaire
                if pseudo == self.pseudo and abs(temps - self.temps_final) < 0.01:
                    pygame.draw.rect(self.screen, (40, 40, 60),
                                     pygame.Rect(cx - 270, y - 18, 540, 44), border_radius=6)

                # on dessine le rang, le pseudo et le temps sur la même ligne
                rang_s  = self.ui_font.render(f"#{i+1}", True, col)
                name_s  = self.ui_font.render(pseudo, True, col)
                temps_s = self.ui_font.render(self._format_chrono(temps), True, col)

                self.screen.blit(rang_s,  rang_s.get_rect(midright=(cx - 180, y)))   # rang à gauche
                self.screen.blit(name_s,  name_s.get_rect(midleft=(cx - 150, y)))    # pseudo au centre-gauche
                self.screen.blit(temps_s, temps_s.get_rect(midright=(cx + 260, y)))  # temps à droite

                # ligne séparatrice entre chaque entrée (sauf après la dernière)
                if i < len(scores) - 1:
                    pygame.draw.line(self.screen, (40, 40, 60), (cx - 270, y + 24), (cx + 270, y + 24), 1)

            btn_continuer.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)

        self._go_to_menu()  # une fois qu'on a cliqué sur continuer, on retourne au menu

    def _go_to_menu(self):
        menu   = MenuManager()
        result = menu.run()  # result vaut ("start", pseudo) si le joueur relance, None s'il quitte
        if result and result[0] == "start":
            self.__init__(pseudo=result[1])  # on réinitialise tout le jeu avec le nouveau pseudo
            self.run()
        else:
            pygame.quit()
            sys.exit()


    # -------------------------------------------------------
    # mise à jour et dessin des coeurs dans le HUD
    # -------------------------------------------------------

    def _update_hearts(self):
        hp = self.player.hp
        if hp < self.prev_hp:
            # le joueur vient de perdre un point de vie, on lance l'animation sur ce coeur
            lost = hp  # l'index du coeur perdu correspond au nouveau HP (ex: passe de 3 à 2 → coeur n°2)
            if 0 <= lost < self.player.max_hp:
                self.heart_states[lost]     = 'losing'
                self.heart_anim_index[lost] = 0.0  # on repart de la première frame d'animation
        self.prev_hp = hp

        # on avance l'animation pour tous les coeurs en train de se perdre
        for i in range(self.player.max_hp):
            if self.heart_states[i] == 'losing':
                self.heart_anim_index[i] += self.HEART_ANIM_SPEED
                if self.heart_anim_index[i] >= len(assets.assets.misc.heart_losing):
                    # l'animation est terminée, le coeur est maintenant vide
                    self.heart_states[i]     = 'empty'
                    self.heart_anim_index[i] = 0.0

        # si le joueur a tous ses HP, on remet tous les coeurs à plein (cas du soin)
        if hp == self.player.max_hp:
            self.heart_states     = ['full'] * self.player.max_hp
            self.heart_anim_index = [0.0] * self.player.max_hp

    def _draw_hud(self):
        m       = assets.assets.misc  # raccourci vers les assets graphiques
        SPACING = 45   # distance en pixels entre chaque coeur
        X0, Y   = 10, 10  # position du premier coeur (coin haut gauche)

        for i in range(self.player.max_hp):
            x     = X0 + i * SPACING
            state = self.heart_states[i]
            self.screen.blit(m.heart_empty, (x, Y))  # on dessine d'abord le coeur vide en dessous
            if state == 'full':
                self.screen.blit(m.heart_full, (x, Y))  # par-dessus on dessine le coeur plein
            elif state == 'losing':
                # on dessine la frame courante de l'animation de perte
                self.screen.blit(m.heart_losing[int(self.heart_anim_index[i])], (x, Y))

        # indicateur visuel du cooldown du dash (cercle vert = prêt, gris = en rechargement)
        now   = pygame.time.get_ticks()
        ready = (now - self.player.last_dash_time) >= self.player.props["dash_cooldown"]
        col   = (0, 200, 0) if ready else (30, 30, 30)  # vert si prêt, gris sinon
        dx    = int(X0 + (self.player.max_hp * SPACING) / 2)  # centré sous les coeurs
        dy    = Y + 50
        pygame.draw.circle(self.screen, col,             (dx, dy), 15)     # cercle coloré
        pygame.draw.circle(self.screen, (200, 200, 200), (dx, dy), 15, 2)  # contour gris clair


    # -------------------------------------------------------
    # sauvegarde du checkpoint le plus récent
    # -------------------------------------------------------

    def _check_checkpoints(self):
        # si le joueur touche un checkpoint, on mémorise sa position comme point de respawn
        for rect in self.checkpoint_rects:
            if self.player.hitbox.colliderect(rect):
                self.player.set_checkpoint(rect.centerx, rect.bottom)


    # -------------------------------------------------------
    # calcul et application des dégâts d'attaque
    # -------------------------------------------------------

    def _get_attack_hitbox(self):
        # retourne un rect étendu devant le joueur selon sa direction
        p  = self.player
        hb = p.hitbox.copy()
        if p.facing_right:
            hb.right += p.props["attack_reach"]  # portée vers la droite
        else:
            hb.left -= p.props["attack_reach"]   # portée vers la gauche
        return hb

    def _handle_attack(self):
        p = self.player
        if not p.is_attacking:
            return  # le joueur n'attaque pas, rien à faire

        # au début de l'animation d'attaque, on vide la liste des ennemis déjà touchés
        # pour pouvoir les toucher à nouveau lors d'une prochaine attaque
        if p.frame_index < p.anim_speed + 0.01:
            self.attacked_enemies.clear()

        atk_hb = self._get_attack_hitbox()  # hitbox d'attaque étendue
        for enemy in self.enemies:
            if enemy in self.attacked_enemies:
                continue  # on ne touche pas deux fois le même ennemi dans la même attaque
            if atk_hb.colliderect(enemy.hitbox):
                d = 1 if p.facing_right else -1  # direction du knockback : +1 droite, -1 gauche
                enemy.take_damage(1, d)
                self.attacked_enemies.add(enemy)  # on mémorise qu'on l'a déjà frappé


    # -------------------------------------------------------
    # déplacements et résolution de toutes les collisions
    # -------------------------------------------------------

    def _handle_collisions(self):
        p           = self.player
        world_width = self.tilemap.map_width  # largeur totale de la carte en pixels

        if not p.is_dying:
            if p.is_dashing:
                # pendant le dash, déplacement horizontal fixe, pas de gravité
                dx = p.dash_direction * p.props["dash_speed"]
                dy = 0
            else:
                dx = p.direction.x * p.props["walk_speed"]
                p.direction.y += p.props["gravity"]  # on applique la gravité à la vitesse verticale
                dy = p.direction.y

            flags = move_and_collide(p.hitbox, dx, dy, self.platforms)
            p.on_ground     = flags["on_ground"]
            p.on_wall_left  = flags["on_wall_left"]
            p.on_wall_right = flags["on_wall_right"]

            # si on touche le sol ou le plafond, on annule la vitesse verticale
            if flags["on_ground"] or flags["hit_ceiling"]:
                p.direction.y = 0
            # si on dash contre un mur, le dash est annulé
            if p.is_dashing and (flags["on_wall_left"] or flags["on_wall_right"]):
                p.is_dashing = False

            # on empêche le joueur de sortir par les bords gauche/droit de la carte
            if p.hitbox.left < 0:            p.hitbox.left  = 0
            if p.hitbox.right > world_width: p.hitbox.right = world_width

            # collision avec les piques : inflige 1 dégât et on sort de la boucle immédiatement
            for spike in self.tilemap.spike_rects:
                if p.hitbox.colliderect(spike):
                    p.take_damage(1)
                    break

        # --- collisions pour chaque ennemi ---
        for enemy in self.enemies:
            if not enemy.is_dying:
                enemy.direction.y += enemy.props["gravity"]  # gravité sur les ennemis aussi

            flags = move_and_collide(enemy.hitbox, enemy.direction.x, enemy.direction.y, self.platforms)
            enemy.on_ground = flags["on_ground"]

            if flags["on_ground"] or flags["hit_ceiling"]:
                enemy.direction.y = 0
                if enemy.is_knocked:
                    enemy.knockback_vel.y = 0  # on stoppe le knockback vertical quand on touche le sol

            # si l'ennemi n'est pas en train d'être repoussé/mourir, il fait demi-tour quand il touche un mur
            if not enemy.is_knocked and not enemy.is_dying:
                if flags["on_wall_right"]:
                    enemy.state = 'left'; enemy.facing_right = False
                    enemy.direction.x = -enemy.move_speed; enemy._set_walk_anim()
                elif flags["on_wall_left"]:
                    enemy.state = 'right'; enemy.facing_right = True
                    enemy.direction.x = enemy.move_speed; enemy._set_walk_anim()

        # --- dégâts de contact : si un ennemi touche le joueur, celui-ci perd 1 HP ---
        for enemy in self.enemies:
            if not enemy.is_dying and p.hitbox.colliderect(enemy.hitbox):
                p.take_damage(1)


    # -------------------------------------------------------
    # boucle principale du jeu, tourne jusqu'à la fin
    # -------------------------------------------------------

    def run(self):
        while True:
            # --- gestion des événements (clavier, souris, fermeture) ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.player.handle_event(event)      # le joueur réagit aux inputs
                self.end_manager.handle_event(event) # la zone de fin peut aussi avoir besoin des events
                for npc in self.npcs:
                    npc.handle_event(event)
                for soldier in self.npcs2:
                    soldier.handle_event(event)

            dt = self.clock.get_time() / 1000  # temps écoulé depuis la dernière frame, en secondes

            # --- mise à jour de la logique ---
            self.player.update()
            self.enemies.update()
            for npc in self.npcs:
                npc.update(self.player.hitbox, dt)  # les PNJ ont besoin de savoir où est le joueur
            for soldier in self.npcs2:
                soldier.update(self.player.hitbox, dt)

            self._handle_collisions()   # déplacements + résolution des collisions
            self._handle_attack()       # détection des hits d'attaque
            self._update_hearts()       # mise à jour de l'état des coeurs
            self._check_checkpoints()   # activation des checkpoints
            self.end_manager.update(self.player.hitbox)  # vérifie si le joueur est dans la zone de fin

            # --- dessin de tout l'écran (ordre important : fond → carte → entités → HUD) ---
            self.screen.fill((0, 0, 0))         # fond noir pour effacer la frame précédente
            self.tilemap.draw(self.screen, 0)    # dessin de la carte (le 0 = offset caméra ou couche)

            for enemy in self.enemies:
                enemy.draw(self.screen, None)
            for npc in self.npcs:
                npc.draw(self.screen, None, self.ui_font_small)
            for soldier in self.npcs2:
                soldier.draw(self.screen, None, self.ui_font_small)

            self.player.draw(self.screen, None)
            self._draw_hud()            # coeurs et indicateur de dash
            self._draw_chrono()         # chrono en haut à droite
            self.end_manager.draw_prompt(self.screen, self.ui_font)  # message d'invite si on est près de la fin

            pygame.display.flip()       # on envoie tout ce qu'on a dessiné à l'écran
            self.clock.tick(FPS)        # on attend pour ne pas dépasser la limite de FPS


# -------------------------------------------------------
# bouton simple utilisé uniquement dans l'écran de score
# -------------------------------------------------------

# couleurs utilisées dans l'écran de score et le bouton
C_ACCENT  = (220, 160,  40)   # doré/orange pour les titres
C_ACCENT2 = (180, 100,  20)   # version plus sombre de l'accent
C_TEXT    = (240, 230, 210)   # blanc cassé pour le texte normal
C_MUTED   = (120, 115, 100)   # gris pour les éléments discrets
C_BG2     = (20,  24,  40)    # fond sombre du bouton
C_GOLD    = (255, 215,   0)   # couleur de la 1ère place
C_SILVER  = (192, 192, 192)   # couleur de la 2ème place
C_BRONZE  = (205, 127,  50)   # couleur de la 3ème place
C_CHRONO  = (255, 230,  80)   # couleur du texte du chrono en jeu
C_SCORE_BG= (12,  14,  23)    # fond très sombre de l'écran de classement


class _SimpleButton:
    # bouton allégé sans icône, créé uniquement pour l'écran de résultat
    def __init__(self, text, cx, cy, w, h, font):
        self.text = text
        self.font = font
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = (cx, cy)  # on centre le bouton sur les coordonnées données
        self.hover_t = 0.0  # valeur entre 0 et 1 qui indique si la souris est dessus (transition douce)

    def update(self, mx, my):
        # on fait glisser hover_t vers 1 si la souris est dessus, vers 0 sinon (interpolation linéaire)
        target = 1.0 if self.rect.collidepoint(mx, my) else 0.0
        self.hover_t += (target - self.hover_t) * 0.12

    def is_clicked(self, event):
        # retourne True seulement si c'est un clic gauche à l'intérieur du bouton
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    def draw(self, surface):
        t = self.hover_t  # on récupère l'état de hover (0 = pas survolé, 1 = survolé)

        # interpolation des couleurs entre l'état normal et l'état survolé
        bg     = tuple(int(C_BG2[i] + (C_ACCENT2[i] - C_BG2[i]) * t) for i in range(3))
        border = tuple(int(C_MUTED[i] + (C_ACCENT[i] - C_MUTED[i]) * t) for i in range(3))
        col    = tuple(int(C_TEXT[i] + ((12 - C_TEXT[i]) * t)) for i in range(3))  # texte s'assombrit au hover

        pygame.draw.rect(surface, bg,     self.rect, border_radius=8)      # fond du bouton
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=8)   # bordure du bouton (épaisseur 2)
        surf = self.font.render(self.text, True, col)
        surface.blit(surf, surf.get_rect(center=self.rect.center))  # texte centré dans le bouton


# -------------------------------------------------------
# point d'entrée : lancé quand on exécute ce fichier directement
# -------------------------------------------------------

if __name__ == "__main__":
    menu   = MenuManager()
    result = menu.run()  # lance le menu et attend le choix du joueur
    if result and result[0] == "start":
        Game(pseudo=result[1]).run()  # on crée le jeu avec le pseudo saisi et on le lance