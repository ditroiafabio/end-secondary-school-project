import pygame

# taille de la fenêtre de jeu en pixels
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1080
FPS = 60

# touches de contrôle du joueur
KEY_MOVE   = pygame.K_z       # maintenir Z pour avancer (la direction dépend de la souris)
KEY_JUMP   = pygame.K_SPACE   # espace pour sauter
KEY_DASH   = pygame.K_LSHIFT  # shift gauche pour le dash
KEY_ATTACK = pygame.K_e       # E pour attaquer

GRAVITY    = 0.8    # accélération vers le bas appliquée chaque frame
WALK_SPEED = 6      # vitesse de déplacement horizontal en pixels par frame
JUMP_FORCE = -17    # force du saut (négatif = vers le haut)

WALL_JUMP_FORCE = (12, -14)  # (poussée horizontale, poussée verticale) lors d'un wall jump

DASH_SPEED    = 22    # vitesse pendant le dash en pixels par frame
DASH_DURATION = 130   # durée du dash en millisecondes
DASH_COOLDOWN = 3000  # temps minimum entre deux dashs en ms (soit 3 secondes)