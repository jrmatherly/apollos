console.log(
  `%c %s`,
  "font-family:monospace",
  `
 __  __     __  __     ______       __        _____      __
/\\ \\/ /    /\\ \\_\\ \\   /\\  __ \\     /\\ \\      /\\  __ \\   /\\ \\
\\ \\  _"-.  \\ \\  __ \\  \\ \\ \\/\\ \\   _\\_\\ \\     \\ \\  __ \\  \\ \\ \\
 \\ \\_\\ \\_\\  \\ \\_\\ \\_\\  \\ \\_____\\ /\\_____\\     \\ \\_\\ \\_\\  \\ \\_\\
  \\/_/\\/_/   \\/_/\\/_/   \\/_____/ \\/_____/      \\/_/\\/_/   \\/_/

Greetings traveller,

I am ✨Apollos✨, your open-source, personal AI copilot.

See my source code at https://github.com/jrmatherly/apollos
Read my operating manual at https://docs.apollosai.dev
`,
);

window.appInfoAPI.getInfo((_, info) => {
  let apollosVersionElement = document.getElementById("about-page-version");
  if (apollosVersionElement) {
    apollosVersionElement.innerHTML = `<code>${info.version}</code>`;
  }
  let apollosTitleElement = document.getElementById("about-page-title");
  if (apollosTitleElement) {
    apollosTitleElement.innerHTML =
      "<b>Apollos for " +
      (info.platform === "win32"
        ? "Windows"
        : info.platform === "darwin"
          ? "macOS"
          : "Linux") +
      "</b>";
  }
});

function toggleNavMenu() {
  let menu = document.getElementById("apollos-nav-menu");
  menu.classList.toggle("show");
}

// Close the dropdown menu if the user clicks outside of it
document.addEventListener("click", function (event) {
  let menu = document.getElementById("apollos-nav-menu");
  let menuContainer = document.getElementById("apollos-nav-menu-container");
  let isClickOnMenu =
    menuContainer?.contains(event.target) || menuContainer === event.target;
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
        <a class="apollos-logo" href="/">
            <img class="apollos-logo" src="./assets/icons/apollos_logo.png" alt="Apollos"></img>
        </a>
        <nav class="apollos-nav">
        ${
          userInfo && userInfo.email
            ? `<div class="apollos-status-box">
              <span class="apollos-status-connected"></span>
               <span class="apollos-status-text">Connected to server</span>
               </div>`
            : `<div class="apollos-status-box">
              <span class="apollos-status-not-connected"></span>
               <span class="apollos-status-text">Not connected to server</span>
               </div>`
        }
            ${
              username
                ? `
                <div id="apollos-nav-menu-container" class="apollos-nav dropdown">
                    ${
                      user_photo && user_photo != "None"
                        ? `
                        <img id="profile-picture" class="${is_active ? "circle subscribed" : "circle"}" src="${user_photo}" alt="${username[0].toUpperCase()}" referrerpolicy="no-referrer">
                    `
                        : `
                        <div id="profile-picture" class="${is_active ? "circle user-initial subscribed" : "circle user-initial"}" alt="${username[0].toUpperCase()}">${username[0].toUpperCase()}</div>
                    `
                    }
                    <div id="apollos-nav-menu" class="apollos-nav-dropdown-content">
                        <div class="apollos-nav-username"> ${username} </div>
                        <a onclick="window.navigateAPI.navigateToWebHome()" class="apollos-nav-link">
                        <img class="apollos-nav-icon" src="./assets/icons/open-link.svg" alt="Open Host Url"></img>
                        Open App
                        </a>
                    </div>
                </div>
            `
                : ""
            }
        </nav>
    `;
}
