// ANNOUNCEMENTS DATA
const announcements = [
    "City Hall Closed on Public Holiday",
    "Free Vaccination Program Available",
    "Traffic Advisory: Molino Road Repair"
];

// DYNAMIC ANNOUNCEMENTS + MODAL + LOCAL STORAGE
const feed = document.getElementById("announcementFeed");
const modal = document.getElementById("announcementModal");
const modalText = document.getElementById("modalText");
const closeBtn = document.querySelector(".close");

if(feed){
    announcements.forEach(item => {
        const div = document.createElement("div");
        div.textContent = item;
        div.style.cursor = "pointer";

        div.onclick = () => {
            if(modal){
                modal.style.display = "block";
                modalText.textContent = item;
                localStorage.setItem("lastViewedAnnouncement", item);
            }
        };

        feed.appendChild(div);
    });
}

if(closeBtn){
    closeBtn.onclick = () => modal.style.display = "none";
}

// SEARCH FILTER
const search = document.getElementById("searchDept");

if(search){
    search.addEventListener("keyup", function(){
        let filter = search.value.toLowerCase();
        let items = document.querySelectorAll("#deptList li");

        items.forEach(item => {
            item.style.display = item.textContent.toLowerCase().includes(filter)
                ? "" : "none";
        });
    });
}

// FORM VALIDATION
const form = document.getElementById("serviceForm");

if(form){
    form.addEventListener("submit", function(e){
        e.preventDefault();

        let name = document.getElementById("name").value.trim();
        let email = document.getElementById("email").value.trim();
        let request = document.getElementById("request").value.trim();

        if(name.length < 3){
            alert("Name must be at least 3 characters.");
            return;
        }

        document.getElementById("formMessage").textContent =
            "Request submitted successfully!";

        form.reset();
    });
}
