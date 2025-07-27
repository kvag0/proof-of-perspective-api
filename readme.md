# API "Prova de Perspectiva" (Proof of Perspective)

Este projeto é um protótipo funcional para uma arquitetura de sistema inovadora, projetada para validar informações com base na diversidade de perspetivas, em vez de um simples voto majoritário. Ele combina uma estratégia de banco de dados híbrido, um ledger de auditoria imutável e um algoritmo de consenso social.

O objetivo principal foi construir e testar a performance e a integridade deste modelo, especialmente ao lidar com dados interconectados e a necessidade de uma trilha de auditoria segura.

---

## 🏛️ Arquitetura e Conceitos Chave

Este projeto assenta em três pilares conceptuais:

### 1. Estratégia de Banco de Dados Híbrido (MongoDB)
Para o MVP, foi utilizado um único banco de dados **MongoDB** que desempenha duas funções:
* **Armazenamento de Documentos:** Guarda os dados principais (utilizadores, propostas) de forma flexível.
* **Simulação de Grafo:** As relações complexas entre os dados (utilizadores que votam em propostas) são exploradas através de consultas nativas do MongoDB, como o operador `$graphLookup`, testando a viabilidade de usar um banco de dados de documentos para consultas de grafo de complexidade moderada.

### 2. Padrão de Ledger "Blockchain-in-a-Box"
Para garantir uma trilha de auditoria imutável e criptograficamente verificável, o sistema implementa um ledger dentro do próprio MongoDB:
* Uma coleção dedicada (`ledger`) regista todas as ações críticas (criação de propostas, votos) em ordem cronológica.
* Cada registo ("bloco") contém um campo `previous_hash`, que armazena o hash SHA-256 do bloco anterior.
* Isto cria uma **cadeia criptográfica** que torna qualquer adulteração de dados passados imediatamente detetável, simulando a propriedade de imutabilidade de uma blockchain sem a sobrecarga de uma rede distribuída.

### 3. Mecanismo de Consenso "Prova de Perspectiva"
O coração do projeto. Este modelo de consenso social não pergunta "quantos concordam?", mas sim "**quais tipos diferentes de perfis concordam?**".
* **Vetor de Perspectiva:** O sistema cria um vetor numérico para cada utilizador, que representa os seus interesses com base no seu histórico de votos em diferentes categorias de conteúdo.
* **Score de Robustez:** Quando uma proposta é validada, o sistema calcula a **distância Euclidiana média** entre os vetores de perspetiva de todos os votantes. Um score alto indica um consenso entre grupos divergentes, tornando a validação mais "robusta" e resistente a conluios ou "bolhas" de opinião.

---

## 🛠️ Tech Stack & Ferramentas

* **Linguagem:** Python
* **Framework:** Flask
* **Banco de Dados:** MongoDB
* **Bibliotecas Python:** `pymongo`, `numpy`, `scipy`
* **Infraestrutura:** Docker e Docker Compose

---

## 📖 Documentação da API (Endpoints)

### Recursos de Utilizadores (`/api/users`)
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/users` | Cria um novo utilizador. |
| `GET` | `/api/users/<username>` | Busca um utilizador pelo nome. |
| `GET` | `/api/users/<username>/perspective` | Calcula e retorna o vetor de perspetiva do utilizador. |

### Recursos de Propostas (`/api/proposals`)
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/proposals` | Cria uma nova proposta. |
| `GET` | `/api/proposals` | Lista todas as propostas. |
| `POST` | `/api/proposals/<id>/vote` | Regista um voto de um utilizador numa proposta. |
| `GET` | `/api/proposals/<id>/related` | Encontra propostas relacionadas com base em votantes em comum. |
| `GET` | `/api/proposals/<id>/robustness` | Calcula o "Score de Robustez" da proposta. |

### Recursos do Ledger (`/api/ledger`)
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/ledger` | Retorna a trilha de auditoria completa e imutável. |

---

## ⚙️ Como Executar o Projeto Localmente

**Pré-requisitos:**
* `pyenv` (recomendado) ou Python 3.11+
* Docker e Docker Compose

**Passos:**

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/proof-of-perspective-api.git](https://github.com/seu-usuario/proof-of-perspective-api.git)
    cd proof-of-perspective-api
    ```

2.  **Configure o Ambiente Python:**
    ```bash
    pyenv local 3.11.8
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    python3 -m pip install -r requirements.txt
    ```
    
4.  **Inicie os serviços com Docker Compose:**
    ```bash
    docker compose up --build
    ```
    O servidor da API estará a correr em `http://localhost:5001` e o MongoDB em `http://localhost:27017`.