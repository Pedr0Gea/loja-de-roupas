from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Boolean
from flask_migrate import Migrate
import os

# Inicializa o aplicativo Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://ip-ou-nome-da-maquina/roupas?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '35634651a' 
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Cria a pasta "instance" se não existir
os.makedirs(app.instance_path, exist_ok=True)

# Inicializa o gerenciador de login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de Usuário
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Modelo de Roupa
class Roupa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False) 
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    publica = db.Column(db.Boolean, default=False)

    usuario = db.relationship('Usuario', backref='roupas')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form.get('login')
        if login in banned_logins:
            flash('Este login está banido')
            return redirect(url_for('register'))
        existing_user = Usuario.query.filter_by(login=login).first()
        if existing_user:
            flash('Esse login já está em uso. Escolha outro.', 'error')
            return redirect(url_for('register'))
        senha = request.form.get('senha')
        hashed_senha = generate_password_hash(senha)
        novo_usuario = Usuario(login=login, senha=hashed_senha)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Registro criado com sucesso!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        senha = request.form.get('senha')
        usuario = Usuario.query.filter_by(login=login).first()
        if usuario and check_password_hash(usuario.senha, senha):
            login_user(usuario)
            return redirect(url_for('index'))
        else:
            flash('Login ou senha incorretos')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add():
    roupa_nome = request.form.get('roupa')
    preco = request.form.get('preco')
    publica = request.form.get('publica') == 'on'

    # Verifica se o nome e o preço foram preenchidos
    if roupa_nome and preco:
        try:
            preco = int(preco)  # Converte o preço para inteiro
            nova_roupa = Roupa(
                nome=roupa_nome, 
                preco=float(preco),
                usuario_id=current_user.id, 
                publica=publica
            )
            db.session.add(nova_roupa)
            db.session.commit()
            flash('Roupa adicionada com sucesso!')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar roupa: {str(e)}', 'error')
            print(f"Erro ao adicionar roupa: {str(e)}")  # Exibe erro no terminal
    else:
        flash('Nome e preço são obrigatórios!', 'error')

    return redirect(url_for('index'))


@app.route('/')
@login_required
def index():
    roupas_publicas = Roupa.query.filter_by(publica=True).all()
    roupas_privadas = Roupa.query.filter_by(usuario_id=current_user.id, publica=False).all()
    return render_template('index.html', roupas_publicas=roupas_publicas, roupas_privadas=roupas_privadas)


@app.route('/delete_selected', methods=['POST'])
@login_required
def delete_selected():
    roupa_ids = request.form.getlist('roupas') 
    if roupa_ids:
        Roupa.query.filter(Roupa.id.in_(roupa_ids)).delete(synchronize_session=False)
        db.session.commit()
    return redirect('/')

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        return redirect('/')
    
    usuarios = Usuario.query.all()
    return render_template('admin.html', usuarios=usuarios)

@app.route('/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.is_admin:
        usuario = Usuario.query.get(id)
        if usuario:
            db.session.delete(usuario)
            db.session.commit()
    return redirect('/admin')

# Lista de logins banidos
banned_logins = []

@app.route('/ban_user/<login>', methods=['POST'])
@login_required
def ban_user(login):
    if current_user.is_admin:
        banned_logins.append(login)
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
