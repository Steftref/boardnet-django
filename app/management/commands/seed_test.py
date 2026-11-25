from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from app.models import *


class Command(BaseCommand):
    help = "Seed test data for BoardNet"

    def handle(self, *args, **kwargs):

        print("Deleting old data...")

        TournamentResult.objects.all().delete()
        MatchParticipant.objects.all().delete()
        Match.objects.all().delete()
        Participation.objects.all().delete()
        Tournament.objects.all().delete()
        Review.objects.all().delete()
        Friendship.objects.all().delete()
        FriendRequest.objects.all().delete()
        Follow.objects.all().delete()
        Notification.objects.all().delete()
        WishlistCollection.objects.all().delete()
        GameCategory.objects.all().delete()
        Category.objects.all().delete()
        Game.objects.all().delete()
        Player.objects.all().delete()
        OrganizerRequest.objects.all().delete()
        Organizer.objects.all().delete()
        Member.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

        print("Creating users...")

        u1 = User.objects.create_user(username="marko", password="test123")
        u2 = User.objects.create_user(username="ana", password="test123")
        u3 = User.objects.create_user(username="nikola", password="test123")

        k1 = Member.objects.create(idu=u1)
        k2 = Member.objects.create(idu=u2)
        k3 = Member.objects.create(idu=u3)

        player1 = Player.objects.create(idu=k1)
        player2 = Player.objects.create(idu=k2)

        org = Organizer.objects.create(idu=k3)

        OrganizerRequest.objects.create(
            idu=org,
            status="approved",
            request_date=timezone.now()
        )

        print("Categories...")

        k = Category.objects.create(name="Strategy")
        k2 = Category.objects.create(name="Family games")

        print("Games...")

        g1 = Game.objects.create(
            name="Catan", min_players=3, max_players=4,
            duration_min=90, duration_max=120, min_age=12
        )
        g2 = Game.objects.create(
            name="Chess", min_players=2, max_players=2,
            duration_min=60, duration_max=60, min_age=6
        )

        GameCategory.objects.create(idg=g1, idc=k)
        GameCategory.objects.create(idg=g2, idc=k)

        print("Matches...")

        p1 = Match.objects.create(
            name="Catan match 1",
            game=g1,
            date=timezone.now(),
            player_count=2,
            winner=player1
        )

        MatchParticipant.objects.create(idm=p1, idu=player1, status="confirmed")
        MatchParticipant.objects.create(idm=p1, idu=player2, status="confirmed")

        print("Friendships...")

        Friendship.objects.create(idu1=player1, idu2=player2)

        print("Tournaments...")

        t1 = Tournament.objects.create(
            name="Weekend Cup",
            game=g1,
            organizer=org,
            capacity=16,
            occupancy=1,
            date=timezone.now() + timedelta(days=10),
            status="active"
        )

        Participation.objects.create(
            idt=t1,
            idu=player1,
            phone_number="123",
            card_number="1111"
        )

        print("✔ Seed finished")