console.log(`%c %s`, "font-family:monospace", `
 __  __     __  __     ______       __        _____      __
/\\ \\/ /    /\\ \\_\\ \\   /\\  __ \\     /\\ \\      /\\  __ \\   /\\ \\
\\ \\  _"-.  \\ \\  __ \\  \\ \\ \\/\\ \\   _\\_\\ \\     \\ \\  __ \\  \\ \\ \\
 \\ \\_\\ \\_\\  \\ \\_\\ \\_\\  \\ \\_____\\ /\\_____\\     \\ \\_\\ \\_\\  \\ \\_\\
  \\/_/\\/_/   \\/_/\\/_/   \\/_____/ \\/_____/      \\/_/\\/_/   \\/_/

Greetings traveller,

I am ✨Apollos✨, your open-source, personal AI copilot.

See my source code at https://github.com/jrmatherly/apollos
Read my operating manual at https://docs.apolloslos.dev
`);


window.appInfoAPI.getInfo((_, info) => {
    let apolloslosVersionElement = document.getElementById("about-page-version");
    if (apolloslosVersionElement) {
        apolloslosVersionElement.innerHTML = `<code>${info.version}</code>`;
    }
    let apolloslosTitleElement = document.getElementById("about-page-title");
    if (apolloslosTitleElement) {
        apolloslosTitleElement.innerHTML = '<b>Apolloslos for ' + (info.platform === 'win32' ? 'Windows' : info.platform === 'darwin' ? 'macOS' : 'Linux') + '</b>';
    }
});

function toggleNavMenu() {
    let menu = document.getElementById("apolloslos-nav-menu");
    menu.classList.toggle("show");
}

// Close the dropdown menu if the user clicks outside of it
document.addEventListener('click', function (event) {
    let menu = document.getElementById("apolloslos-nav-menu");
    let menuContainer = document.getElementById("apolloslos-nav-menu-container");
    let isClickOnMenu = menuContainer?.contains(event.target) || menuContainer === event.target;
    if (menu && isClickOnMenu === false && menu.classList.contains("show")) {
        menu.classList.remove("show");
    }
});

async function populateHeaderPane() {
    let userInfo = null;
    try {
        userInfo = await window.userInfoAPI.getUserInfo();
    } catch (error) {
        console.log("User not logged in");
    }

    let username = userInfo?.username ?? "?";
    let user_photo = userInfo?.photo;
    let is_active = userInfo?.is_active;
    let has_documents = userInfo?.has_documents;

    // Populate the header element with the navigation pane
    return `
        <a class="apolloslos-logo" href="/">
            <img class="apolloslos-logo" src="./assets/icoapollospollos_logo.png" alt="Apolloslos"></img>
        </a>
        <nav class="apolloslos-nav">
        ${userInfo && userInfo.email
            ? `<div class="apolloslos-status-box">
              <span class="apolloslos-status-connected"></span>
               <span class="apolloslos-status-text">Connected to server</span>
               </div>`
            : `<div class="apolloslos-status-box">
              <span class="apolloslos-status-not-connected"></span>
               <span class="apolloslos-status-text">Not connected to server</span>
               </div>`
        }
            ${username ? `
                <div id="apolloslos-nav-menu-container" clasapollospollos-nav dropdown">
                    ${user_photo && user_photo != "None" ? `
                        <img id="profile-picture" class="${is_active ? 'circle subscribed' : 'circle'}" src="${user_photo}" alt="${username[0].toUpperCase()}" referrerpolicy="no-referrer">
                    ` : `
                        <div id="profile-picture" class="${is_active ? 'circle user-initial subscribed' : 'circle user-initial'}" alt="${username[0].toUpperCase()}">${username[0].toUpperCase()}</div>
                    `}
                    <div id="apolloslos-nav-menu" clasapollospollos-nav-dropdown-content">
                        <div class="apolloslos-nav-username"> ${username} </div>
                        <a onclick="window.navigateAPI.navigateToWebHome()" class="apolloslos-nav-link">
                        <img class="apolloslos-nav-icon" src="./assets/icons/open-link.svg" alt="Open Host Url"></img>
                        Open App
                        </a>
                    </div>
                </div>
            ` : ''}
        </nav>
    `;
}
