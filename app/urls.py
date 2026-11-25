from django.urls import path
from app import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # HOME PAGES
    path('', views.loginRegister, name='loginRegister'),
    path('home/', views.home, name='home'),
    path('home-admin/', views.homeAdmin, name='homeAdmin'),
    path('approve-request/<int:idr>/', views.approve_request, name='approve_request'),
    path('reject-request/<int:idr>/', views.reject_request, name='reject_request'),
    path('home-organizer/', views.homeOrganizer, name='homeOrganizer'),
    path('editOrganizerProfile/', views.editOrganizerProfile, name='editOrganizerProfile'),

    # TOURNAMENTS / SEARCH
    path('followed-tournaments/', views.followedTournaments, name='followedTournaments'),
    path('search/', views.search, name='search'),
    path('tournament/', views.tournaments, name='tournament'),
    path('login-register/', views.loginRegister, name='loginRegister'),
    path('login/', views.login_view, name='login'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='app/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='app/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='app/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='app/password_reset_complete.html'), name='password_reset_complete'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('tournament/create/', views.create_tournament, name='create_tournament'),
    path('tournament/cancel/<int:idt>/', views.cancel_tournament_view, name='cancel_tournament'),
    path('tournament/results/<int:idt>/', views.save_results, name='save_results'),
    path('tournament/edit/<int:idt>/', views.edit_tournament, name='edit_tournament'),
    path('remove-game/<int:idg>/', views.remove_game_from_collection, name='remove_game_from_collection'),
    path('home-admin/cancel/<int:idt>/', views.cancel_tournament_admin, name='cancel_tournament_admin'),

    # GAMES
    path('games/', views.games, name='games'),
    path('game/<int:idg>/', views.gameDetails, name='game_details'),
    path('list/<int:idg>/', views.add_to_list, name='add_to_list'),
    path('add_review/<int:idg>/', views.add_review, name="add_review"),

    # PROFILE
    path('profile/', views.profile, name='profile'),
    path('profile/change-picture/', views.changeProfilePicture, name='changeProfilePicture'),
    path('other-profile/<int:user_id>/', views.otherProfile, name='otherProfile'),

    path('my-collection/', views.myCollection, name='myCollection'),
    path('my-wishlist/', views.myWishlist, name='myWishlist'),
    path('my-matches/', views.myMatches, name='myMatches'),
    path('my-tournaments/', views.myTournaments, name='myTournaments'),

    path('friends/<int:user_id>/', views.friends, name='friends'),
    path('friend-requests/', views.friend_requests, name='friend_requests'),

    path('notifications/', views.notifications, name='notifications'),
    path('organizer-notifications/', views.organizerNotifications, name='organizerNotifications'),

    # TOOLS
    path('tools/', views.tools, name='tools'),

    # ADMIN
    path('admin-games/', views.adminGames, name='adminGames'),
    path('admin-organizer/', views.adminOrganizers, name='adminOrganizers'),

    #HELPER FUNCTIONS
    path('confirm-match/', views.confirmMatch, name='confirmMatch'),
    path('remove-friend/<int:friend_id>/', views.removeFriend, name='removeFriend'),
    path('addMatch/', views.addMatch, name='addMatch'),
    path('my-collection/remove/<int:idg>/', views.removeFromCollection, name='removeFromCollection'),
    path('organizers/<int:idu>/deactivate/', views.deactivateOrganizer, name='deactivateOrganizer'),
    path('notifications/read/<int:idn>/', views.notification_read, name='notification_read'),
   ]


#for images
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)