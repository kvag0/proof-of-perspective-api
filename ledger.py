import hashlib
import json
from time import time
from pymongo import DESCENDING

class Ledger:
    def __init__(self, mongo_db_client):
        """Inicializa o Ledger, conectando-se à coleção no MongoDB."""
        self.collection = mongo_db_client.pov_db.ledger
        # Garante que a coleção tem um índice para buscas rápidas
        self.collection.create_index("index")

        # Cria o Bloco Génese se a coleção estiver vazia
        if self.collection.count_documents({}) == 0:
            genesis_block = {
                "index": 0,
                "timestamp": time(),
                "payload": "Genesis Block",
                "previous_hash": "0"
            }
            # O hash de um dicionário não é guardado, mas sim calculado a partir dele
            # Para o guardar, calculamos e adicionamos ao próprio documento.
            genesis_block["hash"] = self._hash(genesis_block)
            self.collection.insert_one(genesis_block)

    def _get_last_block(self):
        """Encontra o último bloco na corrente, ordenando pelo índice."""
        return self.collection.find_one(sort=[("index", DESCENDING)])

    def _hash(self, block_data):
        """Cria um hash SHA-256 de um bloco."""
        # Remove o campo 'hash' se ele já existir, para não se 'hashear' a si mesmo
        block_data_copy = block_data.copy()
        block_data_copy.pop('hash', None)

        block_string = json.dumps(block_data_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def add_entry(self, payload):
        """Adiciona uma nova entrada (bloco) ao ledger."""
        last_block = self._get_last_block()
        new_block = {
            "index": last_block["index"] + 1,
            "timestamp": time(),
            "payload": payload, # Os dados da nossa transação/evento
            "previous_hash": last_block["hash"]
        }
        new_block["hash"] = self._hash(new_block)

        self.collection.insert_one(new_block)
        print(f"Novo bloco {new_block['index']} adicionado ao ledger.")
        return new_block
