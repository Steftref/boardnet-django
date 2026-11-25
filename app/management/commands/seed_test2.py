from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from random import randint, choice

from app.models import *


class Command(BaseCommand):
    help = "Rich seed data for BoardNet"

    def handle(self, *args, **kwargs):

        print("Deleting old data...")

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

        print("Creating users...")

        usernames = ["marko", "ana", "nikola", "jelena", "petar"]

        players = []
        organizers = []

        for u in usernames:
            user = User.objects.create_user(username=u, password="test123")
            k = Member.objects.create(idu=user)

            if u in ["marko", "ana", "nikola", "jelena"]:
                player = Player.objects.create(idu=k)
                players.append(player)
            else:
                org = Organizer.objects.create(idu=k)
                organizers.append(org)

                OrganizerRequest.objects.create(
                    idu=org,
                    status="approved",
                    request_date=timezone.now()
                )

        organizer = organizers[0] if organizers else None

        print("Categories and games...")

        strat = Category.objects.create(name="Strategy")
        family = Category.objects.create(name="Family games")
        party = Category.objects.create(name="Party")

        catan = Game.objects.create(
            name="Catan",
            min_players=3,
            max_players=4,
            duration_min=90,
            duration_max=120,
            min_age=12,
            author="Klaus Teuber",
            description="Trade, build and settle"
        )

        chess = Game.objects.create(
            name="Chess",
            min_players=2,
            max_players=2,
            duration_min=60,
            duration_max=60,
            min_age=12,
            author="Ancient",
            description="Strategy game"
        )

        uno = Game.objects.create(
            name="UNO",
            min_players=2,
            max_players=6,
            duration_min=20,
            duration_max=30,
            min_age=6,
            author="Merle Robbins",
            description="Party card game"
        )

        for game, category in [(catan, strat), (chess, strat), (uno, party), (catan, party)]:
            GameCategory.objects.create(idg=game, idc=category)

        print("Wishlist + collection...")

        for player in players:
            WishlistCollection.objects.create(
                idu=player.idu,
                idg=choice([catan, chess, uno]),
                status=choice(["wishlist", "collection"])
            )

        print("Friendships + requests...")

        Friendship.objects.create(
            idu1=players[0],
            idu2=players[1]
        )

        FriendRequest.objects.create(
            idu1=players[2],
            idu2=players[3],
            status="pending"
        )

        print("Reviews...")

        for player in players:
            Review.objects.create(
                idu=player.idu,
                idg=choice([catan, chess, uno]),
                rating=randint(3, 5),
                comment="Excellent game!",
                date=timezone.now()
            )

        print("Tournaments...")

        t1 = Tournament.objects.create(
            name="Weekend Cup",
            game=catan,
            organizer=organizer,
            capacity=16,
            occupancy=2,
            date=timezone.now(),
            status="active",
            location="Novi Sad",
            prize="500 EUR"
        )

        for player in players[:2]:
            Participation.objects.create(
                idt=t1,
                idu=player,
                phone_number="060123456",
                card_number="****1111"
            )

        print("Matches + results...")

        p = Match.objects.create(
            name="Catan Final",
            game=catan,
            date=timezone.now(),
            winner=players[0]
        )

        for player in players:
            MatchParticipant.objects.create(
                idm=p,
                idu=player,
                status="confirmed"
            )

        print("Notifications...")

        for player in players:
            Notification.objects.create(
                idu=player.idu,
                message="A new match has been scheduled!",
                date=timezone.now()
            )

        print("✔ Rich seed finished")