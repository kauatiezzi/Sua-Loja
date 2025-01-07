document.addEventListener('DOMContentLoaded', function () {
    // Selecionar todos os botões de remover
    const removerBtns = document.querySelectorAll('.remover-btn');

    // Adicionar evento de clique a cada botão
    removerBtns.forEach(function (button) {
        button.addEventListener('click', function () {
            const itemId = this.getAttribute('data-id'); // Pega o ID do item armazenado no data-id
            removerDoCarrinho(itemId); // Chama a função de remoção
        });
    });

    // Função para remover o item do carrinho
    function removerDoCarrinho(itemId) {
        fetch(`/remover_ao_carrinho/${itemId}`, {
            method: 'POST',
        })
        .then(response => {
            if (response.ok) {
                // Atualiza a interface do carrinho
                atualizarCarrinho();
            }
        })
        .catch(error => console.error('Erro ao remover item:', error));
    }

    // Função para atualizar a interface do carrinho
    function atualizarCarrinho() {
        fetch('/carrinho')
            .then(response => response.text())
            .then(html => {
                document.querySelector('#carrinho-container').innerHTML = html;
            });
    }
});
