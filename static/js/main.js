function showLogin() {
    document.getElementById("loginForm").style.display = "block";
    document.getElementById("registerForm").style.display = "none";
}

function showRegister() {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("registerForm").style.display = "block";
}





function filterTournaments() {
    let search = document.getElementById("searchTournament") ? document.getElementById("searchTournament").value.toLowerCase() : "";
    let status = document.getElementById("statusFilter") ? document.getElementById("statusFilter").value : "all";
    let game = document.getElementById("gameFilter") ? document.getElementById("gameFilter").value : "all";
    let location = document.getElementById("locationFilter") ? document.getElementById("locationFilter").value : "all";

    let cards = document.querySelectorAll(".tournament-card");

    cards.forEach(card => {

        let text = card.innerText.toLowerCase();
        let cardStatus = card.dataset.status;
        let cardGame = card.dataset.game || "";
        let cardLocation = card.dataset.location || "";

        let matchesSearch = text.includes(search);
        let matchesStatus = (status === "all" || status === cardStatus);
        let matchesGame = (game === "all" || cardGame === game);
        let matchesLocation = (location === "all" || cardLocation === location);

        if (matchesSearch && matchesStatus && matchesGame && matchesLocation) {
            card.style.display = "block";
        } else {
            card.style.display = "none";
        }
    });

    showEmptyMessage(".tournament-card");
}

function filterUsers() {
    let search = document.getElementById("searchUser").value.toLowerCase();
    let role = document.getElementById("roleFilter").value;

    let users = document.querySelectorAll(".user-card");

    users.forEach(user => {

        let text = user.innerText.toLowerCase();
        let userRole = user.dataset.role;

        let matchesSearch = text.includes(search);
        let matchesRole = (role === "all" || role === userRole);

        if (matchesSearch && matchesRole) {
            user.style.display = "block";
        } else {
            user.style.display = "none";
        }
    });

    showEmptyMessage(".user-card");
}






function toggleCompare(btn) {
    const box = btn.nextElementSibling;

    if (box.style.display === "block") {
        box.style.display = "none";
    } else {
        box.style.display = "block";
    }
}



const users = {
    player: {
        name: "marko22",
        wins: 32,
        losses: 18,
        wishlist: ["Catan", "Gloomhaven"],
        collection: ["Azul", "Chess"]
    },

    org: {
        name: "boardmasters",
        followers: 1200,
        tournaments: 10,
        location: "Belgrade",
        collection: ["Chess"],
        tournamentsList: []
    }
};

//window.onload = function () {
//
//    const id = localStorage.getItem("profileType");
//    const container = document.getElementById("profilePreview");
//    const header = document.getElementById("profileHeader");
//
//    if (container && header) {
//
//        const user = users[id];
//
//        if (!user) {
//            container.innerHTML = "<h2>Profile does not exist</h2>";
//            return;
//        }
//
//        if (id === "player") {
//
//            header.innerHTML = `
//                <img src="https://i.pravatar.cc/150?img=12" class="avatar">
//
//                <div class="profile-info">
//                    <h2>${user.name}</h2>
//                    <p>${user.wins} wins • ${user.losses} losses</p>
//                </div>
//
//                <div class="profile-actions">
//                    <button class="btn-link">➕ Add friend</button>
//                </div>
//                `;
//            container.innerHTML = `
//            <div class="grid">
//
//                <div class="card-prof">
//                    <h2>Wishlist</h2>
//                    <ul>
//                        <li>Gloomhaven</li>
//                        <li>Wingspan</li>
//                        <li>Terraforming Mars</li>
//                    </ul>
//                </div>
//
//                <div class="card-prof">
//                    <h2>Collection</h2>
//                    <ul>
//                        <li>Catan</li>
//                        <li>Chess</li>
//                        <li>Azul</li>
//                    </ul>
//                </div>
//
//                <div class="card-prof">
//                    <h2>Tournaments</h2>
//                    <ul>
//                        <li>Chess Masters — 1. place</li>
//                        <li>Catan Cup — 4. place</li>
//                        <li>D&amp;D Night — participated</li>
//                    </ul>
//                </div>
//
//            </div>
//            `;
//        }
//
//        // ORGANIZER
//        else if (id === "org") {
//
//            header.innerHTML = `
//                <img src="https://i.pravatar.cc/150?img=12" class="avatar">
//
//                <div class="profile-info">
//                    <h2>${user.name}</h2>
//                    <p>${user.tournaments} tournaments • ${user.location}</p>
//                </div>
//
//                <div class="profile-actions">
//                    <button class="btn-link">➕ Follow</button>
//                </div>
//            `;
//            container.innerHTML = `
//                <div class="grid">
//
//                    <div class="card-prof">
//                        <h2>Upcoming tournaments</h2>
//
//                    <div class="tournament-featured">
//                                    <div class="t-title">Catan Championship</div>
//                                    <div class="t-info">20.05.2026 • Catan</div>
//                                    <div class="t-meta">12/16 spots</div>
//                                    <div class="t-extra">
//                                        <div><strong>Entry fee:</strong> 500 RSD</div>
//                                        <div><strong>Prize:</strong> Catan Deluxe + medal</div>
//                                    </div>
//                                    <div class="t-badge open">OPEN</div>
//                                    <button>Apply</button>
//                                </div>
//                    </div>
//
//                    <div class="card-prof">
//                        <h2>Finished tournaments</h2>
//
//                        <div class="tournament-featured">
//                                    <div class="t-title">D&amp;D Night</div>
//                                    <div class="t-info">30.05.2026 • RPG</div>
//                                    <div class="t-meta">4/6 spots</div>
//                                    <div class="t-extra">
//                                        <div><strong>Entry fee:</strong> 500 RSD</div>
//                                        <div><strong>Prize:</strong> Catan Deluxe + medal</div>
//                                    </div>
//                                    <div class="t-badge open">OPEN</div>
//                                    <button>Apply</button>
//                                </div>
//                    </div>
//                </div>
//                `;
//        }
//    }
//
//};




function addCategory(id, name) {
    if (!id) return;

    var hidden = document.getElementById('categoriesHidden');


    if (hidden.querySelector('option[value="' + id + '"]')) {
        document.getElementById('category').value = '';
        return;
    }


    var opt = document.createElement('option');
    opt.value = id;
    opt.text = name;
    opt.selected = true;
    hidden.appendChild(opt);


    var chip = document.createElement('span');
    chip.className = 'category-chip';
    chip.setAttribute('data-id', id);
    chip.textContent = name + " ";

    var x = document.createElement('span');
    x.className = 'category-x';
    x.textContent = '×';
    x.onclick = function () { removeCategory(x, id); };
    chip.appendChild(x);
    document.getElementById('selectedCategories').appendChild(chip);

    document.getElementById('category').value = '';
}


function removeCategory(button, id) {
    button.closest('.category-chip').remove();
    var opt = document.getElementById('categoriesHidden')
                      .querySelector('option[value="' + id + '"]');
    if (opt) opt.remove();
}


function loadCategories(idsStr, namesStr) {
    document.getElementById('selectedCategories').innerHTML = '';
    document.getElementById('categoriesHidden').innerHTML = '';
    if (!idsStr) return;

    var ids = idsStr.split(',');
    var names = namesStr.split('|');
    for (var i = 0; i < ids.length; i++) {
        addCategory(ids[i], names[i]);
    }
}

function filterGames() {
    const search   = document.getElementById('searchInput').value.toLowerCase();
    const type     = document.getElementById('typeFilter').value;
    const players  = parseInt(document.getElementById('playersFilter').value) || 0;
    const duration = parseInt(document.getElementById('durationFilter').value) || 0;
    const age      = parseInt(document.getElementById('ageFilter').value) || 0;
    const rating   = parseFloat(document.getElementById('ratingFilter').value) || 0;


    const cards = document.querySelectorAll('.game-card');
    cards.forEach(card => {
        const title     = card.querySelector('.game-title').textContent.toLowerCase();
        const cardTypes = (card.dataset.type || '').split(',').map(t => t.trim());

        // const cardPlay  = parseInt(card.dataset.maxplayers) || 0;
        const minPlayers = parseInt(card.dataset.minplayers) || 0;
        const maxPlayers = parseInt(card.dataset.maxplayers) || 0;
        // const cardDur   = parseInt(card.dataset.duration) || 0;
        const minDur = parseInt(card.dataset.minduration) || 0;
        const maxDur = parseInt(card.dataset.maxduration || minDur);
        const cardAge   = parseInt(card.dataset.age) || 0;
        const cardRate  = parseFloat(card.dataset.rating) || 0;

        let show = true;

        if (search && !title.includes(search)) show = false;

        if (type !== 'all' && !cardTypes.includes(type)) show = false;

        // number of players — the game must be playable with exactly that many
        // if (players && cardPlay < players) show = false;
        if (players > 0) {
            if (minPlayers > players || maxPlayers < players) show = false;
        }

        // duration — UP TO the selected value (shorter or equal)
        // if (duration && cardDur > duration) show = false;
        if (duration > 0) {
            if (maxDur > duration) show = false;
        }

        // age — exactly that age or lower (a game for 8+ passes the "8" filter)
        if (age > 0 && cardAge > age) show = false;

        if (rating > 0 && cardRate < rating) show = false;

        card.style.display = show ? 'flex' : 'none';
    });

    showEmptyMessage('.game-card');

}

function showEmptyMessage(cardSelector) {
    const cards = [...document.querySelectorAll(cardSelector)];
    const visible = cards.filter(c => c.style.display !== 'none').length;

    // an empty list already has its own message, so this one is only for filtered-out cards
    const msg = document.querySelector('#noResults, .no-results');
    if (msg) msg.style.display = cards.length > 0 && visible === 0 ? 'block' : 'none';
}

function removeGame(btn) {
    btn.closest(".game-card").remove();
}



function filterGamesOrg() {
    const search = document.getElementById("searchInputOrg").value.toLowerCase();
    const type = document.getElementById("typeFilterOrg").value;
    const players = parseInt(document.getElementById("playersFilterOrg").value) || 0;

    document.querySelectorAll("#gamesListOrg .game-card").forEach(card => {
        const title = card.querySelector(".game-title").textContent.toLowerCase();
        const cardTypes = (card.dataset.type || "")
            .split(",")
            .map(t => t.trim());

        const minPlayers = parseInt(card.dataset.minplayers) || 0;
        const maxPlayers = parseInt(card.dataset.maxplayers) || 0;

        const show =
            (!search || title.includes(search)) &&
            (type === "all" || cardTypes.includes(type)) &&
            (!players || (minPlayers <= players && maxPlayers >= players));

        card.style.display = show ? "flex" : "none";
    });

    updateOrgEmptyState();
}

function updateOrgEmptyState() {
    const visible = [...document.querySelectorAll("#gamesListOrg .game-card")]
        .filter(c => c.style.display !== "none").length;

    document.getElementById("noResultsOrg").style.display =
        visible === 0 ? "block" : "none";
}



// ===== FRIENDS: autocomplete =====
let selectedFriends = [];

const friendInput   = document.getElementById("friendSearch");
const friendsEl  = document.getElementById("friends-data");

if (friendInput && friendsEl) {
    const FRIENDS = JSON.parse(friendsEl.textContent);
    const dropdown   = document.getElementById("dropdown");

    friendInput.addEventListener("input", function () {
        const term = this.value.trim().toLowerCase();
        dropdown.innerHTML = "";
        if (!term) return;

        FRIENDS
            .filter(u => u.toLowerCase().includes(term) && !selectedFriends.includes(u))
            .slice(0, 8)
            .forEach(username => {
                const item = document.createElement("div");
                item.className = "dropdown-item";
                item.textContent = username;
                item.addEventListener("click", () => addFriend(username));
                dropdown.appendChild(item);
            });
    });

    // a click outside the dropdown closes it
    document.addEventListener("click", e => {
        if (!dropdown.contains(e.target) && e.target !== friendInput) {
            dropdown.innerHTML = "";
        }
    });
}

function addFriend(username) {
    if (selectedFriends.includes(username)) return;
    selectedFriends.push(username);

    const selected = document.getElementById("selectedFriends");

    const chip = document.createElement("span");
    chip.className = "friend-chip";
    chip.textContent = username;

    // x for removing
    const x = document.createElement("span");
    x.className = "friend-x";
    x.textContent = "×";
    x.addEventListener("click", () => {
        selectedFriends = selectedFriends.filter(f => f !== username);
        chip.remove();
    });

    chip.appendChild(x);
    selected.appendChild(chip);

    // reset the input and dropdown
    document.getElementById("friendSearch").value = "";
    document.getElementById("dropdown").innerHTML = "";
}


function toggleForm() {
    const form = document.getElementById("partyForm");
    form.style.display = form.style.display === "none" ? "block" : "none";
}

// ===== GAMES: autocomplete =====
const gamesDataEl = document.getElementById("games-data");
const gameInput  = document.getElementById("gameName");

if (gamesDataEl && gameInput) {
    const GAMES         = JSON.parse(gamesDataEl.textContent);
    const gameDropdown = document.getElementById("gameDropdown");
    const gameIdField  = document.getElementById("gameId");

    gameInput.addEventListener("input", function () {
        const term = this.value.trim().toLowerCase();
        gameIdField.value = "";
        gameDropdown.innerHTML = "";
        if (!term) return;

        GAMES.filter(g => g.name.toLowerCase().includes(term))
            .slice(0, 8)
            .forEach(g => {
                const item = document.createElement("div");
                item.className = "dropdown-item";
                item.textContent = g.name;
                item.addEventListener("click", () => {
                    gameInput.value   = g.name;
                    gameIdField.value = g.idg;
                    gameDropdown.innerHTML = "";
                });
                gameDropdown.appendChild(item);
            });
    });

    document.addEventListener("click", e => {
        if (!gameDropdown.contains(e.target) && e.target !== gameInput) {
            gameDropdown.innerHTML = "";
        }
    });
}



// ===== CSRF helper =====
function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
}

// ===== ADDING A MATCH =====
async function addParty() {
    const error = document.getElementById("errorMsg");
    error.style.display = "none";

    const gameId   = document.getElementById("gameId").value;
    const name    = document.getElementById("matchName").value.trim();
    const date     = document.getElementById("date").value;
    const winner   = document.getElementById("winner").value.trim();
    const selected = selectedFriends;

    const me = JSON.parse(document.getElementById("my-username").textContent);
    if (winner && winner !== me && !selected.includes(winner)) {
        error.textContent = "The winner must be one of the participants.";
        error.style.display = "block";
        return;
    }
    if (!gameId || selected.length === 0 || !date) {
        error.textContent = "Choose a game from the list, a date and at least one participant.";
        error.style.display = "block";
        return;
    }

    const payload = {
        game_id:      gameId,
        name:         name,
        date:         date,
        winner:       winner,
        participants: selected,
    };

    try {
        const addUrl = document.getElementById("add-url").dataset.url;
        const res = await fetch(addUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (data.ok) {
            window.location.reload();
        } else {
            error.textContent = data.error || "Error while saving.";
            error.style.display = "block";
        }
    } catch (e) {
        error.textContent = "Error communicating with the server.";
        error.style.display = "block";
    }
}



function editGame(btn) {
    const game = btn.dataset;

    document.getElementById("game_id").value = game.gameId;
    document.getElementById("name").value = game.name;
    document.getElementById("min_players").value = game.minPlayers;
    document.getElementById("max_players").value = game.maxPlayers;
    document.getElementById("duration_min").value = game.durationMin;
    document.getElementById("duration_max").value = game.durationMax;
    document.getElementById("min_age").value = game.minAge;
    document.getElementById("category").value = "";
    document.getElementById("author").value = game.author;
    document.getElementById("description").value = game.description;
    loadCategories(game.categoryIds, game.categoryNames);

    scrollToForm();
}

// empties the form, so that saving creates a new game instead of changing the edited one
function newGame() {
    document.querySelectorAll("#gameForm input:not([name=csrfmiddlewaretoken]), #gameForm textarea")
        .forEach(field => field.value = "");
    document.getElementById("preview").style.display = "none";
    loadCategories("", "");

    scrollToForm();
}

//game search in admin game management
function searchGames() {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let cards = document.querySelectorAll(".game-card-adm");

    cards.forEach(card => {
        let name = (card.getAttribute("data-name") || "").toLowerCase();

        if (name.includes(input)) {
            card.style.display = "block";
        } else {
            card.style.display = "none";
        }
    });

    showEmptyMessage(".game-card-adm");
}

// scroll functions
function scrollToForm() {
    document.getElementById("formSection").scrollIntoView({
        behavior: "smooth"
    });
}

function scrollToList() {
    document.getElementById("listSection").scrollIntoView({
        behavior: "smooth"
    });
}

// deleting a game
function deleteGame(button) {
    let card = button.closest(".game-card");

    if (confirm("Are you sure you want to delete the game?")) {
        card.remove();
    }
}

function searchOrg() {
    const q = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('.org-card').forEach(card => {
        const name = card.getAttribute('data-name').toLowerCase();
        card.style.display = name.includes(q) ? '' : 'none';
    });

    showEmptyMessage('.org-card');
}

function togglePanel(id) {
    const el = document.getElementById(id);

    if (el.classList.contains("open")) {
        el.classList.remove("open");
    } else {
        el.classList.add("open");
    }
}

function toggleResults(btn) {
    const card = btn.closest(".tournament-card");

    //close the other forms
    document.querySelectorAll(".tournament-card").forEach(c => {
        if (c !== card) c.classList.remove("expanded");
    });

    card.classList.toggle("expanded");
}

function saveResults(btn) {
    const card = btn.closest(".tournament-card");
    const inputs = card.querySelectorAll(".results-form input");

    console.log({
        first: inputs[0].value,
        second: inputs[1].value,
        third: inputs[2].value
    });

    card.classList.remove("expanded");
}

function toggleEdit(btn) {
    const card = btn.closest(".tournament-card");

    // close the others
    document.querySelectorAll(".tournament-card").forEach(c => {
        if (c !== card) c.classList.remove("edit-open");
    });

    card.classList.toggle("edit-open");
}


function formatDateDMY(dateString) {
    const date = new Date(dateString);

    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();

    return `${day}.${month}.${year}`;
}


// TOURNAMENT REGISTRATION FORM
function openApplyForm(btn) {
    const card = btn.closest(".tournament-card");

    // close the others
    document.querySelectorAll(".tournament-card").forEach(c => {
        if (c !== card) c.classList.remove("apply-open");
    });

    card.classList.toggle("apply-open");
}





function previewImage(event) {
    const file = event.target.files[0];
    const preview = document.getElementById("preview");

    if (file) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    }
}



function toggleReadNotifications() {
    const list = document.getElementById('readList');
    const button = document.getElementById('toggleRead');
    const hidden = list.style.display === 'none';

    list.style.display = hidden ? 'block' : 'none';
    button.innerText = hidden ? 'Hide read' : 'Show read';
}