import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from django.urls import reverse

from app.models import (
    Member, Player, Organizer, Game, Tournament, Participation,
    Match, Friendship, Follow, Notification, FriendRequest,
    OrganizerRequest, Review, WishlistCollection
)

URL_TOURNAMENTS = '/tournament/'
URL_FOLLOWED_TOURNAMENTS = '/followed-tournaments/'
URL_SEARCH = '/search/'
URL_FRIEND_REQUESTS = '/friend-requests/'

from selenium.webdriver.firefox.options import Options

class BoardNetSeleniumBase(StaticLiveServerTestCase):
    """Shared setup: browser + base data."""

    def setUp(self):
        opts = Options()
        opts.add_argument('--headless')
        self.browser = webdriver.Firefox(options=opts)

        #self.browser = webdriver.Firefox()
        self.wait = WebDriverWait(self.browser, 5)

        # player marko
        self.user = User.objects.create_user(username='marko', password='Test12345')
        self.member = Member.objects.create(idu=self.user)
        self.player = Player.objects.create(idu=self.member)

        # player ana (friend of marko)
        self.ana_user = User.objects.create_user(username='ana', password='Test12345')
        self.ana_member = Member.objects.create(idu=self.ana_user)
        self.ana_player = Player.objects.create(idu=self.ana_member)

        a, b = sorted([self.player.pk, self.ana_player.pk])
        Friendship.objects.create(idu1_id=a, idu2_id=b)

        # approved organizer
        org_user = User.objects.create_user(username='zoran', password='Test12345')
        self.org_member = Member.objects.create(idu=org_user)
        self.organizer = Organizer.objects.create(idu=self.org_member)
        OrganizerRequest.objects.create(
            idu=self.organizer, status='approved', request_date=timezone.now()
        )

        # admin (superuser)
        User.objects.create_superuser(
            username='admin', password='Test12345', email='admin@test.com'
        )

        self.game = Game.objects.create(
            name='Catan', min_players=3, max_players=4,
            duration_min=30, duration_max=60, min_age=12,
        )

    def tearDown(self):
        self.browser.quit()

    def _login(self, username='marko', password='Test12345'):
        self.browser.get(self.live_server_url + '/')
        self.browser.find_element(By.NAME, 'username').send_keys(username)
        self.browser.find_element(By.NAME, 'password').send_keys(password)
        self.browser.find_element(
            By.XPATH, '//div[@id="loginForm"]//button[@type="submit"]'
        ).click()
        time.sleep(1)

    def _logout(self):
        self.browser.get(self.live_server_url + reverse('logout'))

    def _create_tournament(self, name='Summer tournament', days_ahead=10,
                        status='active', capacity=10, occupancy=0,
                        organizer=None):
        return Tournament.objects.create(
            name=name, game=self.game,
            organizer=organizer or self.organizer,
            capacity=capacity, occupancy=occupancy,
            date=timezone.now() + timezone.timedelta(days=days_ahead),
            status=status, location='Beograd',
        )


# ============ 1. LOGIN / REGISTRATION ============

class LoginRegSeleniumTest(BoardNetSeleniumBase):

    def test_login_successful(self):
        """Valid class: correct credentials lead to the home page."""
        self._login()
        self.assertIn('Leaderboard Arena', self.browser.page_source)

    def test_login_wrong_password(self):
        """Invalid class: wrong password, error message, stays on the login page."""
        self._login(password='Wrong123')
        self.assertIn('Incorrect username or password', self.browser.page_source)

    def test_tab_toggle(self):
        """Valid class: clicking Register shows the register form (JS)."""
        self.browser.get(self.live_server_url + '/')
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Register")]'
        ).click()
        time.sleep(0.5)
        self.assertTrue(
            self.browser.find_element(By.ID, 'registerForm').is_displayed()
        )

    def test_player_registration(self):
        """Valid class: registration through the UI, automatic login."""
        self.browser.get(self.live_server_url + '/')
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Register")]'
        ).click()
        time.sleep(0.5)

        form = self.browser.find_element(By.ID, 'registerForm')
        form.find_element(By.NAME, 'username').send_keys('new_wd')
        form.find_element(By.NAME, 'email').send_keys('new_wd@test.com')
        form.find_element(By.NAME, 'password1').send_keys('Test12345')
        form.find_element(By.NAME, 'password2').send_keys('Test12345')
        form.find_element(By.XPATH, './/button[@type="submit"]').click()
        time.sleep(1)

        self.assertIn('Leaderboard Arena', self.browser.page_source)
        self.assertTrue(User.objects.filter(username='new_wd').exists())


# ============ 2. HOME (player) ============

class HomeSeleniumTest(BoardNetSeleniumBase):

    def test_leaderboard(self):
        """Valid class: the leaderboard shows marko and friend ana with wins."""
        Match.objects.create(
            name='P1', game=self.game, date=timezone.now(),
            player_count=2, winner=self.player
        )

        self._login()

        rows = self.browser.find_elements(By.CLASS_NAME, 'leader-row')
        self.assertEqual(len(rows), 2)
        self.assertIn('marko', rows[0].text)
        self.assertIn('1 wins', rows[0].text)

    def test_upcoming_tournament_of_followed(self):
        """Valid class: a tournament of a followed organizer on the home page."""
        Follow.objects.create(idu=self.player, ido=self.organizer)
        self._create_tournament(name='Home tournament')

        self._login()

        card = self.browser.find_element(By.CLASS_NAME, 'tournament-featured')
        self.assertIn('Home tournament', card.text)

    def test_explore_games_button(self):
        """Valid class: clicking Explore games leads to the games page."""
        self._login()
        self.browser.find_element(By.CLASS_NAME, 'btn-link-index').click()
        time.sleep(1)
        self.assertIn('games', self.browser.current_url)


# ============ 3. HOME ADMIN ============

class HomeAdminSeleniumTest(BoardNetSeleniumBase):

    def test_display_statistics_and_requests(self):
        """Valid class: the admin sees the statistics and the pending request."""
        candidate_user = User.objects.create_user(
            username='candidate', password='Test12345', email='k@test.com'
        )
        candidate_member = Member.objects.create(idu=candidate_user)
        candidate = Organizer.objects.create(idu=candidate_member)
        OrganizerRequest.objects.create(
            idu=candidate, status='pending', request_date=timezone.now()
        )

        self._login('admin')

        self.assertIn('Admin panel', self.browser.page_source)
        self.assertIn('candidate', self.browser.page_source)
        # stat bar: 1 request awaiting approval
        stat = self.browser.find_element(By.CLASS_NAME, 'stat-bar')
        self.assertIn('1', stat.text)

    def test_approve_request_click(self):
        """Valid class: clicking Approve changes the request status."""
        candidate_user = User.objects.create_user(
            username='candidate', password='Test12345', email='k@test.com'
        )
        candidate_member = Member.objects.create(idu=candidate_user)
        candidate = Organizer.objects.create(idu=candidate_member)
        request_obj = OrganizerRequest.objects.create(
            idu=candidate, status='pending', request_date=timezone.now()
        )

        self._login('admin')
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Approve")]'
        ).click()
        time.sleep(1)

        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, 'approved')

    def test_admin_filter_status(self):
        """Valid class: the JS status filter hides cards."""
        self._create_tournament(name='Active WD', status='active')
        self._create_tournament(name='Finished WD', status='finished', days_ahead=-5)

        self._login('admin')

        Select(self.browser.find_element(By.ID, 'statusFilter')) \
            .select_by_value('active')
        time.sleep(0.5)

        cards = self.browser.find_elements(By.CLASS_NAME, 'tournament-card')
        visible = [k.text for k in cards if k.is_displayed()]
        self.assertTrue(any('Active WD' in t for t in visible))
        self.assertFalse(any('Finished WD' in t for t in visible))


# ============ 4. HOME ORGANIZER ============

class HomeOrgSeleniumTest(BoardNetSeleniumBase):

    def test_display_and_statistics(self):
        """Valid class: the organizer sees their tournaments and counters."""
        self._create_tournament(name='Org tournament')

        self._login('zoran')

        self.assertIn('zoran', self.browser.page_source)
        self.assertIn('Org tournament', self.browser.page_source)
        self.assertIn('Create tournament', self.browser.page_source)

    def test_collapsible_panel(self):
        """Valid class: clicking the header opens the Create tournament panel (JS)."""
        self._login('zoran')

        self.browser.find_element(
            By.XPATH, '//div[@class="card-header"][.//h2[text()="Create tournament"]]'
        ).click()
        time.sleep(0.5)

        panel = self.browser.find_element(By.ID, 'createPanel')
        self.assertTrue(panel.is_displayed())


# ============ 5. TOURNAMENTS (all) ============

class TournamentsSeleniumTest(BoardNetSeleniumBase):

    def test_ajax_registration_successful(self):
        """Valid class: AJAX registration — green message without a reload."""
        self._create_tournament()

        self._login()
        self.browser.get(self.live_server_url + URL_TOURNAMENTS)

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Apply")]'
        ).click()
        time.sleep(0.5)

        self.browser.find_element(By.NAME, 'phone').send_keys('0641234567')
        self.browser.find_element(By.NAME, 'card').send_keys('1111111111111111')
        self.browser.find_element(
            By.XPATH, '//div[@class="apply-form"]//button[@type="submit"]'
        ).click()

        self.wait.until(EC.text_to_be_present_in_element(
            (By.CLASS_NAME, 'form-message'), 'You have registered successfully!'
        ))

    def test_ajax_card_without_funds(self):
        """Invalid class: card 0000... — red message, no registration."""
        tournament = self._create_tournament()

        self._login()
        self.browser.get(self.live_server_url + URL_TOURNAMENTS)

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Apply")]'
        ).click()
        time.sleep(0.5)

        self.browser.find_element(By.NAME, 'phone').send_keys('0641234567')
        self.browser.find_element(By.NAME, 'card').send_keys('0000000000000000')
        self.browser.find_element(
            By.XPATH, '//div[@class="apply-form"]//button[@type="submit"]'
        ).click()

        self.wait.until(EC.text_to_be_present_in_element(
            (By.CLASS_NAME, 'form-message'), 'Insufficient funds.'
        ))
        self.assertFalse(Participation.objects.filter(idt=tournament).exists())

    def test_search_filter(self):
        """Valid class: JS search hides non-matching cards."""
        self._create_tournament(name='Summer tournament')
        self._create_tournament(name='Winter cup')

        self._login()
        self.browser.get(self.live_server_url + URL_TOURNAMENTS)

        self.browser.find_element(By.ID, 'searchTournament').send_keys('Winter')
        time.sleep(0.5)

        cards = self.browser.find_elements(By.CLASS_NAME, 'tournament-card')
        visible = [k for k in cards if k.is_displayed()]
        self.assertEqual(len(visible), 1)
        self.assertIn('Winter cup', visible[0].text)



# ============ 6. FOLLOWED TOURNAMENTS ============

class FollowedTournamentsSeleniumTest(BoardNetSeleniumBase):

    def test_display_only_followed(self):
        """Valid class: the followed organizer's tournament is visible, the unfollowed one's is not."""
        Follow.objects.create(idu=self.player, ido=self.organizer)
        self._create_tournament(name='Followed WD')

        org2_user = User.objects.create_user(username='org2', password='Test12345')
        org2_member = Member.objects.create(idu=org2_user)
        org2 = Organizer.objects.create(idu=org2_member)
        self._create_tournament(name='Unfollowed WD', organizer=org2)

        self._login()
        self.browser.get(self.live_server_url + URL_FOLLOWED_TOURNAMENTS)

        self.assertIn('Followed WD', self.browser.page_source)
        self.assertNotIn('Unfollowed WD', self.browser.page_source)

    def test_empty_state(self):
        """Boundary case: does not follow anyone — message about an empty list."""
        self._login()
        self.browser.get(self.live_server_url + URL_FOLLOWED_TOURNAMENTS)

        self.assertIn(
            'There are no upcoming tournaments from the organizers you follow.',
            self.browser.page_source
        )


# ============ 7. SEARCH ============

class SearchSeleniumTest(BoardNetSeleniumBase):

    def test_display_and_role_filter(self):
        """Valid class: display of users + JS filter by role."""
        self._login()
        self.browser.get(self.live_server_url + URL_SEARCH)

        self.assertIn('ana', self.browser.page_source)
        self.assertIn('zoran', self.browser.page_source)

        # filter organizers only
        Select(self.browser.find_element(By.ID, 'roleFilter')) \
            .select_by_value('organizer')
        time.sleep(0.5)

        cards = self.browser.find_elements(By.CLASS_NAME, 'user-card')
        visible = [k.text for k in cards if k.is_displayed()]
        self.assertTrue(any('zoran' in t for t in visible))
        self.assertFalse(any('ana' in t for t in visible))

    def test_click_on_profile(self):
        """Valid class: clicking Profile leads to otherProfile."""
        self._login()
        self.browser.get(self.live_server_url + URL_SEARCH)

        # the button on ana's card
        self.browser.find_element(
            By.XPATH, '//div[@class="user-card"][.//h3[text()="ana"]]//button'
        ).click()
        time.sleep(1)

        self.assertIn('ana', self.browser.page_source)
        self.assertIn(str(self.ana_player.pk), self.browser.current_url)


# ============ 8. GAME DETAILS ============

class GameDetailsSeleniumTest(BoardNetSeleniumBase):

    def _url(self):
        return self.live_server_url + f'/game/{self.game.idg}/'

    def test_display_and_add_to_list(self):
        """Valid class: details + clicking Add to wishlist changes the button."""
        self._login()
        self.browser.get(self._url())

        self.assertIn('Catan', self.browser.page_source)

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Add to wishlist")]'
        ).click()
        time.sleep(1)

        self.assertIn('Already in wishlist', self.browser.page_source)
        self.assertTrue(
            WishlistCollection.objects.filter(
                idu=self.member, idg=self.game, status='wishlist'
            ).exists()
        )

    def test_adding_review(self):
        """Valid class: a review submitted through the form is shown with its rating."""
        self._login()
        self.browser.get(self._url())

        Select(self.browser.find_element(By.ID, 'rating')).select_by_value('4')
        self.browser.find_element(By.ID, 'review').send_keys('WD test review')
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Post review")]'
        ).click()
        time.sleep(1)

        self.assertIn('WD test review', self.browser.page_source)
        self.assertIn('4 / 5', self.browser.page_source)


# ============ 9. OTHER PROFILE ============

class OtherProfileSeleniumTest(BoardNetSeleniumBase):

    def test_request_and_acceptance_e2e(self):
        """Valid class E2E: marko sends a request to nikola, nikola accepts."""
        # nikola — not a friend of marko
        nikola_user = User.objects.create_user(username='nikola', password='Test12345')
        nikola_member = Member.objects.create(idu=nikola_user)
        nikola_player = Player.objects.create(idu=nikola_member)

        # marko sends a request
        self._login('marko')
        self.browser.get(
            self.live_server_url + f'/other-profile/{nikola_player.pk}/'


        )
        self.browser.find_element(By.XPATH, '//button[@value="add"]').click()
        time.sleep(1)
        self.assertIn('Request sent', self.browser.page_source)

        # nikola accepts
        self._logout()
        self._login('nikola')
        self.browser.get(self.live_server_url + URL_FRIEND_REQUESTS)
        self.assertIn('marko', self.browser.page_source)
        self.browser.find_element(By.XPATH, '//button[@value="accept"]').click()
        time.sleep(1)

        self.assertTrue(
            Friendship.objects.filter(
                idu1_id__in=[self.player.pk, nikola_player.pk],
                idu2_id__in=[self.player.pk, nikola_player.pk],
            ).exists()
        )

    def test_follow_organizer(self):
        """Valid class: clicking Follow changes the button to Unfollow and creates a Follow."""
        self._login('marko')
        self.browser.get(
            self.live_server_url + f'/other-profile/{self.organizer.pk}/'
        )
        self.browser.find_element(By.XPATH, '//button[@value="follow"]').click()
        time.sleep(1)

        self.assertIn('Unfollow', self.browser.page_source)
        self.assertTrue(
            Follow.objects.filter(idu=self.player, ido=self.organizer).exists()
        )

    def test_stranger_privacy(self):
        """Invalid class: not a friend — collection hidden, message about adding."""
        nikola_user = User.objects.create_user(username='nikola', password='Test12345')
        nikola_member = Member.objects.create(idu=nikola_user)
        nikola_player = Player.objects.create(idu=nikola_member)
        WishlistCollection.objects.create(
            idu=nikola_member, idg=self.game, status='collection'
        )

        self._login('marko')
        self.browser.get(
            self.live_server_url + f'/other-profile/{nikola_player.pk}/'
        )

        self.assertIn('Add this player as a friend', self.browser.page_source)
        self.assertNotIn('Catan', self.browser.page_source)