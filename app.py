from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    # Criar a tabela de produtos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT NOT NULL,
        preco REAL NOT NULL,
        imagem TEXT NOT NULL
    )''')

    conn.commit()
    conn.close()

def verificar_e_adicionar_coluna():
    conn = sqlite3.connect('store.db')
    c = conn.cursor()

    # Verificar se a coluna 'tamanhos' existe
    c.execute("PRAGMA table_info(produtos)")
    colunas = [info[1] for info in c.fetchall()]
    
    if 'tamanhos' not in colunas:
        c.execute("ALTER TABLE produtos ADD COLUMN tamanhos TEXT")
        conn.commit()
        print("Coluna 'tamanhos' adicionada com sucesso!")
    else:
        print("Coluna 'tamanhos' já existe.")

    conn.close()

verificar_e_adicionar_coluna()

def remover_produto(id):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()

    # Remover o produto com o ID especificado
    c.execute('DELETE FROM produtos WHERE id = ?', (id,))

    conn.commit()
    conn.close()

def add_default_admin():
    """Add a default admin if none exists."""
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)",
                  ("admin", generate_password_hash("admin")))
        conn.commit()
    conn.close()

@app.route('/')
def home():
    # Conectar ao banco de dados
    conn = get_db_connection()

    # Consulta para pegar todos os produtos
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    categorias = conn.execute('SELECT * FROM categorias').fetchall()  # Buscando todas as categorias

    # Fechar a conexão
    conn.close()

    # Passar os produtos para o template
    return render_template('index.html', produtos=produtos, categorias=categorias)

def get_db_connection():
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verificar credenciais no banco de dados
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['admin'] = username  # Salva na sessão
            flash('Login bem-sucedido!', 'success')
            return redirect('/admin/dashboard')  # Página de administração
        else:
            flash('Usuário ou senha inválidos!', 'danger')

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin/login')
    
    # Conectar ao banco de dados e buscar todos os produtos
    conn = get_db_connection()
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    conn.close()

    # Passar os produtos para o template
    return render_template('dashboard.html', produtos=produtos)

UPLOAD_FOLDER = 'static/produtos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/admin/adicionar-produto', methods=['GET', 'POST'])
def adicionar_produto():
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db_connection()
    
    # Buscar as categorias disponíveis para o formulário
    categorias = conn.execute('SELECT * FROM categorias').fetchall()

    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']

        # Capturar os tamanhos selecionados
        tamanhos = request.form.getlist('tamanhos')
        tamanhos_str = ",".join(tamanhos)  # Transformar em string separada por vírgulas

        # Capturar a categoria selecionada
        categoria_id = request.form.get('categorias')  # Vai pegar o ID da categoria selecionada

        # Verifique se a imagem foi enviada
        imagem = request.files['imagem']
        if imagem and allowed_file(imagem.filename):
            # Salvando a imagem com um nome seguro
            filename = secure_filename(imagem.filename)
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Inserir as informações no banco de dados, incluindo tamanhos e categoria
            conn.execute('''INSERT INTO produtos (nome, descricao, preco, imagem, tamanhos, categoria_id) 
                            VALUES (?, ?, ?, ?, ?, ?)''', (nome, descricao, preco, filename, tamanhos_str, categoria_id))
            conn.commit()
            conn.close()

            flash('Produto adicionado com sucesso!', 'success')
            return redirect('/admin/dashboard')

    return render_template('adicionar-produto.html', categorias=categorias)



@app.route('/admin/editar-produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    conn = get_db_connection()
    
    # Buscar o produto no banco de dados
    produto = conn.execute('SELECT * FROM produtos WHERE id = ?', (id,)).fetchone()
    
    if produto is None:
        flash('Produto não encontrado!', 'danger')
        return redirect('/admin/dashboard')

    # Buscar as categorias disponíveis para o formulário
    categorias = conn.execute('SELECT * FROM categorias').fetchall()
    
    if request.method == 'POST':
        # Capturar os dados do formulário
        nome = request.form['nome']
        preco = request.form['preco'].replace(',', '.')  # Substitui a vírgula por ponto
        imagem = request.form['imagem']  # Caso queira atualizar a imagem ou deixá-la igual
        descricao = request.form['descricao']  # Nova descrição

        tamanhos = request.form.getlist('tamanhos')  # Obtém os tamanhos selecionados do formulário
        tamanhos_str = ",".join(tamanhos)

        # Capturar a categoria selecionada
        categoria_id = request.form.get('categorias')

        # Atualizar o produto no banco de dados
        conn.execute('''UPDATE produtos SET nome = ?, preco = ?, imagem = ?, descricao = ?, tamanhos = ?, categoria_id = ? 
                        WHERE id = ?''', (nome, preco, imagem, descricao, tamanhos_str, categoria_id, id))
        conn.commit()
        conn.close()

        flash('Produto atualizado com sucesso!', 'success')
        return redirect('/admin/dashboard')
    
    # Caso seja uma requisição GET, exibe o formulário com os dados atuais
    tamanhos_produto = produto['tamanhos'].split(",") if produto['tamanhos'] else []
    categoria_produto = produto['categoria_id']  # Obtém a categoria associada ao produto

    return render_template('editar-produto.html', produto=produto, tamanhos_selecionados=tamanhos_produto, categorias=categorias, categoria_produto=categoria_produto)



@app.route('/produto/<int:id>')
def detalhe_produto(id):
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row  # Isso permite acessar as colunas por nome
    c = conn.cursor()
    c.execute('SELECT * FROM produtos WHERE id = ?', (id,))
    produto = c.fetchone()
    conn.close()

    if produto:
        return render_template('detalhe-produto.html', produto=produto)
    else:
        return "Produto não encontrado", 404
    
@app.route('/admin/categorias', methods=['GET'])
def admin_categorias():
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db_connection()
    categorias = conn.execute('SELECT * FROM categorias').fetchall()  # Buscando todas as categorias
    conn.close()

    return render_template('categorias.html', categorias=categorias)

    
@app.route('/admin/editar-categoria/<int:id>', methods=['GET', 'POST'])
def editar_categoria(id):
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db_connection()
    
    # Buscar a categoria no banco
    categoria = conn.execute('SELECT * FROM categorias WHERE id = ?', (id,)).fetchone()
    
    if not categoria:
        flash('Categoria não encontrada!', 'danger')
        return redirect('/admin/categorias')

    if request.method == 'POST':
        novo_nome = request.form['categoria_nome']
        
        # Atualizar a categoria
        conn.execute('UPDATE categorias SET nome = ? WHERE id = ?', (novo_nome, id))
        conn.commit()
        conn.close()

        flash('Categoria atualizada com sucesso!', 'success')
        return redirect('/admin/categorias')

    return render_template('editar-categoria.html', categoria=categoria)

@app.route('/admin/remover-categoria/<int:id>', methods=['GET'])
def remover_categoria(id):
    if 'admin' not in session:
        return redirect('/admin/login')

    conn = get_db_connection()
    
    # Remover a categoria
    conn.execute('DELETE FROM categorias WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Categoria removida com sucesso!', 'success')
    return redirect('/admin/categorias')

@app.route('/admin/adicionar-categoria', methods=['POST'])
def adicionar_categoria():
    if 'admin' not in session:
        return redirect('/admin/login')

    nome_categoria = request.form['categoria_nome']

    # Conectar ao banco de dados
    conn = get_db_connection()

    # Verificar se a categoria já existe
    categoria_existente = conn.execute('SELECT * FROM categorias WHERE nome = ?', (nome_categoria,)).fetchone()

    if categoria_existente:
        flash('A categoria já existe!', 'danger')
        conn.close()
        return redirect('/admin/dashboard')

    # Limite de 8 categorias
    categorias_count = conn.execute('SELECT COUNT(*) FROM categorias').fetchone()[0]
    if categorias_count >= 8:
        flash('Limite de 8 categorias atingido!', 'danger')
        conn.close()
        return redirect('/admin/categorias')

    # Inserir a nova categoria
    conn.execute('INSERT INTO categorias (nome) VALUES (?)', (nome_categoria,))
    conn.commit()
    conn.close()

    flash('Categoria adicionada com sucesso!', 'success')
    return redirect('/admin/categorias')

@app.route('/categorias', methods=['GET'])
def categorias():

    conn = get_db_connection()
    categorias = conn.execute('SELECT * FROM categorias').fetchall()  # Buscando todas as categorias
    conn.close()

    return render_template('index.html', categorias=categorias)


@app.route('/categorias/<categoria_nome>', methods=['GET'])
def categoria_produto(categoria_nome):
    # Conectar ao banco de dados
    conn = get_db_connection()

    # Buscar a categoria no banco de dados, usando LOWER() para tornar a busca insensível a maiúsculas/minúsculas
    categoria = conn.execute('SELECT * FROM categorias WHERE LOWER(nome) = ?', (categoria_nome.lower(),)).fetchone()

    if categoria:
        # Buscar os produtos relacionados a essa categoria
        produtos = conn.execute('SELECT * FROM produtos WHERE categoria_id = ?', (categoria['id'],)).fetchall()
        categorias = conn.execute('SELECT * FROM categorias').fetchall()
        conn.close()

        # Renderizar o template com os produtos
        return render_template('categoria-produtos.html', categoria=categoria, produtos=produtos, categorias=categorias)
    else:
        conn.close()
        return "Categoria não encontrada", 404
    
@app.route('/carrinho')
def carrinho():
    carrinho = session.get('carrinho', [])
    return render_template('carrinho.html', carrinho=carrinho)

@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    produto_id = request.form.get('produto_id')
    produto_nome = request.form.get('produto_nome')
    produto_preco = float(request.form.get('produto_preco'))  # Convertendo o preço para float
    produto_imagem = request.form.get('produto_imagem')

    # Verificar se já existe um carrinho na sessão
    if 'carrinho' not in session:
        session['carrinho'] = []

    # Verificar se o produto já está no carrinho
    carrinho = session['carrinho']
    for item in carrinho:
        if item['id'] == produto_id:
            item['quantidade'] += 1  # Incrementa a quantidade se o produto já estiver no carrinho
            session.modified = True  # Marca a sessão como modificada
            return redirect(url_for('carrinho'))  # Redireciona para o carrinho

    # Caso o produto não esteja no carrinho, adicione-o com quantidade 1
    produto = {
        'id': produto_id,
        'nome': produto_nome,
        'preco': produto_preco,
        'imagem': produto_imagem,
        'quantidade': 1  # Adiciona a quantidade inicial como 1
    }
    session['carrinho'].append(produto)

    # Atualizar a sessão
    session.modified = True

    # Redirecionar para a página do carrinho
    return redirect(url_for('carrinho'))


@app.route('/remover_ao_carrinho/<int:produto_id>')
def remover_ao_carrinho(produto_id):
    # Verifica se o carrinho existe na sessão
    if 'carrinho' not in session:
        return redirect(url_for('carrinho'))  # Se o carrinho não existir, redireciona para a página do carrinho

    carrinho = session['carrinho']
    
    # Converte o produto_id para string para garantir que a comparação seja consistente
    produto_id_str = str(produto_id)
    
    # Itera sobre o carrinho para encontrar o produto e modificar a quantidade ou remover
    for item in carrinho:
        if item['id'] == produto_id_str:  # Agora ambos são strings
            if item['quantidade'] > 1:
                item['quantidade'] -= 1  # Decrementa a quantidade
            else:
                carrinho.remove(item)  # Remove o item se a quantidade for 1
            break

    # Atualiza a sessão
    session.modified = True

    return redirect(url_for('carrinho'))



@app.route('/remover-produto/<int:id>', methods=['POST'])
def remover_produto_route(id):
    remover_produto(id)  # Chama a função para remover o produto
    return redirect('/admin/dashboard')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Você saiu!', 'info')
    return redirect('/admin/login')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    init_db()
    add_default_admin()
    app.run(debug=True)
