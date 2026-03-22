# Condo Geo Crawler (Google Places API)

Script em Python para mapear condomínios residenciais horizontais e exportar coordenadas geográficas em CSV.

## 1) Rodando com Docker (recomendado)

### Pré-requisitos

- Docker
- Docker Compose

### Subir a interface web

```bash
# 1) Defina sua chave (Linux/Mac)
export GOOGLE_MAPS_API_KEY="SUA_CHAVE_AQUI"

# 2) Suba o container
docker compose up --build
```

Acesse: `http://localhost:8501`

### Derrubar o ambiente

```bash
docker compose down
```

## 2) Como conseguir a `GOOGLE_MAPS_API_KEY` (passo a passo)

1. Acesse o **Google Cloud Console**: `https://console.cloud.google.com/`.
2. Crie (ou selecione) um projeto.
3. Ative o faturamento do projeto (Google Maps Platform exige billing ativo).
4. No menu de APIs, habilite pelo menos:
   - **Places API**
   - (Opcional para evoluções) **Geocoding API**
5. Vá em **APIs & Services > Credentials**.
6. Clique em **Create credentials > API key**.
7. Restrinja a chave (fortemente recomendado):
   - **Application restrictions**: IPs (backend) ou HTTP referrers (frontend).
   - **API restrictions**: permita apenas APIs que você usa (ex.: Places API).
8. Copie a chave gerada e use como variável de ambiente `GOOGLE_MAPS_API_KEY`.

> Dica de segurança: nunca versionar a chave no Git. Use `.env`/variáveis de ambiente.

## 3) Instalação local (sem Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) API Key

Você pode informar a chave de duas formas:

1. Por variável de ambiente:

```bash
export GOOGLE_MAPS_API_KEY="SUA_CHAVE_AQUI"
```

2. Por argumento na execução (CLI):

```bash
python condo_geo_crawler.py --api-key "SUA_CHAVE_AQUI"
```

## 5) Execução via linha de comando (crawler)

```bash
python condo_geo_crawler.py
```

Gera o arquivo `condominios_alto_padrao.csv` com as colunas:

- Nome do Condomínio
- Cidade
- Endereço Completo
- Latitude
- Longitude

## 6) Interface simples para visualizar condomínios

Rode a interface web (Streamlit):

```bash
streamlit run condo_viewer_app.py
```

A interface permite:

- Rodar a coleta com API Key, cidades e termos.
- Visualizar os resultados em mapa e tabela.
- Copiar a lista de georreferências em formato CSV (campo de texto).
- Baixar o CSV com um clique.

## 7) Personalizar cidades e termos no CLI

```bash
python condo_geo_crawler.py \
  --cities "Maringá" "Londrina" "Sarandi" \
  --terms "Condomínio Fechado" "Condomínio Residencial" "Resort Residence" "Loteamento Fechado" \
  --output "meus_condominios.csv"
```

## 8) Observações sobre qualidade

O script usa uma heurística para priorizar condomínios horizontais e reduzir ruído de:

- habitação popular (`Minha Casa Minha Vida`, `MCMV`)
- imóveis/comércios (`edifício comercial`, `office`, `shopping`)

Essa filtragem é ajustável dentro do arquivo `condo_geo_crawler.py` nas listas:

- `PALAVRAS_POSITIVAS`
- `PALAVRAS_NEGATIVAS`
- `TIPOS_NEGATIVOS`
