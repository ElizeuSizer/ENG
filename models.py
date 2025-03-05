from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime
import pytz

db = SQLAlchemy()
bcrypt = Bcrypt()

def get_local_time():
    local_tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(local_tz)
                        
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    perfil = db.Column(db.String(20), nullable=False, default="Requisitante")

    # Métodos para segurança da senha
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


class Requisicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    requisitante_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    planta = db.Column(db.String(10), nullable=False)
    projeto = db.Column(db.String(100), nullable=False)
    pertence_processo_produtivo = db.Column(db.String(3), nullable=False)  # Sim ou Não
    local_fabrica = db.Column(db.String(255), nullable=False)
    local_especifico = db.Column(db.String(255), nullable=False)
    aplicabilidade = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.String(50), nullable=True)
    data_criacao = db.Column(db.DateTime, default=get_local_time) 
    
    # Status da requisição
    status = db.Column(db.String(20), default="Pendente")
    
    # Campos para ENG aberta
    eng_aberta = db.Column(db.Boolean, default=False)
    eng_observacao = db.Column(db.Text, nullable=True)
    pr_number = db.Column(db.String(50), nullable=True)
    data_eng_aberta = db.Column(db.DateTime, nullable=True)

    solicitante = db.relationship('User', foreign_keys=[solicitante_id],
                                   backref=db.backref('solicitacoes', cascade="all, delete-orphan", passive_deletes=True),
                                   lazy=True)
    requisitante = db.relationship('User', foreign_keys=[requisitante_id],
                                   backref=db.backref('requisicoes', cascade="all, delete-orphan", passive_deletes=True),
                                   lazy=True)
    anexos = db.relationship('RequisicaoAnexo', backref='requisicao', lazy=True)

    nfs = db.relationship('NotaFiscal', backref='requisicao', lazy=True)


class RequisicaoAnexo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)  # Caminho onde o arquivo foi salvo
    mimetype = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False, unique=True)
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao.id'), nullable=False)
    criado_em = db.Column(db.DateTime, default=get_local_time)

    # Alteramos o backref para 'pedidos', criando um relacionamento 1:N
    requisicao = db.relationship('Requisicao', backref=db.backref('pedidos', lazy=True))


class NotaFiscal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    valor = db.Column(db.String(50), nullable=False)
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao.id'), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=True)
    criado_em = db.Column(db.DateTime, default=get_local_time)
    anexos = db.relationship('NotaFiscalAnexo', backref='notafiscal', lazy=True)
    pedido = db.relationship('Pedido', backref=db.backref('notas_fiscais', lazy=True), foreign_keys=[pedido_id])
    aprovada = db.Column(db.Boolean, default=False)  # Campo para aprovação

    
    # Relacionamento opcional para facilitar o acesso ao Pedido:
    pedido = db.relationship('Pedido', backref=db.backref('notas_fiscais', lazy=True), foreign_keys=[pedido_id])




class NotaFiscalAnexo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notafiscal_id = db.Column(db.Integer, db.ForeignKey('nota_fiscal.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=get_local_time)
