function openModal() {
    document.getElementById("modal").style.display = "block";
}

function closeModal() {
    document.getElementById("modal").style.display = "none";
}

function updateLocalFabrica() {
    var planta = document.getElementById("planta").value;
    var localFabrica = document.getElementById("local_fabrica");

    localFabrica.innerHTML = ""; 

    var defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Selecione...";
    localFabrica.appendChild(defaultOption);

    var options = [];
    if (planta === "SN") {
        options = ["321408 RESTAURANTE", "381413 Manutenção"];
    } else if (planta === "EDP") {
        options = ["321414 ENGENHARIA", "321408 RESTAURANTE"];
    }

    options.forEach(function(op) {
        var newOption = document.createElement("option");
        newOption.value = op;
        newOption.textContent = op;
        localFabrica.appendChild(newOption);
    });
}

window.onload = function() {
    updateLocalFabrica();
};
