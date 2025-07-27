FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN python3 -m pip install -r requirements.txt
# O comando para iniciar será dado pelo docker-compose,
# mas podemos ter um aqui como padrão.
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
