import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv
from ledger import Ledger
from bson import ObjectId
from time import time

load_dotenv()

app = Flask(__name__)

# Configuração do Cliente MongoDB
client = MongoClient(os.getenv('MONGO_URI'))

db = client.get_database() 

# Instancia o nosso Ledger com o cliente do MongoDB
ledger = Ledger(client)

# --- DEFINIÇÃO DAS COLEÇÕES ---
users_collection = db.users
proposals_collection = db.proposals

@app.route('/api')
def hello():
    return jsonify({"message": "Bem-vindo à API Proof of Perspective!"})

# Endpoint para ver o ledger inteiro
@app.route('/api/ledger', methods=['GET'])
def get_ledger():
    # find() retorna um cursor. Convertemos para uma lista.
    # O campo _id do Mongo não é serializável para JSON, por isso o removemos.
    chain = list(ledger.collection.find({}, {'_id': 0}))
    return jsonify(chain), 200

# Endpoint de teste para adicionar uma nova entrada
@app.route('/api/ledger/add', methods=['POST'])
def add_test_entry():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Corpo do pedido vazio"}), 400

    new_block = ledger.add_entry(data)
    # Removemos o _id do Mongo para a resposta
    new_block.pop('_id', None)
    return jsonify(new_block), 201

# --- ROTAS DE UTILIZADORES ---

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or 'username' not in data:
        return jsonify({"error": "O nome de utilizador é obrigatório"}), 400

    # Verifica se o utilizador já existe
    if users_collection.find_one({"username": data['username']}):
        return jsonify({"error": "Nome de utilizador já existe"}), 409

    # Insere o novo utilizador no banco de dados
    result = users_collection.insert_one(data)

    # Busca o documento recém-criado para retornar na resposta
    new_user = users_collection.find_one({"_id": result.inserted_id})

    # Converte o ObjectId para string para ser compatível com JSON
    new_user['_id'] = str(new_user['_id'])

    return jsonify(new_user), 201

@app.route('/api/users/<username>', methods=['GET'])
def get_user(username):
    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"error": "Utilizador não encontrado"}), 404

    user['_id'] = str(user['_id'])
    return jsonify(user), 200


# --- ROTAS DE PROPOSTAS ---

@app.route('/api/proposals', methods=['POST'])
def create_proposal():
    data = request.get_json()
    required_fields = ['title', 'content', 'author_username']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Campos 'title', 'content', e 'author_username' são obrigatórios"}), 400

    # Verifica se o autor da proposta existe
    author = users_collection.find_one({"username": data['author_username']})
    if not author:
        return jsonify({"error": "Utilizador autor não encontrado"}), 404

    # Cria o documento da proposta
    proposal_doc = {
        "title": data['title'],
        "content": data['content'],
        "author_username": data['author_username'],
        "image_url": data.get('image_url', ''), # O URL da imagem é opcional
        "timestamp": time(),
        "votes": [] # Lista para guardar os votos futuros
    }

    # 1. Insere a proposta na sua coleção
    result = proposals_collection.insert_one(proposal_doc)
    new_proposal_id = result.inserted_id

    # 2. Cria o payload para o nosso ledger imutável
    ledger_payload = {
        "action": "CREATE_PROPOSAL",
        "proposal_id": str(new_proposal_id),
        "author": data['author_username'],
        "title": data['title']
    }

    # 3. Adiciona a entrada ao ledger
    ledger.add_entry(ledger_payload)

    # Retorna a proposta recém-criada
    proposal_doc['_id'] = str(new_proposal_id)
    return jsonify(proposal_doc), 201

@app.route('/api/proposals', methods=['GET'])
def get_proposals():
    proposals_cursor = proposals_collection.find()
    proposals_list = []
    for proposal in proposals_cursor:
        proposal['_id'] = str(proposal['_id'])
        proposals_list.append(proposal)
    return jsonify(proposals_list), 200