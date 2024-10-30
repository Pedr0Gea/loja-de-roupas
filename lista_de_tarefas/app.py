from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Boolean
from flask_migrate import Migrate
import os
# Remove-Item -Recurse -Force venv
# python -m venv venv
#.\venv\Scripts\activate
# pip install Flask Flask-SQLAlchemy Flask-Login Flask-Migrate Werkzeug
# flask db init
# flask db migrate -m "Mensagem da migração"
# flask db upgrade

# Inicializa o aplicativo Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'tarefas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '35634651a'  # Alterar para uma chave secreta mais forte
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

# Modelo de Tarefa
class Tarefa(db.Model):
    __tablename__ = 'tarefa'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    usuario_id = Column(Integer, db.ForeignKey('usuario.id'), nullable=True)
    publica = Column(Boolean, default=False)

    # Relacionamento com Usuario
    usuario = db.relationship('Usuario', backref='tarefas')

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
    tarefa_nome = request.form.get('tarefa')
    publica = request.form.get('publica') == 'on'

    if tarefa_nome:
        nova_tarefa = Tarefa(nome=tarefa_nome, usuario_id=current_user.id, publica=publica)
        db.session.add(nova_tarefa)
        db.session.commit()
    return redirect('/')

@app.route('/')
@login_required
def index():
    tarefas_publicas = Tarefa.query.filter_by(publica=True).all()
    tarefas_privadas = Tarefa.query.filter_by(usuario_id=current_user.id, publica=False).all()
    return render_template('index.html', tarefas_publicas=tarefas_publicas, tarefas_privadas=tarefas_privadas)

@app.route('/delete_selected', methods=['POST'])
@login_required
def delete_selected():
    tarefa_ids = request.form.getlist('tarefas')
    if tarefa_ids:
        Tarefa.query.filter(Tarefa.id.in_(tarefa_ids)).delete(synchronize_session=False)
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
