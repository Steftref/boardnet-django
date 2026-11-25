import json
import logging
import re
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Avg, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

#MODELS

from app.models import Game, Friendship, Member, \
    Match, MatchParticipant, WishlistCollection, \
    TournamentResult, FriendRequest, Participation, Tournament, Follow, \
    Organizer, OrganizerRequest, Category, Review, \
    GameCategory, Player, Notification

logger = logging.getLogger(__name__)

# the largest value that fits into an integer column
MAX_INT = 2147483647

# HELPERS

def is_admin(user):
    """Checks whether the user is an admin (staff account)."""
    return user.is_staff

def is_organizer(user):
    """Checks whether the user has an approved organizer account."""
    return Organizer.objects.filter(idu=user.id, organizerrequest__status='approved').exists()

def is_active(user):
    """Checks whether the user account is active."""
    return user.is_active

def role_home(user):
    """Returns the name of the home page that belongs to the user's role."""
    if is_admin(user):
        return 'homeAdmin'
    if is_organizer(user):
        return 'homeOrganizer'
    if Player.objects.filter(idu=user.id).exists():
        return 'home'
    return 'loginRegister'

def role_required(model):
    """
    Decorator — lets in only logged-in users that have a record in the given model
    (Member, Player); the others are redirected to the home page of their own role.
    """
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not model.objects.filter(pk=request.user.id).exists():
                return redirect(role_home(request.user))
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator

member_required = role_required(Member)
player_required = role_required(Player)

def organizer_required(view):
    """Decorator — lets in only active users with an approved organizer account."""
    view = user_passes_test(is_active, login_url='login')(view)
    view = user_passes_test(is_organizer, login_url='loginRegister')(view)
    return login_required(view)

def to_int(value):
    """Converts a value from a request to a positive integer, or returns None if it is not one."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 < number <= MAX_INT else None

def confirmed_matches():
    """Matches whose result was not left unconfirmed by any participant."""
    return Match.objects.exclude(matchparticipant__status='unconfirmed')

def are_friends_query(player_a, player_b):
    """Friendship between two players, regardless of the direction it is stored in."""
    return Friendship.objects.filter(
        Q(idu1=player_a, idu2=player_b) |
        Q(idu1=player_b, idu2=player_a)
    )

def accept_friend_request(sender_id, recipient_id):
    """
    Accepts a pending friend request — deletes the request (and a possible one in the
    opposite direction), creates the friendship only once and notifies both players.
    """
    with transaction.atomic():
        deleted, _ = FriendRequest.objects.filter(
            idu1_id=sender_id, idu2_id=recipient_id, status='pending'
        ).delete()

        if not deleted or sender_id == recipient_id:
            return

        FriendRequest.objects.filter(
            idu1_id=recipient_id, idu2_id=sender_id, status='pending'
        ).delete()

        if are_friends_query(sender_id, recipient_id).exists():
            return

        a, b = sorted([sender_id, recipient_id])
        Friendship.objects.create(idu1_id=a, idu2_id=b)

        sender = User.objects.get(pk=sender_id)
        recipient = User.objects.get(pk=recipient_id)
        for user, friend in ((sender, recipient), (recipient, sender)):
            Notification.objects.create(
                idu_id=user.pk,
                message=f"You are now friends with {friend.username}.",
                date=timezone.now(),
                is_read=False,
            )

def reject_friend_request(sender_id, recipient_id):
    """Rejects a pending friend request; the sender can send a new one later."""
    FriendRequest.objects.filter(
        idu1_id=sender_id, idu2_id=recipient_id, status='pending'
    ).update(status='rejected')

def register_for_tournament(request, player):
    """
    AJAX tournament registration — validates the phone and the test card, creates a
    Participation and updates the occupancy. The tournament row is locked so that two
    players cannot take the same last spot.
    """
    phone = request.POST.get("phone", "").replace(" ", "")
    card = request.POST.get("card", "").replace(" ", "")

    def error(text):
        return JsonResponse({"success": False, "message": text})

    tournament_id = to_int(request.POST.get("tournament_id"))
    if not Tournament.objects.filter(idt=tournament_id).exists():
        return error("The tournament does not exist.")

    if not re.match(r'^[0-9]{6,15}$', phone):
        return error("Invalid phone number.")

    if not re.match(r'^\d{16}$', card):
        return error("The card must have 16 digits.")

    if card == "0000000000000000":
        return error("Insufficient funds.")

    if card != "1111111111111111":
        return error("Invalid card.")

    with transaction.atomic():
        tournament = Tournament.objects.select_for_update().get(idt=tournament_id)

        if not tournament.is_open or Participation.objects.filter(idt=tournament, idu=player).exists():
            return error("Registration error.")

        Participation.objects.create(
            idt=tournament,
            idu=player,
            phone_number=phone,
            card_number=card
        )
        tournament.occupancy = Participation.objects.filter(idt=tournament).count()
        tournament.save()

    return JsonResponse({
        "success": True,
        "message": "You have registered successfully!"
    })

# HOME PAGES

# Katarina
@player_required
def home(request):
    """
    Player home page — builds the leaderboard (logged-in user + friends) by number of
    confirmed wins and shows upcoming tournaments of the organizers the player follows.
    """

    logged_in_id = request.user.id
    relations = Friendship.objects.filter(
        Q(idu1_id=logged_in_id) | Q(idu2_id=logged_in_id)
    ).values('idu1_id', 'idu2_id')

    friends = []

    for relation in relations:
        if relation['idu1_id'] == logged_in_id:
            friends.append(relation['idu2_id'])
        else:
            friends.append(relation['idu1_id'])

    leaderboard_players = friends + [logged_in_id]
    matches = confirmed_matches().filter(
        winner_id__in=leaderboard_players
    )

    leaderboard = {}

    for player_id in leaderboard_players:
        player = Player.objects.get(pk=player_id)
        leaderboard[player] = 0

    for p in matches:
        player = p.winner
        leaderboard[player] += 1

    # sort by number of wins
    leaderboard = sorted(
        leaderboard.items(),
        key=lambda x: x[1],
        reverse=True
    )

    organizers = Follow.objects.filter(
        idu=logged_in_id
    ).values_list('ido_id', flat=True)

    tournaments = Tournament.objects.filter(
        organizer__in=organizers,
        date__gt=timezone.now(),
    ).order_by('date')[:4]

    context = {
        'leaderboard': leaderboard,
        'tournaments': tournaments,
        'logged_in_id' : int(logged_in_id)
    }

    return render(request, 'app/home.html', context)

# Katarina
@login_required
@user_passes_test(is_admin, login_url='loginRegister')
def homeAdmin(request):
    """
    Admin home page — pending requests for organizer accounts, all tournaments
    and basic statistics (number of requests, users and active tournaments).
    """

    statuses = Tournament.objects.values_list('status', flat=True).distinct()

    organizer_requests = (
        OrganizerRequest.objects
        .filter(status='pending')
        .select_related('idu__idu')
        .order_by('-request_date')
    )

    tournaments = (
        Tournament.objects
        .select_related('game', 'organizer__idu__idu')
        .order_by('date')
    )

    context = {
        "request_count": organizer_requests.count(),
        "user_count": Member.objects.count(),
        "active_tournament_count": Tournament.objects.filter(status='active').count(),

        "organizer_requests": organizer_requests,
        "tournaments": tournaments,
        "statuses": statuses,
    }

    return render(request, "app/homeAdmin.html", context)

@login_required
@user_passes_test(is_admin)
def cancel_tournament_admin(request, idt):
    """
    Admin cancels an active tournament — notifies all registered players (cancelTournament)
    and additionally sends a notification to the tournament organizer.
    """
    if request.method == "POST":
        tournament = get_object_or_404(Tournament, idt=idt)

        if tournament.status != 'active':
            return redirect('homeAdmin')

        # notifies the players and changes the status
        cancelTournament(idt)

        # additionally notifies the organizer
        Notification.objects.create(
            idu=tournament.organizer.idu,
            message=f'Tournament "{tournament.name}" was canceled by an admin.',
            date=timezone.now()
        )

    return redirect('homeAdmin')

@login_required
@user_passes_test(is_admin)
@require_POST
def approve_request(request, idr):
    """Approves a pending request for an organizer account."""
    request_obj = get_object_or_404(OrganizerRequest, idr=idr)

    if request_obj.status == 'pending':
        request_obj.status = 'approved'
        request_obj.save()

    return redirect('homeAdmin')

@login_required
@user_passes_test(is_admin)
@require_POST
def reject_request(request, idr):
    """Rejects a pending request for an organizer account and stores the rejection reason."""
    request_obj = get_object_or_404(OrganizerRequest, idr=idr)

    if request_obj.status == 'pending':
        request_obj.status = 'rejected'
        request_obj.rejection_reason = request.POST.get('reason')
        request_obj.save()

    return redirect('homeAdmin')

# Katarina
@organizer_required
def homeOrganizer(request):
    """
    Organizer home page — their tournaments with the number of registered players,
    statistics (active/finished/registered), sections for the game collection, tournament creation and an overview of their tournaments.
    """
    organizer = Organizer.objects.get(idu_id = request.user.id)

    create_form_data = request.session.pop('create_tournament_data', {})

    tournaments = Tournament.objects.filter(organizer=organizer)
    for t in tournaments:
        t.registered = Participation.objects.filter(idt = t).count()

    active_count = tournaments.filter(status='active').count()

    finished_count = tournaments.filter(status = 'finished').count()

    registered_count = Participation.objects.filter(
        idt__organizer=organizer
    ).count()

    list_entries = WishlistCollection.objects.filter(
        idu__idu=request.user,
        status='collection'
    ).select_related('idg')

    games = [item.idg for item in list_entries]

    for game in games:
        categories = GameCategory.objects.filter(
            idg=game.idg
        ).select_related('idc')

        game.categories = [k.idc.name for k in categories]

        if game.categories:
            game.category = game.categories[0]
        else:
            game.category = "Other"

    all_categories = Category.objects.all()

    tournament_messages = defaultdict(list)
    creation_messages = []
    profile_messages = []
    other_messages = []

    for message in get_messages(request):
        tags = message.extra_tags.split() if message.extra_tags else []

        tournament_tag = next((t for t in tags if t.startswith("tournament-")), None)

        if tournament_tag:
            try:
                tournament_id = int(tournament_tag.replace("tournament-", ""))
                tournament_messages[tournament_id].append(message)
            except ValueError:
                other_messages.append(message)
        elif "section-creation" in tags:
            creation_messages.append(message)
        elif "section-profile" in tags:
            profile_messages.append(message)
        else:
            other_messages.append(message)

    for tournament in tournaments:
        tournament.messages = tournament_messages.get(tournament.idt, [])

    has_tournament_message = bool(tournament_messages)
    has_creation_message = bool(creation_messages)
    has_profile_message = bool(profile_messages)

    context = {
        'tournaments': tournaments,
        'active_count': active_count,
        'finished_count': finished_count,
        'registered_count': registered_count,
        'games': games,
        'all_categories': all_categories,
        'organizer': organizer,
        'creation_messages': creation_messages,
        'profile_messages': profile_messages,
        'other_messages': other_messages,
        'has_tournament_message': has_tournament_message,
        'has_creation_message': has_creation_message,
        'has_profile_message': has_profile_message,
        'create_form_data': create_form_data,
    }

    return render(request, 'app/homeOrganizer.html', context)

@organizer_required
def editOrganizerProfile(request):
    """Updates the organizer profile — profile picture and/or description."""
    if request.method == "POST":
        member = request.user.member
        organizer = member.organizer

        new_image = request.FILES.get("profile_picture")
        new_description = request.POST.get("description")

        if new_image:
            member.profile_picture = new_image

        if new_description is not None:
            organizer.description = new_description.strip() or None

        member.save()
        organizer.save()

        messages.success(request, "Profile updated successfully.", extra_tags="section-profile")

    return redirect('homeOrganizer')

@organizer_required
def create_tournament(request):
    """
    Creates a new tournament — checks that all fields are filled in correctly.
    """
    if request.method != "POST":
        return redirect('homeOrganizer')

    organizer = get_object_or_404(Organizer, idu=request.user.id)

    name = request.POST.get('name')
    game = request.POST.get('game')
    date = request.POST.get('date')
    start_time = request.POST.get('start_time')
    capacity = request.POST.get('capacity')
    location = request.POST.get('location')
    entry_fee = request.POST.get('entry_fee')
    prize = request.POST.get('prize')

    if not all([name, game, date, start_time, capacity, location, entry_fee, prize]):
        messages.error(request, "Fill in all fields.", extra_tags="section-creation")
        request.session['create_tournament_data'] = request.POST.dict()
        return redirect('homeOrganizer')

    try:
        capacity = to_int(capacity)
        if capacity is None:
            raise ValueError
        game = to_int(game)
        if not Game.objects.filter(pk=game).exists():
            raise ValueError
        if len(name) > 100 or len(location) > 255 or len(prize) > 255:
            raise ValueError
        date_time = datetime.strptime(
            f"{date} {start_time}",
            "%Y-%m-%d %H:%M"
        )
        date_time = timezone.make_aware(date_time)
        entry_fee = Decimal(entry_fee)
        if not entry_fee.is_finite() or not 0 <= entry_fee < 10 ** 8:
            raise InvalidOperation
        if date_time < timezone.now():
            raise ValueError
    except (ValueError, OverflowError, InvalidOperation):
        messages.error(request, "Fill in the fields correctly.", extra_tags="section-creation")
        request.session['create_tournament_data'] = request.POST.dict()
        return redirect('homeOrganizer')

    Tournament.objects.create(
        name=name,
        game_id=game,
        organizer=organizer,
        capacity=capacity,
        occupancy=0,
        date=date_time,
        location=location,
        description=request.POST.get('description'),
        entry_fee=entry_fee,
        prize=prize,
        status='active',
    )
    messages.success(request, "The tournament was created successfully.", extra_tags="section-creation")
    return redirect('homeOrganizer')

@organizer_required
def cancel_tournament_view(request, idt):
    """Organizer cancels their own tournament — allowed only for active tournaments."""
    organizer = get_object_or_404(Organizer, idu=request.user.id)
    tournament = get_object_or_404(
        Tournament,
        idt=idt,
        organizer=organizer
    )

    if request.method != "POST":
        return redirect("homeOrganizer")

    if tournament.status != "active":
        messages.error(
            request,
            "The tournament cannot be canceled.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    cancelTournament(tournament.idt)

    messages.success(
        request,
        "The tournament was canceled successfully.",
        extra_tags=f"tournament-{tournament.idt}"
    )
    return redirect("homeOrganizer")


@organizer_required
def save_results(request, idt):
    """
    Saves the tournament results (top three places) — validates the order of places,
    duplicates and that the selected players are registered, then in a transaction saves
    the results and marks the tournament as finished.
    """
    organizer = get_object_or_404(Organizer, idu=request.user.id)
    tournament = get_object_or_404(Tournament, idt=idt, organizer=organizer)

    if request.method != "POST":
        return redirect("homeOrganizer")

    if not tournament.enterResultsBool:
        messages.error(
            request,
            "Results cannot be entered yet.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    first_place = request.POST.get("first_place")
    second_place = request.POST.get("second_place")
    third_place = request.POST.get("third_place")

    if second_place and not first_place:
        messages.error(
            request,
            "You cannot enter second place without first place.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    if third_place and (not first_place or not second_place):
        messages.error(
            request,
            "You cannot enter third place without first and second place.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    selected = [player for player in [first_place, second_place, third_place] if player]

    if len(selected) != len(set(selected)):
        messages.error(
            request,
            "The same player cannot take more than one place.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    registered_players = set(
        Participation.objects.filter(idt=tournament)
        .values_list("idu_id", flat=True)
    )

    if any(to_int(player_id) not in registered_players for player_id in selected):
        messages.error(
            request,
            "You can only select players registered for this tournament.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    if registered_players and not first_place:
        messages.error(
            request,
            "You must enter at least the first place.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    with transaction.atomic():
        TournamentResult.objects.filter(idt=tournament).delete()

        for position, player_id in enumerate([first_place, second_place, third_place], start=1):
            if player_id:
                TournamentResult.objects.create(
                    idt=tournament,
                    idu_id=player_id,
                    position=position
                )

        tournament.status = "finished"
        tournament.save()

    messages.success(
        request,
        "Results saved successfully.",
        extra_tags=f"tournament-{tournament.idt}"
    )
    return redirect("homeOrganizer")


@organizer_required
def edit_tournament(request, idt):
    """
    Changes the date/time and capacity of a tournament — validates the input, that the date is
    not in the past and that the capacity is not below the number of registered players; if the
    date has changed, sends notifications to all participants.
    """
    organizer = get_object_or_404(Organizer, idu=request.user.id)
    tournament = get_object_or_404(Tournament, idt=idt, organizer=organizer)

    if request.method != "POST":
        return redirect("homeOrganizer")

    if not tournament.updateTournamentBool:
        messages.error(
            request,
            "The tournament can no longer be changed.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    date = request.POST.get("date")
    start_time = request.POST.get("start_time")
    capacity = request.POST.get("capacity")

    try:
        new_date = timezone.make_aware(
            datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        )
    except (TypeError, ValueError):
        messages.error(
            request,
            "Enter a valid date and time.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    if new_date < timezone.now():
        messages.error(
            request,
            "The tournament date and time cannot be in the past.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    new_capacity = to_int(capacity)

    if new_capacity is None:
        messages.error(
            request,
            "Capacity must be a positive integer.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    registered_count = Participation.objects.filter(idt=tournament).count()

    if new_capacity < registered_count:
        messages.error(
            request,
            "Capacity cannot be less than the number of registered players.",
            extra_tags=f"tournament-{tournament.idt}"
        )
        return redirect("homeOrganizer")

    date_changed = (
        new_date != tournament.date.replace(second=0, microsecond=0)
    )

    tournament.date = new_date
    tournament.capacity = new_capacity
    tournament.save()

    if date_changed:
        participants = Participation.objects.filter(idt=tournament).select_related("idu")

        Notification.objects.bulk_create([
            Notification(
                idu=u.idu.idu,
                message=f'The schedule of tournament "{tournament.name}" has been changed.',
                date=timezone.now(),
            )
            for u in participants
        ])

    messages.success(
        request,
        "Changes saved successfully.",
        extra_tags=f"tournament-{tournament.idt}"
    )
    return redirect("homeOrganizer")

@organizer_required
def remove_game_from_collection(request, idg):
    """Removes a game from the organizer's collection and returns to their home page."""
    if request.method == "POST":
        WishlistCollection.objects.filter(
            idu__idu=request.user,
            idg_id=idg,
            status='collection'
        ).delete()

    return redirect('homeOrganizer')

# TOURNAMENTS / SEARCH

# Katarina
@player_required
def followedTournaments(request):
    """
    POST: AJAX tournament registration (register_for_tournament).
    GET:  upcoming tournaments of the organizers the player follows + values for
          the filters (games, locations, statuses) and already existing registrations.
    """
    player = Player.objects.get(idu=request.user.id)

    if request.method == "POST":
        return register_for_tournament(request, player)

    organizers = Follow.objects.filter(
        idu=player
    ).values_list('ido_id', flat=True)

    registrations = Participation.objects.filter(idu=player).values_list('idt_id', flat=True)

    tournaments = Tournament.objects.filter(
        organizer_id__in=organizers,
        date__gt=timezone.now(),
    ).select_related('game', 'organizer__idu__idu').order_by('date')

    games = tournaments.order_by().values_list('game__name', flat=True).distinct()
    locations = tournaments.order_by().values_list('location', flat=True).distinct()
    statuses = tournaments.order_by().values_list('status', flat=True).distinct()

    context = {
        'tournaments': tournaments,
        'registrations': registrations,
        'games': games,
        'locations': locations,
        'statuses': statuses
    }

    return render(request, 'app/followedTournaments.html', context)

# Katarina
@login_required
def search(request):
    """
    User search — list of all players (with number of wins) and approved
    organizers (with number of tournaments), sorted by username.
    """
    members = []
    logged_in_id = request.user.id
    players = Player.objects.exclude(idu = logged_in_id)

    for player in players:
        win_count = confirmed_matches().filter(
            winner_id=player.idu_id
        ).count()

        members.append({
            'id' : player.idu_id,
            'username' : player.idu.idu.username,
            'type' : 'player',
            'win_count' : win_count,
        })

    organizers = Organizer.objects.filter(
        organizerrequest__status='approved'
    )

    for organizer in organizers:
        tournament_count = Tournament.objects.filter(
            organizer_id=organizer.idu_id
        ).count()

        members.append({
            'id': organizer.idu_id,
            'username': organizer.idu.idu.username,
            'type': 'organizer',
            'tournament_count': tournament_count,
        })

    members.sort(key = lambda k: k['username'].lower())

    context = {
        'members': members,
    }

    return render(request, 'app/search.html', context)

# Katarina
@player_required
def tournaments(request):
    """
    Overview of all tournaments with values for the filters.
    POST: AJAX tournament registration (register_for_tournament).
    """
    player = Player.objects.get(idu=request.user.id)

    if request.method == "POST":
        return register_for_tournament(request, player)

    games = Tournament.objects.values_list('game__name', flat=True).distinct()
    locations = Tournament.objects.values_list('location', flat=True).distinct()
    statuses = Tournament.objects.values_list('status', flat=True).distinct()
    registrations = Participation.objects.filter(idu=player).values_list('idt_id', flat=True)
    tournaments = Tournament.objects.select_related('game', 'organizer')

    return render(request, 'app/tournaments.html', {'tournaments': tournaments, 'registrations': registrations, 'games': games, 'locations': locations, 'statuses': statuses})

# Katarina
def loginRegister(request):
    """Shows the login and registration page."""
    return render(request, 'app/loginRegister.html')


def login_view(request):
    """
    User login — checks the credentials and whether the account is active, then
    redirects to the admin/organizer/player home page. An organizer is let in only
    if their request is approved (pending/rejected returns an error).
    """
    if request.method != 'POST':
        return redirect('loginRegister')

    username = request.POST.get('username')
    password = request.POST.get('password')

    if not username or not password:
        return render(request, 'app/loginRegister.html', {
            "error": "You must enter a username and password"
        })

    user_obj = User.objects.filter(username=username).first()

    if user_obj and not user_obj.is_active and user_obj.check_password(password):
        return render(request, 'app/loginRegister.html', {
            "error": "Your profile has been deactivated"
        })

    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, 'app/loginRegister.html', {
            "error": "Incorrect username or password"
        })

    if user.is_superuser:
        login(request, user)
        return redirect('homeAdmin')

    org = Organizer.objects.filter(idu__idu=user.id).select_related('idu').first()

    if org:
        request_obj = OrganizerRequest.objects.filter(idu=org).first()

        if not request_obj:
            return render(request, 'app/loginRegister.html', {
                "error": "Error: the organizer account is not valid"
            })

        if request_obj.status == 'pending':
            return render(request, 'app/loginRegister.html', {
                "error": "Your request for an organizer account has not been approved yet"
            })

        if request_obj.status == 'rejected':
            return render(request, 'app/loginRegister.html', {
                "error": f"Request rejected: {request_obj.rejection_reason or ''}"
            })

        if request_obj.status != 'approved':
            return render(request, 'app/loginRegister.html', {
                "error": "The organizer account is not active"
            })

        login(request, user)
        return redirect('homeOrganizer')

    login(request, user)
    return redirect('home')


def register(request):
    """
    Registration — validates the input (password, taken email/username), in a
    transaction creates User + Member, then a Player (with automatic login)
    or an Organizer with a pending request.
    """
    if request.method != 'POST':
        return redirect('loginRegister')

    username = request.POST.get('username')
    email = request.POST.get('email')
    password1 = request.POST.get('password1')
    password2 = request.POST.get('password2')

    def error(text):
        return render(request, 'app/loginRegister.html', {
            "error": text,
            "active_tab": "register"
        })

    if not username or not email or not password1 or not password2:
        return error("All required fields must be filled in")

    if password1 != password2:
        return error("Passwords do not match")

    # an account that already has an organizer request gets a specific message,
    # no matter whether it is found by the username or by the email
    for existing_user in User.objects.filter(Q(username=username) | Q(email=email)):
        request_obj = OrganizerRequest.objects.filter(idu__idu__idu=existing_user).first()

        if request_obj is None:
            continue

        if request_obj.status == 'pending':
            return error("You have already sent an organizer request. Please wait for approval.")

        if request_obj.status == 'rejected':
            return error(f"Your previous request was rejected. Reason: {request_obj.rejection_reason or ''}")

        if request_obj.status == 'approved':
            return error("You already have an organizer account.")

    if User.objects.filter(email=email).exists():
        return error("Email is already in use")

    if User.objects.filter(username=username).exists():
        return error("Username already exists")

    new_user = User(username=username, email=email)

    try:
        new_user.full_clean(exclude=['password'])
    except ValidationError:
        return error("Enter a valid username and email")

    try:
        validate_password(password1, user=new_user)
    except ValidationError as e:
        return error(" ".join(e.messages))

    try:
        with transaction.atomic():

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )

            member = Member.objects.create(idu=user)

            if 'organizer' in request.POST:
                organizer = Organizer.objects.create(idu=member)

                OrganizerRequest.objects.create(
                    idu=organizer,
                    status='pending',
                    request_date=timezone.now()
                )

                return render(request, 'app/loginRegister.html', {
                    "message": "Organizer request sent. Please wait for approval.",
                    "active_tab": "register"
                })

            else:
                Player.objects.create(idu=member)
                login(request, user)
                return redirect('home')

    except IntegrityError:
        return error("An error occurred during registration. Please try again.")

def logout_view(request):
    """Logs the user out and returns to the login page."""
    logout(request)
    return redirect('loginRegister')

# GAMES

# Katarina
@member_required
def games(request):
    """
    Catalog of all games — average rating, categories and (for an organizer)
    whether the game is in the collection; the base template depends on the user's role.
    """

    member = Member.objects.get(idu=request.user.id)
    is_organizer = Organizer.objects.filter(idu=member).exists()

    games = Game.objects.all()

    for game in games:
        average = Review.objects.filter(idg=game.idg).aggregate(Avg('rating'))
        game.rating = float(round(average['rating__avg'], 1)) if average['rating__avg'] else 0

        categories = GameCategory.objects.filter(idg=game.idg).select_related('idc')
        game.categories = [k.idc.name for k in categories]
        game.category = game.categories[0] if game.categories else 'Other'

        if is_organizer:
            game.in_collection = WishlistCollection.objects.filter(
                idu=member,
                idg=game,
                status='collection'
            ).exists()

    games = sorted(games, key=lambda x: x.name.lower())
    all_categories = Category.objects.all().order_by('name')

    base_template = 'app/baseOrganizer.html' if is_organizer else 'app/baseUser.html'

    return render(request, 'app/games.html', {
        'games': games,
        'all_categories': all_categories,
        'base_template': base_template,
        'is_organizer': is_organizer
    })


# Katarina
@member_required
def gameDetails(request, idg):
    """
    Details of a single game — categories, reviews with the average rating and the game's
    status in the wishlist/collection of the logged-in user.
    """

    game = get_object_or_404(Game, idg=idg)

    is_organizer = False
    base_template = 'app/baseUser.html'   # default

    member = None

    if request.user.is_authenticated:
        member = Member.objects.get(idu=request.user.id)

        if Organizer.objects.filter(idu=request.user.id).exists():
            is_organizer = True
            base_template = 'app/baseOrganizer.html'

    categories = GameCategory.objects.filter(idg=game).select_related('idc')

    reviews = Review.objects.filter(idg=game).select_related('idu__idu')

    if reviews.exists():
        avg_rating = sum(r.rating for r in reviews) / reviews.count()
    else:
        avg_rating = None

    list_entry = None

    if member:
        list_entry = WishlistCollection.objects.filter(
            idu=member,
            idg=game
        ).first()

    context = {
        'game': game,
        'categories': categories,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'list_entry': list_entry,
        'is_organizer': is_organizer,
        'base_template': base_template,
    }

    return render(request, 'app/gameDetails.html', context)


@member_required
def add_to_list(request, idg):
    """Adds a game to the wishlist or collection, if it is not already in either of them."""

    if request.method != "POST":
        return redirect("game_details", idg=idg)

    member = Member.objects.get(idu=request.user.id)
    game = get_object_or_404(Game, idg=idg)

    status = request.POST.get('status')  # 'wishlist' or 'collection'

    if status not in ['wishlist', 'collection']:
        return redirect("game_details", idg=idg)

    WishlistCollection.objects.get_or_create(
        idu=member,
        idg=game,
        defaults={'status': status}
    )
    return redirect("game_details", idg=idg)


@member_required
def add_review(request, idg):
    """Creates or updates the user's review (rating 1-5 + text) for the given game."""
    if request.method != "POST":
        return redirect("game_details", idg=idg)

    game = get_object_or_404(Game, idg=idg)
    rating = to_int(request.POST.get("rating"))

    if rating is None or rating > 5:
        messages.error(request, "The rating must be between 1 and 5.")
        return redirect("game_details", idg=idg)

    Review.objects.update_or_create(
        idu=Member.objects.get(idu=request.user.id),
        idg=game,
        defaults={
            "rating": rating,
            "comment": request.POST.get("comment"),
            "date": timezone.now()
        }
    )

    return redirect("game_details", idg=idg)

# PROFILE / USER


def detailed_statistics(player_id):
    """
    Detailed player statistics; counts only matches in which
    all participants have confirmed their participation.
    """

    # Find the matches the player took part in
    my_matches = MatchParticipant.objects.filter(
        idu=player_id
    ).select_related('idm', 'idm__game')

    # Keep only the matches in which ALL participants confirmed their participation
    confirmed_matches = []

    for u in my_matches:
        p = u.idm

        confirmed_by_all = not MatchParticipant.objects.filter(
            idm=p
        ).exclude(status='confirmed').exists()

        if confirmed_by_all:
            confirmed_matches.append(p)

    total = len(confirmed_matches)

    wins = 0
    losses = 0
    draws = 0
    game_counter = {}

    # Data for the longest winning streak
    matches_with_date = []

    for p in confirmed_matches:

        # Count the games
        game_name = p.game.name
        game_counter[game_name] = game_counter.get(game_name, 0) + 1

        # Wins, losses and draws
        if p.winner is None:
            draws += 1
            result = 'draw'

        elif p.winner_id == player_id:
            wins += 1
            result = 'win'

        else:
            losses += 1
            result = 'loss'

        matches_with_date.append((p.date, result))

    # Win percentage
    win_rate = round(wins / total * 100) if total > 0 else 0

    # Most played game
    if game_counter:
        most_played = max(game_counter, key=game_counter.get)
    else:
        most_played = '—'

    # Longest winning streak
    matches_with_date.sort()

    longest = 0
    current = 0

    for date, result in matches_with_date:
        if result == 'win':
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    # Number of matches per game category
    category_counter = {}

    for p in confirmed_matches:
        category = GameCategory.objects.filter(
            idg=p.game.idg
        ).first()

        category_name = category.idc.name if category else 'Other'

        category_counter[category_name] = (
            category_counter.get(category_name, 0) + 1
        )

    return {
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'win_rate': win_rate,
        'most_played': most_played,
        'streak': longest,
        'total': total,
        'category_names': list(category_counter.keys()),
        'category_counts': list(category_counter.values()),
    }


def calculate_statistics(player_id):
    """
    Basic player statistics; counts only matches in which
    all participants have confirmed their participation.
    """

    # Find the matches the player took part in
    my_matches = MatchParticipant.objects.filter(
        idu=player_id
    )

    # Keep only the matches that all participants confirmed
    confirmed_matches = []

    for u in my_matches:
        p = u.idm

        confirmed_by_all = not MatchParticipant.objects.filter(
            idm=p
        ).exclude(status='confirmed').exists()

        if confirmed_by_all:
            confirmed_matches.append(p.pk)

    # Number of confirmed matches
    matches = len(confirmed_matches)

    # Number of wins in confirmed matches
    wins = Match.objects.filter(
        pk__in=confirmed_matches,
        winner=player_id
    ).count()

    # Win percentage
    if matches > 0:
        win_rate = round(wins / matches * 100)
    else:
        win_rate = 0

    return {
        'wins': wins,
        'matches': matches,
        'win_rate': win_rate
    }


@member_required
def changeProfilePicture(request):
    """Updates the player's profile picture."""
    if request.method == "POST":
        member = Member.objects.get(idu=request.user.id)
        new_image = request.FILES.get("profile_picture")

        if new_image:
            member.profile_picture = new_image
            member.save()
            messages.success(request, "Profile picture changed successfully.")
        else:
            messages.error(request, "You did not select a picture.")

    return redirect('profile')

# Stefana
@player_required
@never_cache
def profile(request):
    """
    Profile of the logged-in player — statistics (basic and detailed), wishlist,
    collection, tournament participations (position/status) and played matches with
    confirmation statuses. Other roles are redirected to their own home page.
    Uses @never_cache so that profile data is not cached in the browser.
    """
    logged_in_id = request.user.id
    member = Member.objects.get(idu=logged_in_id)

    stat = calculate_statistics(logged_in_id)
    detailed_stats = detailed_statistics(logged_in_id)
    wishlist = WishlistCollection.objects.filter(
        idu=logged_in_id, status='wishlist'
    )[:3]
    collection = WishlistCollection.objects.filter(
        idu=logged_in_id, status='collection'
    )[:3]

    results = TournamentResult.objects.filter(idu=logged_in_id)
    positions = {r.idt_id: r.position for r in results}

    tournaments = []

    participations = Participation.objects.filter(idu=logged_in_id).select_related('idt')

    for u in participations:
        if u.idt_id in positions:
            tournaments.append({'name': u.idt.name, 'position': str(positions[u.idt_id]) + '. place'})
        elif u.idt.status == 'finished':
            tournaments.append({'name': u.idt.name, 'position': 'participated'})
        elif u.idt.status == 'active':
            tournaments.append({'name': u.idt.name, 'position': 'registered'})

    participations = (MatchParticipant.objects
              .filter(idu=logged_in_id)
              .select_related('idm', 'idm__winner'))

    matches = []

    for u in participations:
        p = u.idm

        winner_name = p.winner.idu.idu.username if p.winner else None

        # all participants of that match
        all_participants = (MatchParticipant.objects
               .filter(idm=p.idm)
               .select_related('idu__idu'))

        players = [{
            'name': x.idu.idu.idu.username,
            'confirmed': x.status == 'confirmed',
        } for x in all_participants]

        matches.append({
            'id': p.idm,
            'name': p.name,
            'date': p.date,
            'player_count': p.player_count,
            'winner': winner_name,
            'players': players,
            'confirmed_by_me': u.status == 'confirmed',
            'confirmed_by_all': all(player['confirmed'] for player in players),
        })

    tournaments = tournaments[:3]
    matches = matches[:3]
    return render(request, 'app/profile.html', {
        'member': member,
        'user_id': logged_in_id,
        'stat': stat,
        'wishlist': wishlist,
        'collection': collection,
        'tournaments': tournaments,
        'matches': matches,
        'detailed_stats': detailed_stats,
    })

# Stefana
@member_required
def otherProfile(request, user_id):
    """
    Profile of another user.
    POST: friendship actions (add/accept/reject/remove) and following actions
          (follow/unfollow) with notifications sent, then a redirect (PRG). Only
          players can perform them, and not on their own profile.
    GET:  data and statistics depending on the profile's role and the relation — friends
          see the wishlist/collection/tournaments, followers see the organizer's tournaments.
    """
    logged_in_player = Player.objects.filter(idu=request.user.id).first()
    member = get_object_or_404(Member, idu=user_id)

    profile_player = Player.objects.filter(idu=member).first()
    profile_organizer = Organizer.objects.filter(idu=member).first()
    is_player = profile_player is not None
    is_organizer = profile_organizer is not None

    can_interact = logged_in_player is not None and request.user.id != user_id

    if request.method == "POST":
        action = request.POST.get("action")

        if can_interact and is_player:

            if action == "add":
                already_sent = FriendRequest.objects.filter(
                    idu1=profile_player, idu2=logged_in_player, status='pending'
                ).exists()

                if not already_sent and not are_friends_query(logged_in_player, profile_player).exists():
                    FriendRequest.objects.update_or_create(
                        idu1=logged_in_player,
                        idu2=profile_player,
                        defaults={'status': 'pending'}
                    )

            elif action == "accept":
                accept_friend_request(profile_player.pk, logged_in_player.pk)

            elif action == "reject":
                reject_friend_request(profile_player.pk, logged_in_player.pk)

            elif action == "remove":
                are_friends_query(logged_in_player, profile_player).delete()

        if can_interact and is_organizer:
            if action == "follow":
                _, created = Follow.objects.get_or_create(
                    idu=logged_in_player,
                    ido=profile_organizer
                )

                if created:
                    Notification.objects.create(
                        idu=profile_organizer.idu,
                        message=f"{request.user.username} is now following you.",
                        date=timezone.now(),
                        is_read=False,
                    )
                    Notification.objects.create(
                        idu=logged_in_player.idu,
                        message=f"You are now following organizer {profile_organizer.idu.idu.username}.",
                        date=timezone.now(),
                        is_read=False,
                    )

            elif action == "unfollow":
                Follow.objects.filter(
                    idu=logged_in_player,
                    ido=profile_organizer
                ).delete()

        return redirect('otherProfile', user_id=user_id)

    is_following = False
    are_friends = False
    request_sent = False
    request_received = False

    if can_interact and is_organizer:
        is_following = Follow.objects.filter(
            idu=logged_in_player,
            ido=profile_organizer
        ).exists()

    if can_interact and is_player:
        are_friends = are_friends_query(logged_in_player, profile_player).exists()

        request_sent = FriendRequest.objects.filter(
            idu1=logged_in_player,
            idu2=profile_player,
            status='pending'
        ).exists()

        request_received = FriendRequest.objects.filter(
            idu1=profile_player,
            idu2=logged_in_player,
            status='pending'
        ).exists()

    context = {
        'member': member,
        'user_id': user_id,
        'stat': calculate_statistics(user_id) if is_player else {},
        'is_player': is_player,
        'is_organizer': is_organizer,
        'can_interact': can_interact,
        'are_friends': are_friends,
        'request_sent': request_sent,
        'request_received': request_received,
        'is_following': is_following,
        'tournament_count': Tournament.objects.filter(organizer=profile_organizer).count() if is_organizer else 0,
        'profile_organizer': profile_organizer,
    }

    if is_player and are_friends:
        context['wishlist'] = WishlistCollection.objects.filter(idu=user_id, status='wishlist')
        context['collection'] = WishlistCollection.objects.filter(idu=user_id, status='collection')
        context['tournaments'] = TournamentResult.objects.filter(idu=user_id)
        context['detailed_stats'] = detailed_statistics(user_id)

    if is_organizer and is_following:
        context['organizer_tournaments'] = Tournament.objects.filter(organizer=profile_organizer)
        context['collection'] = WishlistCollection.objects.filter(idu=user_id, status='collection')

    return render(request, 'app/otherProfile.html', context)


@member_required
def removeFromCollection(request, idg):
    """Removes a game from the logged-in user's collection."""
    logged_in_id = request.user.id

    if request.method == 'POST':
        WishlistCollection.objects.filter(
            idu=logged_in_id,
            idg=idg,
            status='collection'
        ).delete()
    return redirect('myCollection')

# Stefana
@member_required
def myCollection(request):
    """Collection of the logged-in user — each game with its average rating and categories."""
    logged_in_id = request.user.id

    my_collection = WishlistCollection.objects.filter(
        idu=logged_in_id, status='collection'
    )

    for item in my_collection:
        game = item.idg

        average = Review.objects.filter(idg=game.idg).aggregate(Avg('rating'))
        item.rating = round(average['rating__avg'], 1) if average['rating__avg'] else '—'

        categories = GameCategory.objects.filter(
            idg=game.idg
        ).select_related('idc')
        item.categories = [k.idc.name for k in categories]

    all_categories = Category.objects.all().order_by('name')

    return render(request, 'app/myCollection.html', {'my_collection': my_collection,
                                                  'all_categories': all_categories})

# Stefana
@member_required
def myWishlist(request):
    """
    Wishlist of the logged-in user.
    POST: 'add_to_collection' moves the item to the collection or 'remove' deletes
          the item, then a redirect (PRG pattern).
    GET:  items with status 'wishlist', each with its average rating and categories.
    """
    logged_in_id = request.user.id

    if request.method == 'POST':
        action = request.POST.get('action')

        qs = WishlistCollection.objects.filter(
            idu_id=logged_in_id,
            idg_id=to_int(request.POST.get('game_id'))
        )
        if action == 'add_to_collection':
            qs.update(status='collection')
        elif action == 'remove':
            qs.delete()

        return redirect('myWishlist')

    wishlist = WishlistCollection.objects.filter(
        idu=logged_in_id, status='wishlist'
    )

    for item in wishlist:
        game = item.idg

        average = Review.objects.filter(idg=game.idg).aggregate(Avg('rating'))
        item.rating = round(average['rating__avg'], 1) if average['rating__avg'] else '—'

        categories = GameCategory.objects.filter(
            idg=game.idg
        ).select_related('idc')
        item.categories = [k.idc.name for k in categories]

    all_categories = Category.objects.all().order_by('name')

    return render(request, 'app/myWishlist.html', {'wishlist': wishlist,
                                                  'all_categories': all_categories})


@player_required
def confirmMatch(request):
    """Confirms the logged-in player's participation/result in a match (status 'confirmed')."""
    if request.method == 'POST':
        MatchParticipant.objects.filter(
            idm=to_int(request.POST.get('match_id')), idu=request.user.id
        ).update(status='confirmed')

    # only our own pages are allowed, never an address from the request
    next_page = request.POST.get('next')
    return redirect(next_page if next_page in ('myMatches', 'profile') else 'myMatches')


@login_required
@require_POST
def addMatch(request):
    """
    AJAX match creation — validates the data, the date (must not be in the
    future), that the game exists, that all participants are friends of the logged-in user and
    that the winner is one of the participants; the creator confirms the match automatically.
    """
    logged_in_id = request.user.id

    def error(text, status=400):
        return JsonResponse({'ok': False, 'error': text}, status=status)

    if not Player.objects.filter(pk=logged_in_id).exists():
        return error('Only players can add matches.', 403)

    try:
        data = json.loads(request.body)
    except ValueError:
        return error('Missing data')

    if not isinstance(data, dict):
        return error('Missing data')

    name = str(data.get('name') or '').strip()
    date = str(data.get('date') or '')
    game_id = to_int(data.get('game_id'))
    participant_names = data.get('participants')
    winner_name = str(data.get('winner') or '').strip()

    if not name or not date or not game_id or not isinstance(participant_names, list) or not participant_names:
        return error('Missing data')

    if len(name) > 100:
        return error('The match name is too long.')

    try:
        date_obj = parse_date(date)
    except ValueError:
        date_obj = None

    if date_obj is None:
        return error('Invalid date format.')

    if date_obj > timezone.localdate():
        return error('The match date cannot be in the future.')

    date_dt = timezone.make_aware(datetime.combine(date_obj, time.min))

    if not Game.objects.filter(pk=game_id).exists():
        return error('The selected game does not exist.')

    participant_names = {str(n) for n in participant_names}
    players = list(Player.objects.filter(idu__idu__username__in=participant_names))
    if len(players) != len(participant_names):
        return error('A participant was not found')

    relations = Friendship.objects.filter(
        Q(idu1=logged_in_id) | Q(idu2=logged_in_id)
    )
    friend_ids = set()
    for relation in relations:
        friend_ids.add(relation.idu2_id if relation.idu1_id == logged_in_id else relation.idu1_id)

    for player in players:
        if player.pk != logged_in_id and player.pk not in friend_ids:
            return error('All participants must be your friends.')

    participant_ids = {player.pk for player in players}
    participant_ids.add(logged_in_id)

    if len(participant_ids) < 2:
        return error('A match needs at least one other participant.')

    winner = None
    if winner_name:
        winner = Player.objects.filter(idu__idu__username=winner_name).first()

        if winner is None or winner.pk not in participant_ids:
            return error('The winner must be one of the participants.')

    try:
        with transaction.atomic():
            match = Match.objects.create(
                name=name,
                game_id=game_id,
                date=date_dt,
                player_count=len(participant_ids),
                winner=winner,
            )

            for player_id in participant_ids:
                # the logged-in user auto-confirms (they propose the result), the others do not
                status = 'confirmed' if player_id == logged_in_id else 'unconfirmed'
                MatchParticipant.objects.create(
                    idm=match, idu_id=player_id, status=status
                )
    except Exception:
        # the details go to the log, not to the user
        logger.exception("Adding a match failed")
        return error('An error occurred. Please try again.', 500)

    return JsonResponse({'ok': True, 'id': match.idm})

# Stefana
@player_required
def myMatches(request):
    """
    Matches of the logged-in player — for each one shows the other participants and their
    confirmation statuses, plus the lists of games and friends needed for the add-match form.
    """

    logged_in_id = request.user.id

    relations = Friendship.objects.filter(
        Q(idu1=logged_in_id) | Q(idu2=logged_in_id)
    )

    friend_ids = set()
    for v in relations:
        if v.idu1_id == logged_in_id:
            friend_ids.add(v.idu2_id)
        else:
            friend_ids.add(v.idu1_id)

    friends = list(
        Player.objects.filter(pk__in=friend_ids)
        .values_list('idu__idu__username', flat=True)
    )
    my_username = Player.objects.filter(pk=logged_in_id).values_list('idu__idu__username', flat=True).first()

    participations = MatchParticipant.objects.filter(idu=logged_in_id).select_related('idm__game', 'idm__winner__idu__idu')
    matches = []
    for u in participations:
        p = u.idm
        winner_name = p.winner.idu.idu.username if p.winner else None


        all_participants = MatchParticipant.objects.filter(idm=p.idm).select_related('idu__idu__idu')
        players = []
        for participant in all_participants:
            if participant.idu_id == logged_in_id:
                continue
            players.append({
                'name': participant.idu.idu.idu.username,
                'confirmed': participant.status == 'confirmed',
            })
        confirmed_by_me = u.status == 'confirmed'
        confirmed_by_all = all(player['confirmed'] for player in players)and confirmed_by_me


        matches.append({
            'id': p.idm,
            'name': p.name,
            'date': p.date,
            'player_count': p.player_count,
            'winner': winner_name,
            'confirmed_by_all': confirmed_by_all,
            'confirmed_by_me': confirmed_by_me,
            'players': players,
            'game': p.game.name,
        })

    games = list(Game.objects.values('idg', 'name'))

    return render(request, 'app/myMatches.html', {'matches': matches,
                                                    'games': games,
                                                    'friends': friends,
                                                    'my_username': my_username,})

# Stefana
@player_required
def myTournaments(request):
    """
    Tournaments of the logged-in player.
    POST: unregister from an active tournament — possible only if there are more than
          5 days left until the start (deletes the participation, decreases the occupancy
          and refunds the entry fee).
    GET:  upcoming tournaments and the history (finished ones with the positions won,
          and canceled ones).
    """
    player = request.user.id

    message = None
    message_idt = None

    if request.method == 'POST':
        message_idt = request.POST.get('idt')

        with transaction.atomic():
            # the tournament is locked first, in the same order as when registering
            tournament = (Tournament.objects
                          .select_for_update()
                          .filter(idt=to_int(message_idt), participation__idu=player)
                          .first())

            if tournament is None:
                message = 'You are not registered for this tournament.'
            elif tournament.status != 'active':
                message = 'You can only unregister from an active tournament.'
            elif tournament.date < timezone.now() + timedelta(days=5):
                # less than 5 days until the start -> no unregistering
                message = 'You cannot unregister because there are less than 5 days until the start of the tournament.'
            else:
                # more than 5 days -> refund, delete the participation and update the occupancy
                participation = Participation.objects.select_related('idt').get(idt=tournament, idu=player)
                amount = refundMoney(participation)[player]
                participation.delete()

                tournament.occupancy = max(tournament.occupancy - 1, 0)
                tournament.save()

                Notification.objects.create(
                    idu_id=player,
                    message=f'You have unregistered from tournament "{tournament.name}".{refund_text(amount)}',
                    date=timezone.now(),
                )

        if message is None:
            return redirect('myTournaments')

    participations = (Participation.objects
              .filter(idu=player)
              .select_related('idt', 'idt__game', 'idt__organizer'))

    upcoming = [u.idt for u in participations if u.idt.status == 'active']
    finished = [u.idt for u in participations if u.idt.status == 'finished']
    canceled = [u.idt for u in participations if u.idt.status == 'canceled']

    results = TournamentResult.objects.filter(idu=player, idt__in=[t.idt for t in finished])
    positions = {r.idt_id: r.position for r in results}

    upcoming.sort(key=lambda t: t.date)
    finished.sort(key=lambda t: t.date, reverse=True)
    history = sorted(finished + canceled, key=lambda t: t.date, reverse=True)

    for t in finished:
        t.my_position = positions.get(t.idt)

    games = Game.objects.all().order_by('name')

    return render(request, 'app/myTournaments.html', {
        'upcoming': upcoming,
        'finished': finished,
        'history': history,
        'games': games,
        'message': message,
        'message_idt': message_idt,
    })


@player_required
@require_POST
def removeFriend(request, friend_id):
    """Removes a friendship regardless of the direction it is stored in."""
    are_friends_query(request.user.id, friend_id).delete()
    return redirect('friends', user_id=request.user.id)


# Stefana
@player_required
def friends(request, user_id):
    """
    List of the user's friends (only their own, otherwise 403) — for each
    friend and for the logged-in user calculates statistics (wins, matches, win rate).
    """
    logged_in_id = request.user.id
    if logged_in_id != user_id:
        return HttpResponseForbidden("You do not have permission to access this page.")

    relations = Friendship.objects.filter(
        Q(idu1=user_id) | Q(idu2=user_id)
    )


    friends_list = []
    for relation in relations:
        # find out who the friend is (the opposite side)
        if relation.idu1_id == user_id:
            friend = relation.idu2
        else:
            friend = relation.idu1

        # calculate their statistics and attach them to the object
        stat = calculate_statistics(friend.idu_id)
        friend.wins = stat['wins']
        friend.matches = stat['matches']
        friend.win_rate = stat['win_rate']

        friends_list.append(friend)

    # my statistics
    my_statistics = calculate_statistics(logged_in_id)

    return render(request, 'app/friends.html', {
        'friends': friends_list,
        'my_statistics': my_statistics
    })

# Stefana
@player_required
def friend_requests(request):
    """
    Friend requests.
    POST: 'accept' or 'reject' a pending request, the same way as on the other
          player's profile. Then a redirect (PRG pattern).
    GET:  pending requests sent to the logged-in user.
    """
    logged_in_id = request.user.id

    if request.method == 'POST':
        sender_id = to_int(request.POST.get('sender_id'))
        action = request.POST.get('action')

        if sender_id is not None:
            if action == 'accept':
                accept_friend_request(sender_id, logged_in_id)
            elif action == 'reject':
                reject_friend_request(sender_id, logged_in_id)

        return redirect('friend_requests')

    # GET
    friend_requests = FriendRequest.objects.filter(
        idu2_id=logged_in_id,
        status='pending'
    ).select_related('idu1__idu__idu')
    return render(request, 'app/friendRequests.html', {'friend_requests': friend_requests})


@require_POST
def notification_read(request, idn):
    """AJAX: marks a notification of the logged-in user as read."""
    logged_in_id = request.user.id

    updated = (
        Notification.objects
        .filter(idn=idn, idu_id=logged_in_id)
        .update(is_read=True)
    )

    if updated:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=404)

# Stefana
@login_required
def notifications(request):
    """User notifications — unread and read, sorted by date descending."""
    logged_in_id = request.user.id

    notifications = (
        Notification.objects
        .filter(idu_id=logged_in_id, is_read=False)
        .order_by('-date')
    )
    read_notifications = (
        Notification.objects
        .filter(idu_id=logged_in_id, is_read=True)
        .order_by('-date')
    )
    return render(request, 'app/notifications.html', {'notifications': notifications,
                                                    'read_notifications': read_notifications})

# Stefana
@login_required
def organizerNotifications(request):
    """Unread notifications of the organizer, sorted by date descending."""
    logged_in_id = request.user.id

    notifications = (
        Notification.objects
        .filter(idu_id=logged_in_id, is_read=False)
        .order_by('-date')
    )

    read_notifications = (
        Notification.objects
        .filter(idu_id=logged_in_id, is_read=True)
        .order_by('-date')
    )
    return render(request, 'app/organizerNotifications.html', {'notifications': notifications,
                                                                'read_notifications': read_notifications})


# TOOLS

# Stefana
@login_required
def tools(request):
    """Static page with the tools."""
    return render(request, 'app/tools.html')


# ADMIN


def _render_admin_games(request, errors=None, form_data=None):
    """
    Helper — renders the admin games page (games with prepared
    categories + all categories) with the given validation errors and the
    values that were entered in the form.
    """
    games = Game.objects.all()
    for game in games:
        relations = list(GameCategory.objects.filter(idg=game.idg).select_related('idc'))
        game.category_ids = ",".join(str(v.idc.idc) for v in relations)
        game.category_names = "|".join(v.idc.name for v in relations)
        game.category_display = ", ".join(v.idc.name for v in relations)

    all_categories = Category.objects.all().order_by('name')
    return render(request, 'app/adminGames.html', {
        'games': games,
        'all_categories': all_categories,
        'errors': errors or [],
        'form_data': form_data or {},
    })


# Katarina
@login_required
@user_passes_test(is_admin)
def adminGames(request):
    """
    Admin game management.
    POST: validates the fields (name required and unique, positive numbers, min <= max), then
          creates a new game, or updates the one given by game_id (including its name and
          categories), and saves the image. Everything in a transaction.
    GET:  list of all games with categories prepared for display/editing.
    """
    if request.method != 'POST':
        return _render_admin_games(request)

    errors = []

    name = (request.POST.get('name') or '').strip()
    author = (request.POST.get('author') or '').strip()
    description = (request.POST.get('description') or '').strip()
    game_id = request.POST.get('game_id')
    game = None

    if game_id:
        game = Game.objects.filter(pk=to_int(game_id)).first()
        if game is None:
            errors.append('The game you are editing does not exist.')

    if not name:
        errors.append('Game name is required.')
    elif len(name) > 100:
        errors.append('Game name is too long.')
    elif Game.objects.filter(name=name).exclude(pk=game.pk if game else None).exists():
        errors.append('A game with this name already exists.')

    if len(author) > 100:
        errors.append('Author is too long.')

    def get_number(field, label):
        """Reads a field from POST and validates that it is a positive integer; adds errors to the list."""
        value = request.POST.get(field)
        if not value:
            errors.append(f'{label} is a required field.')
            return None
        try:
            number = int(value)
        except ValueError:
            errors.append(f'{label} must be a number.')
            return None
        if number <= 0:
            errors.append(f'{label} must be a positive number.')
            return None
        if number > MAX_INT:
            errors.append(f'{label} is too large.')
            return None
        return number

    min_players = get_number('min_players', 'Minimum number of players')
    max_players = get_number('max_players', 'Maximum number of players')
    duration_min = get_number('duration_min', 'Minimum duration')
    duration_max = get_number('duration_max', 'Maximum duration')
    min_age = get_number('min_age', 'Minimum age')

    if min_players and max_players and max_players < min_players:
        errors.append('Maximum number of players cannot be less than the minimum.')

    if duration_min and duration_max and duration_max < duration_min:
        errors.append('Maximum duration cannot be less than the minimum.')

    categories = Category.objects.filter(
        pk__in=[to_int(c) for c in request.POST.getlist('categories') if to_int(c)]
    )

    if errors:
        form_data = request.POST.dict()
        form_data['category_ids'] = ",".join(str(c.pk) for c in categories)
        form_data['category_names'] = "|".join(c.name for c in categories)
        return _render_admin_games(request, errors=errors, form_data=form_data)

    with transaction.atomic():
        if game is None:
            game = Game()

        game.name = name
        game.min_players = min_players
        game.max_players = max_players
        game.duration_min = duration_min
        game.duration_max = duration_max
        game.min_age = min_age
        game.author = author or None
        game.description = description or None

        image = request.FILES.get('image')
        if image:
            path = default_storage.save(f'games/{image.name}', image)
            game.game_image = default_storage.url(path)

        game.save()

        GameCategory.objects.filter(idg=game).exclude(idc__in=categories).delete()
        for category in categories:
            GameCategory.objects.get_or_create(idg=game, idc=category)

    return redirect('adminGames')


def _execute_refund(card, idu_id, amount):
    """
    Simulation of a refund to the user's card. There is no real payment service,
    so the refund is only written to the log (with the last 4 digits of the card).
    """
    logger.info("Simulated refund of %s RSD to card ****%s of user %s", amount, str(card)[-4:], idu_id)
    # money refund logic


def refundMoney(participations):
    """
    Refunds the entry fee of the tournament the user is registered for (one participation
    or more of them). Free tournaments have nothing to refund.
    Returns the user and the amount so that notifications can be sent later.
    """
    if isinstance(participations, Participation):
        participations = [participations]

    amounts = {}
    for u in participations:
        amount = u.idt.entry_fee or Decimal(0)
        if amount > 0:
            _execute_refund(card=u.card_number, idu_id=u.idu_id, amount=amount)
        amounts[u.idu_id] = amount

    return amounts

def refund_text(amount):
    """The part of a notification that mentions the refund; empty for free tournaments."""
    return f' {amount} RSD has been refunded to your card.' if amount > 0 else ''


@transaction.atomic
def cancelTournament(tournament_id):
    """
    Helper — sets the status of an active tournament to 'canceled', refunds all
    registered participants and sends them notifications.
    """
    # locked so that the same tournament cannot be canceled and refunded twice
    tournament = Tournament.objects.select_for_update().get(idt=tournament_id)
    if tournament.status != 'active':
        return

    tournament.status = 'canceled'
    tournament.save()

    participations = Participation.objects.filter(idt=tournament).select_related('idt')

    amounts = refundMoney(participations)
    now = timezone.now()
    Notification.objects.bulk_create([
        Notification(
            idu_id=u.idu_id,
            message=f'Tournament "{tournament.name}" has been canceled.{refund_text(amounts[u.idu_id])}',
            date=now,
        )
        for u in participations
    ])


@login_required
@user_passes_test(is_admin)
def deactivateOrganizer(request, idu):
    """
    Admin deactivates an organizer — in a transaction cancels all of their
    active tournaments (cancelTournament) and disables the User account (is_active=False).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST only.'}, status=405)

    try:
        with transaction.atomic():
            organizer = Organizer.objects.select_related('idu__idu').get(idu=idu)

            tournament_ids = list(
                Tournament.objects
                .filter(organizer=idu, status='active')
                .values_list('idt', flat=True)
            )
            for tid in tournament_ids:
                cancelTournament(tid)

            User.objects.filter(id=organizer.idu.idu.id).update(is_active=False)

    except Organizer.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'The organizer does not exist.'}, status=404)

    return JsonResponse({'ok': True, 'canceled_tournaments': len(tournament_ids)})

# Stefana
@login_required
@user_passes_test(is_admin)
def adminOrganizers(request):
    """Admin list of all organizers with the related user data."""
    organizers = (
        Organizer.objects
        .select_related('idu__idu')  # fetches Member + AuthUser in a single query
        .all()
    )
    return render(request, 'app/adminOrganizers.html', {'organizers': organizers})