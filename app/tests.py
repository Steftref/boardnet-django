from app.models import WishlistCollection
from app.models import Friendship, FriendRequest

from app.models import (OrganizerRequest, Match, MatchParticipant, Review)
from app.models import (TournamentResult)

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from app.models import (Member, Player, Organizer, Game, Tournament, Participation, Notification, Follow, Category, GameCategory)

import json
from django.db.models import Q


class ToolsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username='testplayer',
            password='Test12345'
        )
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

    def test_tools_logged_in_user(self):
        """
        Valid class: the user is logged in.
        Expected: the page works normally and shows all tools.
        """

        # the user logs in
        self.client.login(username='testplayer', password='Test12345')

        # opens /tools/
        response = self.client.get(reverse('tools'))

        # was the page returned successfully (HTTP 200 = OK)
        self.assertEqual(response.status_code, 200)

        # does the exact text from the template appear
        self.assertContains(response, 'Tools')
        self.assertContains(response, 'Dice')
        self.assertContains(response, 'Random number')
        self.assertContains(response, 'Picker')
        self.assertContains(response, 'Timer/Stopwatch')

    def test_tools_logged_out_user(self):
        """
        Case 2 (invalid class): the user is not logged in.
        Expected: redirect to the login page.
        """

        # no login, just opening /tools/
        response = self.client.get(reverse('tools'))

        # 302 (redirect)
        self.assertEqual(response.status_code, 302)



class MyCollectionTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username='testplayer',
            password='Test12345'
        )
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

    def test_collection_with_items(self):
        """Valid class: the user has a game in the collection."""

        WishlistCollection.objects.create(
            idu=self.member,
            idg=self.game,
            status='collection'
        )

        self.client.login(username='testplayer', password='Test12345')
        response = self.client.get(reverse('myCollection'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catan')

    def test_collection_empty(self):
        """
        Boundary case: the user has no games in the collection.
        Expected message "Your collection is empty."
        """

        self.client.login(username='testplayer', password='Test12345')
        response = self.client.get(reverse('myCollection'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your collection is empty.')

    def test_collection_without_login(self):
        """Invalid class: the user is not logged in."""

        response = self.client.get(reverse('myCollection'))
        self.assertEqual(response.status_code, 302)

class MyWishlistTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username='testplayer',
            password='Test12345'
        )
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.item = WishlistCollection.objects.create(
            idu=self.member,
            idg=self.game,
            status='wishlist'
        )

        self.client.login(username='testplayer', password='Test12345')

    def test_list_with_items(self):
        """Valid class: the user has a game in the wishlist."""

        response = self.client.get(reverse('myWishlist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catan')

    def test_list_empty(self):
        """
        Boundary case: the user has no games in the wishlist.
        Expected message "Your wishlist is empty."
        """

        self.item.delete()  # deletes the only item

        response = self.client.get(reverse('myWishlist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is empty')

    def test_list_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('myWishlist'))
        self.assertEqual(response.status_code, 302)

    def test_list_post_add_to_collection(self):
        """
        Valid class: POST action 'add_to_collection'.
        Expected: the item changes its status from 'wishlist' to 'collection'.
        """

        response = self.client.post(reverse('myWishlist'), {
            'action': 'add_to_collection',
            'game_id': self.game.idg,
        })

        # redirect to myWishlist
        self.assertEqual(response.status_code, 302)

        # checks the new status
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'collection')

    def test_list_post_remove(self):
        """
        Valid class: POST action 'remove'.
        Expected: the item is deleted from the database.
        """

        response = self.client.post(reverse('myWishlist'), {
            'action': 'remove',
            'game_id': self.game.idg,
        })

        self.assertEqual(response.status_code, 302)

        # checks that the item is no longer in the database
        self.assertFalse(
            WishlistCollection.objects.filter(pk=self.item.pk).exists()
        )

class MyMatchesTest(TestCase):

    def setUp(self):
        self.client = Client()

        # logged-in user
        self.user = User.objects.create_user(
            username='marko', password='Test12345'
        )

        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.friend_user = User.objects.create_user(
            username='ana', password='Test12345'
        )
        self.friend_member = Member.objects.create(idu=self.friend_user)
        self.friend_player = Player.objects.create(idu=self.friend_member)

        self.nonfriend_user = User.objects.create_user(
            username='nikola', password='Test12345'
        )
        self.nonfriend_member = Member.objects.create(idu=self.nonfriend_user)
        self.nonfriend_player = Player.objects.create(idu=self.nonfriend_member)

        a, b = sorted([self.player.pk, self.friend_player.pk])
        Friendship.objects.create(idu1_id=a, idu2_id=b)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='marko', password='Test12345')

    def _create_match(self, confirmed_by_marko=True):
        match = Match.objects.create(
            name='Catan evening',
            game=self.game,
            date=timezone.now(),
            player_count=2,
            winner=self.player,
        )
        MatchParticipant.objects.create(
            idm=match, idu=self.player,
            status='confirmed' if confirmed_by_marko else 'unconfirmed'
        )
        MatchParticipant.objects.create(
            idm=match, idu=self.friend_player, status='unconfirmed'
        )
        return match

    def test_display_matches(self):
        """Valid class: the user has played matches."""
        self._create_match()

        response = self.client.get(reverse('myMatches'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catan evening')

    def test_display_without_matches(self):
        """Boundary case: the user has no matches."""
        response = self.client.get(reverse('myMatches'))
        self.assertEqual(response.status_code, 200)

    def test_display_without_login(self):
        """Invalid class: the user is not logged in."""
        self.client.logout()
        response = self.client.get(reverse('myMatches'))
        self.assertEqual(response.status_code, 302)

    def test_add_match_correctly(self):
        """Valid class: correct data, the participant is a friend."""

        payload = {
            'name': 'New match',
            'date': '2026-07-10',
            'game_id': self.game.idg,
            'participants': ['ana'],
            'winner': 'marko',
        }

        response = self.client.post(
            reverse('addMatch'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])

        # is the match in the database
        self.assertTrue(Match.objects.filter(name='New match').exists())

    def test_add_match_missing_name(self):
        """Invalid class: the required field 'name' is missing."""

        payload = {
            'name': '',
            'date': '2026-07-10',
            'game_id': self.game.idg,
            'participants': ['ana'],
            'winner': 'marko',
        }

        response = self.client.post(
            reverse('addMatch'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])

    def test_add_match_winner_not_participant(self):
        """Invalid class: the winner is not among the participants."""

        payload = {
            'name': 'New match',
            'date': '2026-07-10',
            'game_id': self.game.idg,
            'participants': ['ana'],
            'winner': 'nikola',
        }

        response = self.client.post(
            reverse('addMatch'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])


    def test_add_match_participant_not_friend(self):
        """
        Invalid class: adding a participant who is not a friend of the logged-in user.
        Expected: the add action is rejected
        """

        payload = {
            'name': 'Test match',
            'date': '2026-07-10',
            'game_id': self.game.idg,
            'participants': ['nikola'],
            'winner': 'marko',
        }

        response = self.client.post(
            reverse('addMatch'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        data = response.json()
        self.assertFalse(
            data['ok'],
            msg="Match created although the participant is not a friend of the logged-in user"
        )


    def test_confirm_match(self):
        """Valid class: the user confirms a match they take part in."""

        match = self._create_match(confirmed_by_marko=False)

        response = self.client.post(reverse('confirmMatch'), {
            'match_id': match.idm,
        })

        self.assertEqual(response.status_code, 302)

        participant = MatchParticipant.objects.get(idm=match, idu=self.player)
        self.assertEqual(participant.status, 'confirmed')


class FriendsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.friend_user = User.objects.create_user(username='ana', password='Test12345')
        self.friend_member = Member.objects.create(idu=self.friend_user)
        self.friend_player = Player.objects.create(idu=self.friend_member)

        self.nonfriend_user = User.objects.create_user(username='nikola', password='Test12345')
        self.nonfriend_member = Member.objects.create(idu=self.nonfriend_user)
        self.nonfriend_player = Player.objects.create(idu=self.nonfriend_member)

        a, b = sorted([self.player.pk, self.friend_player.pk])
        self.friendship = Friendship.objects.create(idu1_id=a, idu2_id=b)

        self.client.login(username='marko', password='Test12345')

    def test_display_own_friends(self):
        """Valid class: the user has a friend and views their own friend list."""

        response = self.client.get(
            reverse('friends', kwargs={'user_id': self.player.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ana')

    def test_display_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(
            reverse('friends', kwargs={'user_id': self.player.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_access_to_others_friend_list(self):
        """
        Invalid class: the logged-in user tries to access the friend list of another user
        Expected: the system rejects the action
        """

        self.client.logout()
        self.client.login(username='nikola', password='Test12345')

        # nikola tries to see marko's friend list
        response = self.client.get(
            reverse('friends', kwargs={'user_id': self.player.pk})
        )

        # we expect that they do NOT see it
        self.assertEqual(response.status_code, 403)

    def test_remove_friend(self):
        """Valid class: removing an existing friendship."""

        response = self.client.post(
            reverse('removeFriend', kwargs={'friend_id': self.friend_player.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Friendship.objects.filter(pk=self.friendship.pk).exists()
        )


class FriendRequestsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.sender_user = User.objects.create_user(username='ana', password='Test12345')
        self.sender_member = Member.objects.create(idu=self.sender_user)
        self.sender_player = Player.objects.create(idu=self.sender_member)

        self.client.login(username='marko', password='Test12345')

    def test_display_with_requests(self):
        """Valid class: there is a pending request sent to the logged-in user."""

        FriendRequest.objects.create(
            idu1=self.sender_player,
            idu2=self.player,
            status='pending'
        )

        response = self.client.get(reverse('friend_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ana')

    def test_display_without_requests(self):
        """Boundary case: there are no pending requests."""

        response = self.client.get(reverse('friend_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have no friend requests.')

    def test_display_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('friend_requests'))
        self.assertEqual(response.status_code, 302)

    def test_accept_request(self):
        """Valid class: accepting a friend request."""

        FriendRequest.objects.create(
            idu1=self.sender_player,
            idu2=self.player,
            status='pending'
        )

        response = self.client.post(reverse('friend_requests'), {
            'sender_id': self.sender_player.pk,
            'action': 'accept',
        })

        self.assertEqual(response.status_code, 302)

        a, b = sorted([self.player.pk, self.sender_player.pk])
        # checks whether the friendship was created
        self.assertTrue(
            Friendship.objects.filter(idu1_id=a, idu2_id=b).exists()
        )

    def test_reject_request(self):
        """Valid class: rejecting a friend request."""

        request_obj = FriendRequest.objects.create(
            idu1=self.sender_player,
            idu2=self.player,
            status='pending'
        )

        response = self.client.post(reverse('friend_requests'), {
            'sender_id': self.sender_player.pk,
            'action': 'reject',
        })

        self.assertEqual(response.status_code, 302)

        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, 'rejected')

        a, b = sorted([self.player.pk, self.sender_player.pk])
        self.assertFalse(
            Friendship.objects.filter(idu1_id=a, idu2_id=b).exists()
        )

class NotificationsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.other_user = User.objects.create_user(username='ana', password='Test12345')
        self.other_member = Member.objects.create(idu=self.other_user)
        self.other_player = Player.objects.create(idu=self.other_member)

        self.client.login(username='marko', password='Test12345')

    def test_notifications_with_unread(self):
        """Valid class: the user has an unread notification."""

        Notification.objects.create(
            idu=self.member,
            message='You are now friends with ana.',
            date=timezone.now(),
            is_read=False
        )

        response = self.client.get(reverse('notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You are now friends with ana.')

    def test_notifications_without_unread(self):
        """Boundary case: there are no unread notifications."""

        response = self.client.get(reverse('notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have no notifications.')

    def test_notifications_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 302)

    def test_mark_read_own(self):
        """Valid class: the user marks a notification as read."""

        notification = Notification.objects.create(
            idu=self.member,
            message='Test message',
            date=timezone.now(),
            is_read=False
        )

        response = self.client.post(
            reverse('notification_read', kwargs={'idn': notification.idn})
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_read_without_login(self):
        """
        Invalid class: a logged-out user tries to mark a notification.
        """

        notification = Notification.objects.create(
            idu=self.member,
            message='Test message',
            date=timezone.now(),
            is_read=False
        )

        self.client.logout()

        response = self.client.post(
            reverse('notification_read', kwargs={'idn': notification.idn})
        )

        # 404 because there is no @login_req but it filters by idu_id and django raises DoesNotExist
        self.assertEqual(response.status_code, 404)

class OrganizerNotificationsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='org', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.organizer = Organizer.objects.create(idu=self.member)

        self.client.login(username='org', password='Test12345')

    def test_display_with_messages(self):
        """Valid class: the organizer has an unread notification."""

        Notification.objects.create(
            idu=self.member,
            message='The tournament was canceled by an admin.',
            date=timezone.now(),
            is_read=False
        )

        response = self.client.get(reverse('organizerNotifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The tournament was canceled by an admin.')

    def test_display_without_messages(self):
        """Boundary case: the organizer has no unread notifications."""

        response = self.client.get(reverse('organizerNotifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have no notifications.')

    def test_display_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('organizerNotifications'))
        self.assertEqual(response.status_code, 302)

class PlayerProfileTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        self.client.login(username='marko', password='Test12345')

    def test_player_profile_with_data(self):
        """Valid class: the player has a played match and a tournament participation."""

        org_user = User.objects.create_user(username='org', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        organizer = Organizer.objects.create(idu=org_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        tournament = Tournament.objects.create(
            name='Test tournament',
            game=self.game,
            organizer=organizer,
            capacity=10,
            occupancy=1,
            date=timezone.now() + timezone.timedelta(days=1),
            status='active',
        )
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        match = Match.objects.create(
            name='Catan evening', game=self.game, date=timezone.now(),
            player_count=1, winner=self.player
        )
        MatchParticipant.objects.create(idm=match, idu=self.player, status='confirmed')

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'marko')
        self.assertContains(response, 'Player')
        self.assertContains(response, 'Catan evening')
        self.assertContains(response, 'Test tournament')

    def test_player_profile_without_data(self):
        """
        Boundary case: new player, all lists empty
        """

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'marko')
        self.assertContains(response, 'Player')

    def test_profile_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

class OrganizerProfileTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='org', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.organizer = Organizer.objects.create(idu=self.member)

        OrganizerRequest.objects.create(
            idu=self.organizer,
            status='approved',
            request_date=timezone.now()
        )

        self.client.login(username='org', password='Test12345')

    def test_organizer_redirected_from_profile(self):
        """
        Valid class: an organizer opens /profile/
        Expected: redirect to homeOrganizer.
        """

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('homeOrganizer'))

class MyTournamentsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        org_user = User.objects.create_user(username='org', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='marko', password='Test12345')

    def _create_tournament(self, days_ahead, status='active', occupancy=1):
        return Tournament.objects.create(
            name='Test tournament',
            game=self.game,
            organizer=self.organizer,
            capacity=10,
            occupancy=occupancy,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status=status,
        )

    def test_upcoming_tournament(self):
        """Valid class: the user has an upcoming tournament."""

        tournament = self._create_tournament(days_ahead=10)
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.get(reverse('myTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test tournament')
        self.assertContains(response, 'REGISTERED')

    def test_without_upcoming_tournaments(self):
        """Boundary case: no upcoming tournaments."""

        response = self.client.get(reverse('myTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No upcoming tournaments.')

    def test_finished_tournament_with_placement(self):
        """Valid class: finished tournament where the player has a recorded placement."""

        tournament = self._create_tournament(days_ahead=-10, status='finished')
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )
        TournamentResult.objects.create(idt=tournament, idu=self.player, position=1)

        response = self.client.get(reverse('myTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Placement: 1. place')

    def test_finished_tournament_without_placement(self):
        """Valid class: finished tournament where the player has no recorded placement (participation only)."""

        tournament = self._create_tournament(days_ahead=-10, status='finished')
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.get(reverse('myTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Participated')

    def test_without_finished_tournaments(self):
        """Boundary case: no finished tournaments."""

        response = self.client.get(reverse('myTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No finished tournaments.')

    def test_display_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('myTournaments'))
        self.assertEqual(response.status_code, 302)


    def test_unregister_allowed(self):
        """Valid class: unregistering from a tournament that is more than 5 days ahead."""

        tournament = self._create_tournament(days_ahead=10, occupancy=5)
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.post(reverse('myTournaments'), {'idt': tournament.idt})

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Participation.objects.filter(idt=tournament, idu=self.player).exists()
        )
        tournament.refresh_from_db()
        self.assertEqual(tournament.occupancy, 4)

    def test_unregister_less_than_5_days(self):
        """Invalid class: unregistering from a tournament that starts in less than 5 days."""

        tournament = self._create_tournament(days_ahead=3)
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.post(reverse('myTournaments'), {'idt': tournament.idt})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'You cannot unregister because there are less than 5 days until the start of the tournament.'
        )

        # the participation must still exist
        self.assertTrue(
            Participation.objects.filter(idt=tournament, idu=self.player).exists()
        )

    def test_unregister_boundary_value_exactly_5_days(self):
        """
        Boundary case: the tournament is just slightly more than 5 days ahead.
        We expect that unregistering is possible 5 days and a few minutes ahead.
        """

        tournament = self._create_tournament(days_ahead=5)
        tournament.date = timezone.now() + timezone.timedelta(days=5, minutes=5)
        tournament.save()

        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.post(reverse('myTournaments'), {'idt': tournament.idt})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Participation.objects.filter(idt=tournament, idu=self.player).exists()
        )

class AdminGamesTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin', password='Test12345', is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='marko', password='Test12345'
        )

    def test_get_as_admin(self):
        """Valid class: GET as a staff user."""

        Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='admin', password='Test12345')
        response = self.client.get(reverse('adminGames'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catan')

    def test_get_without_login(self):
        """Invalid class: the user is not logged in."""

        response = self.client.get(reverse('adminGames'))
        self.assertEqual(response.status_code, 302)

    def test_get_as_regular_member(self):
        """Invalid class: logged-in user who is not an admin."""

        self.client.login(username='marko', password='Test12345')
        response = self.client.get(reverse('adminGames'))
        self.assertEqual(response.status_code, 302)

    def test_post_correct_creation(self):
        """Valid class: all data correct, new game."""

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': 'Ticket to Ride',
            'min_players': '2',
            'max_players': '5',
            'duration_min': '30',
            'duration_max': '60',
            'min_age': '8',
            'author': 'Alan R. Moon',
            'description': 'A game about trains.',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Game.objects.filter(name='Ticket to Ride').exists())

    def test_post_without_name(self):
        """Invalid class: the required field 'name' is missing."""

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': '',
            'min_players': '2',
            'max_players': '5',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Game name is required.')
        self.assertFalse(Game.objects.exists())

    def test_post_min_players_zero(self):
        """Invalid class: min_players = 0 (on the boundary)."""

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': 'Test game',
            'min_players': '0',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Minimum number of players must be a positive number.')
        self.assertFalse(Game.objects.filter(name='Test game').exists())

    def test_post_min_players_one_boundary(self):
        """
        Boundary case: min_players = 1 (on the boundary).
        Expected: passes without errors.
        """

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': 'Test game',
            'min_players': '1',
            'max_players': '4',
            'duration_min': '20',
            'duration_max': '30',
            'min_age': '8',
        })

        self.assertEqual(response.status_code, 302)
        game = Game.objects.get(name='Test game')#AAAA
        self.assertEqual(game.min_players, 1)

    def test_post_missing_required_numeric_field(self):
        """
        Invalid class: all numeric fields are required.
        Expected: returns an error if one of them is not filled in.
        """

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': 'Test game',
            'min_players': '2',
            'max_players': '4',
            'duration_min': '20',
            'duration_max': '40',
            # 'min_age'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Minimum age is a required field.')
        self.assertFalse(Game.objects.filter(name='Test game').exists())

    def test_post_max_less_than_min(self):
        """Invalid class: maximum number of players less than the minimum."""

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': 'Test game',
            'min_players': '5',
            'max_players': '2',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'Maximum number of players cannot be less than the minimum.'
        )
        self.assertFalse(Game.objects.filter(name='Test game').exists())

    def test_post_negative_min_players(self):
        """
        Invalid class: game with a negative number of players
        """

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'name': 'Test game',
            'min_players': '-5',
            'max_players': '4',
            'duration_min': '20',
            'duration_max': '40',
            'min_age': '8',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Minimum number of players must be a positive number.')
        self.assertFalse(Game.objects.filter(name='Test game').exists())

    def test_post_update_existing_game(self):
        """Valid class: sending game_id updates the existing game (does not duplicate it)."""

        game = Game.objects.create(name='Catan', duration_min=30, author='Old author', min_players=3, max_players=4, duration_max=60, min_age=10)

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(reverse('adminGames'), {
            'game_id': game.idg,
            'name': 'Catan',
            'author': 'Klaus Teuber',
            'min_players': '3',
            'max_players': '4',
            'duration_min': '45',
            'duration_max': '90',
            'min_age': '10',
        })

        self.assertEqual(response.status_code, 302)

        # checks that there is still only one catan
        self.assertEqual(Game.objects.filter(name='Catan').count(), 1)

        game = Game.objects.get(name='Catan')
        self.assertEqual(game.author, 'Klaus Teuber')


class AdminOrganizersTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.admin_user = User.objects.create_user(
            username='admin', password='Test12345', is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='marko', password='Test12345'
        )

        self.org_user = User.objects.create_user(username='org', password='Test12345')
        self.org_member = Member.objects.create(idu=self.org_user)
        self.organizer = Organizer.objects.create(idu=self.org_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

    def test_get_as_admin(self):
        """Valid class: GET as a staff user."""

        self.client.login(username='admin', password='Test12345')
        response = self.client.get(reverse('adminOrganizers'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'org')

    def test_get_without_login(self):
        """Invalid class: the user is not logged in."""

        response = self.client.get(reverse('adminOrganizers'))
        self.assertEqual(response.status_code, 302)

    def test_get_as_regular_member(self):
        """Invalid class: logged-in user who is not an admin."""

        self.client.login(username='marko', password='Test12345')
        response = self.client.get(reverse('adminOrganizers'))
        self.assertEqual(response.status_code, 302)


    def test_deactivation_with_active_tournament(self):
        """
        Valid class: deactivating an organizer who has an active tournament with a registered player.
        Expected:
        - the organizer account becomes inactive
        - the tournament becomes 'canceled'
        - the registered player gets a notification
        """

        player_user = User.objects.create_user(username='petar', password='Test12345')
        player_member = Member.objects.create(idu=player_user)
        player_player = Player.objects.create(idu=player_member)

        tournament = Tournament.objects.create(
            name='Org tournament',
            game=self.game,
            organizer=self.organizer,
            capacity=10,
            occupancy=1,
            date=timezone.now() + timezone.timedelta(days=5),
            status='active',
        )
        Participation.objects.create(
            idt=tournament, idu=player_player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(
            reverse('deactivateOrganizer', kwargs={'idu': self.organizer.pk})
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['canceled_tournaments'], 1)

        self.org_user.refresh_from_db()
        self.assertFalse(self.org_user.is_active)

        tournament.refresh_from_db()
        self.assertEqual(tournament.status, 'canceled')

        self.assertTrue(
            Notification.objects.filter(
                idu=player_member, message__icontains='canceled'
            ).exists()
        )

    def test_deactivation_without_active_tournaments(self):
        """Boundary case: the organizer has no active tournaments."""

        self.client.login(username='admin', password='Test12345')

        response = self.client.post(
            reverse('deactivateOrganizer', kwargs={'idu': self.organizer.pk})
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['canceled_tournaments'], 0)

        self.org_user.refresh_from_db()
        self.assertFalse(self.org_user.is_active)

    def test_deactivation_nonexistent_organizer(self):
        """Invalid class: idu does not match any organizer."""

        self.client.login(username='admin', password='Test12345')

        nonexistent_id = 999999

        response = self.client.post(
            reverse('deactivateOrganizer', kwargs={'idu': nonexistent_id})
        )

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['ok'])

    def test_deactivation_get_instead_of_post(self):
        """Invalid class: GET request to an endpoint that requires POST."""

        self.client.login(username='admin', password='Test12345')

        response = self.client.get(
            reverse('deactivateOrganizer', kwargs={'idu': self.organizer.pk})
        )

        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertFalse(data['ok'])

    def test_deactivation_without_login(self):
        """Invalid class: a logged-out user attempts the deactivation."""

        response = self.client.post(
            reverse('deactivateOrganizer', kwargs={'idu': self.organizer.pk})
        )

        self.assertEqual(response.status_code, 302)

    def test_deactivation_as_regular_member(self):
        """Invalid class: a logged-in user who is not an admin attempts the deactivation."""

        self.client.login(username='marko', password='Test12345')

        response = self.client.post(
            reverse('deactivateOrganizer', kwargs={'idu': self.organizer.pk})
        )

        self.assertEqual(response.status_code, 302)


class HomeTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username='testplayer',
            password='Test12345'
        )
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        # friend
        self.friend_user = User.objects.create_user(username='testfriend', password='Test12345')
        self.friend_member = Member.objects.create(idu=self.friend_user)
        self.friend_player = Player.objects.create(idu=self.friend_member)

        # player who is NOT a friend
        self.nonfriend_user = User.objects.create_user(username='testnotfriend', password='Test12345')
        self.nonfriend_member = Member.objects.create(idu=self.nonfriend_user)
        self.nonfriend_player = Player.objects.create(idu=self.nonfriend_member)

        a, b = sorted([self.player.pk, self.friend_player.pk])
        Friendship.objects.create(idu1_id=a, idu2_id=b)

        # organizer
        org_user = User.objects.create_user(username='org', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)

        # organizer the logged-in user does not follow
        org2_user = User.objects.create_user(username='org2', password='Test12345')
        org2_member = Member.objects.create(idu=org2_user)
        self.unfollowed_organizer = Organizer.objects.create(idu=org2_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='testplayer', password='Test12345')

    def _create_match(self, winner):
        return Match.objects.create(
            name='Test match',
            game=self.game,
            date=timezone.now(),
            player_count=2,
            winner=winner,
        )

    def _create_tournament(self, organizer, days_ahead=10, name='Test tournament'):
        return Tournament.objects.create(
            name=name,
            game=self.game,
            organizer=organizer,
            capacity=10,
            occupancy=1,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status='active',
        )

    def test_leaderboard_with_wins(self):
        """Valid class: the logged-in user and a friend have wins, the leaderboard shows them."""

        self._create_match(winner=self.player)
        self._create_match(winner=self.friend_player)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testplayer')
        self.assertContains(response, 'testfriend')

    def test_leaderboard_sorting(self):
        """Valid class: the player with more wins is first on the leaderboard."""

        # testfriend has 2 wins, testplayer 1
        self._create_match(winner=self.friend_player)
        self._create_match(winner=self.friend_player)
        self._create_match(winner=self.player)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)

        leaderboard = response.context['leaderboard']
        self.assertEqual(leaderboard[0][0].pk, self.friend_player.pk)
        self.assertEqual(leaderboard[0][1], 2)
        self.assertEqual(leaderboard[1][0].pk, self.player.pk)
        self.assertEqual(leaderboard[1][1], 1)

    def test_leaderboard_without_matches(self):
        """Boundary case: no played matches, everyone on the leaderboard has 0 wins."""

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)

        leaderboard = response.context['leaderboard']
        # logged-in user + 1 friend = 2 rows
        self.assertEqual(len(leaderboard), 2)
        for player, wins in leaderboard:
            self.assertEqual(wins, 0)

    def test_leaderboard_without_friends(self):
        """Boundary case: the user has no friends, only they are on the leaderboard."""

        Friendship.objects.all().delete()

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)

        leaderboard = response.context['leaderboard']
        self.assertEqual(len(leaderboard), 1)
        self.assertEqual(leaderboard[0][0].pk, self.player.pk)

    def test_leaderboard_does_not_show_non_friends(self):
        """Invalid class: wins of a player who is not a friend do not count for the leaderboard."""

        self._create_match(winner=self.nonfriend_player)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)

        leaderboard = response.context['leaderboard']
        players_on_board = [player.pk for player, _ in leaderboard]
        self.assertNotIn(self.nonfriend_player.pk, players_on_board)

    def test_followed_organizer_tournaments(self):
        """Valid class: the user follows the organizer, the upcoming tournament is shown."""

        Follow.objects.create(idu=self.player, ido=self.organizer)
        self._create_tournament(self.organizer, name='Followed tournament')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Followed tournament')

    def test_unfollowed_organizer_tournaments(self):
        """Invalid class: a tournament of an organizer the user does not follow is not shown."""

        Follow.objects.create(idu=self.player, ido=self.organizer)
        self._create_tournament(self.unfollowed_organizer, name='Foreign tournament')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Foreign tournament')

    def test_tournaments_past_date(self):
        """Boundary case: a tournament with a past date is not shown (date__gt=now)."""

        Follow.objects.create(idu=self.player, ido=self.organizer)
        self._create_tournament(self.organizer, days_ahead=-1, name='Past tournament')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Past tournament')

    def test_tournaments_limit_four(self):
        """Boundary case: at most the 4 nearest tournaments are shown."""

        Follow.objects.create(idu=self.player, ido=self.organizer)

        for i in range(5):
            self._create_tournament(
                self.organizer,
                days_ahead=i + 1,
                name=f'Tournament {i + 1}'
            )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)

        tournaments = response.context['tournaments']
        self.assertEqual(len(tournaments), 4)

        self.assertNotContains(response, 'Tournament 5')

    def test_without_followed_organizers(self):
        """Boundary case: the user does not follow any organizer, the tournament list is empty."""

        self._create_tournament(self.organizer)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tournaments']), 0)

    def test_home_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)



class HomeAdminTest(TestCase):
    def setUp(self):
        self.client = Client()

        # admin
        self.admin_user = User.objects.create_user(
            username='admin', password='Test12345', is_staff=True
        )

        # regular user (player)
        self.regular_user = User.objects.create_user(
            username='testplayer', password='Test12345'
        )
        self.regular_member = Member.objects.create(idu=self.regular_user)
        self.player = Player.objects.create(idu=self.regular_member)

        # organizer (for tournaments)
        org_user = User.objects.create_user(username='org', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)

        # organizer candidate (for requests)
        self.candidate_user = User.objects.create_user(
            username='candidate', password='Test12345', email='candidate@test.com'
        )
        self.candidate_member = Member.objects.create(idu=self.candidate_user)
        self.candidate_organizer = Organizer.objects.create(idu=self.candidate_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='admin', password='Test12345')

    def _create_request(self, status='pending'):
        return OrganizerRequest.objects.create(
            idu=self.candidate_organizer,
            status=status,
            request_date=timezone.now(),
        )

    def _create_tournament(self, status='active', name='Test tournament', days_ahead=10):
        return Tournament.objects.create(
            name=name,
            game=self.game,
            organizer=self.organizer,
            capacity=10,
            occupancy=1,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status=status,
        )

    def test_access_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('homeAdmin'))
        self.assertEqual(response.status_code, 302)

    def test_access_as_regular_member(self):
        """Invalid class: logged-in user who is not an admin, redirect to login."""

        self.client.logout()
        self.client.login(username='marko', password='Test12345')

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('loginRegister'), response.url)

    def test_access_as_admin(self):
        """Valid class: an admin accesses the page."""

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin panel')


    def test_display_pending_request(self):
        """Valid class: there is a pending request, shown with the candidate's data."""

        self._create_request()

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'candidate')
        self.assertContains(response, 'candidate@test.com')

    def test_processed_requests_not_shown(self):
        """Invalid class: approved/rejected requests are not included in the pending list."""

        self._create_request(status='approved')

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['organizer_requests']), 0)
        self.assertContains(response, 'No pending requests')

    def test_without_requests(self):
        """Boundary case: there are no requests in the database."""

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No pending requests')
        self.assertEqual(response.context['request_count'], 0)


    def test_display_tournaments(self):
        """Valid class: tournaments are shown with the organizer and status."""

        self._create_tournament(name='Summer tournament')

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Summer tournament')
        self.assertContains(response, 'org')
        self.assertContains(response, 'ACTIVE')

    def test_display_all_tournament_statuses(self):
        """Valid class: the admin sees all tournaments, not only active ones."""

        self._create_tournament(status='active', name='Active tournament')
        self._create_tournament(status='finished', name='Finished tournament', days_ahead=-10)
        self._create_tournament(status='canceled', name='Canceled tournament')

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tournaments']), 3)
        self.assertContains(response, 'Active tournament')
        self.assertContains(response, 'Finished tournament')
        self.assertContains(response, 'Canceled tournament')

    def test_tournaments_sorted_by_date(self):
        """Valid class: tournaments are sorted by date ascending."""

        self._create_tournament(name='Later', days_ahead=20)
        self._create_tournament(name='Earlier', days_ahead=5)

        response = self.client.get(reverse('homeAdmin'))

        tournaments = list(response.context['tournaments'])
        self.assertEqual(tournaments[0].name, 'Earlier')
        self.assertEqual(tournaments[1].name, 'Later')

    def test_without_tournaments(self):
        """Boundary case: there are no tournaments in the database."""

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No tournaments to display')

    def test_statuses_for_filter(self):
        """Valid class: the status list for the filter contains distinct values from the database."""

        self._create_tournament(status='active')
        self._create_tournament(status='active', name='Second active')
        self._create_tournament(status='finished', name='Finished', days_ahead=-5)

        response = self.client.get(reverse('homeAdmin'))

        statuses = list(response.context['statuses'])
        self.assertEqual(len(statuses), 2)  # distinct: active, finished
        self.assertIn('active', statuses)
        self.assertIn('finished', statuses)

    def test_statistics_counters(self):
        """Valid class: the counters in the stat bar match the database state."""

        self._create_request()
        self._create_tournament(status='active')
        self._create_tournament(status='finished', name='Finished', days_ahead=-5)

        response = self.client.get(reverse('homeAdmin'))

        self.assertEqual(response.context['request_count'], 1)
        # candidate + marko + org = 3 (the admin has no Member record)
        self.assertEqual(response.context['user_count'], 3)
        # only the active one is counted
        self.assertEqual(response.context['active_tournament_count'], 1)



class HomeOrganizerTest(TestCase):

    def setUp(self):
        self.client = Client()

        # organizer (approved)
        self.user = User.objects.create_user(username='org', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.organizer = Organizer.objects.create(idu=self.member)
        OrganizerRequest.objects.create(
            idu=self.organizer,
            status='approved',
            request_date=timezone.now(),
        )

        # second organizer (for other people's tournaments)
        other_user = User.objects.create_user(username='org2', password='Test12345')
        other_member = Member.objects.create(idu=other_user)
        self.other_organizer = Organizer.objects.create(idu=other_member)

        # regular player
        self.player_user = User.objects.create_user(username='marko', password='Test12345')
        self.player_member = Member.objects.create(idu=self.player_user)
        self.player = Player.objects.create(idu=self.player_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='org', password='Test12345')

    def _create_tournament(self, organizer=None, status='active',
                        name='Test tournament', days_ahead=10):
        return Tournament.objects.create(
            name=name,
            game=self.game,
            organizer=organizer or self.organizer,
            capacity=10,
            occupancy=1,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status=status,
        )

    def _register_player(self, tournament, player=None):
        return Participation.objects.create(
            idt=tournament,
            idu=player or self.player,
            phone_number='0641234567',
            card_number='1111111111111111',
        )

    def test_access_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('homeOrganizer'))
        self.assertEqual(response.status_code, 302)

    def test_access_as_player(self):
        """Invalid class: logged-in player (not an organizer), redirect."""

        self.client.logout()
        self.client.login(username='marko', password='Test12345')

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('loginRegister'), response.url)

    def test_access_as_organizer(self):
        """Valid class: an approved organizer accesses the page."""

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'org')
        self.assertContains(response, 'My tournaments')
        self.assertContains(response, 'Create tournament')


    def test_display_own_tournaments(self):
        """Valid class: the tournaments of the logged-in organizer are shown."""

        self._create_tournament(name='My tournament')

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My tournament')

    def test_other_organizers_tournaments_not_shown(self):
        """Invalid class: tournaments of another organizer are not shown."""

        self._create_tournament(organizer=self.other_organizer, name='Foreign tournament')

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Foreign tournament')
        self.assertEqual(len(response.context['tournaments']), 0)

    def test_without_tournaments(self):
        """Boundary case: the organizer has no tournaments."""

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tournaments']), 0)

    def test_registered_count_per_tournament(self):
        """Valid class: the registered count on the tournament card matches the number of Participation records."""

        tournament = self._create_tournament()
        self._register_player(tournament)

        response = self.client.get(reverse('homeOrganizer'))

        tournaments = list(response.context['tournaments'])
        self.assertEqual(tournaments[0].registered, 1)
        self.assertContains(response, '1/10 players')



    def test_statistics_counters(self):
        """Valid class: the counters match the database state."""

        active = self._create_tournament(status='active', name='Active')
        self._create_tournament(status='active', name='Active 2')
        self._create_tournament(status='finished', name='Finished', days_ahead=-10)
        self._create_tournament(status='canceled', name='Canceled')

        self._register_player(active)

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.context['active_count'], 2)
        self.assertEqual(response.context['finished_count'], 1)
        self.assertEqual(response.context['registered_count'], 1)

    def test_statistics_do_not_count_others(self):
        """Invalid class: registrations for other organizers' tournaments are not included in registered_count."""

        others = self._create_tournament(organizer=self.other_organizer, name='Foreign')
        self._register_player(others)

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.context['registered_count'], 0)

    def test_statistics_all_zeros(self):
        """Boundary case: a new organizer without tournaments, all counters 0."""

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.context['active_count'], 0)
        self.assertEqual(response.context['finished_count'], 0)
        self.assertEqual(response.context['registered_count'], 0)


    def test_display_games_from_collection(self):
        """Valid class: a game from the collection is shown with its category."""

        category = Category.objects.create(name='Strategy')
        GameCategory.objects.create(idg=self.game, idc=category)

        WishlistCollection.objects.create(
            idu=self.member,
            idg=self.game,
            status='collection'
        )

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catan')
        self.assertContains(response, 'Strategy')

    def test_game_without_category(self):
        """Boundary case: a game in the collection has no category — 'Other'."""

        WishlistCollection.objects.create(
            idu=self.member,
            idg=self.game,
            status='collection'
        )

        response = self.client.get(reverse('homeOrganizer'))

        games = response.context['games']
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0].category, 'Other')
        self.assertEqual(games[0].categories, [])

    def test_wishlist_not_shown(self):
        """Invalid class: a game with status 'wishlist' is not included in My games."""

        WishlistCollection.objects.create(
            idu=self.member,
            idg=self.game,
            status='wishlist'
        )

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(len(response.context['games']), 0)
        self.assertContains(response, 'The game list is empty')

    def test_empty_collection(self):
        """Boundary case: empty collection."""

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(len(response.context['games']), 0)
        self.assertContains(response, 'The game list is empty')


    def test_without_messages(self):
        """Boundary case: no messages, all flags False."""

        response = self.client.get(reverse('homeOrganizer'))

        self.assertFalse(response.context['has_tournament_message'])
        self.assertFalse(response.context['has_creation_message'])
        self.assertFalse(response.context['has_profile_message'])

    def test_access_as_deactivated_organizer(self):
        """
        Invalid class: an organizer whose account is deactivated (is_active=False).
        Expected: redirect (is_active fails, login_url='login').
        """

        self.user.is_active = False
        self.user.save()

        response = self.client.get(reverse('homeOrganizer'))

        self.assertEqual(response.status_code, 302)


class FollowedTournamentsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        org_user = User.objects.create_user(username='org', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)

        # organizer marko does NOT follow
        org2_user = User.objects.create_user(username='org2', password='Test12345')
        org2_member = Member.objects.create(idu=org2_user)
        self.unfollowed_organizer = Organizer.objects.create(idu=org2_member)

        Follow.objects.create(idu=self.player, ido=self.organizer)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='marko', password='Test12345')

    def _create_tournament(self, organizer=None, name='Test tournament', days_ahead=10,
                        status='active', capacity=10, occupancy=1, location='Beograd'):
        return Tournament.objects.create(
            name=name,
            game=self.game,
            organizer=organizer or self.organizer,
            capacity=capacity,
            occupancy=occupancy,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status=status,
            location=location,
        )

    def _apply(self, tournament, phone='0641234567', card='1111111111111111'):
        return self.client.post(reverse('followedTournaments'), {
            'tournament_id': tournament.idt,
            'phone': phone,
            'card': card,
        })

    def test_display_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('followedTournaments'))
        self.assertEqual(response.status_code, 302)

    def test_display_followed_organizer_tournaments(self):
        """Valid class: an upcoming tournament of a followed organizer is shown."""

        self._create_tournament(name='Summer tournament')

        response = self.client.get(reverse('followedTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Summer tournament')

    def test_does_not_show_unfollowed(self):
        """Invalid class: a tournament of an organizer the user does not follow."""

        self._create_tournament(organizer=self.unfollowed_organizer, name='Foreign tournament')

        response = self.client.get(reverse('followedTournaments'))

        self.assertNotContains(response, 'Foreign tournament')

    def test_does_not_show_past(self):
        """Boundary case: a tournament with a past date is not shown."""

        self._create_tournament(name='Past tournament', days_ahead=-1)

        response = self.client.get(reverse('followedTournaments'))

        self.assertNotContains(response, 'Past tournament')

    def test_empty_list(self):
        """Boundary case: no upcoming tournaments."""

        response = self.client.get(reverse('followedTournaments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'There are no upcoming tournaments from the organizers you follow.')

    def test_registered_tournament_in_registrations(self):
        """Valid class: a tournament the user is registered for is in the registrations list (Registered button)."""

        tournament = self._create_tournament()
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.get(reverse('followedTournaments'))

        self.assertIn(tournament.idt, list(response.context['registrations']))
        self.assertContains(response, 'Registered ✔')

    def test_filters_distinct_values(self):
        """Valid class: the lists of games and locations for the filters are distinct."""

        self._create_tournament(name='T1', location='Beograd')
        self._create_tournament(name='T2', location='Beograd')
        self._create_tournament(name='T3', location='Novi Sad')

        response = self.client.get(reverse('followedTournaments'))

        locations = list(response.context['locations'])
        self.assertEqual(len(locations), 2)
        self.assertIn('Beograd', locations)
        self.assertIn('Novi Sad', locations)


    def test_registration_successful(self):
        """Valid class: valid data, test card with funds."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'You have registered successfully!')

        # participation created
        self.assertTrue(Participation.objects.filter(idt=tournament, idu=self.player).exists())

        # occupancy recalculated from the database
        tournament.refresh_from_db()
        self.assertEqual(tournament.occupancy, 1)


    def test_phone_too_short(self):
        """Invalid class: phone with 5 digits (below the limit of 6)."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, phone='12345')

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Invalid phone number.')
        self.assertFalse(Participation.objects.filter(idt=tournament, idu=self.player).exists())

    def test_phone_lower_boundary(self):
        """Boundary case: phone with exactly 6 digits (lower limit) — passes."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, phone='123456')

        self.assertTrue(response.json()['success'])

    def test_phone_upper_boundary(self):
        """Boundary case: phone with exactly 15 digits (upper limit) — passes."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, phone='1' * 15)

        self.assertTrue(response.json()['success'])

    def test_phone_too_long(self):
        """Invalid class: phone with 16 digits (above the limit of 15)."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, phone='1' * 16)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Invalid phone number.')

    def test_phone_with_letters(self):
        """Invalid class: the phone contains characters that are not allowed."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, phone='064abc4567')

        self.assertFalse(response.json()['success'])

    def test_phone_with_spaces(self):
        """Valid class: spaces in the phone are removed before validation."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, phone='064 123 4567')

        self.assertTrue(response.json()['success'])


    def test_card_wrong_length(self):
        """Invalid class: card with 15 digits (below the required 16)."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, card='1' * 15)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'The card must have 16 digits.')

    def test_card_without_funds(self):
        """Invalid class: test card without funds (all zeros)."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, card='0000000000000000')

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Insufficient funds.')
        self.assertFalse(Participation.objects.filter(idt=tournament, idu=self.player).exists())

    def test_card_invalid(self):
        """Invalid class: card with 16 digits that is not a test card."""

        tournament = self._create_tournament(occupancy=0)

        response = self._apply(tournament, card='1234567812345678')

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Invalid card.')


    def test_duplicate_registration(self):
        """Invalid class: the user is already registered for the tournament."""

        tournament = self._create_tournament(occupancy=0)
        self._apply(tournament)  # first registration

        response = self._apply(tournament)  # second registration

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Registration error.')

        # still only one participation
        self.assertEqual(Participation.objects.filter(idt=tournament, idu=self.player).count(), 1)

    def test_registration_for_full_tournament(self):
        """Boundary case: occupancy == capacity, the tournament is not open."""

        tournament = self._create_tournament(capacity=2, occupancy=2)

        response = self._apply(tournament)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertFalse(Participation.objects.filter(idt=tournament, idu=self.player).exists())

    def test_registration_last_spot(self):
        """Boundary case: exactly one free spot left — the registration passes."""

        tournament = self._create_tournament(capacity=2, occupancy=1)

        response = self._apply(tournament)

        self.assertTrue(response.json()['success'])

class SearchTest(TestCase):

    def setUp(self):
        self.client = Client()

        # logged-in player
        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        # another player
        self.other_user = User.objects.create_user(username='ana', password='Test12345')
        self.other_member = Member.objects.create(idu=self.other_user)
        self.other_player = Player.objects.create(idu=self.other_member)

        # approved organizer
        org_user = User.objects.create_user(username='zoran', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)
        OrganizerRequest.objects.create(
            idu=self.organizer, status='approved', request_date=timezone.now()
        )

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='marko', password='Test12345')

    def test_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 302)

    def test_display_player_with_wins(self):
        """Valid class: another player is shown with the number of wins."""

        Match.objects.create(
            name='Match 1', game=self.game, date=timezone.now(),
            player_count=2, winner=self.other_player
        )
        Match.objects.create(
            name='Match 2', game=self.game, date=timezone.now(),
            player_count=2, winner=self.other_player
        )

        response = self.client.get(reverse('search'))

        self.assertEqual(response.status_code, 200)

        members = response.context['members']
        ana = next(k for k in members if k['username'] == 'ana')
        self.assertEqual(ana['type'], 'player')
        self.assertEqual(ana['win_count'], 2)

    def test_player_without_wins(self):
        """Boundary case: a player without any wins — 0 wins."""

        response = self.client.get(reverse('search'))

        members = response.context['members']
        ana = next(k for k in members if k['username'] == 'ana')
        self.assertEqual(ana['win_count'], 0)

    def test_logged_in_user_not_shown(self):
        """Invalid class: the logged-in user is not in the list (exclude)."""

        response = self.client.get(reverse('search'))

        members = response.context['members']
        usernames = [k['username'] for k in members]
        self.assertNotIn('marko', usernames)


    def test_display_organizer_with_tournaments(self):
        """Valid class: an approved organizer is shown with the number of tournaments."""

        Tournament.objects.create(
            name='Tournament 1', game=self.game, organizer=self.organizer,
            capacity=10, occupancy=0,
            date=timezone.now() + timezone.timedelta(days=5),
            status='active',
        )

        response = self.client.get(reverse('search'))

        members = response.context['members']
        zoran = next(k for k in members if k['username'] == 'zoran')
        self.assertEqual(zoran['type'], 'organizer')
        self.assertEqual(zoran['tournament_count'], 1)

    def test_unapproved_organizer_not_shown(self):
        """Invalid class: an organizer with a pending request is not in the list."""

        candidate_user = User.objects.create_user(username='candidate', password='Test12345')
        candidate_member = Member.objects.create(idu=candidate_user)
        candidate = Organizer.objects.create(idu=candidate_member)
        OrganizerRequest.objects.create(
            idu=candidate, status='pending', request_date=timezone.now()
        )

        response = self.client.get(reverse('search'))

        usernames = [k['username'] for k in response.context['members']]
        self.assertNotIn('candidate', usernames)

    def test_rejected_organizer_not_shown(self):
        """Invalid class: an organizer with a rejected request is not in the list."""

        rejected_user = User.objects.create_user(username='rejected', password='Test12345')
        rejected_member = Member.objects.create(idu=rejected_user)
        rejected = Organizer.objects.create(idu=rejected_member)
        OrganizerRequest.objects.create(
            idu=rejected, status='rejected', request_date=timezone.now()
        )

        response = self.client.get(reverse('search'))

        usernames = [k['username'] for k in response.context['members']]
        self.assertNotIn('rejected', usernames)

    def test_sorting_by_username(self):
        """Valid class: the list is sorted by username, case-insensitive, players and organizers together."""

        response = self.client.get(reverse('search'))

        members = response.context['members']
        usernames = [k['username'] for k in members]

        # ana (player) before zoran (organizer)
        self.assertEqual(usernames, sorted(usernames, key=str.lower))
        self.assertIn('ana', usernames)
        self.assertIn('zoran', usernames)

    def test_empty_list(self):
        """Boundary case: there is no other user."""

        # remove everyone except the logged-in user
        self.other_player.delete()
        self.other_member.delete()
        self.other_user.delete()
        OrganizerRequest.objects.all().delete()
        self.organizer.delete()

        response = self.client.get(reverse('search'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['members']), 0)

    def test_display_in_template(self):
        """Valid class: the cards show the role and statistics."""

        response = self.client.get(reverse('search'))

        self.assertContains(response, 'ana')
        self.assertContains(response, 'Player')
        self.assertContains(response, 'Wins: 0')
        self.assertContains(response, 'zoran')
        self.assertContains(response, 'Organizer')
        self.assertContains(response, 'Tournaments: 0')

class GameDetailsTest(TestCase):

    def setUp(self):
        self.client = Client()

        # player
        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        # organizer
        org_user = User.objects.create_user(username='org', password='Test12345')
        self.org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=self.org_member)

        # another player (for reviews)
        other_user = User.objects.create_user(username='ana', password='Test12345')
        self.other_member = Member.objects.create(idu=other_user)
        Player.objects.create(idu=self.other_member)

        self.game = Game.objects.create(
            name='Catan', duration_min=45, duration_max=90,
            min_players=3, max_players=4, min_age=10, author='Klaus Teuber',
            description='A game about an island.'
        )

        self.client.login(username='marko', password='Test12345')

    def _url(self, idg=None):
        return reverse('game_details', kwargs={'idg': idg or self.game.idg})

    def test_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_game(self):
        """Invalid class: idg does not match any game — 404."""

        response = self.client.get(self._url(idg=99999))
        self.assertEqual(response.status_code, 404)

    def test_display_details(self):
        """Valid class: all the game data is shown."""

        category = Category.objects.create(name='Strategy')
        GameCategory.objects.create(idg=self.game, idc=category)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catan')
        self.assertContains(response, 'Klaus Teuber')
        self.assertContains(response, 'Strategy')
        self.assertContains(response, 'A game about an island.')


    def test_average_rating(self):
        """Valid class: avg_rating is the average of all ratings."""

        Review.objects.create(idg=self.game, idu=self.member, rating=5, comment='Excellent', date=timezone.now())
        Review.objects.create(idg=self.game, idu=self.other_member, rating=4, comment='Good', date=timezone.now())

        response = self.client.get(self._url())

        self.assertEqual(response.context['avg_rating'], 4.5)
        self.assertContains(response, '4.5 / 5')

    def test_without_ratings(self):
        """Boundary case: no reviews — avg_rating is None, shows 'No ratings'."""

        response = self.client.get(self._url())

        self.assertIsNone(response.context['avg_rating'])
        self.assertContains(response, 'No ratings')
        self.assertContains(response, 'There are no reviews for this game.')

    def test_single_review(self):
        """Boundary case: exactly one review — the average equals that rating."""

        Review.objects.create(idg=self.game, idu=self.other_member, rating=3, comment='Ok', date=timezone.now())

        response = self.client.get(self._url())

        self.assertEqual(response.context['avg_rating'], 3)
        self.assertContains(response, 'ana')
        self.assertContains(response, 'Ok')


    def test_player_game_not_in_list(self):
        """Valid class: player, the game is neither in the wishlist nor in the collection — both buttons."""

        response = self.client.get(self._url())

        self.assertIsNone(response.context['list_entry'])
        self.assertFalse(response.context['is_organizer'])
        self.assertContains(response, 'Add to wishlist')
        self.assertContains(response, 'Add to collection')

    def test_player_game_in_wishlist(self):
        """Valid class: game in the wishlist — button 'Already in wishlist'."""

        WishlistCollection.objects.create(
            idu=self.member, idg=self.game, status='wishlist'
        )

        response = self.client.get(self._url())

        self.assertContains(response, 'Already in wishlist')
        self.assertNotContains(response, 'Add to wishlist')

    def test_player_game_in_collection(self):
        """Valid class: game in the collection — button 'Already in collection'."""

        WishlistCollection.objects.create(
            idu=self.member, idg=self.game, status='collection'
        )

        response = self.client.get(self._url())

        self.assertContains(response, 'Already in collection')

    def test_organizer_base_template(self):
        """Valid class: the organizer gets the organizer template and only the collection."""

        self.client.logout()
        self.client.login(username='org', password='Test12345')

        response = self.client.get(self._url())

        self.assertTrue(response.context['is_organizer'])
        self.assertEqual(response.context['base_template'], 'app/baseOrganizer.html')
        self.assertContains(response, 'Add to collection')
        # the organizer has no wishlist
        self.assertNotContains(response, 'Add to wishlist')

    def test_organizer_game_in_collection(self):
        """Valid class: organizer, the game is already in the collection."""

        self.client.logout()
        self.client.login(username='org', password='Test12345')

        WishlistCollection.objects.create(
            idu=self.org_member, idg=self.game, status='collection'
        )

        response = self.client.get(self._url())

        self.assertContains(response, 'Already in collection')

    def test_player_base_template(self):
        """Valid class: the player gets the user template."""

        response = self.client.get(self._url())

        self.assertEqual(response.context['base_template'], 'app/baseUser.html')

class OtherProfileTest(TestCase):

    def setUp(self):
        self.client = Client()

        # logged-in player
        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        # another player (whose profile we are viewing)
        self.other_user = User.objects.create_user(username='ana', password='Test12345')
        self.other_member = Member.objects.create(idu=self.other_user)
        self.other_player = Player.objects.create(idu=self.other_member)

        # organizer (whose profile we are viewing)
        org_user = User.objects.create_user(username='zoran', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='marko', password='Test12345')

    def _player_url(self):
        return reverse('otherProfile', kwargs={'user_id': self.other_player.pk})

    def _org_url(self):
        return reverse('otherProfile', kwargs={'user_id': self.organizer.pk})

    def _befriend(self):
        a, b = sorted([self.player.pk, self.other_player.pk])
        return Friendship.objects.create(idu1_id=a, idu2_id=b)


    def test_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(self._player_url())
        self.assertEqual(response.status_code, 302)

    def test_player_profile_stranger(self):
        """Valid class: not friends, no request — button 'Add friend', lists hidden."""

        WishlistCollection.objects.create(
            idu=self.other_member, idg=self.game, status='collection'
        )

        response = self.client.get(self._player_url())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['are_friends'])
        self.assertContains(response, 'Add friend')
        # privacy: the collection is NOT visible
        self.assertNotContains(response, 'Catan')
        self.assertContains(response, 'Add this player as a friend')

    def test_player_profile_request_sent(self):
        """Valid class: the logged-in user sent a request — button 'Request sent'."""

        FriendRequest.objects.create(
            idu1=self.player, idu2=self.other_player, status='pending'
        )

        response = self.client.get(self._player_url())

        self.assertTrue(response.context['request_sent'])
        self.assertContains(response, 'Request sent')

    def test_player_profile_request_received(self):
        """Valid class: the other player sent a request to the logged-in user — Accept/Reject buttons."""

        FriendRequest.objects.create(
            idu1=self.other_player, idu2=self.player, status='pending'
        )

        response = self.client.get(self._player_url())

        self.assertTrue(response.context['request_received'])
        self.assertContains(response, 'Accept')
        self.assertContains(response, 'Reject')

    def test_player_profile_friends(self):
        """Valid class: friends — the collection, wishlist and tournaments are visible."""

        self._befriend()
        WishlistCollection.objects.create(
            idu=self.other_member, idg=self.game, status='collection'
        )

        response = self.client.get(self._player_url())

        self.assertTrue(response.context['are_friends'])
        self.assertContains(response, 'Remove friend')
        self.assertContains(response, 'Catan')
        self.assertIn('detailed_stats', response.context)

    def test_friendship_reversed_direction(self):
        """Boundary case: friendship stored in the opposite direction (idu1/idu2) — the Q query finds it."""

        # intentionally reversed order
        a, b = sorted([self.player.pk, self.other_player.pk])
        Friendship.objects.create(idu1_id=b, idu2_id=a)

        response = self.client.get(self._player_url())

        self.assertTrue(response.context['are_friends'])

    def test_organizer_profile_not_following(self):
        """Valid class: does not follow the organizer — button 'Follow', tournaments hidden."""

        Tournament.objects.create(
            name='Hidden tournament', game=self.game, organizer=self.organizer,
            capacity=10, occupancy=0,
            date=timezone.now() + timezone.timedelta(days=5), status='active',
        )

        response = self.client.get(self._org_url())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_following'])
        self.assertContains(response, 'Follow profile')
        self.assertNotContains(response, 'Hidden tournament')
        self.assertContains(response, 'Follow this organizer')

    def test_organizer_profile_following(self):
        """Valid class: follows the organizer — tournaments and collection visible, button 'Unfollow'."""

        Follow.objects.create(idu=self.player, ido=self.organizer)
        Tournament.objects.create(
            name='Visible tournament', game=self.game, organizer=self.organizer,
            capacity=10, occupancy=0,
            date=timezone.now() + timezone.timedelta(days=5), status='active',
        )

        response = self.client.get(self._org_url())

        self.assertTrue(response.context['is_following'])
        self.assertContains(response, 'Unfollow')
        self.assertContains(response, 'Visible tournament')
        self.assertEqual(response.context['tournament_count'], 1)


    def test_action_add(self):
        """Valid class: sending a friend request."""

        response = self.client.post(self._player_url(), {'action': 'add'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FriendRequest.objects.filter(
                idu1=self.player, idu2=self.other_player, status='pending'
            ).exists()
        )

    def test_action_add_again_does_not_duplicate(self):
        """Boundary case: sending the request again does not create a duplicate record (update_or_create)."""

        self.client.post(self._player_url(), {'action': 'add'})
        self.client.post(self._player_url(), {'action': 'add'})

        self.assertEqual(
            FriendRequest.objects.filter(idu1=self.player, idu2=self.other_player).count(), 1
        )

    def test_action_accept(self):
        """Valid class: accepting a request — the request is deleted, the friendship and notifications are created."""

        FriendRequest.objects.create(
            idu1=self.other_player, idu2=self.player, status='pending'
        )

        response = self.client.post(self._player_url(), {'action': 'accept'})

        self.assertEqual(response.status_code, 302)

        # request deleted
        self.assertFalse(
            FriendRequest.objects.filter(idu1=self.other_player, idu2=self.player).exists()
        )

        # friendship exists
        self.assertTrue(
            Friendship.objects.filter(
                Q(idu1=self.player, idu2=self.other_player) |
                Q(idu1=self.other_player, idu2=self.player)
            ).exists()
        )

        # both notifications
        self.assertTrue(
            Notification.objects.filter(
                idu=self.member, message__contains='ana'
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                idu=self.other_member, message__contains='marko'
            ).exists()
        )

    def test_action_reject(self):
        """Valid class: rejecting a request — the request is rejected, the friendship is NOT created."""

        FriendRequest.objects.create(
            idu1=self.other_player, idu2=self.player, status='pending'
        )

        response = self.client.post(self._player_url(), {'action': 'reject'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FriendRequest.objects.filter(idu1=self.other_player, idu2=self.player, status='rejected').exists()
        )
        self.assertFalse(
            Friendship.objects.filter(
                Q(idu1=self.player, idu2=self.other_player) |
                Q(idu1=self.other_player, idu2=self.player)
            ).exists()
        )

    def test_action_remove(self):
        """Valid class: removing a friend deletes the friendship."""

        self._befriend()

        response = self.client.post(self._player_url(), {'action': 'remove'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Friendship.objects.filter(
                Q(idu1=self.player, idu2=self.other_player) |
                Q(idu1=self.other_player, idu2=self.player)
            ).exists()
        )

    def test_action_follow(self):
        """Valid class: following an organizer + notifications to both sides."""

        response = self.client.post(self._org_url(), {'action': 'follow'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Follow.objects.filter(idu=self.player, ido=self.organizer).exists()
        )
        # notification to the organizer and to oneself
        self.assertTrue(
            Notification.objects.filter(
                idu=self.organizer.idu, message__contains='marko'
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                idu=self.member, message__contains='zoran'
            ).exists()
        )

    def test_action_follow_again(self):
        """Boundary case: following again does not duplicate the follow NOR the notifications (get_or_create + created flag)."""

        self.client.post(self._org_url(), {'action': 'follow'})
        notification_count = Notification.objects.count()

        self.client.post(self._org_url(), {'action': 'follow'})

        self.assertEqual(
            Follow.objects.filter(idu=self.player, ido=self.organizer).count(), 1
        )
        # no new notifications
        self.assertEqual(Notification.objects.count(), notification_count)

    def test_action_unfollow(self):
        """Valid class: unfollowing deletes the Follow record."""

        Follow.objects.create(idu=self.player, ido=self.organizer)

        response = self.client.post(self._org_url(), {'action': 'unfollow'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Follow.objects.filter(idu=self.player, ido=self.organizer).exists()
        )

    def test_player_action_on_organizer_profile(self):
        """Invalid class: action 'add' on an organizer profile — nothing happens."""

        response = self.client.post(self._org_url(), {'action': 'add'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(FriendRequest.objects.exists())

    def test_unknown_action(self):
        """Invalid class: nonexistent action — redirect without changes in the database."""

        response = self.client.post(self._player_url(), {'action': 'something_made_up'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(FriendRequest.objects.exists())
        self.assertFalse(Friendship.objects.exists())

    def test_nonexistent_member(self):
        """Invalid class: user_id does not match any user — 404."""

        response = self.client.get(
            reverse('otherProfile', kwargs={'user_id': 99999})
        )
        self.assertEqual(response.status_code, 404)

class TournamentsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        org_user = User.objects.create_user(username='org', password='Test12345')
        org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=org_member)

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

        self.client.login(username='marko', password='Test12345')

    def _create_tournament(self, name='Test tournament', days_ahead=10, status='active',
                        capacity=10, occupancy=0, location='Beograd'):
        return Tournament.objects.create(
            name=name,
            game=self.game,
            organizer=self.organizer,
            capacity=capacity,
            occupancy=occupancy,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status=status,
            location=location,
        )

    def _apply(self, tournament, phone='0641234567', card='1111111111111111'):
        return self.client.post(reverse('tournament'), {
            'tournament_id': tournament.idt,
            'phone': phone,
            'card': card,
        })

    def test_without_login(self):
        """Invalid class: the user is not logged in."""

        self.client.logout()
        response = self.client.get(reverse('tournament'))
        self.assertEqual(response.status_code, 302)

    def test_display_all_tournaments(self):
        """Valid class: ALL tournaments are shown — all statuses and organizers."""

        self._create_tournament(name='Active', status='active')
        self._create_tournament(name='Finished', status='finished', days_ahead=-10)
        self._create_tournament(name='Canceled', status='canceled')

        response = self.client.get(reverse('tournament'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tournaments']), 3)
        self.assertContains(response, 'Active')
        self.assertContains(response, 'Finished')
        self.assertContains(response, 'Canceled')

    def test_without_tournaments(self):
        """Boundary case: database without tournaments — the page works, empty list."""

        response = self.client.get(reverse('tournament'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tournaments']), 0)

    def test_registered_tournament(self):
        """Valid class: a tournament the user is registered for — Registered button."""

        tournament = self._create_tournament()
        Participation.objects.create(
            idt=tournament, idu=self.player,
            phone_number='0641234567', card_number='1111111111111111'
        )

        response = self.client.get(reverse('tournament'))

        self.assertIn(tournament.idt, list(response.context['registrations']))
        self.assertContains(response, 'Registered ✔')

    def test_filters_distinct(self):
        """Valid class: the filters contain distinct values."""

        self._create_tournament(name='T1', location='Beograd')
        self._create_tournament(name='T2', location='Beograd')
        self._create_tournament(name='T3', location='Novi Sad')

        response = self.client.get(reverse('tournament'))

        locations = list(response.context['locations'])
        self.assertEqual(len(locations), 2)

    def test_registration_successful(self):
        """Valid class: valid registration through this endpoint."""

        tournament = self._create_tournament()

        response = self._apply(tournament)

        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(Participation.objects.filter(idt=tournament, idu=self.player).exists())
        tournament.refresh_from_db()
        self.assertEqual(tournament.occupancy, 1)

    def test_registration_invalid_phone(self):
        """Invalid class: phone validation also works on this endpoint."""

        tournament = self._create_tournament()

        response = self._apply(tournament, phone='123')

        self.assertFalse(response.json()['success'])
        self.assertFalse(Participation.objects.exists())

    def test_registration_for_inactive_tournament(self):
        """Invalid class: registration for a canceled tournament (visible on this page!) is rejected."""

        tournament = self._create_tournament(status='canceled')

        response = self._apply(tournament)

        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Registration error.')
        self.assertFalse(Participation.objects.exists())

class LoginRegisterTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_display_page(self):
        """Valid class: GET returns the page with both forms."""

        response = self.client.get(reverse('loginRegister'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
        self.assertContains(response, 'Register')
        self.assertContains(response, 'Forgot your password?')

    def test_available_to_logged_in(self):
        """Boundary case: an already logged-in user can open the page (no redirect)."""

        user = User.objects.create_user(username='marko', password='Test12345')
        member = Member.objects.create(idu=user)
        Player.objects.create(idu=member)
        self.client.login(username='marko', password='Test12345')

        response = self.client.get(reverse('loginRegister'))

        self.assertEqual(response.status_code, 200)


class LoginTest(TestCase):

    def setUp(self):
        self.client = Client()

        # player
        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        # superuser (admin)
        self.admin = User.objects.create_superuser(
            username='admin', password='Test12345', email='admin@test.com'
        )

    def _login(self, username='marko', password='Test12345'):
        return self.client.post(reverse('login'), {
            'username': username,
            'password': password,
        })

    def _make_organizer(self, request_status=None):
        user = User.objects.create_user(username='org', password='Test12345')
        member = Member.objects.create(idu=user)
        organizer = Organizer.objects.create(idu=member)
        if request_status:
            OrganizerRequest.objects.create(
                idu=organizer, status=request_status, request_date=timezone.now(),
                rejection_reason='Incomplete data' if request_status == 'rejected' else None,
            )
        return user


    def test_get_redirect(self):
        """Invalid class: GET instead of POST."""

        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('loginRegister'))


    def test_player_login(self):
        """Valid class: player — redirect to the home page."""

        response = self._login()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_admin_login(self):
        """Valid class: superuser — redirect to the admin home page."""

        response = self._login(username='admin')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('homeAdmin'))

    def test_approved_organizer_login(self):
        """Valid class: organizer with an approved request — redirect to the organizer home page."""

        self._make_organizer(request_status='approved')

        response = self._login(username='org')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('homeOrganizer'))

    def test_empty_fields(self):
        """Invalid class: empty username/password."""

        response = self._login(username='', password='')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You must enter a username and password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password(self):
        """Invalid class: wrong password."""

        response = self._login(password='Wrong123')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect username or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_nonexistent_username(self):
        """Invalid class: the username does not exist."""

        response = self._login(username='doesnotexist')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect username or password')

    def test_deactivated_account(self):
        """Invalid class: deactivated account — specific message before authenticate."""

        self.user.is_active = False
        self.user.save()

        response = self._login()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your profile has been deactivated')
        self.assertNotIn('_auth_user_id', self.client.session)


    def test_organizer_request_pending(self):
        """Invalid class: an organizer with a pending request cannot log in."""

        self._make_organizer(request_status='pending')

        response = self._login(username='org')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'has not been approved yet')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_organizer_request_rejected(self):
        """Invalid class: organizer with a rejected request — message with the reason."""

        self._make_organizer(request_status='rejected')

        response = self._login(username='org')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Request rejected')
        self.assertContains(response, 'Incomplete data')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_organizer_without_request(self):
        """Boundary case: the Organizer record exists but has no OrganizerRequest — invalid account."""

        self._make_organizer(request_status=None)

        response = self._login(username='org')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'the organizer account is not valid')
        self.assertNotIn('_auth_user_id', self.client.session)

class RegistrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('register')

        self.valid_payload = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password1': 'Test12345',
            'password2': 'Test12345',
        }

    def _register(self, **changes):
        """Sends a POST with valid data + the given changes."""
        payload = {**self.valid_payload, **changes}
        # a None value means: drop the field completely
        payload = {k: v for k, v in payload.items() if v is not None}
        return self.client.post(self.url, payload)


    def test_get_request_redirect(self):
        """Invalid class: GET instead of POST, redirect to loginRegister."""

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('loginRegister'))


    def test_successful_player_registration(self):
        """Valid class: all data correct, User + Member + Player are created and the user is logged in."""

        response = self._register()

        # redirect to the home page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

        # all records created
        user = User.objects.get(username='newuser')
        self.assertTrue(Member.objects.filter(idu=user).exists())
        member = Member.objects.get(idu=user)
        self.assertTrue(Player.objects.filter(idu=member).exists())

        # not an organizer
        self.assertFalse(Organizer.objects.filter(idu=member).exists())

        # the user is automatically logged in
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_successful_organizer_registration(self):
        """Valid class: the organizer option is checked, a request is created and the user is NOT logged in."""

        response = self._register(organizer='on')

        # no redirect — render with a message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organizer request sent.')

        user = User.objects.get(username='newuser')
        member = Member.objects.get(idu=user)
        organizer = Organizer.objects.get(idu=member)

        # pending request created
        request_obj = OrganizerRequest.objects.get(idu=organizer)
        self.assertEqual(request_obj.status, 'pending')

        # Player not created
        self.assertFalse(Player.objects.filter(idu=member).exists())

        # NOT logged in
        self.assertNotIn('_auth_user_id', self.client.session)


    def test_without_username(self):
        """Invalid class: username missing."""

        response = self._register(username=None)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All required fields must be filled in')
        self.assertFalse(User.objects.filter(email='new@test.com').exists())

    def test_empty_username(self):
        """Invalid class: username is an empty string."""

        response = self._register(username='')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All required fields must be filled in')

    def test_without_password(self):
        """Invalid class: password1 missing."""

        response = self._register(password1=None)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All required fields must be filled in')
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_passwords_do_not_match(self):
        """Invalid class: password1 != password2."""

        response = self._register(password2='Different123')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')
        self.assertFalse(User.objects.filter(username='newuser').exists())


    def test_taken_email(self):
        """Invalid class: the email already exists in the database."""

        User.objects.create_user(
            username='existing', email='new@test.com', password='Test12345'
        )

        response = self._register()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email is already in use')
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_taken_username_regular_member(self):
        """Invalid class: the username already exists (regular player)."""

        existing = User.objects.create_user(
            username='newuser', email='old@test.com', password='Test12345'
        )
        member = Member.objects.create(idu=existing)
        Player.objects.create(idu=member)

        response = self._register()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username already exists')
        # still only one user with that name
        self.assertEqual(User.objects.filter(username='newuser').count(), 1)


    def _make_organizer_with_request(self, status, reason=None):
        user = User.objects.create_user(
            username='newuser', email='org@test.com', password='Test12345'
        )
        member = Member.objects.create(idu=user)
        organizer = Organizer.objects.create(idu=member)
        OrganizerRequest.objects.create(
            idu=organizer,
            status=status,
            request_date=timezone.now(),
            rejection_reason=reason,
        )
        return organizer

    def test_request_pending(self):
        """Invalid class: a pending request already exists for the same username."""

        self._make_organizer_with_request('pending')

        response = self._register(organizer='on')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have already sent an organizer request.')
        # no new request was created
        self.assertEqual(OrganizerRequest.objects.count(), 1)

    def test_request_rejected(self):
        """Invalid class: previous request rejected, the reason is shown."""

        self._make_organizer_with_request('rejected', reason='Incomplete data')

        response = self._register(organizer='on')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your previous request was rejected.')
        self.assertContains(response, 'Incomplete data')

    def test_request_approved(self):
        """Invalid class: the account is already approved as an organizer."""

        self._make_organizer_with_request('approved')

        response = self._register(organizer='on')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You already have an organizer account.')

    def test_request_rejected_without_reason(self):
        """Boundary case: rejected request without a reason — message without crashing (or '')."""

        self._make_organizer_with_request('rejected', reason=None)

        response = self._register(organizer='on')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your previous request was rejected.')

    def test_without_email(self):
        """Invalid class: email missing."""

        response = self._register(email='')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All required fields must be filled in')
        self.assertFalse(User.objects.filter(username='newuser').exists())