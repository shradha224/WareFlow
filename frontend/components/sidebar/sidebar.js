document.addEventListener("DOMContentLoaded",()=>{
    const sidebar=document.getElementById("sidebar");
    const overlay=document.getElementById("sidebar-overlay");
    const menu=document.getElementById("menu-toggle");
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