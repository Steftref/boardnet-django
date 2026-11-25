from django.utils import timezone

from django.contrib.auth.models import User
from django.db import models
from django_cryptography.fields import encrypt

STATUS_TOURNAMENT = [
    ('active', 'Active'),
    ('canceled', 'Canceled'),
    ('finished', 'Finished'),
]

STATUS_LIST = [
    ('wishlist', 'Wishlist'),
    ('collection', 'Collection'),
]

STATUS_PARTICIPANT = [
    ('confirmed', 'Confirmed'),
    ('unconfirmed', 'Unconfirmed'),
]

STATUS_ORG_REQUEST = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

STATUS_FRIENDSHIP = [
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
]


class Game(models.Model):
    idg = models.AutoField(db_column='IdG', primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    # player_count = models.IntegerField(blank=True, null=True)
    min_players = models.IntegerField(null=False, blank=False)
    max_players = models.IntegerField(null=False, blank=False)
    # duration = models.IntegerField(blank=True, null=True)
    duration_min = models.IntegerField(null=False, blank=False)
    duration_max = models.IntegerField(null=False, blank=False)
    game_image = models.CharField(max_length=255, blank=True, null=True)
    min_age = models.IntegerField(blank=False, null=False)
    author = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'game'


class Category(models.Model):
    idc = models.AutoField(db_column='IdC', primary_key=True)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = True
        db_table = 'category'


class GameCategory(models.Model):
    # id = models.AutoField(primary_key=True)
    idg = models.ForeignKey(Game, on_delete=models.RESTRICT, db_column='IdG')
    idc = models.ForeignKey(Category, on_delete=models.RESTRICT, db_column='IdC')

    class Meta:
        managed = True
        db_table = 'game_category'
        constraints = [
            models.UniqueConstraint(
                fields=['idg', 'idc'],
                name='game_category_unique'
            )
        ]
        # unique_together = (('idg', 'idc'),)


class Member(models.Model):
    idu = models.OneToOneField(User, on_delete=models.CASCADE, db_column='IdU', primary_key=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'member'


class Player(models.Model):
    idu = models.OneToOneField(Member, on_delete=models.CASCADE, db_column='IdU', primary_key=True)

    class Meta:
        managed = True
        db_table = 'player'


class Organizer(models.Model):
    idu = models.OneToOneField(Member, on_delete=models.CASCADE, db_column='IdU', primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'organizer'


class WishlistCollection(models.Model):
    idu = models.ForeignKey(Member, on_delete=models.RESTRICT, db_column='IdU')
    idg = models.ForeignKey(Game, on_delete=models.RESTRICT, db_column='IdG')
    status = models.CharField(max_length=10, choices=STATUS_LIST)

    class Meta:
        managed = True
        db_table = 'wishlist_collection'
        constraints = [
            models.UniqueConstraint(
                fields=['idu', 'idg'],
                name='wishlist_collection_unique'
            )
        ]
        # unique_together = (('idu', 'idg'),)


class Notification(models.Model):
    idn = models.AutoField(db_column='IdN', primary_key=True)
    idu = models.ForeignKey(Member, on_delete=models.RESTRICT, db_column='IdU')
    message = models.TextField()
    date = models.DateTimeField()
    is_read = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'notification'

class Match(models.Model):
    idm = models.AutoField(db_column='IdM', primary_key=True)
    name = models.CharField(max_length=100,  null=False)
    game = models.ForeignKey(Game, on_delete=models.RESTRICT, db_column='game', null=False)
    date = models.DateTimeField(null=False)
    player_count = models.IntegerField(blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)
    winner = models.ForeignKey('Player', on_delete=models.SET_NULL, db_column='winner', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'game_match'


class MatchParticipant(models.Model):
    # id = models.AutoField(primary_key=True)
    idm = models.ForeignKey(Match, on_delete=models.RESTRICT, db_column='IdM')
    idu = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU')
    status = models.CharField(max_length=12, choices=STATUS_PARTICIPANT, default='unconfirmed')

    class Meta:
        managed = True
        db_table = 'match_participant'
        constraints = [
            models.UniqueConstraint(
                fields=['idm', 'idu'],
                name='match_participant_unique'
            )
        ]
        # unique_together = (('idm', 'idu'),)


class Follow(models.Model):
    # id = models.AutoField(primary_key=True)
    idu = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU')
    ido = models.ForeignKey(Organizer, on_delete=models.RESTRICT, db_column='IdO')

    class Meta:
        managed = True
        db_table = 'follow'
        constraints = [
            models.UniqueConstraint(
                fields=['idu', 'ido'],
                name='follow_unique'
            )
        ]
        # unique_together = (('idu', 'ido'),)


class Friendship(models.Model):
    # id = models.AutoField(primary_key=True)
    idu1 = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU1', related_name='friendships1')
    idu2 = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU2', related_name='friendships2')

    class Meta:
        managed = True
        db_table = 'friendship'
        constraints = [
            models.UniqueConstraint(
                fields=['idu1', 'idu2'],
                name='friendship_unique'
            )
        ]
        # unique_together = (('idu1', 'idu2'),)


class Review(models.Model):
    # id = models.AutoField(primary_key=True)
    idu = models.ForeignKey(Member, on_delete=models.RESTRICT, db_column='IdU')
    idg = models.ForeignKey(Game, on_delete=models.RESTRICT, db_column='IdG')
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    date = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'review'
        constraints = [
            models.UniqueConstraint(
                fields=['idu', 'idg'],
                name='review_unique'
            )
        ]
        # unique_together = (('idu', 'idg'),)


class Tournament(models.Model):
    idt = models.AutoField(db_column='IdT', primary_key=True)
    name = models.CharField(max_length=100)
    game = models.ForeignKey(Game, on_delete=models.RESTRICT, db_column='game')
    organizer = models.ForeignKey(Organizer, on_delete=models.RESTRICT, db_column='organizer')
    capacity = models.IntegerField()
    occupancy = models.IntegerField(default=0)
    date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True, null=True)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    prize = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=8, choices=STATUS_TOURNAMENT, default='active')
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'tournament'

    @property
    def is_open(self):
        return self.status =='active' and not self.date < timezone.now() and self.occupancy<self.capacity

    @property
    def updateTournamentBool(self):
        return self.status == 'active' and not self.date < timezone.now()

    @property
    def enterResultsBool(self):
        return self.date < timezone.now() and self.status == 'active'


class TournamentResult(models.Model):
    # id = models.AutoField(primary_key=True)
    idt = models.ForeignKey(Tournament, on_delete=models.RESTRICT, db_column='IdT')
    idu = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU')
    position = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'tournament_result'
        constraints = [
            models.UniqueConstraint(
                fields=['idt', 'idu'],
                name='unique_player_in_tournament'
            ),
            models.UniqueConstraint(
                fields=['idt', 'position'],
                name='unique_position_in_tournament'
            ),
        ]
        # unique_together = (('idt', 'idu'), ('idt', 'position'),)


class Participation(models.Model):
    # id = models.AutoField(primary_key=True)
    idt = models.ForeignKey(Tournament, on_delete=models.RESTRICT, db_column='IdT')
    idu = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU')
    phone_number = models.CharField(max_length=30)
    card_number = encrypt(models.CharField(max_length=50))

    class Meta:
        managed = True
        db_table = 'participation'
        constraints = [
            models.UniqueConstraint(
                fields=['idt', 'idu'],
                name='participation_unique'
            )
        ]
        # unique_together = (('idt', 'idu'),)


class OrganizerRequest(models.Model):
    idr = models.AutoField(db_column='IdR', primary_key=True)
    idu = models.OneToOneField(Organizer, on_delete=models.RESTRICT, db_column='IdU')
    status = models.CharField(max_length=11, choices=STATUS_ORG_REQUEST, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    request_date = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'organizer_request'


class FriendRequest(models.Model):
    # id = models.AutoField(primary_key=True)
    idu1 = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU1', related_name='sent_requests')
    idu2 = models.ForeignKey(Player, on_delete=models.RESTRICT, db_column='IdU2', related_name='received_requests')
    status = models.CharField(max_length=11, choices=STATUS_FRIENDSHIP)

    class Meta:
        managed = True
        db_table = 'friend_request'
        constraints = [
            models.UniqueConstraint(
                fields=['idu1', 'idu2'],
                name='friend_request_unique'
            )
        ]
        # unique_together = (('idu1', 'idu2'),)