# urbansense-api

API em FastAPI que recebe uma foto e detecta **lixo** (`Trash`) e **buracos** (`pothole`) usando um modelo YOLO11 (`best.pt`) treinado especificamente para essas duas classes.

## Como funciona

1. O cliente envia uma imagem via `multipart/form-data` para `POST /predict`.
2. A API carrega o modelo `best.pt` uma única vez em memória (na primeira requisição) e o reutiliza nas chamadas seguintes.
3. A imagem é processada pelo YOLO11, que retorna as detecções (classe, confiança e coordenadas da caixa delimitadora).
4. A API responde com um JSON indicando se foi encontrado lixo e/ou buraco na imagem, além da lista detalhada de detecções.

### Estrutura do projeto

```
urbansense-api/
├── app/
│   ├── main.py      # endpoints da API (FastAPI)
│   ├── model.py     # carregamento do modelo YOLO (singleton)
│   └── schemas.py   # modelos de resposta (Pydantic)
├── best.pt           # pesos do modelo YOLO11 (classes: Trash, pothole)
└── requirements.txt
```

## Pré-requisitos

- Python 3.12+

## Inicializando o projeto

Clone o repositório e entre na pasta do projeto:

```bash
git clone git@github.com:HenriqueDiass/urbansense-api.git
cd urbansense-api
```

Crie o ambiente virtual e instale as dependências:

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Linux / macOS**
```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

## Rodando o servidor

**Windows (PowerShell)**
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Linux / macOS**
```bash
./.venv/bin/python -m uvicorn app.main:app --reload
```

O servidor sobe em `http://127.0.0.1:8000`. A documentação interativa (Swagger) fica disponível em `http://127.0.0.1:8000/docs`.

## Endpoints

### `GET /health`

Verifica se a API está no ar.

```json
{"status": "ok"}
```

### `POST /predict`

Recebe uma imagem e retorna as detecções de lixo/buraco.

**Parâmetros:**
- `file` (obrigatório, multipart) — imagem em `jpeg`, `png`, `webp` ou `bmp`.
- `confidence` (opcional, query) — limiar mínimo de confiança (0 a 1, padrão `0.25`).

**Exemplo:**

```bash
curl -X POST "http://127.0.0.1:8000/predict" -F "file=@foto.jpg"
```

**Resposta:**

```json
{
  "has_trash": true,
  "has_pothole": false,
  "detections": [
    {
      "label": "Trash",
      "confidence": 0.87,
      "box": [12.3, 45.1, 300.2, 210.9]
    }
  ]
}
```

- `has_trash` — `true` se alguma detecção de lixo passou do limiar de confiança.
- `has_pothole` — `true` se alguma detecção de buraco passou do limiar de confiança.
- `detections` — lista com todas as detecções, incluindo classe, confiança e coordenadas `[x1, y1, x2, y2]` da caixa na imagem original.
