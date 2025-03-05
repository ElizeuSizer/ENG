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
  document.addEventListener("DOMContentLoaded", function () {
    function addFileInput() {
        const fileInputs = document.getElementById("file-inputs");

        // Criar um novo input para arquivo
        const newInput = document.createElement("input");
        newInput.type = "file";
        newInput.name = "attachments[]"; // Garante que Flask reconheça como lista
        newInput.classList.add("file-upload");
        newInput.addEventListener("change", updateFileList);

        // Adicionar o novo input na div
        fileInputs.appendChild(newInput);
    }

    function updateFileList() {
        const fileList = document.getElementById("file-list");
        fileList.innerHTML = ""; // Limpa a lista antes de atualizar

        // Percorre todos os inputs de arquivos para listar os nomes corretamente
        document.querySelectorAll(".file-upload").forEach((input, index) => {
            if (input.files.length > 0) {
                Array.from(input.files).forEach(file => {
                    const listItem = document.createElement("li");
                    listItem.textContent = file.name + " ";
                    
                    // Botão de remover arquivo
                    const removeButton = document.createElement("button");
                    removeButton.textContent = "Remover";
                    removeButton.classList.add("btn-remove-file");
                    removeButton.onclick = function () {
                        fileInputs.removeChild(input); // Remove o input da lista
                        updateFileList();
                    };

                    listItem.appendChild(removeButton);
                    fileList.appendChild(listItem);
                });
            }
        });
    }

    // Adiciona evento ao primeiro input de arquivo
    document.querySelector(".file-upload").addEventListener("change", updateFileList);
    window.addFileInput = addFileInput; // Permite que o HTML chame a função
});
// Inicializa variáveis do canvas
const salvarAssinaturaUrl = "{{ url_for('salvar_assinatura') }}";
let canvas = document.getElementById('signaturePad');
let ctx = canvas.getContext('2d');
let drawing = false;


// Configurações iniciais do canvas (fundo transparente e traço preto)
ctx.strokeStyle = "#000";
ctx.lineWidth = 2;

// Eventos para capturar o desenho
canvas.addEventListener('mousedown', function(e) {
  drawing = true;
  ctx.beginPath();
  ctx.moveTo(e.offsetX, e.offsetY);
});
canvas.addEventListener('mousemove', function(e) {
  if (drawing) {
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
  }
});
canvas.addEventListener('mouseup', function(e) {
  drawing = false;
});
canvas.addEventListener('mouseout', function(e) {
  drawing = false;
});

// Função para limpar o canvas
function clearSignature() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// Funções para abrir/fechar o modal de assinatura
function openSignatureModal() {
  document.getElementById('signatureModal').style.display = 'block';
}
function closeSignatureModal() {
  document.getElementById('signatureModal').style.display = 'none';
}

// Função para salvar a assinatura
function saveSignature() {
  // Gera a imagem PNG em base64
  let dataURL = canvas.toDataURL('image/png');
  // Remove a parte do header "data:image/png;base64,"
  let base64Data = dataURL.split(',')[1];
  
  // Envia via fetch para a rota Flask
  fetch("{{ url_for('salvar_assinatura') }}", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Caso utilize proteção CSRF, adicione o token aqui
      "X-CSRFToken": "{{ csrf_token() }}"
    },
    body: JSON.stringify({ signature: base64Data })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert("Assinatura salva com sucesso!");
      closeSignatureModal();
      clearSignature();
    } else {
      alert("Erro ao salvar assinatura: " + data.message);
    }
  })
  .catch(error => console.error("Erro:", error));
}

  
