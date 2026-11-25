# BoardNet

A web platform for board game fans: discover games, record matches with friends, and organize or join tournaments.

BoardNet was built by a team of two as a university project at the School of Electrical Engineering, University of Belgrade.

## Features

**Players**
- Browse the game catalog and filter it by category, number of players, duration, age and rating
- Rate and review games
- Keep a wishlist and a personal game collection
- Add friends and compare statistics
- Record matches, with results confirmed by the other participants
- Follow organizers, register for tournaments and see past placements
- View a profile with win rate, longest winning streak and charts
- Use built-in tools: dice, random number, player picker, timer and stopwatch

**Organizers**
- Request an organizer account, which an admin approves or rejects
- Create, edit and cancel tournaments and enter the final results
- Manage their own game collection and public profile

**Admins**
- Approve or reject organizer requests
- Add and edit games and categories
- Cancel tournaments and deactivate organizers

Players and organizers also get in-app notifications, for example about new friends and followers or changed and canceled tournaments.

> Payments are only simulated. No real payment service is connected.

## Tech stack

| Part | Technologies |
|---|---|
| Backend | Python 3.11, Django 5.2 |
| Database | MySQL 8.0 |
| Frontend | Django templates, JavaScript, HTML, CSS, Chart.js |
| Testing | Django test framework, Selenium (Firefox) |

## Getting started

You need Python 3.11 and a running MySQL 8.0 server. Run the commands in the folder that contains `manage.py`.

1. Create and activate a virtual environment (Windows PowerShell):

   ```powershell
   py -3.11 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   On Linux or macOS:

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

2. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Create the database in MySQL:

   ```sql
   CREATE DATABASE boardnet_en CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

4. Copy `boardnet/local_settings.example.py` to `boardnet/local_settings.py`, then set a secret key and your MySQL user and password in it. This file is ignored by Git.

5. Create the tables:

   ```bash
   python manage.py migrate
   ```

6. Optional: fill the database with demo data. **This deletes the existing app data and all regular users.**

   ```bash
   python manage.py seed
   ```

7. Create an admin account:

   ```bash
   python manage.py createsuperuser
   ```

8. Start the server and open http://127.0.0.1:8000/:

   ```bash
   python manage.py runserver
   ```

### Demo accounts

After seeding, all demo accounts use the password `test123`.

| Role | Usernames |
|---|---|
| Player | `marko`, `ana`, `nikola`, `jelena` |
| Organizer | `petar` |

These accounts are for local use only.

## Tests

Unit tests:

```bash
python manage.py test app.tests app.tests_bugfixes
```

Selenium tests, which need Firefox:

```bash
python manage.py test app.tests_selenium app.test_selenium2
```

The project has 247 unit tests and 32 Selenium tests.

## Project structure

```text
├── app/
│   ├── management/commands/   demo data scripts
│   ├── migrations/            database migrations
│   ├── templates/app/         HTML templates
│   ├── models.py              database models
│   ├── urls.py                routes
│   ├── views.py               application logic
│   └── tests*.py, test_*.py   unit and Selenium tests
├── boardnet/                  project settings
├── static/                    JavaScript, CSS and images
├── manage.py
└── requirements.txt
```

## Team

BoardNet was developed by a team of two. [Stefana Radić](https://github.com/Steftref) built the player profiles and statistics, friends and friend requests, matches, wishlist and collection, the player's tournament page, notifications, the tools page and organizer management for admins.
