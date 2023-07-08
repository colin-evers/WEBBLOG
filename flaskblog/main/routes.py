from flask import render_template, request, Blueprint, url_for, redirect, current_app
from flask_login import current_user
from flaskblog.models import Post

main = Blueprint('main', __name__)



#@main.route("/home")
#def home():
#    page = request.args.get('page', 1, type=int)
#    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=4)
#    return render_template('post.html', posts=posts)

@main.route("/intro")
def intro():
    if current_user.is_authenticated:
        return render_template('intro.html')
    else:
        return redirect(url_for('users.index'))

@main.route("/methods")
def methods():
    if current_user.is_authenticated:
        return render_template('methods.html')
    else:
        return redirect(url_for('users.index'))

@main.route("/trades")
def trades():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=4)
        return render_template( 'trades.html', posts=posts)
    else:
        return redirect(url_for('users.index'))

@main.route("/pnl")
def pnl():    
    if current_user.is_authenticated:
        return render_template('pnl.html')
    else:
        return redirect(url_for('users.index'))

@main.route("/about")
def about():
    if current_user.is_authenticated:        
        return render_template('about.html', rp=current_app.root_path, ip=current_app.instance_path, title='About')
    else:
        return redirect(url_for('users.index'))




