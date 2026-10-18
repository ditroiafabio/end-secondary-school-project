import pygame
import pytmx

# noms des calques Tiled qui doivent bloquer le passage du joueur et des ennemis
SOLID_LAYERS = ("ground", "solid props")

KEY_INTERACT = pygame.K_f  # touche pour interagir avec la zone de fin


# ---------------------------------------------------------------
# charge et parse un fichier .tmx créé avec l'éditeur Tiled
# ---------------------------------------------------------------

class TileMap:

    def __init__(self, tmx_path):
        # on charge le fichier .tmx avec pygame comme backend pour les images
        self.tmx_data = pytmx.load_pygame(tmx_path, pixelalpha=True)

        # dimensions d'une tuile et de la carte complète en pixels
        self.tile_width  = self.tmx_data.tilewidth
        self.tile_height = self.tmx_data.tileheight
        self.map_width   = self.tmx_data.width  * self.tile_width
        self.map_height  = self.tmx_data.height * self.tile_height

        self.tile_surfaces = []                      # liste de (nom_calque, surface) pour le rendu
        self.platforms     = pygame.sprite.Group()   # sprites invisibles représentant les tuiles solides

        # données extraites des calques d'objets Tiled
        self.enemy_spawns  = []  # dicts {x, y, left_x, right_x} pour chaque ennemi
        self.npc_spawns    = []  # positions (x, y) des renards PNJ
        self.npc_spawns2   = []  # positions (x, y) des soldats PNJ
        self.checkpoints   = []  # rects des zones de checkpoint
        self.end_zones     = []  # rects des zones de sortie de niveau
        self.text_triggers = []  # dicts {rect, message} pour les messages de zone
        self.spike_rects   = []  # rects des tuiles de piques

        self._parse()  # on analyse tous les calques au moment du chargement


    def _parse(self):
        raw_spp   = []  # points de spawn des ennemis (avant association avec leurs limites)
        raw_limit = []  # points de limite de patrouille des ennemis

        for layer in self.tmx_data.layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                # calque de tuiles : on le dessine et on vérifie s'il est solide
                if layer.visible:
                    surf = self._render_tile_layer(layer)
                else:
                    continue  # on ignore les calques masqués
                self.tile_surfaces.append((layer.name, surf))

                if layer.name in SOLID_LAYERS:
                    self._build_collisions(layer)  # on crée les sprites de collision
                if layer.name == "spikes":
                    self._build_spike_rects(layer)  # on stocke les rects des piques séparément

            elif isinstance(layer, pytmx.TiledObjectGroup):
                # calque d'objets : on parse chaque objet selon son calque et son nom
                self._parse_objects(layer, raw_spp, raw_limit)

        # une fois tous les objets lus, on associe chaque spawn d'ennemi à sa borne de patrouille
        self._associate_enemies(raw_spp, raw_limit)

    def _render_tile_layer(self, layer):
        # dessine toutes les tuiles du calque sur une grande surface de la taille de la carte
        surf = pygame.Surface((self.map_width, self.map_height), pygame.SRCALPHA)
        tw, th = self.tile_width, self.tile_height
        for x, y, gid in layer:
            tile = self.tmx_data.get_tile_image_by_gid(gid)
            if tile:
                surf.blit(tile, (x * tw, y * th))
        return surf

    def _build_collisions(self, layer):
        # pour chaque tuile solide, on crée un sprite invisible avec un rect de collision
        tw, th = self.tile_width, self.tile_height
        for x, y, gid in layer:
            if gid == 0:
                continue  # gid == 0 = case vide, pas de tuile
            sprite       = pygame.sprite.Sprite()
            sprite.rect  = pygame.Rect(x * tw, y * th, tw, th)
            sprite.image = pygame.Surface((tw, th), pygame.SRCALPHA)  # image vide (invisible)
            self.platforms.add(sprite)

    def _build_spike_rects(self, layer):
        # stocke juste les rects des piques pour vérifier les collisions dans main.py
        tw, th = self.tile_width, self.tile_height
        for x, y, gid in layer:
            if gid != 0:
                self.spike_rects.append(pygame.Rect(x * tw, y * th, tw, th))

    def _parse_objects(self, layer, raw_spp, raw_limit):
        layer_name = layer.name.lower()  # on compare en minuscules pour éviter les erreurs de casse

        for obj in layer:
            name = (obj.name or "").lower()
            x    = int(obj.x)
            y    = int(obj.y)
            w    = int(obj.width)  if obj.width  else self.tile_width
            h    = int(obj.height) if obj.height else self.tile_height
            rect = pygame.Rect(x, y, w, h)

            if layer_name == "text":
                # on récupère le message dans les propriétés de l'objet Tiled
                msg = (getattr(obj, "properties", {}) or {}).get("message", "Sautez sur le mur !")
                self.text_triggers.append({"rect": rect, "message": msg})

            elif layer_name == "pnj2":
                # spawn de renard : le bas-centre de l'objet = position des pieds du PNJ
                self.npc_spawns.append((x + w // 2, y + h))

            elif layer_name == "pnj3":
                self.npc_spawns2.append((x + w // 2, y + h))

            elif layer_name == "enemy":
                if name == "enemyspp":
                    raw_spp.append({"x": x + w // 2, "y": y + h})     # point de spawn
                elif name == "enemylimit":
                    raw_limit.append({"x": x + w // 2})                # borne de patrouille

            elif name in ("checkpoint", "checkpoints"):
                self.checkpoints.append(rect)

            elif layer_name == "end" or name == "end":
                # on accepte l'objet s'il est dans un calque "end" OU s'il s'appelle "end"
                self.end_zones.append(rect)

    def _associate_enemies(self, raw_spp, raw_limit):
        # pour chaque spawn d'ennemi, on cherche le point de limite le plus proche en X
        for spp in raw_spp:
            sx = spp["x"]
            sy = spp["y"]

            best    = min(raw_limit, key=lambda l: abs(l["x"] - sx), default=None)
            limit_x = best["x"] if best else sx + 200  # 200px par défaut si pas de limite définie

            self.enemy_spawns.append({
                "x":       sx,
                "y":       sy,
                "left_x":  min(sx, limit_x),   # la borne gauche est la plus petite des deux X
                "right_x": max(sx, limit_x),   # la borne droite est la plus grande
            })


    def draw(self, screen, camera_offset_x):
        # on dessine chaque calque en décalant selon l'offset de caméra (scrolling horizontal)
        for _, surf in self.tile_surfaces:
            screen.blit(surf, (-camera_offset_x, 0))


# ---------------------------------------------------------------
# gère la zone de sortie de niveau définie dans Tiled
# ---------------------------------------------------------------

class EndZoneManager:

    def __init__(self, end_zones, on_level_complete):
        self.end_zones         = end_zones          # liste de rects des zones de fin
        self.on_level_complete = on_level_complete  # fonction appelée quand le joueur sort
        self._prompt_visible   = False              # True si le joueur est actuellement dans une zone de fin

    def update(self, player_hitbox):
        # on vérifie si le joueur touche au moins une zone de fin
        self._prompt_visible = any(player_hitbox.colliderect(z) for z in self.end_zones)

    def handle_event(self, event):
        # si le joueur est dans la zone et appuie sur F, on déclenche la fin du niveau
        if self._prompt_visible and event.type == pygame.KEYDOWN and event.key == KEY_INTERACT:
            self.on_level_complete()

    def draw_prompt(self, screen, font):
        if not self._prompt_visible:
            return
        # message affiché en bas au centre de l'écran
        surf = font.render("[F] Sortir", True, (255, 230, 80))
        cx   = screen.get_width()