/**********************************************
 * TOGGLE DROPDOWN (AVATAR)
 **********************************************/
function toggleDropdown() {
    const dropdown = document.getElementById("dropdownMenu");
    dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
  }
  
  /**********************************************
   * MODAL DE PEDIDO
   **********************************************/
  // Abre o modal de Pedido e define o ID da requisição
  function openModal(reqId) {
    document.getElementById('requisicao_id').value = reqId;
    document.getElementById('modalPedido').style.display = 'block';
  }
  
  // Fecha o modal de Pedido
  function closeModal() {
    document.getElementById("modalPedido").style.display = "none";
  }
  
  /**********************************************
   * MODAL DE NF - ABRIR E FECHAR
   **********************************************/
  function openNFModal(reqId) {
    document.getElementById("modalNF").style.display = "block";
    document.getElementById("req_id_nf").value = reqId;
    loadPedidoList(reqId); // Carrega os pedidos da requisição
    loadNFList(reqId);     // Carrega a lista de NF's (já existente)
  }
  
  
  function closeNFModal() {
    const modal = document.getElementById("modalNF");
    if (modal) {
      modal.style.display = "none";
    }
  }
  
  /**********************************************
   * FILTRO DE REQUISIÇÕES
   **********************************************/
  function filterRequisitions() {
    const input = document.getElementById("search-bar").value.toLowerCase();
    const pendentes = document.querySelectorAll("#pendentes-list .requisition-card");
    const abertas = document.querySelectorAll("#abertas-list .requisition-card");
  
    function filterCards(cards) {
      cards.forEach(card => {
        const text = card.innerText.toLowerCase();
        card.style.display = text.includes(input) ? "flex" : "none";
      });
    }
  
    filterCards(pendentes);
    filterCards(abertas);
  }
  
  /**********************************************
   * LISTAR NF's VIA AJAX
   **********************************************/
  function loadNFList(reqId) {
    const nfListDiv = document.getElementById("nfList");
    if (!nfListDiv) return;
    
    nfListDiv.innerHTML = "<p>Carregando...</p>";
    
    fetch(`/get_nf_list/${reqId}`)
      .then(response => response.json())
      .then(data => {
        console.log("Dados NF recebidos:", data);
        nfListDiv.innerHTML = "";
        if (data.error) {
          nfListDiv.innerHTML = `<p>${data.error}</p>`;
        } else if (data.length === 0) {
          nfListDiv.innerHTML = `<p>Nenhuma Nota Fiscal cadastrada.</p>`;
        } else {
          data.forEach(nf => {
            let nfRow = document.createElement("div");
            nfRow.className = "nf-item-row";
            nfRow.innerHTML = `
              <div class="nf-pedido">Pedido: ${nf.pedido}</div>
              <div class="nf-valor">Valor: R$ ${nf.valor}</div>
              <div class="nf-actions">
                <a href="/download_nf_anexo/${(nf.anexos && nf.anexos.length > 0) ? nf.anexos[0].anexo_id : ''}" class="btn-download">Baixar</a>
                <button class="btn-excluir" onclick="deleteNF('${nf.id}', '${reqId}')">Excluir</button>
              </div>
            `;
            nfListDiv.appendChild(nfRow);
          });
        }
      })
      .catch(err => {
        console.error("Erro ao carregar NF's:", err);
        nfListDiv.innerHTML = `<p>Erro ao carregar NF's.</p>`;
      });
  }
  
  
  
  /**********************************************
   * EXCLUIR NF E ATUALIZAR LISTA
   **********************************************/
  function deleteNF(nfId, reqId) {
    if (!confirm("Tem certeza que deseja excluir esta NF?")) return;
  
    fetch(`/excluir_nf?nf_id=${nfId}&req_id=${reqId}`, { method: "GET" })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert("Nota Fiscal excluída com sucesso!");
          // Fecha o modal e recarrega a lista
          closeNFModal();
          // Recarrega a lista usando a mesma função
          loadNFList(reqId);
        } else {
          alert("Erro ao excluir NF!");
        }
      })
      .catch(err => console.error("Erro ao excluir NF:", err));
  }
  
  /**********************************************
   * ADICIONAR MAIS INPUTS DE ARQUIVOS (NF)
   **********************************************/
  function addNFFileInput() {
    const container = document.getElementById("nf-file-inputs");
    if (!container) {
      console.error("Container 'nf-file-inputs' não encontrado");
      return;
    }
    const input = document.createElement("input");
    input.type = "file";
    input.name = "nf_attachments[]";
    input.className = "file-upload";
    container.appendChild(input);
    console.log("Novo input de arquivo adicionado");
  }
  function loadPedidoList(reqId) {
    fetch(`/get_pedido_list/${reqId}`)
      .then(response => response.json())
      .then(data => {
        const select = document.getElementById("pedido_id");
        select.innerHTML = "";
        if (data.error) {
          select.innerHTML = `<option value="">Nenhum pedido disponível</option>`;
        } else if (data.length === 0) {
          select.innerHTML = `<option value="">Nenhum pedido disponível</option>`;
        } else if (data.length === 1) {
          data.forEach(function(pedido) {
            const option = document.createElement("option");
            option.value = pedido.id;
            option.textContent = pedido.numero;
            select.appendChild(option);
          });
          // Opcional: se só houver um pedido, pode desabilitar a escolha
          select.disabled = true;
        } else {
          data.forEach(function(pedido) {
            const option = document.createElement("option");
            option.value = pedido.id;
            option.textContent = pedido.numero;
            select.appendChild(option);
          });
          select.disabled = false;
        }
      })
      .catch(err => console.error("Erro ao carregar pedidos:", err));
  }
  
  