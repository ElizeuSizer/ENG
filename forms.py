from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegisterForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = StringField('Senha', validators=[DataRequired(), Length(min=6)])  # Senha visível para facilitar cadastro
    confirm_password = StringField('Confirme a Senha', validators=[DataRequired(), EqualTo('password')])
    perfil = SelectField('Perfil', choices=[('Requisitante', 'Requisitante'), ('Solicitante', 'Solicitante')], validators=[DataRequired()])
    submit = SubmitField('Cadastrar')

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RequisicaoForm(FlaskForm):
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    
    # ✅ Definindo corretamente para evitar erro
    requisitante = SelectField(
        'Requisitante',
        choices=[],  # Começa sem opções, será preenchido no app.py
        validators=[DataRequired()],
        coerce=int  # Garante que os valores serão convertidos corretamente para int
    )

    planta = SelectField('Planta', choices=[
        ("", "Selecione..."),  # Opção vazia inicial
        ("SN", "SN"),
        ("EDP", "EDP")
    ], validators=[DataRequired()])

    local_fabrica = SelectField('Local da Fábrica', choices=[
        ("", "Selecione...")  # Opção vazia inicial
    ], validators=[DataRequired()])

    projeto = SelectField('Projeto', choices=[
        ("", "Selecione..."),
        ("@8102402 BRAZIL SN SAFETY", "@8102402 BRAZIL SN SAFETY"),
        ("@8102403 BRAZIL SN QUALITY", "@8102403 BRAZIL SN QUALITY"),
        ("@2102402 BEST OF SECURITY AND SAFETY", "@2102402 BEST OF SECURITY AND SAFETY")
    ], validators=[DataRequired()])

    pertence_processo_produtivo = SelectField('Pertence ao processo produtivo?', choices=[
        ("", "Selecione..."),
        ("Sim", "Sim"),
        ("Não", "Não")
    ], validators=[DataRequired()])

    local_especifico = StringField('Descreva mais especificamente o Local', validators=[DataRequired()])
    aplicabilidade = StringField('Aplicabilidade (função do bem)', validators=[DataRequired()])
    valor = StringField('Valor (Se proposta)')
    submit = SubmitField('Enviar Requisição')


class EngAbertaForm(FlaskForm):
    observacao = TextAreaField('Observação', validators=[DataRequired()])
    pr_number = StringField('Número da PR', validators=[DataRequired()])
    submit = SubmitField('Registrar ENG Aberta')
    

class RejeitarForm(FlaskForm):
    motivo = TextAreaField("Motivo da Rejeição", validators=[DataRequired()])
    submit = SubmitField("Rejeitar")