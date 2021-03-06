import datetime
import json

from flask import jsonify
from flask import abort
from flask import request
import app.models as models
from app import db
from app.main.login.views import valid_token
from app.models import Article, Relation, Price
from . import article

article_schema = models.ArticleSchema()
articles_schema = models.ArticleSchema(many=True)
child_schema = models.ChildSchema()
relations_schema = models.RelationSchema(many=True)
relation_schema = models.RelationSchema()
prices_schema = models.PriceSchema(many=True)


@article.route('/article/<int:article_id>', methods=['PUT'])
@valid_token()
@models.validate_json
@models.validate_schema(article_schema)
def api_update_article(article_id):
    if request.method == 'PUT':
        old_article = db.session.query(Article).get(article_id)
        if old_article is None:
            abort(400)
        req = request.get_json()
        old_article.title = req['title']
        old_article.content = req['content']
        old_article.cover_url = req['cover_url']
        old_article.summary = req['summary']
        db.session.add(old_article)
        # db.session.commit()
        old_price = db.session.query(Price).filter_by(article_id=article_id).all()
        for i in old_price:
            db.session.delete(i)
        # db.session.commit()
        old_children = db.session.query(Relation).filter_by(parent=article_id).all()
        for i in old_children:
            db.session.delete(i)
        # db.session.commit()
        if 'price' in req and len(req['price']) != 0:

            price = req['price']
            for i in price:
                price = Price(article_id=req['id'], site_url=i['site_url'],
                              site_name=i['site_name'], price=i['price'])
                db.session.add(price)
                # try:
                #     db.session.commit()
                # except Exception, e:
                #     return e.message
        if 'children' in req and len(req['children']) != 0:
            children = req['children']
            for i in children:
                child = Relation(parent=req['id'], child=i['id'])
                db.session.add(child)
                # try:
                #     db.session.commit()
                # except Exception, e:
                #     return e.message
        try:
            db.session.commit()
        except Exception, e:
            return e.message

        return jsonify({"success": True})


@article.route('/article/<int:article_id>', methods=['DELETE'])
def api_article_by_id(article_id):
    if request.method == 'DELETE':
        article = db.session.query(Article).get(article_id)
        price = db.session.query(Price).filter_by(article_id=article_id).all()
        relation = db.session.query(Relation).filter_by(parent=article_id).all()
        db.session.delete(article)
        for i in price:
            db.session.delete(i)
        for i in relation:
            db.session.delete(i)
        try:
            db.session.commit()
        except Exception, e:
            return e.message
        return jsonify({"success": True})


@article.route('/article/<int:article_id>', methods=['GET'])
def api_delete_by_id(article_id):
    if request.method == 'GET':
        article = Article.query.get(article_id)
        if article is None:
            abort(404)

        child = Article.get_article_child(article_id)
        article.children = child
        price = Article.get_article_price(article_id)
        article.price = price.data
        article.good = article.good + 1
        db.session.add(article)
        db.session.commit()
        return article_schema.jsonify(article)


@article.route('/article', methods=['POST'])
@valid_token()
@models.validate_json
@models.validate_schema(article_schema)
def api_add_article():
    if request.method == 'POST':
        req = request.get_json()
        insert = Article(title=req['title'], content=req['content'],
                         good=0, cover_url=req['cover_url'],
                         category=req['category'],
                         create_time=datetime.datetime.now(),
                         summary=req['summary'])
        db.session.add(insert)
        db.session.commit()
        article_id = insert.id
        if 'price' in req and len(req['price']) != 0:
            price = req['price']
            for i in price:
                insert = Price(site_name=i['site_name'],
                               price=i['price'],
                               site_url=i['site_url'],
                               article_id=article_id)
                db.session.add(insert)
            try:
                db.session.commit()
            except Exception, e:
                db.session.rollback()
                return e.message
        if 'children' in req and len(req['children']) != 0:
            child = req['children']
            for i in child:
                insert = Relation(parent=article_id, child=i['id'])
                db.session.add(insert)
            try:
                db.session.commit()
            except Exception, e:
                db.session.rollback()
                return e.message

        return jsonify({"code": 201, "success": True})


@article.route('/article', methods=['GET'])
def api_articles():
    if request.method == 'GET':
        limit = request.args.get('limit')
        offset = request.args.get('offset')
        order_by = request.args.get('order')
        pagination, offset = models.set_pagination(limit, offset, Article, order_by)
        articles = pagination.items
        pages_num = pagination.pages
        for i in articles:
            i.price = []
            i.children = []
        result = articles_schema.dump(articles)
        return jsonify({'data': result.data, 'total_page': pages_num, 'offset': offset})
