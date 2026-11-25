from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from random import randint, choice, sample
from datetime import timedelta
from urllib.parse import quote_plus

from app.models import (
    Game, Category, GameCategory, Member, Player, Organizer,
    WishlistCollection, Notification, Match, MatchParticipant, Follow,
    Friendship, Review, Tournament, TournamentResult, Participation,
    OrganizerRequest, FriendRequest,
)

# ---------------------------------------------------------------------------
# Data for generating realistic names / titles
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Marko", "Ana", "Nikola", "Jelena", "Petar", "Milan", "Ivana", "Stefan",
    "Milica", "Aleksandar", "Tijana", "Nemanja", "Jovana", "Dusan", "Katarina",
    "Bojan", "Sara", "Vladimir", "Teodora", "Filip", "Andjela", "Uros",
    "Marija", "Luka", "Anastasija", "Igor", "Sofija", "Nikolina", "Dejan",
    "Tamara", "Ognjen", "Isidora", "Vukasin", "Milena", "Strahinja", "Jana",
    "Vasilije", "Dunja", "Aleksa", "Mila",
]

LAST_NAMES = [
    "Petrovic", "Jovanovic", "Nikolic", "Markovic", "Djordjevic", "Stojanovic",
    "Ilic", "Stankovic", "Pavlovic", "Milosevic", "Simic", "Kovacevic",
    "Ristic", "Vukovic", "Antic", "Popovic", "Radovic", "Dimitrijevic",
    "Todorovic", "Lazic", "Maric", "Zivkovic", "Krstic", "Savic", "Obradovic",
    "Cvetkovic", "Milic", "Vasic", "Aleksic", "Filipovic",
]

ADJECTIVES = [
    "Mysterious", "Lost", "Forgotten", "Last", "Ancient",
    "Gloomy", "Golden", "Icy", "Fiery", "Unknown", "Royal",
    "Wild", "Silent", "Endless", "Hidden", "Dangerous", "Mighty", "Cursed",
    "Shining", "Dark",
]

NOUNS = [
    "Island", "Tower", "Empire", "Legend", "Quest", "Hunt", "Trail",
    "Horizon", "Labyrinth", "Chest", "City", "World", "Portal", "Landscape",
    "Trace", "Castle", "Club", "Tournament", "Garden", "Gambit",
]

EXTRA_CATEGORIES = [
    "Cooperative games", "Dice games", "Card games", "Economic games",
    "Abstract games", "Board games", "Children's games", "Word games",
    "Trivia games", "War games", "Role-playing games", "Detective games",
    "Building games", "Bluffing games", "Two-player games",
]

GAME_DESCRIPTIONS = [
    "A game for the whole family with simple rules.",
    "A strategy game that requires planning ahead.",
    "A fast game ideal for larger groups.",
    "A cooperative game in which all players work together against the board.",
    "A classic that is easy to learn but hard to master.",
    "A game with elements of bluffing and negotiation.",
]

REVIEW_TEXTS = [
    "Excellent game, tested over many matches!",
    "Fun, but lasts a bit longer than we expected.",
    "The rules are clear and easy to teach to new players.",
    "One of the favorites in our group.",
    "Solid game, but not for everyone.",
    "Recommended for larger groups and a relaxed evening.",
]

# Color palettes (background, text) for generated placeholder game images
COLOR_PALETTE = [
    ("2c3e50", "f5deb3"),
    ("8b4513", "fdf5e6"),
    ("1e3a5f", "e8d9b5"),
    ("3d2817", "f0e6d2"),
    ("4a5d23", "faf3e0"),
    ("6b2737", "f5e6d3"),
]


class Command(BaseCommand):
    help = "Extended seed for BoardNet: base data + bulk test data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        self._clean()

        self.stdout.write("Creating base users (marko, ana, nikola, jelena, petar)...")
        players, organizers, used_usernames = self._create_base_users()

        self.stdout.write("Creating base categories and games...")
        categories, games, used_game_names, used_category_names = self._create_base_catalog()

        self.stdout.write("Creating base relations (wishlist, friendships, reviews, tournament, match, notifications)...")
        self._create_base_relations(players, organizers, games)

        self.stdout.write("Adding 100 new users (85 players, 15 organizers)...")
        new_players, new_organizers = self._create_extra_users(85, 15, used_usernames)
        players += new_players
        organizers += new_organizers

        self.stdout.write("Adding 100 new games...")
        new_games = self._create_extra_games(100, used_game_names)
        games += new_games

        self.stdout.write("Adding categories (15 new - more than that makes no sense, categories are by nature a limited set)...")
        new_categories = self._create_extra_categories(used_category_names)
        categories += new_categories

        self.stdout.write("Adding 50 game-category relations...")
        self._create_game_categories(games, categories, 50)

        self.stdout.write("Adding 50 wishlist/collection records...")
        self._create_wishlist(players, organizers, games, 50)

        self.stdout.write("Adding 50 friendships...")
        self._create_friendships(players, 50)

        self.stdout.write("Adding 50 friend requests...")
        self._create_friend_requests(players, 50)

        self.stdout.write("Adding 50 reviews...")
        self._create_reviews(players, organizers, games, 50)

        self.stdout.write("Adding organizer requests (1 per new organizer - OneToOne constraint)...")
        newly_approved = self._create_organizer_requests(new_organizers)
        # petar (base organizer) is already approved in _create_base_users
        approved_organizers = [organizers[0]] + newly_approved

        self.stdout.write("Adding 50 new tournaments (only approved organizers can run them)...")
        new_tournaments = self._create_tournaments(approved_organizers, games, 50)

        self.stdout.write("Adding tournament participations and results...")
        self._create_participations_and_results(new_tournaments, players)

        self.stdout.write("Adding 50 follows (player follows organizer)...")
        self._create_follows(players, organizers, 50)

        self.stdout.write("Adding 50 matches (with participants)...")
        self._create_matches(players, games, 50)

        self.stdout.write(self.style.SUCCESS("Extended seed finished!"))

    # -----------------------------------------------------------------
    # Game images (placeholder generated through a URL, without storing files)
    # -----------------------------------------------------------------

    def _image_url(self, name, width=400, height=300):
        bg, fg = choice(COLOR_PALETTE)
        text = quote_plus(name)
        return f"https://placehold.co/{width}x{height}/{bg}/{fg}?text={text}&font=playfair-display"

    # -----------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------

    def _clean(self):
        TournamentResult.objects.all().delete()
        Participation.objects.all().delete()
        MatchParticipant.objects.all().delete()
        Match.objects.all().delete()
        Review.objects.all().delete()
        Friendship.objects.all().delete()
        FriendRequest.objects.all().delete()
        Follow.objects.all().delete()
        WishlistCollection.objects.all().delete()
        GameCategory.objects.all().delete()
        Tournament.objects.all().delete()
        Notification.objects.all().delete()

        Game.objects.all().delete()
        Category.objects.all().delete()

        Player.objects.all().delete()
        OrganizerRequest.objects.all().delete()
        Organizer.objects.all().delete()
        Member.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

    # -----------------------------------------------------------------
    # Base data (identical to the original seed_test2)
    # -----------------------------------------------------------------

    def _create_base_users(self):
        usernames = ["marko", "ana", "nikola", "jelena", "petar"]
        players, organizers = [], []

        for u in usernames:
            user = User.objects.create_user(
                username=u, password="test123", email=f"{u}@boardnet.rs"
            )
            k = Member.objects.create(idu=user)

            if u in ["marko", "ana", "nikola", "jelena"]:
                players.append(Player.objects.create(idu=k))
            else:
                org = Organizer.objects.create(idu=k)
                organizers.append(org)
                OrganizerRequest.objects.create(
                    idu=org, status="approved", request_date=timezone.now()
                )
                Notification.objects.create(
                    idu=org.idu,
                    message="Your organizer request has been approved. Welcome among the organizers!",
                    date=timezone.now(), is_read=False,
                )

        return players, organizers, set(usernames)

    def _create_base_catalog(self):
        strat = Category.objects.create(name="Strategy")
        family = Category.objects.create(name="Family games")
        party = Category.objects.create(name="Party")
        categories = [strat, family, party]

        catan = Game.objects.create(
            name="Catan", min_players=3, max_players=4, duration_min=90,
            duration_max=120, min_age=12, author="Klaus Teuber",
            description="Trade, build and settle",
            game_image=self._image_url("Catan"),
        )
        chess = Game.objects.create(
            name="Chess", min_players=2, max_players=2, duration_min=60,
            duration_max=60, min_age=12, author="Ancient",
            description="Strategy game",
            game_image=self._image_url("Chess"),
        )
        uno = Game.objects.create(
            name="UNO", min_players=2, max_players=6, duration_min=20,
            duration_max=30, min_age=6, author="Merle Robbins",
            description="Party card game",
            game_image=self._image_url("UNO"),
        )
        games = [catan, chess, uno]

        for game, category in [(catan, strat), (chess, strat), (uno, party), (catan, party)]:
            GameCategory.objects.create(idg=game, idc=category)

        used_game_names = {"Catan", "Chess", "UNO"}
        used_category_names = {"Strategy", "Family games", "Party"}
        return categories, games, used_game_names, used_category_names

    def _create_base_relations(self, players, organizers, games):
        for player in players:
            WishlistCollection.objects.create(
                idu=player.idu, idg=choice(games),
                status=choice(["wishlist", "collection"]),
            )

        friendship = Friendship.objects.create(idu1=players[0], idu2=players[1])
        self._notify_friendship(friendship)

        FriendRequest.objects.create(idu1=players[2], idu2=players[3], status="pending")

        for player in players:
            Review.objects.create(
                idu=player.idu, idg=choice(games), rating=randint(3, 5),
                comment="Excellent game!", date=timezone.now(),
            )

        organizer = organizers[0]
        catan = games[0]
        t1 = Tournament.objects.create(
            name="Weekend Cup", game=catan, organizer=organizer,
            capacity=16, occupancy=2, date=timezone.now(),
            status="active", location="Novi Sad", prize="500 EUR",
        )
        for player in players[:2]:
            Participation.objects.create(
                idt=t1, idu=player, phone_number="060123456",
                card_number="****1111",
            )

        p = Match.objects.create(
            name="Catan Final", game=catan, date=timezone.now(),
            winner=players[0],
        )
        for player in players:
            MatchParticipant.objects.create(idm=p, idu=player, status="confirmed")

    # -----------------------------------------------------------------
    # Helpers for notifications related to specific events
    # -----------------------------------------------------------------

    def _username(self, member_player_or_org):
        """Returns the username regardless of whether a Member, Player or Organizer was passed."""
        obj = member_player_or_org
        # Player.idu and Organizer.idu lead to Member, Member.idu leads to User
        if hasattr(obj, "idu") and not isinstance(obj, Member):
            obj = obj.idu
        return obj.idu.username

    def _notify_friendship(self, friendship):
        # both players get a notification that they are now friends
        Notification.objects.create(
            idu=friendship.idu1.idu,
            message=f"You are now friends with {self._username(friendship.idu2)}.",
            date=timezone.now(), is_read=False,
        )
        Notification.objects.create(
            idu=friendship.idu2.idu,
            message=f"You are now friends with {self._username(friendship.idu1)}.",
            date=timezone.now(), is_read=False,
        )

    def _notify_follow(self, follow):
        # the organizer gets a notification that a player followed them
        Notification.objects.create(
            idu=follow.ido.idu,
            message=f"{self._username(follow.idu)} is now following you.",
            date=timezone.now(), is_read=False,
        )

    def _notify_approved_organizer(self, request_obj):
        Notification.objects.create(
            idu=request_obj.idu.idu,
            message="Your organizer request has been approved. Welcome among the organizers!",
            date=timezone.now(), is_read=False,
        )

    def _notify_canceled_tournament(self, tournament, participant_players):
        for player in participant_players:
            Notification.objects.create(
                idu=player.idu,
                message=f"Tournament '{tournament.name}' you are registered for has been canceled.",
                date=timezone.now(), is_read=False,
            )

    # -----------------------------------------------------------------
    # Extension: users, games, categories
    # -----------------------------------------------------------------

    def _unique_username(self, used_usernames):
        for _ in range(200):
            candidate = f"{choice(FIRST_NAMES)}.{choice(LAST_NAMES)}".lower()
            if candidate not in used_usernames:
                used_usernames.add(candidate)
                return candidate
        # fallback if the combinations run out
        candidate = f"user{len(used_usernames) + 1}"
        used_usernames.add(candidate)
        return candidate

    def _create_extra_users(self, n_players, n_organizers, used_usernames):
        new_players, new_organizers = [], []

        for _ in range(n_players):
            username = self._unique_username(used_usernames)
            user = User.objects.create_user(
                username=username, password="test123", email=f"{username}@boardnet.rs"
            )
            k = Member.objects.create(idu=user)
            new_players.append(Player.objects.create(idu=k))

        for _ in range(n_organizers):
            username = self._unique_username(used_usernames)
            user = User.objects.create_user(
                username=username, password="test123", email=f"{username}@boardnet.rs"
            )
            k = Member.objects.create(idu=user)
            org = Organizer.objects.create(
                idu=k, description="I organize board game tournaments."
            )
            new_organizers.append(org)

        return new_players, new_organizers

    def _create_extra_games(self, n, used_names):
        new_games = []
        attempts = 0
        while len(new_games) < n and attempts < n * 20:
            attempts += 1
            name = f"{choice(ADJECTIVES)} {choice(NOUNS)}"
            if name in used_names:
                continue
            used_names.add(name)

            min_players = randint(1, 4)
            max_players = min_players + randint(0, 4)
            duration_min = randint(15, 90)
            duration_max = duration_min + randint(0, 60)

            new_games.append(Game.objects.create(
                name=name,
                min_players=min_players,
                max_players=max_players,
                duration_min=duration_min,
                duration_max=duration_max,
                min_age=choice([6, 8, 10, 12, 14, 16, 18]),
                author=f"{choice(FIRST_NAMES)} {choice(LAST_NAMES)}",
                description=choice(GAME_DESCRIPTIONS),
                game_image=self._image_url(name),
            ))

        if len(new_games) < n:
            self.stdout.write(self.style.WARNING(
                f"Created only {len(new_games)}/{n} games - name combinations exhausted."
            ))
        return new_games

    def _create_extra_categories(self, used_category_names):
        new_categories = []
        for name in EXTRA_CATEGORIES:
            if name in used_category_names:
                continue
            used_category_names.add(name)
            new_categories.append(Category.objects.create(name=name))
        return new_categories

    # -----------------------------------------------------------------
    # Generic helper for deduplicating pairs (unique_together tables)
    # -----------------------------------------------------------------

    def _existing_pairs(self, model, field_a, field_b):
        return set(model.objects.values_list(f"{field_a}_id", f"{field_b}_id"))

    # -----------------------------------------------------------------
    # Extension: secondary tables (~50 records each)
    # -----------------------------------------------------------------

    def _create_game_categories(self, games, categories, count):
        existing = self._existing_pairs(GameCategory, "idg", "idc")
        created = 0
        attempts = 0
        while created < count and attempts < count * 20:
            attempts += 1
            game, category = choice(games), choice(categories)
            if (game.pk, category.pk) in existing:
                continue
            existing.add((game.pk, category.pk))
            GameCategory.objects.create(idg=game, idc=category)
            created += 1

    def _create_wishlist(self, players, organizers, games, count):
        members = [i.idu for i in players] + [o.idu for o in organizers]
        existing = self._existing_pairs(WishlistCollection, "idu", "idg")
        created = 0
        attempts = 0
        while created < count and attempts < count * 20:
            attempts += 1
            k, game = choice(members), choice(games)
            if (k.pk, game.pk) in existing:
                continue
            existing.add((k.pk, game.pk))
            WishlistCollection.objects.create(
                idu=k, idg=game, status=choice(["wishlist", "collection"])
            )
            created += 1

    def _create_friendships(self, players, count):
        existing_ordered = self._existing_pairs(Friendship, "idu1", "idu2")
        existing_undirected = {frozenset(p) for p in existing_ordered}
        created = 0
        attempts = 0
        while created < count and attempts < count * 20:
            attempts += 1
            a, b = sample(players, 2)
            key = frozenset((a.pk, b.pk))
            if key in existing_undirected:
                continue
            existing_undirected.add(key)
            friendship = Friendship.objects.create(idu1=a, idu2=b)
            self._notify_friendship(friendship)
            created += 1

    def _create_friend_requests(self, players, count):
        existing_ordered = self._existing_pairs(FriendRequest, "idu1", "idu2")
        existing_undirected = {frozenset(p) for p in existing_ordered}
        created = 0
        attempts = 0
        while created < count and attempts < count * 20:
            attempts += 1
            a, b = sample(players, 2)
            key = frozenset((a.pk, b.pk))
            if key in existing_undirected:
                continue
            existing_undirected.add(key)
            FriendRequest.objects.create(
                idu1=a, idu2=b,
                status=choice(["pending", "accepted", "rejected"]),
            )
            created += 1

    def _create_reviews(self, players, organizers, games, count):
        members = [i.idu for i in players] + [o.idu for o in organizers]
        existing = self._existing_pairs(Review, "idu", "idg")
        created = 0
        attempts = 0
        while created < count and attempts < count * 20:
            attempts += 1
            k, game = choice(members), choice(games)
            if (k.pk, game.pk) in existing:
                continue
            existing.add((k.pk, game.pk))
            Review.objects.create(
                idu=k, idg=game, rating=randint(1, 5),
                comment=choice(REVIEW_TEXTS),
                date=timezone.now() - timedelta(days=randint(0, 180)),
            )
            created += 1

    def _create_organizer_requests(self, new_organizers):
        # OrganizerRequest.idu is a OneToOneField -> exactly 1 per organizer,
        # so it is not possible to add "50 new ones" independently of the number of organizers.
        # An organizer exists even before approval (they can register), but
        # until approved they cannot run tournaments - so we return a separate
        # list of approved ones, so that only they are used for Tournament.
        approved = []
        for org in new_organizers:
            status = choice(["pending", "approved", "approved", "rejected"])
            request_obj = OrganizerRequest.objects.create(
                idu=org,
                status=status,
                rejection_reason="Incomplete documentation." if status == "rejected" else None,
                request_date=timezone.now() - timedelta(days=randint(0, 120)),
            )
            if status == "approved":
                self._notify_approved_organizer(request_obj)
                approved.append(org)
        return approved

    def _create_tournaments(self, organizers, games, count):
        locations = ["Novi Sad", "Beograd", "Nis", "Subotica", "Kragujevac", "Pancevo"]
        new_tournaments = []
        for i in range(count):
            capacity = randint(8, 32)
            new_tournaments.append(Tournament.objects.create(
                name=f"Tournament #{i + 1} - {choice(NOUNS)}",
                game=choice(games),
                organizer=choice(organizers),
                capacity=capacity,
                occupancy=0,
                date=timezone.now() + timedelta(days=randint(-30, 60)),
                location=choice(locations),
                entry_fee=choice([0, 500, 1000, 1500, 2000]),
                prize=choice(["100 EUR", "300 EUR", "500 EUR", "Trophy", "No prize"]),
                status=choice(["active", "finished", "canceled"]),
                description="Automatically generated tournament for test data.",
            ))
        return new_tournaments

    def _create_participations_and_results(self, tournaments, players):
        for tournament in tournaments:
            participant_count = min(tournament.capacity, randint(2, 8))
            participants = sample(players, participant_count)

            for player in participants:
                Participation.objects.create(
                    idt=tournament, idu=player,
                    phone_number=f"06{randint(10000000, 99999999)}",
                    card_number=f"****{randint(1000, 9999)}",
                )

            # occupancy follows the actual number of registered players
            tournament.occupancy = participant_count
            tournament.save()

            # if the tournament is canceled, all registered players get a notification
            if tournament.status == "canceled":
                self._notify_canceled_tournament(tournament, participants)

            # results only for finished tournaments, unique positions 1..N
            if tournament.status == "finished":
                positions = list(range(1, participant_count + 1))
                for player, position in zip(participants, positions):
                    TournamentResult.objects.create(
                        idt=tournament, idu=player, position=position
                    )

    def _create_follows(self, players, organizers, count):
        existing = self._existing_pairs(Follow, "idu", "ido")
        created = 0
        attempts = 0
        while created < count and attempts < count * 20:
            attempts += 1
            player, org = choice(players), choice(organizers)
            if (player.pk, org.pk) in existing:
                continue
            existing.add((player.pk, org.pk))
            follow = Follow.objects.create(idu=player, ido=org)
            self._notify_follow(follow)
            created += 1

    def _create_matches(self, players, games, count):
        for i in range(count):
            player_count = randint(2, 6)
            participants = sample(players, player_count)
            winner = choice(participants)

            match = Match.objects.create(
                name=f"Match #{i + 1}",
                game=choice(games),
                date=timezone.now() - timedelta(days=randint(0, 90)),
                player_count=player_count,
                duration=randint(20, 150),
                winner=winner,
            )

            for player in participants:
                MatchParticipant.objects.create(
                    idm=match, idu=player,
                    status=choice(["confirmed", "unconfirmed"]),
                )