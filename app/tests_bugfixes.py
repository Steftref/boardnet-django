"""Regression tests — every test describes a bug that existed and was fixed."""
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import (
    Category, Follow, FriendRequest, Friendship, Game, GameCategory, Match,
    MatchParticipant, Member, Notification, Organizer, OrganizerRequest,
    Participation, Player, Review, Tournament, TournamentResult,
)


class BugfixBase(TestCase):

    def setUp(self):
        self.marko = self._player('marko')
        self.ana = self._player('ana')
        self.organizer = self._organizer('zoran', 'approved')
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'Test12345')
        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=10,
        )

    def _member(self, username):
        user = User.objects.create_user(username, f'{username}@test.com', 'Test12345')
        return Member.objects.create(idu=user)

    def _player(self, username):
        return Player.objects.create(idu=self._member(username))

    def _organizer(self, username, status):
        organizer = Organizer.objects.create(idu=self._member(username))
        OrganizerRequest.objects.create(
            idu=organizer, status=status, request_date=timezone.now(),
            rejection_reason='Incomplete data' if status == 'rejected' else None,
        )
        return organizer

    def _tournament(self, days=30, status='active', **kwargs):
        values = dict(
            name='Cup', game=self.game, organizer=self.organizer, capacity=4,
            date=timezone.now() + timedelta(days=days), status=status, entry_fee=500,
        )
        values.update(kwargs)
        return Tournament.objects.create(**values)

    def _participate(self, tournament, player):
        Tournament.objects.filter(pk=tournament.pk).update(occupancy=1)
        return Participation.objects.create(
            idt=tournament, idu=player, phone_number='0641234567', card_number='1111111111111111'
        )

    def _befriend(self, a, b):
        return Friendship.objects.create(idu1=a, idu2=b)

    def login(self, username):
        self.client.logout()
        self.assertTrue(self.client.login(username=username, password='Test12345'))


class SecurityTest(BugfixBase):

    def test_confirm_match_does_not_redirect_outside(self):
        self.login('marko')
        for target in ('https://evil.example/', '//evil.example', 'nonexistent_page', ''):
            response = self.client.post(reverse('confirmMatch'), {'match_id': 1, 'next': target})
            self.assertRedirects(response, reverse('myMatches'), fetch_redirect_response=False)
        response = self.client.post(reverse('confirmMatch'), {'match_id': 1, 'next': 'profile'})
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)

    def test_unapproved_organizer_cannot_use_organizer_pages(self):
        for status in ('pending', 'rejected'):
            organizer = self._organizer(status, status)
            tournament = self._tournament(organizer=organizer)
            self.login(status)
            self.client.post(reverse('create_tournament'), self._form())
            self.client.post(reverse('cancel_tournament', args=[tournament.idt]))
            self.client.post(reverse('edit_tournament', args=[tournament.idt]), {
                'date': '2035-01-01', 'start_time': '10:00', 'capacity': 9})
            tournament.refresh_from_db()
            self.assertEqual(Tournament.objects.filter(organizer=organizer).count(), 1)
            self.assertEqual((tournament.status, tournament.capacity), ('active', 4))
            self.assertEqual(self.client.get(reverse('homeOrganizer')).status_code, 302)

    def _form(self, **kwargs):
        values = {'name': 'New', 'game': self.game.idg, 'date': '2035-01-01', 'start_time': '10:00',
                  'capacity': 4, 'location': 'Belgrade', 'entry_fee': '100', 'prize': 'Cup'}
        values.update(kwargs)
        return values

    def test_approved_organizer_can_create_tournament(self):
        self.login('zoran')
        self.client.post(reverse('create_tournament'), self._form())
        self.assertTrue(Tournament.objects.filter(name='New').exists())

    def test_changes_are_not_possible_with_get(self):
        request_obj = self._organizer('pending', 'pending').organizerrequest
        self.login('admin')
        for name in ('approve_request', 'reject_request'):
            self.assertEqual(self.client.get(reverse(name, args=[request_obj.idr])).status_code, 405)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, 'pending')

        self._befriend(self.marko, self.ana)
        self.login('marko')
        self.assertEqual(self.client.get(reverse('removeFriend', args=[self.ana.pk])).status_code, 405)
        self.assertEqual(Friendship.objects.count(), 1)

    def test_handled_request_cannot_be_changed_again(self):
        request_obj = self._organizer('rejected', 'rejected').organizerrequest
        self.login('admin')
        self.client.post(reverse('approve_request', args=[request_obj.idr]))
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, 'rejected')

    def test_weak_password_is_rejected(self):
        for password in ('1', 'password', '84739261', 'newplayer1'):
            response = self.client.post(reverse('register'), {
                'username': 'newplayer', 'email': 'n@test.com', 'password1': password, 'password2': password})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(User.objects.filter(username='newplayer').exists(), password)

    def test_invalid_username_or_email_is_rejected(self):
        for username, email in (('a' * 200, 'n@test.com'), ('bad name!', 'n@test.com'), ('newplayer', 'notanemail')):
            response = self.client.post(reverse('register'), {
                'username': username, 'email': email, 'password1': 'Strong-pass-77', 'password2': 'Strong-pass-77'})
            self.assertContains(response, 'Enter a valid username and email')

    def test_deactivated_account_is_not_disclosed_with_wrong_password(self):
        User.objects.filter(username='marko').update(is_active=False)
        response = self.client.post(reverse('login'), {'username': 'marko', 'password': 'wrong'})
        self.assertNotContains(response, 'deactivated')
        response = self.client.post(reverse('login'), {'username': 'marko', 'password': 'Test12345'})
        self.assertContains(response, 'deactivated')


class CrashTest(BugfixBase):

    def test_wrong_list_status_returns_to_the_game(self):
        self.login('marko')
        response = self.client.post(reverse('add_to_list', args=[self.game.idg]), {'status': 'x'})
        self.assertRedirects(response, reverse('game_details', args=[self.game.idg]))

    def test_every_page_opens_or_redirects_for_every_role(self):
        pages = [reverse(n) for n in (
            'home', 'homeAdmin', 'homeOrganizer', 'followedTournaments', 'search', 'tournament', 'games',
            'profile', 'myCollection', 'myWishlist', 'myMatches', 'myTournaments', 'friend_requests',
            'notifications', 'organizerNotifications', 'tools', 'adminGames', 'adminOrganizers',
            'create_tournament', 'editOrganizerProfile', 'changeProfilePicture', 'confirmMatch')]
        pages += [reverse('game_details', args=[self.game.idg]), reverse('otherProfile', args=[self.marko.pk]),
                  reverse('otherProfile', args=[self.organizer.pk]), reverse('friends', args=[self.marko.pk]),
                  reverse('add_to_list', args=[self.game.idg]), reverse('add_review', args=[self.game.idg])]
        for username in (None, 'marko', 'zoran', 'admin'):
            self.client.logout()
            if username:
                self.login(username)
            for page in pages:
                status = self.client.get(page).status_code
                self.assertIn(status, (200, 302, 403), (username, page))

    def test_other_roles_go_to_their_own_home(self):
        for username, home in (('zoran', 'homeOrganizer'), ('admin', 'homeAdmin')):
            self.login(username)
            for page in ('home', 'tournament', 'followedTournaments', 'profile'):
                self.assertRedirects(self.client.get(reverse(page)), reverse(home))
        self.login('admin')
        self.assertRedirects(self.client.get(reverse('games')), reverse('homeAdmin'))

    def test_logged_out_user_is_sent_to_login(self):
        for url in (reverse('add_to_list', args=[self.game.idg]), reverse('add_review', args=[self.game.idg]),
                    reverse('removeFromCollection', args=[self.game.idg]), reverse('confirmMatch'),
                    reverse('removeFriend', args=[self.ana.pk]), reverse('addMatch')):
            response = self.client.post(url, {'rating': 5, 'status': 'wishlist'})
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse('loginRegister'), response['Location'])

    def test_organizer_adding_a_friend_does_nothing(self):
        self.login('zoran')
        for action in ('add', 'accept', 'reject', 'remove', 'follow', 'unfollow'):
            for pk in (self.marko.pk, self.organizer.pk):
                self.assertEqual(self.client.post(reverse('otherProfile', args=[pk]), {'action': action}).status_code, 302)
        self.assertEqual(FriendRequest.objects.count() + Follow.objects.count(), 0)

    def test_create_tournament_with_invalid_values(self):
        self.login('zoran')
        base = {'name': 'New', 'game': self.game.idg, 'date': '2035-01-01', 'start_time': '10:00',
                'capacity': '4', 'location': 'L', 'entry_fee': '1', 'prize': 'P'}
        for field, value in (('game', 'abc'), ('game', '99999'), ('capacity', '0'), ('capacity', '9' * 20),
                             ('entry_fee', 'NaN'), ('entry_fee', 'Infinity'), ('entry_fee', '9' * 12),
                             ('entry_fee', '-1'), ('name', 'x' * 101), ('date', '2020-01-01'), ('date', 'x')):
            response = self.client.post(reverse('create_tournament'), dict(base, **{field: value}))
            self.assertEqual(response.status_code, 302, (field, value))
        self.assertEqual(Tournament.objects.count(), 0)

    def test_capacity_must_stay_positive(self):
        tournament = self._tournament()
        self.login('zoran')
        for value in ('0', '-5', 'abc', ''):
            self.client.post(reverse('edit_tournament', args=[tournament.idt]), {
                'date': '2035-01-01', 'start_time': '10:00', 'capacity': value})
            tournament.refresh_from_db()
            self.assertEqual(tournament.capacity, 4)

    def test_tournament_registration_with_invalid_values(self):
        tournament = self._tournament()
        self.login('marko')
        for page in ('tournament', 'followedTournaments'):
            for data in ({}, {'tournament_id': tournament.idt}, {'tournament_id': 'abc', 'phone': '123456', 'card': '1' * 16},
                         {'tournament_id': 99999, 'phone': '123456', 'card': '1' * 16}):
                response = self.client.post(reverse(page), data)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()['success'])

    def test_ids_that_are_not_numbers(self):
        self.login('marko')
        for page, data in (('myWishlist', {'game_id': 'x', 'action': 'remove'}), ('friend_requests', {'sender_id': 'x', 'action': 'accept'}),
                           ('myTournaments', {'idt': 'x'}), ('confirmMatch', {'match_id': 'x'})):
            self.assertIn(self.client.post(reverse(page), data).status_code, (200, 302), page)

    def test_add_match_with_invalid_data(self):
        self._befriend(self.marko, self.ana)
        self.login('marko')
        good = {'name': 'M', 'date': '2026-01-01', 'game_id': self.game.idg, 'participants': ['ana'], 'winner': ''}
        for change in ({'name': None}, {'name': 5 * 'x' * 30}, {'game_id': 'abc'}, {'participants': 'ana'}, {'participants': [1]},
                       {'date': '2026-13-45'}, {'date': 5}, {'participants': ['marko']}):
            response = self.client.post(reverse('addMatch'), json.dumps(dict(good, **change)), content_type='application/json')
            self.assertEqual(response.status_code, 400, change)
        for body in ('not json', '[]', 'null'):
            self.assertEqual(self.client.post(reverse('addMatch'), body, content_type='application/json').status_code, 400)
        self.assertEqual(Match.objects.count(), 0)
        self.assertEqual(self.client.post(reverse('addMatch'), json.dumps(good), content_type='application/json').status_code, 200)

    def test_add_match_hides_internal_errors(self):
        self._befriend(self.marko, self.ana)
        self.login('marko')
        with patch('app.views.Match.objects.create', side_effect=RuntimeError('secret detail')), self.assertLogs('app.views', 'ERROR'):
            response = self.client.post(reverse('addMatch'), json.dumps({
                'name': 'M', 'date': '2026-01-01', 'game_id': self.game.idg, 'participants': ['ana']}), content_type='application/json')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret', response.content.decode())


class LogicTest(BugfixBase):

    def _match(self, winner, status):
        match = Match.objects.create(name='M', game=self.game, date=timezone.now(), player_count=2, winner=winner)
        MatchParticipant.objects.create(idm=match, idu=self.marko, status='confirmed')
        MatchParticipant.objects.create(idm=match, idu=self.ana, status=status)
        return match

    def test_unconfirmed_win_does_not_count(self):
        self._befriend(self.marko, self.ana)
        self._match(self.marko, 'unconfirmed')
        self.login('ana')
        wins = lambda: {p.idu.idu.username: n for p, n in self.client.get(reverse('home')).context['leaderboard']}
        searched = lambda: {m['username']: m.get('win_count') for m in self.client.get(reverse('search')).context['members']}
        self.assertEqual((wins()['marko'], searched()['marko']), (0, 0))
        MatchParticipant.objects.update(status='confirmed')
        self.assertEqual((wins()['marko'], searched()['marko']), (1, 1))

    def test_accepting_twice_creates_one_friendship(self):
        for first, second in (('profile', 'list'), ('list', 'profile')):
            Friendship.objects.all().delete()
            Notification.objects.all().delete()
            FriendRequest.objects.create(idu1=self.marko, idu2=self.ana, status='pending')
            FriendRequest.objects.create(idu1=self.ana, idu2=self.marko, status='pending')
            for username, other, way in (('ana', self.marko, first), ('marko', self.ana, second)):
                self.login(username)
                if way == 'profile':
                    self.client.post(reverse('otherProfile', args=[other.pk]), {'action': 'accept'})
                else:
                    self.client.post(reverse('friend_requests'), {'sender_id': other.pk, 'action': 'accept'})
            self.assertEqual(Friendship.objects.count(), 1)
            self.assertEqual(FriendRequest.objects.count(), 0)
            self.assertEqual(Notification.objects.count(), 2)

    def test_user_cannot_befriend_themselves(self):
        self.login('marko')
        for action in ('add', 'accept'):
            self.client.post(reverse('otherProfile', args=[self.marko.pk]), {'action': action})
        FriendRequest.objects.create(idu1=self.marko, idu2=self.marko, status='pending')
        self.client.post(reverse('friend_requests'), {'sender_id': self.marko.pk, 'action': 'accept'})
        self.assertEqual(Friendship.objects.count(), 0)

    def test_friend_request_to_a_friend_is_not_created(self):
        self._befriend(self.ana, self.marko)
        self.login('marko')
        self.client.post(reverse('otherProfile', args=[self.ana.pk]), {'action': 'add'})
        self.assertEqual(FriendRequest.objects.count(), 0)

    def test_rejected_request_can_be_sent_again(self):
        self.login('ana')
        FriendRequest.objects.create(idu1=self.marko, idu2=self.ana, status='pending')
        self.client.post(reverse('friend_requests'), {'sender_id': self.marko.pk, 'action': 'reject'})
        self.assertEqual(FriendRequest.objects.get().status, 'rejected')
        self.login('marko')
        self.client.post(reverse('otherProfile', args=[self.ana.pk]), {'action': 'add'})
        self.assertEqual(FriendRequest.objects.get().status, 'pending')

    def test_rating_must_be_between_1_and_5(self):
        self.login('marko')
        url = reverse('add_review', args=[self.game.idg])
        for rating in ('999', '6', '0', '-1', 'abc', None):
            response = self.client.post(url, {} if rating is None else {'rating': rating}, follow=True)
            self.assertContains(response, 'The rating must be between 1 and 5.')
        self.assertEqual(Review.objects.count(), 0)
        self.client.post(url, {'rating': '5', 'comment': 'Great'})
        self.assertEqual(Review.objects.get().rating, 5)

    def test_results_need_first_place_if_there_are_players(self):
        tournament = self._tournament(days=-1)
        self._participate(tournament, self.marko)
        self.login('zoran')
        url = reverse('save_results', args=[tournament.idt])
        for data in ({}, {'first_place': 'abc'}, {'first_place': self.ana.pk}):
            self.client.post(url, data)
            tournament.refresh_from_db()
            self.assertEqual(tournament.status, 'active')
        self.client.post(url, {'first_place': self.marko.pk})
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, 'finished')
        self.assertEqual(TournamentResult.objects.get().idu, self.marko)

    def test_tournament_without_players_can_be_finished(self):
        tournament = self._tournament(days=-1)
        self.login('zoran')
        self.client.post(reverse('save_results', args=[tournament.idt]), {})
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, 'finished')

    def test_unregistering_refunds_the_entry_fee(self):
        tournament = self._tournament(entry_fee=Decimal('500.00'))
        self._participate(tournament, self.marko)
        self.login('marko')
        with self.assertLogs('app.views', 'INFO') as log:
            self.client.post(reverse('myTournaments'), {'idt': tournament.idt})
        self.assertIn('500.00 RSD to card ****1111', log.output[0])
        self.assertNotIn('1' * 16, log.output[0])
        self.assertEqual(Participation.objects.count(), 0)
        tournament.refresh_from_db()
        self.assertEqual(tournament.occupancy, 0)
        self.assertIn('500.00 RSD has been refunded', Notification.objects.get().message)

    def test_free_tournament_has_no_refund(self):
        for fee in (0, None):
            Notification.objects.all().delete()
            tournament = self._tournament(entry_fee=fee)
            self._participate(tournament, self.marko)
            self.login('zoran')
            self.client.post(reverse('cancel_tournament', args=[tournament.idt]))
            self.assertEqual(Notification.objects.get().message, 'Tournament "Cup" has been canceled.')

    def test_canceled_tournament_is_refunded_only_once(self):
        tournament = self._tournament()
        self._participate(tournament, self.marko)
        with patch('app.views._execute_refund') as refund:
            self.login('zoran')
            self.client.post(reverse('cancel_tournament', args=[tournament.idt]))
            self.login('admin')
            self.client.post(reverse('cancel_tournament_admin', args=[tournament.idt]))
            self.login('marko')
            response = self.client.post(reverse('myTournaments'), {'idt': tournament.idt})
        self.assertEqual(refund.call_count, 1)
        self.assertEqual(Participation.objects.count(), 1)
        self.assertContains(response, 'CANCELED')

    def test_rejected_organizer_sees_the_reason(self):
        self._organizer('rejected', 'rejected')
        for username, email in (('rejected', 'other@test.com'), ('rejected', 'rejected@test.com'), ('newname', 'rejected@test.com')):
            response = self.client.post(reverse('register'), {
                'username': username, 'email': email, 'password1': 'Strong-pass-77', 'password2': 'Strong-pass-77', 'organizer': 'on'})
            self.assertContains(response, 'Incomplete data')

    def test_taken_email_and_username(self):
        for username, email, text in (('newname', 'marko@test.com', 'Email is already in use'), ('marko', 'new@test.com', 'Username already exists')):
            response = self.client.post(reverse('register'), {
                'username': username, 'email': email, 'password1': 'Strong-pass-77', 'password2': 'Strong-pass-77'})
            self.assertContains(response, text)

    def test_removing_the_organizer_description(self):
        self.login('zoran')
        self.client.post(reverse('editOrganizerProfile'), {'description': 'Hello'})
        self.client.post(reverse('editOrganizerProfile'), {'description': ''})
        self.organizer.refresh_from_db()
        self.assertIsNone(self.organizer.description)
        self.assertNotContains(self.client.get(reverse('homeOrganizer')), '>None<')


class AdminGamesBugfixTest(BugfixBase):

    def setUp(self):
        super().setUp()
        self.strategy = Category.objects.create(name='Strategy')
        self.party = Category.objects.create(name='Party')
        self.login('admin')

    def _post(self, **kwargs):
        values = {'name': 'Catan', 'min_players': '3', 'max_players': '4', 'duration_min': '30', 'duration_max': '60', 'min_age': '10'}
        values.update(kwargs)
        return self.client.post(reverse('adminGames'), values)

    def test_each_error_is_shown_once(self):
        errors = self._post(name='New', min_players='-1').context['errors']
        self.assertEqual(errors, ['Minimum number of players must be a positive number.'])

    def test_existing_game_is_not_overwritten(self):
        response = self._post(min_age='18')
        self.assertContains(response, 'A game with this name already exists.')
        self.game.refresh_from_db()
        self.assertEqual(self.game.min_age, 10)

    def test_game_can_be_renamed(self):
        self._post(game_id=self.game.idg, name='Catan 2')
        self.game.refresh_from_db()
        self.assertEqual(self.game.name, 'Catan 2')
        self.assertEqual(Game.objects.count(), 1)

    def test_name_of_another_game_cannot_be_taken(self):
        other = Game.objects.create(name='Chess', min_players=2, max_players=2, duration_min=1, duration_max=2, min_age=6)
        self.assertContains(self._post(game_id=other.idg), 'A game with this name already exists.')

    def test_categories_can_be_changed_and_cleared(self):
        GameCategory.objects.create(idg=self.game, idc=self.strategy)
        names = lambda: list(GameCategory.objects.filter(idg=self.game).values_list('idc__name', flat=True))
        self._post(game_id=self.game.idg, categories=[self.party.pk, 'abc', '99999'])
        self.assertEqual(names(), ['Party'])
        self._post(game_id=self.game.idg)
        self.assertEqual(names(), [])

    def test_author_and_description_can_be_cleared(self):
        self._post(game_id=self.game.idg, author='A', description='D')
        self._post(game_id=self.game.idg)
        self.game.refresh_from_db()
        self.assertEqual((self.game.author, self.game.description), (None, None))

    def test_entered_values_stay_after_an_error(self):
        response = self._post(game_id=self.game.idg, name='Changed', min_age='0', categories=[self.party.pk])
        self.assertContains(response, 'value="Changed"')
        self.assertContains(response, f'name="game_id" value="{self.game.idg}"')
        self.assertContains(response, f'data-ids="{self.party.pk}"')

    def test_invalid_values(self):
        for values in ({'name': 'x' * 101}, {'name': 'New', 'min_age': '9' * 20}, {'name': 'New', 'author': 'x' * 101},
                       {'game_id': 'abc'}, {'game_id': '99999', 'name': 'New'}):
            self.assertEqual(self._post(**values).status_code, 200)
        self.assertEqual(Game.objects.count(), 1)

    def test_edit_button_with_quotes_and_new_lines(self):
        Game.objects.update(description="It's a \"nice\"\ngame <b>")
        content = self.client.get(reverse('adminGames')).content.decode()
        self.assertIn('data-description="It&#x27;s a &quot;nice&quot;\ngame &lt;b&gt;"', content)
        self.assertIn('onclick="editGame(this)"', content)


class PagesTest(BugfixBase):

    def test_charts_only_on_a_friends_profile(self):
        self.login('marko')
        url = reverse('otherProfile', args=[self.ana.pk])
        self.assertNotContains(self.client.get(url), 'new Chart')
        self._befriend(self.marko, self.ana)
        self.assertContains(self.client.get(url), 'new Chart')

    def test_no_friend_buttons_on_own_profile_or_for_organizers(self):
        for username in ('marko', 'zoran'):
            self.login(username)
            self.assertNotContains(self.client.get(reverse('otherProfile', args=[self.marko.pk])), 'name="action"')
