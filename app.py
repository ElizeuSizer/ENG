from flask import Flask, render_template, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Requisicao, RequisicaoAnexo, Pedido, NotaFiscal, NotaFiscalAnexo
from flask_migrate import Migrate
from forms import RegisterForm, LoginForm, RequisicaoForm, EngAbertaForm, RejeitarForm
import os
from flask import request
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_mail import Mail, Message
import pandas as pd
import uuid
import base64
from PIL import Image, ImageDraw, ImageFont
import fitz
from sentence_transformers import SentenceTransformer, util
import json
import numpy as np


app = Flask(__name__)
app.config['SECRET_KEY'] = "chave_secreta_super_segura"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


db.init_app(app)

embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

with open('data/faq.json', 'r', encoding='utf-8') as f:
    faqs = json.load(f)

faq_questions = [faq['input'] for faq in faqs]
faq_embeddings = embedding_model.encode(faq_questions, convert_to_tensor=True)




migrate = Migrate(app, db)
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = base64.b64encode(os.urandom(32)).decode('utf-8')
    return session['_csrf_token']

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token())

# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True  # Use SSL para a porta 465
app.config['MAIL_USERNAME'] = 'engenhariadanonecapex@gmail.com'
app.config['MAIL_PASSWORD'] = 'glilbapfxuzutbgw'
app.config['MAIL_DEFAULT_SENDER'] = 'engenhariadanonecapex@gmail.com'

mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    form = LoginForm()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Conta criada com sucesso!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)

            # **Se for ADMIN, redireciona para a área de administração**
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            
            # **Se for SOLICITANTE, redireciona para a área de Solicitantes**
            elif user.perfil == "Solicitante":
                return redirect(url_for('solicitante_dashboard'))

            # **Se for REQUISITANTE, redireciona para a área de Requisitantes**
            elif user.perfil == "Requisitante":
                return redirect(url_for('requisitante_dashboard'))

            # Se não tiver um perfil válido, volta para o login
            else:
                flash('Perfil inválido. Entre em contato com o administrador.', 'danger')
                return redirect(url_for('login'))

        else:
            flash('Usuário ou senha inválidos', 'danger')

    return render_template('login.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not getattr(current_user, "is_admin", False):
        flash('Acesso negado! Apenas administradores podem acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))

    form = RegisterForm()
    users = User.query.all()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Erro: Esse e-mail já está cadastrado.', 'danger')
        else:
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                perfil=form.perfil.data,  # Agora salvando o perfil corretamente
                is_admin=False
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Usuário {new_user.username} cadastrado como {new_user.perfil}!', 'success')
            return redirect(url_for('admin_dashboard'))  

    return render_template('admin.html', form=form, users=users)
  # Enviando os usuários para o template

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not getattr(current_user, "is_admin", False):
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuário {user.username} foi excluído com sucesso!', 'success')
    else:
        flash('Usuário não encontrado!', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/suporte')
def suporte():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('message')
    if not user_input:
        return jsonify({"answer": "Por favor, insira uma mensagem."})
    
    # Calcula o embedding da pergunta do usuário
    query_embedding = embedding_model.encode(user_input, convert_to_tensor=True)
    
    # Calcula a similaridade coseno entre a entrada do usuário e as perguntas do FAQ
    cos_scores = util.cos_sim(query_embedding, faq_embeddings)[0]
    
    # Encontra o índice da melhor correspondência
    best_idx = int(np.argmax(cos_scores))
    best_score = float(cos_scores[best_idx])
    
    # Defina um limiar para considerar uma correspondência como confiável
    threshold = 0.6
    if best_score < threshold:
        answer = "Desculpe, não entendi sua pergunta. Pode reformular?"
    else:
        answer = faqs[best_idx]['response']
    
    print("User input:", user_input)
    print("Best match:", faq_questions[best_idx])
    print("Score:", best_score)
    print("Answer:", answer)
    
    return jsonify({"answer": answer})

#SOLICITANTE !!!

@app.route('/solicitante_dashboard', methods=['GET', 'POST'])
@login_required
def solicitante_dashboard():
    if current_user.perfil != "Solicitante":
        flash('Acesso negado!', 'danger')
        return redirect(url_for('login'))
    
    form = RequisicaoForm()
    
    
    requisitantes = User.query.filter_by(perfil="Requisitante").all()
    form.requisitante.choices = [(str(u.id), u.username) for u in requisitantes]
    
  
    try:
        df = pd.read_excel("projetos.xlsx", header=None)
        projetos_sn = df.iloc[:, 0].dropna().tolist()   
        projetos_edp = df.iloc[:, 1].dropna().tolist()    # Coluna B para EDP
        locais_sn = df.iloc[:, 2].dropna().tolist()        # Coluna C para SN
        locais_edp = df.iloc[:, 3].dropna().tolist()       # Coluna D para EDP
    except Exception as e:
        projetos_sn, projetos_edp, locais_sn, locais_edp = [], [], [], []
        print(f"Erro ao ler projetos/locais do Excel: {str(e)}")
    
    # Atualizar as escolhas dos campos com base no valor de "planta"
    if request.method == "POST":
        if form.planta.data == "SN":
            form.projeto.choices = [("", "Selecione o projeto")] + [(proj, proj) for proj in projetos_sn]
            form.local_fabrica.choices = [("", "Selecione o local da fábrica")] + [(loc, loc) for loc in locais_sn]
        elif form.planta.data == "EDP":
            form.projeto.choices = [("", "Selecione o projeto")] + [(proj, proj) for proj in projetos_edp]
            form.local_fabrica.choices = [("", "Selecione o local da fábrica")] + [(loc, loc) for loc in locais_edp]
        else:
            form.projeto.choices = [("", "Selecione o projeto")]
            form.local_fabrica.choices = [("", "Selecione o local da fábrica")]
    else:
        # GET: define os valores padrão para exibição inicial
        form.projeto.choices = [("", "Selecione a planta primeiro")]
        form.local_fabrica.choices = [("", "Selecione a planta primeiro")]
    
    if form.validate_on_submit():
        try:
            requisitante_id = int(form.requisitante.data)
            
            # Cria a nova requisição
            nova_requisicao = Requisicao(
                descricao=form.descricao.data,
                requisitante_id=requisitante_id,
                solicitante_id=current_user.id,
                planta=form.planta.data,
                projeto=form.projeto.data,
                pertence_processo_produtivo=form.pertence_processo_produtivo.data,
                local_fabrica=form.local_fabrica.data,
                local_especifico=form.local_especifico.data,
                aplicabilidade=form.aplicabilidade.data,
                valor=form.valor.data
            )
            db.session.add(nova_requisicao)
            db.session.flush()  # Gera o ID da requisição para uso imediato
            
            # Processamento dos anexos (permitindo múltiplos arquivos)
            uploaded_files = request.files.getlist('attachments[]')
            print("Arquivos enviados:", len(uploaded_files))  # Debug
            for file in uploaded_files:
                if file and file.filename != "":
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{nova_requisicao.id}_{filename}")
                    file.save(file_path)
                    
                    novo_anexo = RequisicaoAnexo(
                        requisicao_id=nova_requisicao.id,
                        filename=filename,
                        filepath=file_path,
                        mimetype=file.content_type
                    )
                    db.session.add(novo_anexo)
            db.session.commit()
            
            # Enviar e-mail para o requisitante com link direcionando para o detalhe da requisição (rota solicitante)
            requisitante_user = User.query.get(requisitante_id)
            if requisitante_user and requisitante_user.email:
                from flask_mail import Message
                msg = Message(
                    subject="Nova Requisição Criada",
                    recipients=[requisitante_user.email]
                )
                # Gera o link usando a rota 'detalhe_requisicao_solicitante'
                detalhe_link = url_for('detalhe_requisicao_solicitante', requisicao_id=nova_requisicao.id, _external=True)
                msg.body = f"""
Olá {requisitante_user.username},

Uma nova requisição foi criada por {current_user.username}.

Detalhes:
- Descrição: {nova_requisicao.descricao}
- Projeto: {nova_requisicao.projeto}

Por favor, acesse o sistema para visualizar mais detalhes:
{detalhe_link}

Atenciosamente,
Equipe de Requisições
                """
                msg.html = f"""
<html>
  <head>
    <style>
      @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
        100% {{ transform: scale(1); }}
      }}
      .btn {{
        display: inline-block;
        background-color: #0075C9;
        color: #fff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
        animation: pulse 2s infinite;
      }}
    </style>
  </head>
  <body style="font-family: 'Roboto', sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #0075C9;">Nova Requisição Criada</h2>
      <p>Olá {requisitante_user.username},</p>
      <p>Uma nova requisição foi criada por <strong>{current_user.username}</strong>.</p>
      <p><strong>Detalhes:</strong></p>
      <ul>
        <li><strong>Descrição:</strong> {nova_requisicao.descricao}</li>
        <li><strong>Projeto:</strong> {nova_requisicao.projeto}</li>
      </ul>
      <p>Clique no botão abaixo para visualizar a requisição:</p>
      <p style="text-align: center;">
        <a href="{detalhe_link}" class="btn">Ver Requisição</a>
      </p>
    </div>
  </body>
</html>
                """
                msg.charset = 'utf-8'
                try:
                    mail.send(msg)
                    print(f"E-mail enviado para {requisitante_user.email}")
                except Exception as e:
                    print(f"Erro ao enviar e-mail para {requisitante_user.email}: {str(e)}")
            
            flash('Requisição enviada com sucesso!', 'success')
            return redirect(url_for('solicitante_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao salvar a requisição. Tente novamente!', 'danger')
            print(f"Erro: {str(e)}")
    
    return render_template('solicitante_dashboard.html', form=form, user=current_user,
                           projetos_sn=projetos_sn, projetos_edp=projetos_edp,
                           locais_sn=locais_sn, locais_edp=locais_edp)


@app.route('/minhas_requisicoes')
@login_required
def minhas_requisicoes():
    
    print(f"DEBUG: Usuário logado: ID={current_user.id}, Nome={current_user.username}")

    
    minhas_reqs = Requisicao.query.filter_by(solicitante_id=current_user.id).all()
    print(f"DEBUG: Total de requisições encontradas: {len(minhas_reqs)}")

    # Depuração: informações de cada requisição
    for req in minhas_reqs:
        pr_number = req.pr_number if hasattr(req, 'pr_number') else 'N/A'
        pedidos_info = [pedido.numero for pedido in req.pedidos] if req.pedidos else []
        print(f"DEBUG: Requisição ID={req.id} | PR: {pr_number} | Pedidos: {pedidos_info}")

    # Tenta carregar a planilha "cep.xlsx" para buscar os prazos
    prazos_dict = {}
    try:
        # Ajuste o caminho do arquivo se necessário
        df = pd.read_excel("cep.xlsx", header=None)

        prazos_dict = df.set_index(0)[5].to_dict()
        print(f"DEBUG: prazos_dict carregado com sucesso: {prazos_dict}")
    except Exception as e:
        print("DEBUG: Erro ao ler a planilha 'cep.xlsx':", str(e))

    # Depuração: verificação do prazo para cada requisição sem pedidos
    for req in minhas_reqs:
        if not req.pedidos or len(req.pedidos) == 0:
            chave = req.pr_number
            prazo = prazos_dict.get(chave)
            print(f"DEBUG: Verificando requisição ID={req.id} com PR={chave} -> Prazo encontrado: {prazo}")

    return render_template('minhas_requisicoes.html', requisicoes=minhas_reqs, prazos_dict=prazos_dict)



@app.route('/alterar_anexo/<int:requisicao_id>', methods=['GET', 'POST'])
@login_required
def alterar_anexo(requisicao_id):
    req = Requisicao.query.get_or_404(requisicao_id)
    
    # Apenas o solicitante (quem criou a requisição) pode alterar o anexo
    if req.solicitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('solicitante_dashboard'))
    
    if request.method == 'POST':
        # Verifica se o comentário foi fornecido
        comentario = request.form.get('comentario', '').strip()
        if not comentario:
            flash("Você deve escrever um comentário.", "danger")
            return redirect(url_for('alterar_anexo', requisicao_id=req.id))
        
        # Exclui os anexos antigos
        for anexo in req.anexos:
            if os.path.exists(anexo.filepath):
                os.remove(anexo.filepath)
            db.session.delete(anexo)
        db.session.commit()
        
        # Processa os novos anexos (permitindo múltiplos arquivos)
        uploaded_files = request.files.getlist('attachments[]')
        if not uploaded_files:
            flash("Nenhum arquivo foi selecionado!", "danger")
            return redirect(url_for('alterar_anexo', requisicao_id=req.id))
        
        for file in uploaded_files:
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{req.id}_{filename}")
                file.save(file_path)
                
                novo_anexo = RequisicaoAnexo(
                    requisicao_id=req.id,
                    filename=filename,
                    filepath=file_path,
                    mimetype=file.content_type
                )
                db.session.add(novo_anexo)
        db.session.commit()
        
        flash("Anexo alterado com sucesso! Comentário registrado: " + comentario, "success")
        
        # Enviar e-mail para o requisitante (quem recebeu a requisição)
        requisitante_user = User.query.get(req.requisitante_id)
        if requisitante_user and requisitante_user.email:
            from flask_mail import Message
            msg = Message(
                subject="Anexo Alterado na Requisição",
                recipients=[requisitante_user.email]
            )
            msg.body = f"""
Olá {requisitante_user.username},

O solicitante {current_user.username} alterou os anexos da requisição {req.id}.
Comentário: {comentario}

Por favor, acesse o sistema para visualizar os novos anexos.

Atenciosamente,
Equipe de Requisições
            """
            msg.html = f"""
<html>
  <head>
    <style>
      @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
        100% {{ transform: scale(1); }}
      }}
      .btn {{
        display: inline-block;
        background-color: #0075C9;
        color: #fff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
        animation: pulse 2s infinite;
      }}
    </style>
  </head>
  <body style="font-family: 'Roboto', sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #0075C9;">Anexo Alterado na Requisição {req.id}</h2>
      <p>Olá {requisitante_user.username},</p>
      <p>O solicitante <strong>{current_user.username}</strong> alterou os anexos da requisição <strong>{req.id}</strong>.</p>
      <p><strong>Comentário:</strong> {comentario}</p>
      <p>Clique no botão abaixo para visualizar a requisição:</p>
      <p style="text-align: center;">
        <a href="{url_for('detalhe_requisicao', requisicao_id=req.id, _external=True)}" class="btn">Ver Requisição</a>
      </p>
      <p>Atenciosamente,<br>Equipe de Requisições</p>
    </div>
  </body>
</html>
            """
            msg.charset = 'utf-8'
            try:
                mail.send(msg)
                print(f"E-mail enviado para {requisitante_user.email}")
            except Exception as e:
                print(f"Erro ao enviar e-mail para {requisitante_user.email}: {str(e)}")
        
        # Redireciona para a rota /minhas_requisicoes após a alteração
        return redirect(url_for('minhas_requisicoes'))
    
    # Se o método for GET, renderiza o formulário para alteração
    return render_template('alterar_anexo.html', requisicao=req)

@app.route('/download_anexo/<int:anexo_id>')
@login_required
def download_anexo(anexo_id):
    anexo = RequisicaoAnexo.query.get_or_404(anexo_id)
    # Verifique se o solicitante é o usuário logado para segurança
    if anexo.requisicao.solicitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('minhas_requisicoes'))
    
    # Extrair apenas o nome do arquivo (se o caminho completo estiver salvo)
    filename = os.path.basename(anexo.filepath)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, download_name=anexo.filename)

@app.route('/excluir_requisicao/<int:requisicao_id>', methods=['POST'])
@login_required
def excluir_requisicao(requisicao_id):
    requisicao = Requisicao.query.get_or_404(requisicao_id)

    # Verifica se o usuário logado é o dono da requisição (solicitante)
    if requisicao.solicitante_id != current_user.id:
        return jsonify({'error': 'Acesso negado'}), 403

    # Excluir anexos da requisição
    for anexo in requisicao.anexos:
        if os.path.exists(anexo.filepath):
            os.remove(anexo.filepath)
        db.session.delete(anexo)

    # Excluir NF's e seus anexos
    for nf in requisicao.nfs:
        for anexo_nf in nf.anexos:
            if os.path.exists(anexo_nf.filepath):
                os.remove(anexo_nf.filepath)
            db.session.delete(anexo_nf)
        db.session.delete(nf)

    # Excluir Pedidos associados
    for pedido in requisicao.pedidos:
        db.session.delete(pedido)

    # Excluir a própria requisição
    db.session.delete(requisicao)
    db.session.commit()

    return jsonify({'success': 'Requisição excluída com sucesso!'})


@app.route('/detalhe_requisicao_solicitante/<int:requisicao_id>')
@login_required
def detalhe_requisicao_solicitante(requisicao_id):
    req = Requisicao.query.get_or_404(requisicao_id)
    # Apenas o solicitante (quem criou a requisição) pode acessar estes detalhes
    if req.solicitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for("minhas_requisicoes"))
    
    # Separar as NF's em aprovadas e não aprovadas
    # (Utiliza o atributo 'aprovada' se existir; caso não, assume False)
    nfs_aprovadas = [nf for nf in req.nfs if getattr(nf, 'aprovada', False)]
    nfs_nao_aprovadas = [nf for nf in req.nfs if not getattr(nf, 'aprovada', False)]
    
    return render_template('detalhe_requisicao_solicitante.html', requisicao=req, 
                           nfs_aprovadas=nfs_aprovadas, nfs_nao_aprovadas=nfs_nao_aprovadas)

@app.route('/aprovar_nf/<int:nf_id>', methods=['POST'])
@login_required
def aprovar_nf(nf_id):
    nf = NotaFiscal.query.get_or_404(nf_id)
    
    # Verifica se o usuário logado (solicitante) tem permissão para aprovar a NF
    if nf.requisicao.solicitante_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado!"})
    
    nf.aprovada = True

    if not nf.anexos:
        return jsonify({"success": False, "message": "NF sem anexos para processar."})
    
    attachment = nf.anexos[0]
    nf_filepath = attachment.filepath

    signature_path = os.path.join(app.config['UPLOAD_FOLDER'], f"signature_{nf.requisicao.solicitante_id}.png")

    if nf_filepath.lower().endswith('.pdf'):
        try:
            doc = fitz.open(nf_filepath)
            last_page = doc[-1]
            page_width = last_page.rect.width
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao abrir o PDF: {str(e)}"})
        
        try:
            new_page_height = 300
            new_page = doc.new_page(width=page_width, height=new_page_height)
            
            today_str = datetime.now().strftime("%d/%m/%Y")
            approval_text = f"Aprovado por: {current_user.username}       {today_str}"
            margin = 20
            new_page.insert_text((margin, margin), approval_text, fontsize=12, color=(0, 0, 0))
            
            try:
                sig_img_pil = Image.open(signature_path)
            except Exception as e:
                return jsonify({"success": False, "message": f"Erro ao abrir a assinatura: {str(e)}"})
            
            sig_width = page_width * 0.3
            ratio = sig_width / sig_img_pil.width
            sig_height = sig_img_pil.height * ratio
            
            text_height = 20  
            x0 = (page_width - sig_width) / 2
            y0 = margin + text_height + 10
            x1 = x0 + sig_width
            y1 = y0 + sig_height
            sig_rect = fitz.Rect(x0, y0, x1, y1)
            
            new_page.insert_image(sig_rect, filename=signature_path, overlay=True)
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao inserir aprovação no PDF: {str(e)}"})
        
        try:
            temp_filepath = nf_filepath + ".tmp"
            doc.save(temp_filepath, encryption=fitz.PDF_ENCRYPT_NONE)
            doc.close()
            os.replace(temp_filepath, nf_filepath)
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao salvar o PDF atualizado: {str(e)}"})
    
    else:
        try:
            nf_image = Image.open(nf_filepath).convert("RGBA")
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao abrir o arquivo da NF: {str(e)}"})
        try:
            signature_img = Image.open(signature_path).convert("RGBA")
        except Exception as e:
            return jsonify({"success": False, "message": f"Assinatura não encontrada: {str(e)}"})
        
        nf_width, nf_height = nf_image.size
        new_signature_width = int(nf_width * 0.3)
        ratio = new_signature_width / signature_img.width
        new_signature_height = int(signature_img.height * ratio)
        signature_img = signature_img.resize((new_signature_width, new_signature_height), Image.Resampling.LANCZOS)
        
        padding = 20
        text_height = 30  
        new_height = nf_height + new_signature_height + padding + text_height
        combined_image = Image.new("RGBA", (nf_width, new_height), (255, 255, 255, 0))
        combined_image.paste(nf_image, (0, 0))
        
        draw = ImageDraw.Draw(combined_image)
        today_str = datetime.now().strftime("%d/%m/%Y")
        approval_text = f"Aprovado por: {current_user.username}       {today_str}"
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()
        text_bbox = draw.textbbox((0, 0), approval_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (nf_width - text_width) // 2
        text_y = nf_height + padding // 2
        draw.text((text_x, text_y), approval_text, fill="black", font=font)
        
        signature_x = (nf_width - new_signature_width) // 2
        signature_y = text_y + text_height
        combined_image.paste(signature_img, (signature_x, signature_y), mask=signature_img)
        
        try:
            combined_image.save(nf_filepath, "PNG")
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao salvar a NF atualizada: {str(e)}"})
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Erro ao atualizar o banco de dados: {str(e)}"})
    
    # Envio de e-mail para o requisitante (quem recebeu a requisição)
    requisitante_user = User.query.get(nf.requisicao.requisitante_id)
    if requisitante_user and requisitante_user.email:
        try:
            msg = Message(
                subject="Nota Fiscal Aprovada",
                recipients=[requisitante_user.email]
            )
            msg.body = f"""
Olá {requisitante_user.username},

A NF referente à requisição com ID {nf.requisicao.id} foi aprovada por {current_user.username}.
O arquivo da NF foi atualizado com a assinatura e a data de aprovação.

Por favor, acesse o sistema para visualizar os detalhes.

Atenciosamente,
Equipe de Requisições
            """
            msg.html = f"""
<html>
  <head>
    <style>
      .btn {{
        display: inline-block;
        background-color: #4CAF50;
        color: #fff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
        animation: pulse 2s infinite;
      }}
    </style>
  </head>
  <body style="font-family: 'Roboto', sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #4CAF50;">Nota Fiscal Aprovada</h2>
      <p>Olá {requisitante_user.username},</p>
      <p>A NF referente à requisição com ID <strong>{nf.requisicao.id}</strong> foi aprovada pelo solicitante <strong>{current_user.username}</strong>.</p>
      <p>O arquivo da NF foi atualizado com a assinatura e a data de aprovação.</p>
      <p style="text-align: center;">
        <a href="{url_for('detalhe_requisicao', requisicao_id=nf.requisicao.id, _external=True)}" class="btn">Ver Requisição</a>
      </p>
      <p>Atenciosamente,<br>Equipe de Requisições</p>
    </div>
  </body>
</html>
            """
            mail.send(msg)
            print(f"Depuração: E-mail enviado para {requisitante_user.email}")
        except Exception as e:
            print(f"Depuração: Erro ao enviar e-mail para {requisitante_user.email}: {str(e)}")
    else:
        print("Depuração: Requisitante não possui e-mail cadastrado.")
    
    return jsonify({"success": True, "message": "Nota Fiscal aprovada e atualizada com assinatura!"})



@app.route('/salvar_assinatura', methods=['POST'])
@login_required
def salvar_assinatura():
    data = request.get_json()
    signature_data = data.get("signature")
    if not signature_data:
        return jsonify({"success": False, "message": "Nenhuma assinatura enviada!"})
    
    # Decodifica a string base64 para bytes
    try:
        signature_bytes = base64.b64decode(signature_data)
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro na decodificação: {str(e)}"})
    
    # Define o caminho para salvar a assinatura (exemplo: UPLOAD_FOLDER/signature_<user_id>.png)
    filename = f"signature_{current_user.id}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        with open(filepath, "wb") as f:
            f.write(signature_bytes)
        # Opcional: atualizar o usuário no banco com o caminho da assinatura,
        # ex: current_user.signature = filename; db.session.commit()
        return jsonify({"success": True, "message": "Assinatura salva com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao salvar arquivo: {str(e)}"})

@app.route('/assinatura/<int:user_id>')
@login_required
def ver_assinatura(user_id):
    filename = f"signature_{user_id}.png"
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

@app.route('/download_nf/<int:nf_id>', methods=['GET'])
@login_required
def download_nf(nf_id):
    nf = NotaFiscal.query.get_or_404(nf_id)
    
    # Verifica se o usuário tem permissão para baixar a NF
    if nf.requisicao.solicitante_id != current_user.id and nf.requisicao.requisitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('minhas_requisicoes'))
    
    # Verifica se há anexos; aqui assumimos que o primeiro anexo é o arquivo da NF
    if not nf.anexos:
        flash("NF não possui anexos para download.", "danger")
        return redirect(url_for('detalhe_requisicao_solicitante', requisicao_id=nf.requisicao_id))
    
    attachment = nf.anexos[0]
    if not os.path.exists(attachment.filepath):
        flash("Arquivo não encontrado.", "danger")
        return redirect(url_for('detalhe_requisicao_solicitante', requisicao_id=nf.requisicao_id))
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        os.path.basename(attachment.filepath),
        as_attachment=True,
        download_name=attachment.filename
    )


#REQUISITANTE !!!
@app.route('/requisitante_dashboard')
@login_required
def requisitante_dashboard():
    if current_user.perfil != "Requisitante":
        flash("Acesso negado!", "danger")
        return redirect(url_for("login"))
    
    pendentes = Requisicao.query.filter(
        Requisicao.requisitante_id == current_user.id,
        Requisicao.eng_aberta == False,
        Requisicao.status != "Rejeitado"
    ).all()
    abertas = Requisicao.query.filter(
        Requisicao.requisitante_id == current_user.id,
        Requisicao.eng_aberta == True,
        Requisicao.status != "Rejeitado"
    ).all()
    
    return render_template("requisitante_dashboard.html", user=current_user,
                           pendentes=pendentes, abertas=abertas)



@app.route('/requisicao/<int:requisicao_id>')
@login_required
def detalhe_requisicao(requisicao_id):
    req = Requisicao.query.get_or_404(requisicao_id)
    
    if req.requisitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('requisitante_dashboard'))
    
    return render_template('detalhe_requisicao.html', requisicao=req)

@app.route('/download_attachment/<int:anexo_id>')
@login_required
def download_attachment(anexo_id):
    anexo = RequisicaoAnexo.query.get_or_404(anexo_id)
    
    # Se desejar permitir download para o solicitante OU para o requisitante:
    if (anexo.requisicao.solicitante_id != current_user.id and
        anexo.requisicao.requisitante_id != current_user.id):
        flash("Acesso negado!", "danger")
        return redirect(url_for('minhas_requisicoes'))
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        os.path.basename(anexo.filepath),
        as_attachment=True,
        download_name=anexo.filename
    )

@app.route('/eng_aberta/<int:requisicao_id>', methods=['GET', 'POST'])
@login_required
def eng_aberta(requisicao_id):
    req = Requisicao.query.get_or_404(requisicao_id)
    
    # Verifica se o usuário logado é o requisitante dessa requisição
    if req.requisitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('requisitante_dashboard'))
    
    form = EngAbertaForm()
    if form.validate_on_submit():
        req.eng_aberta = True
        req.eng_observacao = form.observacao.data
        req.pr_number = form.pr_number.data
        req.data_eng_aberta = datetime.utcnow()
        db.session.commit()

        # Enviar e-mail para o solicitante (quem criou a requisição)
        solicitante_user = User.query.get(req.solicitante_id)
        if solicitante_user and solicitante_user.email:
            from flask_mail import Message
            msg = Message(
                subject="ENG Aberta com PR Registrada",
                recipients=[solicitante_user.email]
            )
            
            # Gera o link para a rota detalhe_requisicao_solicitante
            detalhe_link = url_for('detalhe_requisicao_solicitante', requisicao_id=req.id, _external=True)
            
            # Versão plain text
            msg.body = f"""
Olá {solicitante_user.username},

A requisição com ID {req.id} foi atualizada pelo requisitante {current_user.username}.

Detalhes:
- Número da PR: {req.pr_number}
- Observação: {req.eng_observacao}

Acesse o sistema para visualizar a requisição:
{detalhe_link}

Atenciosamente,
Equipe de Requisições
            """
            
            # Versão HTML com design aprimorado
            msg.html = f"""
<html>
  <head>
    <meta charset="utf-8">
    <style>
      body {{
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f5;
        color: #333;
        margin: 0;
        padding: 0;
      }}
      .email-container {{
        max-width: 600px;
        margin: 20px auto;
        background: #fff;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      }}
      h2 {{
        color: #0075C9;
        font-size: 24px;
        margin-bottom: 20px;
      }}
      p {{
        font-size: 16px;
        line-height: 1.5;
      }}
      ul {{
        list-style: none;
        padding: 0;
      }}
      ul li {{
        background: #f9f9f9;
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 4px;
      }}
      .btn {{
        display: inline-block;
        background-color: #0075C9;
        color: #fff;
        text-decoration: none;
        padding: 12px 20px;
        border-radius: 4px;
        font-weight: bold;
        margin-top: 20px;
      }}
      .btn:hover {{
        background-color: #005fa3;
      }}
      .footer {{
        margin-top: 30px;
        font-size: 12px;
        color: #777;
      }}
    </style>
  </head>
  <body>
    <div class="email-container">
      <h2>ENG Aberta com PR Registrada</h2>
      <p>Olá {solicitante_user.username},</p>
      <p>A requisição com ID <strong>{req.id}</strong> foi atualizada pelo requisitante <strong>{current_user.username}</strong>.</p>
      <p><strong>Detalhes da atualização:</strong></p>
      <ul>
        <li><strong>Número da PR:</strong> {req.pr_number}</li>
        <li><strong>Observação:</strong> {req.eng_observacao}</li>
      </ul>
      <p>Clique no botão abaixo para visualizar a requisição:</p>
      <p style="text-align: center;">
        <a href="{detalhe_link}" class="btn">Ver Requisição</a>
      </p>
      <div class="footer">
        <p>Este é um e-mail automático. Por favor, não responda.</p>
        <p>Equipe de Requisições</p>
      </div>
    </div>
  </body>
</html>
            """
            msg.charset = 'utf-8'
            try:
                mail.send(msg)
                print(f"E-mail enviado para {solicitante_user.email}")
            except Exception as e:
                print(f"Erro ao enviar e-mail para {solicitante_user.email}: {str(e)}")

        flash("ENG registrada com sucesso!", "success")
        return redirect(url_for('detalhe_requisicao', requisicao_id=req.id))
    
    return render_template('eng_aberta.html', form=form, requisicao=req)


@app.route('/rejeitar/<int:requisicao_id>', methods=["GET", "POST"])
@login_required
def rejeitar_requisicao(requisicao_id):
    req = Requisicao.query.get_or_404(requisicao_id)
    
    # Verifica se o usuário logado é o requisitante
    if req.requisitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for("requisitante_dashboard"))
    
    form = RejeitarForm()
    if form.validate_on_submit():
        req.status = "Rejeitado"         # Atualiza para "Rejeitado"
        req.motivo_rejeicao = form.motivo.data
        req.data_rejeicao = datetime.utcnow()
        db.session.commit()
        
        # Envio de e-mail para o solicitante
        solicitante = User.query.get(req.solicitante_id)
        if solicitante and solicitante.email:
            from flask_mail import Message
            msg = Message(
                subject="Requisição Rejeitada",
                recipients=[solicitante.email]  # Envia o e-mail para o solicitante
            )
            msg.body = f"""
Olá {solicitante.username},

A requisição com ID {req.id} foi rejeitada pelo requisitante {current_user.username}.
Motivo da rejeição: {req.motivo_rejeicao}

Por favor, acesse o sistema para visualizar os detalhes.

Atenciosamente,
Equipe de Requisições
            """
            msg.html = f"""
<html>
  <head>
    <style>
      @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
        100% {{ transform: scale(1); }}
      }}
      .btn {{
        display: inline-block;
        background-color: #0075C9;
        color: #fff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
        animation: pulse 2s infinite;
      }}
    </style>
  </head>
  <body style="font-family: 'Roboto', sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
      <h2 style="color: #0075C9;">Requisição Rejeitada</h2>
      <p>Olá {solicitante.username},</p>
      <p>A requisição com ID <strong>{req.id}</strong> foi rejeitada pelo requisitante <strong>{current_user.username}</strong>.</p>
      <p><strong>Motivo da rejeição:</strong> {req.motivo_rejeicao}</p>
      <p>Clique no botão abaixo para visualizar a requisição:</p>
      <p style="text-align: center;">
        <a href="{url_for('detalhe_requisicao', requisicao_id=req.id, _external=True)}" class="btn">Ver Requisição</a>
      </p>
    </div>
  </body>
</html>
            """
            try:
                mail.send(msg)
                print(f"E-mail enviado para {solicitante.email}")
            except Exception as e:
                print(f"Erro ao enviar e-mail: {str(e)}")
        
        flash("Requisição rejeitada com sucesso!", "success")
        return redirect(url_for("detalhe_requisicao", requisicao_id=req.id))
    
    return render_template("rejeitar_requisicao.html", form=form, requisicao=req)

@app.route('/adicionar_pedido', methods=['POST'])
@login_required
def adicionar_pedido():
    if current_user.perfil != "Requisitante":
        flash("Acesso negado!", "danger")
        return redirect(url_for("login"))

    numero_pedido = request.form.get("numero_pedido")
    requisicao_id = request.form.get("requisicao_id")  # Novo campo

    if not numero_pedido:
        flash("Número do pedido é obrigatório!", "danger")
        return redirect(url_for("requisitante_dashboard"))

    if not requisicao_id:
        flash("Requisição não informada!", "danger")
        return redirect(url_for("requisitante_dashboard"))

    # Verifica se o número do pedido já existe
    pedido_existente = Pedido.query.filter_by(numero=numero_pedido).first()
    if pedido_existente:
        flash("Este número de pedido já está cadastrado!", "warning")
        return redirect(url_for("requisitante_dashboard"))

    # Busca a requisição com o ID passado
    requisicao = Requisicao.query.get(requisicao_id)
    if not requisicao:
        flash("Requisição não encontrada!", "warning")
        return redirect(url_for("requisitante_dashboard"))

    # Cria e vincula o pedido à requisição correta
    novo_pedido = Pedido(numero=numero_pedido, requisicao_id=requisicao.id)
    db.session.add(novo_pedido)
    try:
        db.session.commit()
        flash("Pedido adicionado à requisição com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        print("DEBUG: Erro ao adicionar pedido:", e)
        flash("Erro ao adicionar o pedido.", "danger")

    return redirect(url_for("requisitante_dashboard"))


@app.route('/adicionar_nf', methods=['POST'])
@login_required
def adicionar_nf():
    app.logger.debug("Iniciando a rota adicionar_nf")
    
    req_id = request.form.get("req_id_nf")
    nf_valor = request.form.get("nf_valor")
    pedido_id = request.form.get("pedido_id")  # Pode vir vazio se só houver um pedido
    
    app.logger.debug(f"Valores recebidos - req_id: {req_id}, nf_valor: {nf_valor}, pedido_id: {pedido_id}")

    # Verificações iniciais para req_id e nf_valor
    if not req_id or not nf_valor:
        app.logger.error("Requisição ou valor da NF não informados!")
        flash("Valor da NF e ID da requisição são obrigatórios!", "danger")
        return redirect(url_for("requisitante_dashboard"))

    # Busca a requisição e valida se pertence ao usuário atual
    req = Requisicao.query.get_or_404(req_id)
    app.logger.debug(f"Requisição encontrada: {req}")

    # Se pedido_id não for informado, tenta buscar o único pedido associado à requisição
    if not pedido_id:
        pedidos = Pedido.query.filter_by(requisicao_id=req.id).all()
        if len(pedidos) == 1:
            pedido_selecionado = pedidos[0]
            app.logger.debug(f"Apenas um pedido encontrado, selecionando automaticamente: {pedido_selecionado}")
        else:
            app.logger.error("Pedido não informado e não há um único pedido associado!")
            flash("Selecione um pedido ou certifique-se de que há apenas um pedido associado à requisição.", "danger")
            return redirect(url_for("requisitante_dashboard"))
    else:
        # Se o pedido foi informado, valida se ele pertence à requisição
        pedido_selecionado = Pedido.query.filter_by(id=pedido_id, requisicao_id=req.id).first()
        if not pedido_selecionado:
            app.logger.error("Pedido selecionado inválido!")
            flash("Pedido selecionado inválido!", "danger")
            return redirect(url_for("requisitante_dashboard"))
        app.logger.debug(f"Pedido selecionado: {pedido_selecionado}")

    # Verifica se há arquivos anexados
    uploaded_files = request.files.getlist("nf_attachments[]")
    if not uploaded_files or all(file.filename == "" for file in uploaded_files):
        app.logger.error("Nenhum arquivo válido foi enviado!")
        flash("Nenhum arquivo válido foi enviado!", "danger")
        return redirect(url_for("requisitante_dashboard"))
    app.logger.debug(f"{len(uploaded_files)} arquivos recebidos")

    try:
        # Gerar um número temporário para a NF
        nf_numero_temp = f"NF_{uuid.uuid4().hex[:8]}"
        app.logger.debug(f"Número temporário da NF gerado: {nf_numero_temp}")
        
        # Cria a NF associando ao pedido selecionado
        nf = NotaFiscal(
            numero=nf_numero_temp,
            valor=nf_valor,
            requisicao_id=req.id,
            pedido_id=pedido_selecionado.id,
            criado_em=datetime.utcnow()
        )
        db.session.add(nf)
        db.session.flush()  # Gera o ID da NF
        app.logger.debug(f"NF criada com ID temporário: {nf.id}")

        if not nf.id:
            db.session.rollback()
            app.logger.error("Erro ao salvar a Nota Fiscal no banco (ID não gerado)!")
            flash("Erro ao salvar a Nota Fiscal no banco!", "danger")
            return redirect(url_for("requisitante_dashboard"))

        # Atualiza o número da NF para garantir exclusividade
        nf.numero = f"NF_{nf.id}"
        db.session.flush()
        app.logger.debug(f"Número final da NF atualizado para: {nf.numero}")

        # Salvar os anexos enviados
        anexos_salvos = 0
        for file in uploaded_files:
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{nf.id}_{filename}")
                file.save(file_path)
                app.logger.debug(f"Arquivo salvo: {file_path}")

                novo_anexo = NotaFiscalAnexo(
                    notafiscal_id=nf.id,
                    filename=filename,
                    filepath=file_path,
                    mimetype=file.content_type,
                    uploaded_at=datetime.utcnow()
                )
                db.session.add(novo_anexo)
                anexos_salvos += 1
        app.logger.debug(f"Total de anexos salvos: {anexos_salvos}")

        if anexos_salvos == 0:
            db.session.rollback()
            app.logger.error("Erro ao salvar anexos da NF!")
            flash("Erro ao salvar anexos da NF!", "danger")
            return redirect(url_for("requisitante_dashboard"))

        db.session.commit()
        app.logger.debug("Transação commitada com sucesso")

        # Envio de e-mail para o solicitante (quem criou a requisição)
        solicitante = User.query.get(req.solicitante_id)
        app.logger.debug(f"Solicitante obtido: {solicitante}")
        if solicitante and solicitante.email:
            try:
                from flask_mail import Message
                msg = Message(
                    subject="Nova Nota Fiscal Registrada",
                    recipients=[solicitante.email]
                )
                # Gera o link utilizando a rota detalhe_requisicao_solicitante
                detalhe_link = url_for('detalhe_requisicao_solicitante', requisicao_id=req.id, _external=True)
                pedido_info = pedido_selecionado.numero if pedido_selecionado else "Não informado"
                msg.body = f"""
Olá {solicitante.username},

Uma nova Nota Fiscal referente à requisição com ID {req.id} e Pedido {pedido_info} foi registrada com valor de R$ {nf_valor}.
Clique no link abaixo para visualizar os detalhes da NF:
{detalhe_link}

Atenciosamente,
Equipe de Requisições
                """
                msg.html = f"""
<html>
<head>
    <style>
    .btn {{
        display: inline-block;
        background-color: #0075C9;
        color: #fff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
    }}
    </style>
</head>
<body style="font-family: 'Roboto', sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
    <h2 style="color: #0075C9;">Nova Nota Fiscal Registrada</h2>
    <p>Olá {solicitante.username},</p>
    <p>Uma nova Nota Fiscal referente à requisição com ID <strong>{req.id}</strong> e Pedido <strong>{pedido_info}</strong> foi registrada com valor de R$ {nf_valor}.</p>
    <p>Clique no botão abaixo para visualizar os detalhes da NF:</p>
    <p style="text-align: center;">
        <a href="{detalhe_link}" class="btn">Ver NF</a>
    </p>
    <p>Atenciosamente,<br>Equipe de Requisições</p>
    </div>
</body>
</html>
                """
                mail.send(msg)
                app.logger.debug("E-mail enviado com sucesso para o solicitante")
            except Exception as e:
                app.logger.error(f"Falha ao enviar e-mail: {e}")
                print(f"[ERRO] Falha ao enviar e-mail: {e}")

        flash("Nota Fiscal registrada e e-mail enviado!", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Exceção ao salvar NF: {e}")
        flash("Erro ao salvar a Nota Fiscal!", "danger")
        print(f"[ERRO] Exceção ao salvar NF: {e}")

    return redirect(url_for("requisitante_dashboard"))



@app.route('/excluir_nf')
@login_required
def excluir_nf():
    nf_id = request.args.get("nf_id")
    req_id = request.args.get("req_id")
    
    if not nf_id or not req_id:
        return jsonify(success=False, message="Parâmetros inválidos para exclusão da NF.")
    
    nf = NotaFiscal.query.get(nf_id)
    if not nf:
        return jsonify(success=False, message="Nota Fiscal não encontrada.")
    
    # Exclui os anexos associados à NF
    for anexo in nf.anexos:
        if os.path.exists(anexo.filepath):
            try:
                os.remove(anexo.filepath)
            except Exception as e:
                print("Erro ao remover arquivo:", e)
        db.session.delete(anexo)
    
    db.session.delete(nf)
    try:
        db.session.commit()
        return jsonify(success=True, message="Nota Fiscal excluída com sucesso!")
    except Exception as e:
        db.session.rollback()
        print("Erro ao excluir NF:", e)
        return jsonify(success=False, message="Erro ao excluir a Nota Fiscal.")


@app.route('/get_nf_list/<int:req_id>')
@login_required
def get_nf_list(req_id):
    req = Requisicao.query.get_or_404(req_id)
    # Verifica se o usuário tem acesso à requisição
    if req.requisitante_id != current_user.id:
        return jsonify({'error': 'Acesso negado'}), 403

    nf_list = []
    for nf in req.nfs:
        anexos = []
        for anexo in nf.anexos:
            anexos.append({
                'anexo_id': anexo.id,
                'filename': anexo.filename
            })
        
        # Inclui o número do pedido, se existir; caso contrário, exibe "Sem pedido"
        pedido_info = nf.pedido.numero if nf.pedido else "Sem pedido"
        
        nf_list.append({
            'id': nf.id,
            'numero': nf.numero,
            'valor': nf.valor,
            'pedido': pedido_info,
            'anexos': anexos
        })
    
    return jsonify(nf_list)


@app.route('/get_pedido_list/<int:req_id>')
@login_required
def get_pedido_list(req_id):
    req = Requisicao.query.get_or_404(req_id)
    if req.requisitante_id != current_user.id:
        return jsonify({'error': 'Acesso negado'}), 403
    pedidos = [{'id': pedido.id, 'numero': pedido.numero} for pedido in req.pedidos]
    return jsonify(pedidos)


@app.route('/download_nf_anexo/<int:anexo_id>')
@login_required
def download_nf_anexo(anexo_id):
    anexo = NotaFiscalAnexo.query.get_or_404(anexo_id)
    # Verifica permissões e envia arquivo
    req = anexo.notafiscal.requisicao
    if req.requisitante_id != current_user.id:
        flash("Acesso negado!", "danger")
        return redirect(url_for('requisitante_dashboard'))
    
    if not os.path.exists(anexo.filepath):
        flash("Arquivo não encontrado no servidor.", "danger")
        return redirect(url_for('requisitante_dashboard'))
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        os.path.basename(anexo.filepath),
        as_attachment=True,
        download_name=anexo.filename
    )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado!', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)

