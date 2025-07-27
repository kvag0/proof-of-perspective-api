import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv
from ledger import Ledger
from bson import json_util, ObjectId
import json
from time import time
import numpy as np

# DEFINIR CATEGORIAS DE CONTEÚDO GLOBAIS
CONTENT_CATEGORIES = ["Tecnologia", "Arte", "Sociedade", "Ciência", "Desporto"]

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

@app.route('/api/users/<username>/perspective', methods=['GET'])
def get_user_perspective(username):
    # Verifica se o utilizador existe
    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"error": "Utilizador não encontrado"}), 404

    # Encontra todas as propostas em que este utilizador votou
    voted_proposals = list(proposals_collection.find({"votes": username}))

    if not voted_proposals:
        # Se o utilizador não votou em nada, o seu vetor é neutro (zeros)
        perspective_vector = np.zeros(len(CONTENT_CATEGORIES)).tolist()
        return jsonify({
            "username": username,
            "vote_count": 0,
            "perspective_vector": perspective_vector
        }), 200

    # Calcula o vetor: conta quantos votos foram para cada categoria
    vote_counts = np.zeros(len(CONTENT_CATEGORIES))
    for proposal in voted_proposals:
        try:
            category_index = CONTENT_CATEGORIES.index(proposal['category'])
            vote_counts[category_index] += 1
        except (ValueError, KeyError):
            # Ignora propostas com categorias inválidas ou em falta
            continue

    # Normaliza o vetor (para que a sua "magnitude" seja 1)
    # Isto transforma a contagem bruta numa "direção" de interesse.
    norm = np.linalg.norm(vote_counts)
    if norm == 0:
        normalized_vector = vote_counts # Evita divisão por zero
    else:
        normalized_vector = vote_counts / norm

    return jsonify({
        "username": username,
        "vote_count": len(voted_proposals),
        "perspective_vector_raw": vote_counts.tolist(), # Contagem bruta
        "perspective_vector": normalized_vector.tolist() # Vetor normalizado (a "direção")
    }), 200

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
        "category": data['category'], # Adiciona a categoria ao documento
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
        "title": data['title'],
        "category": data['category'] 
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

@app.route('/api/proposals/<proposal_id>/vote', methods=['POST'])
def vote_on_proposal(proposal_id):
    try:
        data = request.get_json()
        username = data.get('username')

        if not username:
            return jsonify({"error": "O nome de utilizador (username) é obrigatório"}), 400

        # Validações de Lógica de Negócio
        proposal = proposals_collection.find_one({"_id": ObjectId(proposal_id)})
        if not proposal:
            return jsonify({"error": "Proposta não encontrada"}), 404

        voter = users_collection.find_one({"username": username})
        if not voter:
            return jsonify({"error": "Utilizador votante não encontrado"}), 404

        if proposal['author_username'] == username:
            return jsonify({"error": "Não é permitido votar na sua própria proposta"}), 403

        if username in proposal['votes']:
            return jsonify({"error": "Utilizador já votou nesta proposta"}), 409

        # Operação de Escrita
        proposals_collection.update_one(
            {"_id": ObjectId(proposal_id)},
            {"$addToSet": {"votes": username}}
        )

        ledger_payload = {
            "action": "VOTE_CAST",
            "proposal_id": proposal_id,
            "voter_username": username,
            "timestamp": time()
        }
        ledger.add_entry(ledger_payload)

        return jsonify({"message": f"Voto de '{username}' registado com sucesso!"}), 200

    except Exception as e:
        return jsonify({'message': 'Erro ao processar o voto', 'error': str(e)}), 500

@app.route('/api/proposals/<proposal_id>/related', methods=['GET'])
def get_related_proposals(proposal_id):
    try:
        # 1. Primeiro, garantimos que a proposta inicial existe.
        start_proposal = proposals_collection.find_one({"_id": ObjectId(proposal_id)})
        if not start_proposal:
            return jsonify({"error": "Proposta inicial não encontrada"}), 404

        # Pega na lista de votantes da proposta inicial.
        start_voters = start_proposal.get('votes', [])
        if not start_voters:
            return jsonify([]), 200 # Retorna lista vazia se não houver votantes para comparar

        # 2. Este é o nosso "Pipeline de Agregação" com o $graphLookup.
        pipeline = [
            {
                # Etapa 1: $graphLookup - A exploração do grafo.
                '$graphLookup': {
                    'from': 'proposals',             # Começa a busca na coleção de propostas.
                    'startWith': start_voters,       # O ponto de partida são os votantes da nossa proposta.
                    'connectFromField': 'votes',     # "Saia" de um documento pelo seu campo 'votes'.
                    'connectToField': 'votes',       # "Conecte-se" a outro documento pelo seu campo 'votes'.
                    'as': 'related_proposals_data',  # Guarde os resultados da travessia aqui.
                    'maxDepth': 1,                   # Explore apenas um nível de conexão para ser eficiente.
                }
            },
            {
                # Etapa 2: $match - Filtra os resultados para encontrar apenas as propostas relacionadas.
                '$match': {
                    # A condição é que a lista de votantes tenha pelo menos um em comum com a nossa lista inicial.
                    'votes': {'$in': start_voters},
                    # E excluímos a própria proposta inicial do resultado.
                    '_id': {'$ne': ObjectId(proposal_id)}
                }
            },
            {
                # Etapa 3: $limit - Limita o número de recomendações (boa prática).
                '$limit': 5
            }
        ]

        related_proposals_cursor = proposals_collection.aggregate(pipeline)

        # Converte o cursor do MongoDB para uma lista Python
        results = list(related_proposals_cursor)

        # Usa o json_util para converter a lista para uma string JSON que lida corretamente com ObjectId
        json_results = json_util.dumps(results)

        # Carregamos a string JSON de volta para um objeto Python que o Flask pode usar
        return json.loads(json_results), 200

    except Exception as e:
        return jsonify({'message': 'Erro ao buscar propostas relacionadas', 'error': str(e)}), 500
