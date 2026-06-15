# GerbiTools

Ferramentas pessoais para jogadores, num site só.

**https://gerbitools-production-c9b9.up.railway.app**

## Ferramentas

- **Dead Island Collectables** — checa quais Personal IDs você coletou no save do Dead Island 1 DE
- **Steam Platinum Viewer** — varre sua biblioteca Steam e mostra conquistas + tempo HLTB por jogo

## Rodando localmente

```
pip install -r backend/requirements.txt
```

Crie um `.env` na raiz:

```
STEAM_API_KEY=sua_chave_aqui
```

```
cd backend
uvicorn main:app --reload
```

## Estrutura

FastAPI no backend, HTML/JS puro no frontend. As ferramentas ficam em `tools/` como submódulos do Git — o backend importa delas dinamicamente sem instalar como pacotes.
