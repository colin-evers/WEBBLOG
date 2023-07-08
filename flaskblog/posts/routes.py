from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from flaskblog import db
from flaskblog.models import Post
from flaskblog.posts.forms import PostForm

posts = Blueprint('posts', __name__)


@posts.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user, teaser_title=form.teaser_title.data, teaser_details=form.teaser_details.data,teaser_caption=form.teaser_caption.data, teaser_img=form.teaser_img.data, teaser_content=form.teaser_content.data, teaser_wkid=form.teaser_wkid.data)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('main.intro'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@posts.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    if len(post.teaser_wkid) != 0:
        weekly = post.teaser_wkid
    else:
        weekly = ""        
    return render_template('post.html', weekly=weekly, title=post.title, post=post)

@posts.route("/embed_viewer/<weekly_id>")
def embed_viewer(weekly_id):
    return render_template('embed_viewer.html', weekly=weekly_id, title="embed viewer")

@posts.route("/detach_viewer/<weekly_id>")
def detach_viewer(weekly_id):
    return render_template('detach_viewer.html', weekly=weekly_id, title="detach viewer")

@posts.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.teaser_title = form.teaser_title.data
        post.teaser_details = form.teaser_details.data
        post.teaser_caption = form.teaser_caption.data
        post.teaser_img = form.teaser_img.data
        post.teaser_content = form.teaser_content.data
        post.teaser_wkid = form.teaser_wkid.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title        
        form.content.data = post.content
        form.teaser_title.data = post.teaser_title
        form.teaser_details.data = post.teaser_details
        form.teaser_caption.data = post.teaser_caption
        form.teaser_img.data = post.teaser_img
        form.teaser_content.data = post.teaser_content
        form.teaser_wkid.data = post.teaser_wkid
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@posts.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main.intro'))
