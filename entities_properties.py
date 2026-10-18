class EntityProperties:

    # stats complètes du joueur
    PLAYER = {
        "name": "Joueur",

        # dimensions de la hitbox (zone de collision, plus petite que le sprite visible)
        "hitbox_width":  30,
        "hitbox_height": 40,

        # espace vide entre le bas de l'image et les pieds réels du personnage
        # sert à aligner correctement le sprite sur la hitbox
        "empty_space_bottom": 40,

        # facteur d'agrandissement du sprite au chargement (2 = deux fois plus grand)
        "scale_factor": 2,

        # vitesses de déplacement
        "walk_speed":       6,
        "jump_force":      -17,   # valeur négative car Y=0 est en haut de l'écran
        "wall_jump_force_x": 12,  # poussée horizontale lors d'un saut mural
        "wall_jump_force_y": -14, # poussée verticale lors d'un saut mural

        # paramètres du dash
        "dash_speed":    22,
        "dash_duration": 130,   # durée en ms pendant laquelle le dash est actif
        "dash_cooldown": 3000,  # délai en ms avant de pouvoir re-dasher

        "gravity":    0.8,   # accélération gravitationnelle ajoutée à direction.y chaque frame
        "anim_speed": 0.15,  # nombre de frames d'animation avancées par frame de jeu

        "attack_reach": 30,  # extension de la hitbox d'attaque au-delà de la hitbox normale (en px)

        "max_hp": 3,  # points de vie maximum du joueur

        # invincibilité temporaire après avoir subi des dégâts (pour éviter les coups répétés)
        "iframe_duration": 1000,  # durée en ms pendant laquelle on ne peut pas être re-touché
        "hurt_duration":    800,  # durée de l'animation de douleur en ms
    }

    # stats du slime vert, ennemi de base du jeu
    SLIME_GREEN = {
        "name": "Slime Vert",

        "hitbox_width":  28,
        "hitbox_height": 28,
        "empty_space_bottom": 30,
        "scale_factor": 1.2,  # agrandi par rapport à la taille originale

        "move_speed": 1.5,  # vitesse de patrouille en pixels par frame
        "gravity":    0.5,  # gravité plus faible que le joueur
        "anim_speed": 0.1,  # animation plus lente que le joueur

        "max_hp": 5,  # le slime résiste à 5 coups avant de mourir

        # recul appliqué au slime quand il reçoit un coup
        "knockback_x":        5,    # vitesse horizontale du recul en px/frame
        "knockback_y":       -3,    # petit bond vers le haut (valeur négative = vers le haut)
        "knockback_duration": 200,  # durée du recul en ms avant de reprendre le comportement normal

        # vitesses d'animation pour les états spéciaux (différentes de l'anim de marche)
        "death_anim_speed": 0.08,  # mort : animation lente pour bien la voir
        "hurt_anim_speed":  0.15,  # dégât : animation rapide

        # séquence de comportements que le slime répète en boucle (pattern de patrouille)
        # chaque tuple : ("état", durée en ms)
        "pattern": [
            ("idle",  2000),  # reste immobile 2 secondes
            ("right", 1500),  # avance vers la droite pendant 1,5 secondes
            ("idle",  2000),  # pause à nouveau
            ("left",  1500),  # revient vers la gauche
        ]
    }

    # propriétés du renard PNJ (guide joueur)
    FOX = {
        "name":         "Renard",
        "scale_factor": 2,
        "anim_speed":   0.12,
    }

    # propriétés du soldat PNJ (je l'utilise pas)
    SOLDIER = {
        "name":         "Soldier",
        "scale_factor": 2,
        "anim_speed":   0.12,
    }