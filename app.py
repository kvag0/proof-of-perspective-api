import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv
from ledger import Ledger # Importa a nossa nova classe

load_dotenv()

app = Flask(__name__)

# Configuração do Cliente MongoDB
client = MongoClient(os.getenv('MONGO_URI'))

# Instancia o nosso Ledger com o cliente do MongoDB
ledger = Ledger(client)

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