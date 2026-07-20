document.addEventListener("DOMContentLoaded",()=>{
    const sidebar=document.getElementById("sidebar");
    const overlay=document.getElementById("sidebar-overlay");
    const menu=document.getElementById("menu-toggle");
    const logout=document.querySelector(".logout-btn");
    if(!sidebar || !menu || !overlay) return;
    menu.addEventListener("click",(e)=>{
        e.stopPropagation();
        sidebar.classList.toggle("show");
        overlay.classList.toggle("show");
    });
    overlay.addEventListener("click",()=>{
        sidebar.classList.remove("show");
        overlay.classList.remove("show");
    });
    logout.addEventListener("click",()=>{  
        localStorage.clear();
        sessionStorage.clear();
        let path = window.location.pathname;
        let index = path.indexOf("/frontend/");
        if (index !== -1) {
            window.location.href = path.substring(0, index) + "/frontend/pages/login/login.html";
        } else {
            let pagesIndex = path.indexOf("/pages/");
            if (pagesIndex !== -1) {
                window.location.href = path.substring(0, pagesIndex) + "/pages/login/login.html";
            } else {
                window.location.href = "/pages/login/login.html";
            }
        }
    });
    document.querySelectorAll(".menu-item").forEach(item=>{
        item.addEventListener("click",()=>{
            if(window.innerWidth<=768){
                sidebar.classList.remove("show");
                overlay.classList.remove("show");
            }
        });
    });
    document.addEventListener("keydown",(e)=>{
        if(e.key==="Escape"){
            sidebar.classList.remove("show");
            overlay.classList.remove("show");
        }
    });
    window.addEventListener("resize",()=>{
        if(window.innerWidth>768){
            sidebar.classList.remove("show");
            overlay.classList.remove("show");
        }
    });
});