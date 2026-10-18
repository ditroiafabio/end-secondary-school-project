import pygame
import os
from entities_properties import EntityProperties

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # dossier racine du projet


def _path(*parts):
    # construit un chemin absolu à partir du dossier racine
    return os.path.join(BASE_DIR, *parts)


def get_frames(sheet, row, frame_count, frame_width, frame_height):
    # extrait une liste de frames depuis un spritesheet (une grille d'images)
    # row = numéro de la ligne à extraire, frame_count = nombre de frames sur cette ligne
    frames = []
    for i in range(frame_count):
        rect = pygame.Rect(i * frame_width, row * frame_height, frame_width, frame_height)
        frames.append(sheet.subsurface(rect))
    return frames


def scale_frames(frames, factor):
    # redimensionne toutes les frames d'une liste par le facteur donné
    scaled = []
    for frame in frames:
        new_size = (int(frame.get_width() * factor), int(frame.get_height() * factor))
        scaled.append(pygame.transform.scale(frame, new_size))
    return scaled


# ============================================================
# sprites du joueur (swordsman)
# ============================================================

class PlayerAssets:
    def __init__(self):
        factor = EntityProperties.PLAYER["scale_factor"]  # facteur d'agrandissement défini dans les stats

        # chargement de tous les spritesheets du joueur (une image = toutes les frames d'une animation)
        run_sheet        = pygame.image.load(_path("assets", "Swordsman", "Swordsman_lvl1", "With_shadow", "Swordsman_lvl1_Run_with_shadow.png")).convert_alpha()
        idle_sheet       = pygame.image.load(_path("assets", "Swordsman", "Swordsman_lvl1", "With_shadow", "Swordsman_lvl1_Idle_with_shadow.png")).convert_alpha()
        attack_sheet     = pygame.image.load(_path("assets", "Swordsman", "Swordsman_lvl1", "With_shadow", "Swordsman_lvl1_attack_with_shadow.png")).convert_alpha()
        death_sheet      = pygame.image.load(_path("assets", "Swordsman", "Swordsman_lvl1", "With_shadow", "Swordsman_lvl1_Death_with_shadow.png")).convert_alpha()
        hurt_sheet       = pygame.image.load(_path("assets", "Swordsman", "Swordsman_lvl1", "With_shadow", "Swordsman_lvl1_Hurt_with_shadow.png")).convert_alpha()
        run_attack_sheet = pygame.image.load(_path("assets", "Swordsman", "Swordsman_lvl1", "With_shadow", "Swordsman_lvl1_Run_Attack_with_shadow.png")).convert_alpha()

        # on calcule la largeur d'une frame en divisant la largeur totale par le nombre de frames
        W_run,        H_run        = run_sheet.get_width() // 8,         run_sheet.get_height() // 4
        W_idle,       H_idle       = idle_sheet.get_width() // 12,       idle_sheet.get_height() // 4
        W_attack,     H_attack     = attack_sheet.get_width() // 8,      attack_sheet.get_height() // 4
        W_death,      H_death      = death_sheet.get_width() // 7,       death_sheet.get_height() // 4
        W_hurt,       H_hurt       = hurt_sheet.get_width() // 5,        hurt_sheet.get_height() // 4
        W_run_attack, H_run_attack = run_attack_sheet.get_width() // 8,  run_attack_sheet.get_height() // 4

        # ligne 0 = face, ligne 1 = gauche, ligne 2 = droite dans les spritesheets
        self.idle = scale_frames(get_frames(idle_sheet, 0, 12, W_idle, H_idle), factor)  # 12 frames d'idle

        self.run_left  = scale_frames(get_frames(run_sheet, 1, 8, W_run, H_run), factor)
        self.run_right = scale_frames(get_frames(run_sheet, 2, 8, W_run, H_run), factor)

        self.attack_left  = scale_frames(get_frames(attack_sheet, 1, 8, W_attack, H_attack), factor)
        self.attack_right = scale_frames(get_frames(attack_sheet, 2, 8, W_attack, H_attack), factor)

        self.death_left  = scale_frames(get_frames(death_sheet, 1, 7, W_death, H_death), factor)
        self.death_right = scale_frames(get_frames(death_sheet, 2, 7, W_death, H_death), factor)

        self.hurt_left  = scale_frames(get_frames(hurt_sheet, 1, 5, W_hurt, H_hurt), factor)
        self.hurt_right = scale_frames(get_frames(hurt_sheet, 2, 5, W_hurt, H_hurt), factor)

        self.run_attack_left  = scale_frames(get_frames(run_attack_sheet, 1, 8, W_run_attack, H_run_attack), factor)
        self.run_attack_right = scale_frames(get_frames(run_attack_sheet, 2, 8, W_run_attack, H_run_attack), factor)


# sprites du renard PNJ guide
class FoxAssets:
    def __init__(self):
        factor = EntityProperties.FOX["scale_factor"]

        idle_fox_sheet = pygame.image.load(_path("assets", "Renard", "Fox_Idle.png")).convert_alpha()
        talk_fox_sheet = pygame.image.load(_path("assets", "Renard", "Fox_Talk.png")).convert_alpha()

        # le renard n'a qu'une seule ligne dans ses spritesheets
        W_idle, H_idle = idle_fox_sheet.get_width() // 14, idle_fox_sheet.get_height()
        W_talk, H_talk = talk_fox_sheet.get_width() // 14, talk_fox_sheet.get_height()

        self.idle = scale_frames(get_frames(idle_fox_sheet, 0, 6,  W_idle, H_idle), factor)   # 6 frames d'idle
        self.talk = scale_frames(get_frames(talk_fox_sheet, 0, 14, W_talk, H_talk), factor)   # 14 frames de dialogue


# sprites du soldat PNJ
class SoldierAssets:
    def __init__(self):
        factor = EntityProperties.SOLDIER["scale_factor"]

        idle_soldier_sheet = pygame.image.load(_path("assets", "Soldat", "Soldier-Idle.png")).convert_alpha()

        W_idle, H_idle = idle_soldier_sheet.get_width() // 6, idle_soldier_sheet.get_height()

        self.idle = scale_frames(get_frames(idle_soldier_sheet, 0, 6, W_idle, H_idle), factor)  # 6 frames d'idle


# sprites du slime vert (ennemi de base)
class SlimeGreenAssets:
    def __init__(self):
        factor = EntityProperties.SLIME_GREEN["scale_factor"]

        idle_sheet  = pygame.image.load(_path("assets", "Slime", "Green_Slime", "Idle.png")).convert_alpha()
        walk_sheet  = pygame.image.load(_path("assets", "Slime", "Green_Slime", "Walk.png")).convert_alpha()
        death_sheet = pygame.image.load(_path("assets", "Slime", "Green_Slime", "Dead.png")).convert_alpha()
        hurt_sheet  = pygame.image.load(_path("assets", "Slime", "Green_Slime", "Hurt.png")).convert_alpha()

        # le slime n'a qu'une ligne par spritesheet
        W_idle,  H_idle  = idle_sheet.get_width() // 8,  idle_sheet.get_height()
        W_walk,  H_walk  = walk_sheet.get_width() // 8,  walk_sheet.get_height()
        W_death, H_death = death_sheet.get_width() // 3, death_sheet.get_height()  # seulement 3 frames de mort
        W_hurt,  H_hurt  = hurt_sheet.get_width() // 6,  hurt_sheet.get_height()

        self.idle  = scale_frames(get_frames(idle_sheet,  0, 8, W_idle,  H_idle),  factor)
        self.walk  = scale_frames(get_frames(walk_sheet,  0, 8, W_walk,  H_walk),  factor)
        self.death = scale_frames(get_frames(death_sheet, 0, 3, W_death, H_death), factor)
        self.hurt  = scale_frames(get_frames(hurt_sheet,  0, 6, W_hurt,  H_hurt),  factor)


# ============================================================
# assets de l'interface utilisateur (HUD, coeurs, etc.)
# ============================================================

class MiscAssets:
    def __init__(self):
        self.bg_color = (240, 240, 240)

        # petit carré gris pour les murs (résidu de debug, pas utilisé visuellement en jeu)
        self.wall_img = pygame.Surface((10, 10))
        self.wall_img.fill((70, 70, 70))

        HEART_SIZE = (40, 40)  # taille d'affichage des icônes de coeur dans le HUD

        # chargement des images des coeurs
        full_img     = pygame.image.load(_path("assets", "Vie", "basic", "heart.png")).convert_alpha()
        empty_img    = pygame.image.load(_path("assets", "Vie", "basic", "background.png")).convert_alpha()
        losing_sheet = pygame.image.load(_path("assets", "vie", "animated", "no_border", "heart_animated_2.png")).convert_alpha()

        self.heart_full  = pygame.transform.scale(full_img,  HEART_SIZE)
        self.heart_empty = pygame.transform.scale(empty_img, HEART_SIZE)

        # extraction des 4 frames de l'animation de perte de coeur depuis le spritesheet
        frame_w = losing_sheet.get_width() // 5
        frame_h = losing_sheet.get_height()
        self.heart_losing = [
            pygame.transform.scale(
                losing_sheet.subsurface(pygame.Rect(i * frame_w, 0, frame_w, frame_h)),
                HEART_SIZE
            )
            for i in range(4)  # on extrait seulement 4 frames sur les 5 disponibles
        ]


# ============================================================
# conteneur global qui regroupe tous les assets du jeu
# ============================================================

class Assets:
    def __init__(self):
        self.player      = PlayerAssets()
        self.fox         = FoxAssets()
        self.soldier     = SoldierAssets()
        self.slime_green = SlimeGreenAssets()
        self.misc        = MiscAssets()


# variable globale accessible depuis tout le projet via "import assets; assets.assets.xxx"
assets: Assets = None


def load_assets():
    # à appeler une seule fois au démarrage, après pygame.init()
    global assets
    assets = Assets()