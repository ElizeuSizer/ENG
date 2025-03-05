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
