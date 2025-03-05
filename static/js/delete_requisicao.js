document.addEventListener("DOMContentLoaded", function () {
    let requisicaoIdParaExcluir = null;

    function abrirConfirmacao(requisicaoId) {
        requisicaoIdParaExcluir = requisicaoId;
        document.getElementById("confirm-modal").style.display = "flex";

    }

    function fecharConfirmacao() {
        document.getElementById("confirm-modal").style.display = "none";
    }

    document.getElementById("confirm-delete").addEventListener("click", function () {
        if (requisicaoIdParaExcluir) {
            fetch(`/excluir_requisicao/${requisicaoIdParaExcluir}`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json"
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("Requisição excluída com sucesso!");
                    document.getElementById(`requisicao-${requisicaoIdParaExcluir}`).remove();
                } else {
                    alert("Erro ao excluir: " + data.error);
                }
                fecharConfirmacao();
            })
            .catch(error => console.error("Erro:", error));
        }
    });

    // Fechar modal ao clicar fora do conteúdo
    window.addEventListener("click", function (event) {
        const modal = document.getElementById("confirm-modal");
        if (event.target === modal) {
            fecharConfirmacao();
        }
    });

    // Disponibilizar funções globalmente
    window.abrirConfirmacao = abrirConfirmacao;
    window.fecharConfirmacao = fecharConfirmacao;
});
document.querySelectorAll('.btn-details').forEach(function(button) {
    button.addEventListener('click', function() {
      var url = this.getAttribute('data-url');
      window.location.href = url;
    });
  });
  
