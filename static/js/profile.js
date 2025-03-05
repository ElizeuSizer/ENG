function toggleDropdown() {
    var dropdown = document.getElementById("dropdownMenu");
    if (dropdown.style.display === "block") {
      dropdown.style.display = "none";
    } else {
      dropdown.style.display = "block";
    }
  }
  
  // Opcional: Fechar o dropdown se clicar fora dele
  window.onclick = function(event) {
    if (!event.target.matches('.profile-avatar')) {
      var dropdown = document.getElementById("dropdownMenu");
      if (dropdown.style.display === "block") {
        dropdown.style.display = "none";
      }
    }
  };
  