import time

from django.contrib.auth.models import User
from selenium.webdriver.common.by import By

from app.models import Member, Player, Game, Tournament, Participation, Friendship

from app.tests_selenium import BoardNetSeleniumBase


class ToolsSeleniumTest(BoardNetSeleniumBase):

    def test_logged_out_user_redirected_from_tools(self):
        """
        Invalid class: a logged-out user tries to open /tools/.
        """

        tools_url = self.live_server_url + '/tools/'
        self.browser.get(tools_url)

        self.assertNotIn('Dice', self.browser.page_source)
        self.assertNotIn('Timer/Stopwatch', self.browser.page_source)
        self.assertNotEqual(self.browser.current_url, tools_url)


class ProfileSeleniumTest(BoardNetSeleniumBase):

    def test_organizer_redirected_from_profile(self):
        """
        Valid class: an organizer who opens /profile/ is redirected to 'homeOrganizer' and does not see profile.html.
        """

        self._login('zoran', 'Test12345')
        self.browser.get(self.live_server_url + '/profile/')

        self.assertIn('/home-organizer/', self.browser.current_url)


class MyMatchesSeleniumTest(BoardNetSeleniumBase):

    def test_participant_dropdown_shows_only_friends(self):
        """
        Valid class: in the add-match action, the dropdown shows only friends of the logged-in user.
        """

        stranger_user = User.objects.create_user(username='nikola', password='Test12345')
        stranger_member = Member.objects.create(idu=stranger_user)
        Player.objects.create(idu=stranger_member)

        self._login()  # marko
        self.browser.get(self.live_server_url + '/my-matches/')

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Add new match")]'
        ).click()
        time.sleep(0.3)

        friend_search = self.browser.find_element(By.ID, 'friendSearch')
        friend_search.send_keys('a') #Ana nikolA
        time.sleep(0.3)

        dropdown = self.browser.find_element(By.ID, 'dropdown')
        self.assertIn('ana', dropdown.text)
        self.assertNotIn('nikola', dropdown.text)


class MyTournamentsSeleniumTest(BoardNetSeleniumBase):

    def test_unregister_allowed_more_than_5_days(self):
        """Valid class: unregistering from a tournament that is more than 5 days ahead."""

        tournament = self._create_tournament(name='Test tournament', days_ahead=10)
        Participation.objects.create(
            idt=tournament,
            idu=self.player,
            phone_number='0641234567',
            card_number='1111111111111111'
        )

        self._login()
        self.browser.get(self.live_server_url + '/my-tournaments/')

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Unregister")]'
        ).click()
        time.sleep(1)

        self.assertFalse(Participation.objects.filter(idt=tournament, idu=self.player).exists())

    def test_unregister_rejected_less_than_5_days(self):
        """Invalid class: unregistering from a tournament that starts in less than 5 days"""

        tournament = self._create_tournament(name='Test tournament', days_ahead=3)
        Participation.objects.create(
            idt=tournament,
            idu=self.player,
            phone_number='0641234567',
            card_number='1111111111111111'
        )

        self._login()
        self.browser.get(self.live_server_url + '/my-tournaments/')

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Unregister")]'
        ).click()
        time.sleep(1)

        self.assertTrue(Participation.objects.filter(idt=tournament, idu=self.player).exists())


class FriendsSeleniumTest(BoardNetSeleniumBase):

    def test_access_to_others_friend_list_denied(self):
        """
        Invalid class: the user tries to access someone else's friend list (ID in the URL).
        """

        stranger1_user = User.objects.create_user(username='petar', password='Test12345')
        stranger1_member = Member.objects.create(idu=stranger1_user)
        stranger1_player = Player.objects.create(idu=stranger1_member)

        stranger2_user = User.objects.create_user(username='jovana', password='Test12345')
        stranger2_member = Member.objects.create(idu=stranger2_user)
        stranger2_player = Player.objects.create(idu=stranger2_member)

        a, b = sorted([stranger1_player.pk, stranger2_player.pk])
        Friendship.objects.create(idu1_id=a, idu2_id=b)

        self._login()  # marko
        others_url = self.live_server_url + f'/friends/{stranger1_player.pk}/'
        self.browser.get(others_url)

        self.assertNotIn('jovana', self.browser.page_source)


class AdminGamesSeleniumTest(BoardNetSeleniumBase):

    def test_create_game_correctly(self):
        """Valid class: the admin creates a new game through the form with all correct data."""

        self._login('admin', 'Test12345')
        self.browser.get(self.live_server_url + '/admin-games/')

        self.browser.find_element(By.ID, 'name').send_keys('Ticket to Ride')
        self.browser.find_element(By.ID, 'min_players').send_keys('2')
        self.browser.find_element(By.ID, 'max_players').send_keys('5')
        self.browser.find_element(By.ID, 'duration_min').send_keys('30')
        self.browser.find_element(By.ID, 'duration_max').send_keys('60')
        self.browser.find_element(By.ID, 'min_age').send_keys('8')
        self.browser.find_element(By.ID, 'author').send_keys('Alan R. Moon')

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Save game")]'
        ).click()
        time.sleep(1)

        self.assertTrue(Game.objects.filter(name='Ticket to Ride').exists())
        self.assertIn('Ticket to Ride', self.browser.page_source)

    def test_create_game_negative_player_count(self):
        """
        Invalid class: negative min_players when creating a game.
        """

        self._login('admin', 'Test12345')
        self.browser.get(self.live_server_url + '/admin-games/')

        self.browser.execute_script("document.getElementById('min_players').removeAttribute('min');")

        self.browser.find_element(By.ID, 'name').send_keys('Test game')
        self.browser.find_element(By.ID, 'min_players').send_keys('-5')
        self.browser.find_element(By.ID, 'max_players').send_keys('4')
        self.browser.find_element(By.ID, 'duration_min').send_keys('20')
        self.browser.find_element(By.ID, 'duration_max').send_keys('40')
        self.browser.find_element(By.ID, 'min_age').send_keys('8')

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Save game")]'
        ).click()
        time.sleep(1)

        self.assertIn('Minimum number of players must be a positive number.', self.browser.page_source)
        self.assertFalse(Game.objects.filter(name='Test game').exists())