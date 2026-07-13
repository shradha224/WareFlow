document.addEventListener("DOMContentLoaded", initializeDashboard);

function initializeDashboard() {
    initializeChart();
    registerEvents();
}

function registerEvents() {
    const placeOrderBtn = document.querySelector(".place-order-btn");
    if(placeOrderBtn){
        placeOrderBtn.addEventListener("click", goToRequestMaterials);
    }
}

function goToRequestMaterials(){
    const material = "Material D";
    const shortage = 250;
    localStorage.setItem("requestedMaterial", material);
    localStorage.setItem("requestedQuantity", shortage);
    window.location.href =
    "../request-raw-materials/request-raw-materials.html";
}

function initializeChart(){
    const ctx =document.getElementById("demandChart");
    if(!ctx) return;
    new Chart(ctx,{
        type:"bar",
        data:{
            labels:[
                "Week 1",
                "Week 2",
                "Week 3",
                "Week 4",
                "Week 5"
            ],
            datasets:[
                {
                    label:"Predicted",
                    data:[75,90,70,105,85],
                    backgroundColor:"#DCD1FF",
                    borderColor:"#9A82FF",
                    borderWidth:2,
                    borderRadius:6
                },

                {
                    label:"Actual",
                    data:[65,80,60,95,75],
                    backgroundColor:"#D8F7E5",
                    borderColor:"#2ECC71",
                    borderWidth:2,
                    borderRadius:6
                }
            ]
        },
        options:{
            responsive:true,
            maintainAspectRatio:false,
            plugins:{
                legend:{
                    position:"top"
                }
            },
            scales:{
                y:{
                    beginAtZero:true
                }
            }
        }
    });
}